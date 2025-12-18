import re
import argparse
import pathlib
import importlib
import logging
import uuid
import email.message
from smtplib import SMTP

import numpy
from astropy.io import fits
import astropy.table

import desidb.db
from desidb.logger import DBLogger


# ======================================================================

class EntryExistsError(RuntimeError):
    def __init__( self, *args, **kwargs ):
        super().__init__( self, *args, **kwargs )


class TopLevelEntryExistsError(EntryExistsError):
    def __init__( self, *args, **kwargs ):
        super().__init__( self, *args, **kwargs )


class SchemaMismatchError(RuntimeError):
    def __init__( self, data, *args, **kwargs ):
        """data needs to be a dictionary:
        filepath : String, full path to the file read (or array of strings)
        missingdatablock : set of data blocks (BinTable HDU extension names)
                           expected to be found in the data that weren't there
        extradatablock : set of data blocks (BinTable HDU extension names)
                         that were in the data that we didn't expect
        models:
          <key is database model that was expected>
          <value is a dictionary>:
              datablock : Name of HDU that (mostly) corresponds to the table, or None if not present
                         (Note: even if none, one of the other HDUs may have this table in moved).
              missingfromdata  : set of columsn that were in the database table but not the HDU
              indatabutshouldnotbe: set of columns that were in the HDU but aren't in the database table
              coltypemismatch : set of columns where HDU and table didn't match
              datatypes : dictionary of column -> types from the FITS file
              modeltypes : dictionary of column -> type from database
        """
        super().__init__( *args, **kwargs )
        self.data = data


# ======================================================================

class RRVersion:
    verparse = re.compile( r'^([0-9]+)\.([0-9]+)\.([0-9]+)(\.(.*))?$' )

    def __init__( self, versionstring ):
        match = self.verparse.search( versionstring )
        if match is None:
            raise RuntimeError( f'Failed to parse redrock version string {versionstring}' )
        self.major = int(match.group(1))
        self.minor = int(match.group(2))
        self.stepping = int(match.group(3))
        self.tag = match.group(5)


    def get_tiles_hdu_map( self ):
        """A mapping of stuff in the FITS files to the database model.

        This started fairly clean, and has become kind of a mess because
        of having to deal with various special-case schema changes.

        It's a dictionary.  Each key is one of the database models:
        Redshifts, Fibermap, ExpFibermap, or TSNR2.  The Values are:
            hdu : name of the HDU that has the information for this table
            duplicates : 'error', 'skip', 'update'
            skipcheck : see _actually_load for documentation
            ignore : set of columns that should be ignored (expect all others; 'expect' should be None)
            expect : set of columns that we should expect (ignore all others; 'ignore' should be None)
            map : dictionary.  Keys are Django columns, values are dictionary:
                matchcolumn : column in main HDU for this table that must match:
                otherhdumatchcolumn : column in other HDU
                otherhdu : name of other HDU
                column : column in other HDU with information
            deduplication : if not None, then the pandas dataframe that results
                            will be grouped on this list of columns
                            (aggregating by 'first')

        All FITS column names have been converted to lower case.

        WARNING : I'm using I-don't-think-it's-documetented behavior of
        Django here.  I told Django to have a unique constraint on
        cumultile, but of course we define that as a foreign key to a
        whole *table*.  I know from looking at what happened to the
        database that this meant the cretion of a column cumultile_id,
        but I am not 100% sure we can actually depend on Django always
        doing this.  Given everything I'm trying to knit together
        (Django, Pandas, SQLalchemy so we can use Pandas to_sql, raw
        PostgresSQL since pandas doesn't support updating exiting table
        rows with data in the dataframe), there's probably not a "right"
        way to even do this.  (Well, other than rolling your own and not
        using big existing libraries....)

        """

        # SAD NOTE
        # There are files with the same RRVER header file that have different schema :(

        # Default: expect full schema match
        hdumap = {
            'TilesRedshifts': { 'hdu': 'REDSHIFTS',
                                'skipcheck': None,
                                'duplicates': 'error',
                                'customfields': [ 'cumultile_id' ]
            },
            'TilesFibermap': { 'hdu': 'FIBERMAP',
                               'skipcheck': None,
                               'duplicates': 'update',
                               'conflict_update': "(cumultile_id,targetid)",
                               'customfields': [ 'cumultile_id' ]
            },
            'TilesExpFibermap': { 'hdu': 'EXP_FIBERMAP',
                                  'skipcheck': [ 'tileid',  'petal_loc', 'night', 'expid' ],
                                  'duplicates': 'skip',
                                  'customfields': [ 'cumultile_id' ]
                                 },
            'TilesTSNR2': { 'hdu': 'TSNR2',
                            'skipcheck': None,
                            'duplicates': 'error',
                            'customfields': [ 'cumultile_id' ]
                           }
        }
        for key, val in hdumap.items():
            val['ignore'] = set()
            val['expect'] = None
            val['map'] = {}

        if ( self.major == 0 ) and ( self.minor < 14 ):
            raise ValueError( f"Don't know how to deal with redrock version {self.major}.{self.minor}" )
        if ( self.major == 0 ) and ( self.minor == 14 ):
            return {
                'TilesRedshifts': {
                    'hdu' : 'ZBEST',
                    'skipcheck': None,
                    'duplicates': 'error',
                    'ignore': { 'numexp', 'numtile' },
                    'expect' : None,
                    'customfields': [ 'cumultile_id' ],
                    'map': {}
                },
                'TilesFibermap': {
                    'hdu' : 'FIBERMAP',
                    'skipcheck': None,
                    'duplicates': 'update',
                    'conflict_update': "(cumultile_id,targetid)",
                    'ignore' : { 'fiber_ra', 'fiber_dec', 'fiber_x', 'fiber_y', 'delta_x', 'delta_y',
                                 'night', 'exptime', 'num_iter', 'psf_to_fiber_specflux', 'expid',
                                 'fiberstatus', 'mjd' },
                    'expect' : None,
                    'customfields': [ 'cumultile_id' ],
                    'map': {
                        'coadd_numexp': {
                            'matchcolumn' : ['targetid'],
                            'otherhdumatchcolumn' : ['targetid'],
                            'otherhdu' : 'ZBEST',
                            'column': 'numexp',
                            'typeconv': numpy.int16
                            },
                        'coadd_numtile': {
                            'matchcolumn' : ['targetid'],
                            'otherhdumatchcolumn' : ['targetid'],
                            'otherhdu' : 'ZBEST',
                            'column' : 'numtile',
                            'typeconv': numpy.int16
                        }
                    },
                    'deduplication': [ 'targetid' ]
                },
                'TilesExpFibermap': {
                    'hdu' : 'FIBERMAP',
                    'skipcheck': [ 'tileid', 'petal_loc', 'night', 'expid' ],
                    'duplicates': 'skip',
                    'ignore' : None,
                    'expect' :  { 'targetid', 'tileid', 'petal_loc', 'fiber',
                                  'fiber_ra', 'fiber_dec', 'fiber_x', 'fiber_y', 'delta_x', 'delta_y',
                                  'night', 'exptime', 'num_iter', 'psf_to_fiber_specflux', 'expid',
                                  'fiberstatus', 'mjd' },
                    'customfields': [ 'cumultile_id' ],
                    'map' : {}
                }
            }

        return hdumap


    def get_healpix_hdu_map( self ):
        hdumap = {
            'HealpixRedshifts': { 'hdu': 'REDSHIFTS',
                                  'skipcheck': None,
                                  'duplicates': 'error' },
            'HealpixFibermap': { 'hdu': 'FIBERMAP',
                                 'skipcheck': None,
                                 'duplicates': 'error' },
            'HealpixExpFibermap': { 'hdu': 'EXP_FIBERMAP',
                                    'skipcheck': None,
                                    'duplicates': 'skip' },
            'HealpixTSNR2': { 'hdu': 'TSNR2',
                              'skipcheck': None,
                              'duplicates': 'error' }
        }
        for key, val in hdumap.items():
            val['ignore'] = set()
            val['expect'] = None
            val['map'] = {}
        return hdumap


# ======================================================================

class DESILoader:
    emailto = "raknop@lbl.gov"
    emailfrom = "raknop@lbl.gov"

    datematch = re.compile( r'^[0-9]{8}$' )
    numbersmatch = re.compile( r'^[0-9]+$' )

    def __init__( self, desi_release, donotload=False, noemail=False ):
        self.desi_release = desi_release
        self.desi_release_module = importlib.import_module( desi_release )
        self.basetiledir = pathlib.Path( f'/data/spectro/redux/{desi_release}/tiles/cumulative' )
        self.basehealpixdir = ( pathlib.Path( f'/data/spectro/redux/{desi_release}/healpix' )
                                if desi_release != 'daily' else None )
        self.donotload = donotload
        self.noemail = noemail


    def _read_and_verify_fits( self, filepath, hdumap, rrver ):
        # I feel a bit queasy about this
        typematch = {
            'bool'  : [ 'boolean' ],
            'uint8' : [ 'smallint' ],
            'float32' : [ 'real' ],
            'float64' : [ 'double precision' ],
            'int16' : [ 'smallint' ],
            'int32' : [ 'integer' ],
            'int64' : [ 'bigint' ],
            'object' : [ ( 'ARRAY', 'character varying' ) ]
        }

        bintables = {}
        with fits.open( filepath ) as hdulist:
            for hdu in hdulist:
                if isinstance( hdu, fits.hdu.BinTableHDU ):
                    if hdu.name in bintables.keys():
                        raise RuntimeError( f"Extension {hdu.name} shows up in the FITS file "
                                            f"{filepath} more than once." )
                    bintables[ hdu.name ] = astropy.table.Table( hdu.data )

        parseinfo = {
            'filepath': str(filepath),
            'rrver' : ( rrver.major, rrver.minor, rrver.stepping ),
            'missingdatablock': set(),
            'extradatablock': set(),
            'models': {}
        }
        schemaok = True

        # Make sure we found all expected HDUs
        for modeltable in hdumap.keys():
            if hdumap[modeltable]['hdu'] not in bintables.keys():
                parseinfo['missingdatablock'].add( hdumap[modeltable]['hdu'] )
                schemaok = False

        # Make sure there aren't unexpected HDUs
        for bintable in bintables.keys():
            if bintable not in [ hdumap[modeltable]['hdu'] for modeltable in hdumap.keys() ]:
                parseinfo['extradatablock'].add( bintable )
                schemaok = False

        # Wrangle around the input tables using the "map" information in hdumap.
        # This is because earlier versions of Redrock had some stuff in different HDUs from later
        # versions, and we want to have a single schema for the model....
        for modeltable in hdumap.keys():
            hdu = hdumap[modeltable]['hdu']
            for col, mapping in hdumap[modeltable]['map'].items():
                if mapping['otherhdu'] not in bintables.keys():
                    parseinfo['missingdatablock'].add( mapping['otherhdu'] )
                    schemaok = False
                    continue
                maintable = bintables[hdu]
                othertable = bintables[mapping['otherhdu']][ mapping['otherhdumatchcolumn'], mapping['column'] ]
                maintable = astropy.table.join( maintable, othertable,
                                                keys_left=mapping['matchcolumn'],
                                                keys_right=mapping['otherhdumatchcolumn'] )
                bintables[hdu] = maintable

        # Deduplicate if necessary
        for modeltable in hdumap.keys():
            modmap = hdumap[modeltable]
            if 'deduplication' in modmap.keys():
                bintables[ modmap['hdu'] ] = astropy.table.unique( bintables[ modmap['hdu'] ],
                                                                   keys=modmap['deduplication'] )

        # Verify that either all expected columns are there or no ignored columns are there,
        #   and that dataytypes between FITS and Django match
        for modeltable in hdumap.keys():
            model = getattr( self.desi_release_module, modeltable )
            model._load_table_meta()
            if hdumap[modeltable]['hdu'] not in bintables.keys():
                # This will have been flagged as an error in parseinfo above, so just skip and punt
                continue
            tab = bintables[ hdumap[modeltable]['hdu'] ]
            parseinfo['models'][modeltable] = {
                'datablock' : hdumap[modeltable]['hdu'],
                'missingfromdata': set(),
                'indatabutshouldnotbe': set(),
                'coltypemismatch': set(),
                'datatypes': {},
                'modeltypes': {}
            }
            smm = parseinfo['models'][modeltable]

            # Go through the FITS columns and make sure that we expect each one of them,
            # and that the data types match.
            # sys.stderr.write( f'Working on {modeltable}; ignore is {hdumap[modeltable]["ignore"]}\n' )
            for datacol in tab.columns:
                datatype = str( tab[datacol].dtype )
                if datatype not in typematch.keys():
                    raise RuntimeError( f"Unknown type for FITS column {datacol}: {datatype}" )
                smm['datatypes'][datacol] = datatype

                if ( hdumap[modeltable]['ignore'] is not None ) and ( datacol in hdumap[modeltable]['ignore'] ):
                    continue
                if ( hdumap[modeltable]['expect'] is not None ) and ( datacol not in hdumap[modeltable]['expect'] ):
                    continue

                if str(datacol).lower() not in model._tablemeta:
                    smm['missingfromodel'].add( datacol )
                    schemaok = False
                    continue

                pgtype = model._tablemeta[datacol]['data_type']
                pgelemtype = model._tablemeta[datacol]['element_type']

                ok = False
                for possible_pgtype in typematch[ datatype ]:
                    if isinstance( possible_pgtype, tuple ):
                        if ( pgtype == possible_pgtype[0] ) and ( pgelemtype == possible_pgtype[1] ):
                            ok = True
                            break
                    elif pgtype == possible_pgtype:
                        ok = True
                        break
                if not ok:
                    smm['coltypemismatch'].add( datacol )
                    schemaok = False

            # Go through the Model and check which things are missing from the FITS file
            # (Don't have to check datatypes, as we've already looked at all FITS columns.)
            # This won't be considered an error unless the column is not nullable.
            for field in model._tablemeta:
                pgtype = model._tablemeta[field]['data_type']
                elemtype = model._tablemeta[field]['element_type']

                if elemtype is not None:
                    smm['modeltypes'][field.name] = pgtype
                else:
                    smm['modeltypes'][field.name] = ( pgtype, elemtype )

                tabfield = str(field).upper()

                if field in hdumap[modeltable]['customfields']:
                    if tabfield in tab.columns:
                        smm['indatabutshouldnotbe'].add( tabfield )
                        schemaok = False
                    continue

                if tabfield not in tab.columns:
                    # TODO : worry that 'YES'/'NO' is not universal psycopg / postgres!!
                    smm['missingfromdata'].add( tabfield )
                    if model._tablemeta[field]['is_nullable'] != 'YES':
                        schemaok = False

        # Raise an exception if there was a fatal parseinfo
        if not schemaok:
            # import pdb; pdb.set_trace()
            raise SchemaMismatchError( parseinfo )

        return hdumap, bintables, parseinfo

    # ======================================================================
    # NOTE : I've got the fact that the root directory is /data
    # (mounted from /global/cfs/cdirs/desi/spectro/redux)
    #  hardcoded below!  This is suboptimal.

    def import_tile_night_petal( self, tileid, night, petal ):
        """Try to import a redrock-*.fits or zbest-*.fits file into the database.

        * tileid, night, petal are integers

        Returns a dictionary with various information about HDUs form the
        fits files, columns not found in the fits file, and datatypes.
        Raises a SchemaMismatchError if expected HDUs were missing from the
        FITS file, if there were unexpected HDUs in the FITS file, if there
        were unexpected columns in the fits files, if necessary columns in
        the FITS file were missing, or if the datatype from the FITS file
        didn't match what was expected from the model.

        """
        direc = self.basetiledir / str(tileid) / str(night)
        if not direc.is_dir():
            raise FileNotFoundError( f"{str(direc)} isn't an existing directory" )
        zbest = direc / f'zbest-{petal}-{tileid}-thru{night}.fits'
        redrock = direc / f'redrock-{petal}-{tileid}-thru{night}.fits'
        filetoread = None
        if redrock.is_file():
            filetoread = redrock
        elif zbest.is_file():
            filetoread = zbest
        else:
            raise FileNotFoundError( f"Did not find {redrock} or {zbest}" )

        if str(filetoread)[0:6] != "/data/":
            raise ValueError( f'Trying to reading file {str(filetoread)} which doesn\'t start with /data/!' )
        relfilepath = str(filetoread)[6:]

        with fits.open( filetoread, memmap=False ) as hdul:
            rrver = RRVersion( hdul[0].header['RRVER'] )
        hdumap = rrver.get_tiles_hdu_map()

        with desidb.db.DBCon() as dbcon:
            baseclass = getattr( self.desi_release_module, 'CumulativeTiles' )
            baseclass._load_table_meta( dbcon=dbcon )

            if not self.donotload:
                res = dbcon.execute( f"SELECT * FROM {baseclass.__tableschema__}.{baseclass.__tablename__} "
                                     f"WHERE tileid=%(tileid)s AND petal=%(petal)s AND night=%(night)s" )
                if len(res) > 0:
                    raise TopLevelEntryExistsError( f'Entry already exists: tile={tileid}, '
                                                    f'petal={petal}, night={night}' )

            hdumap, bintables, parseinfo = self._read_and_verify_fits( filetoread, hdumap, rrver )

            if not self.donotload:
                # I'm assuming that no other process is loading at the same time.  We checked way up
                # at the top that this entry didn't already exist.  If multiple processes are doing
                # this at once, I'm writing in a race condition here....
                cumultile = baseclass( id=uuid.uuid4(), tileid=tileid, petal=petal, night=night,
                                       filename=relfilepath, dbcon=dbcon )
                cumultile.insert( nocommit=True, refresh=False )

                for modeltable in hdumap.keys():
                    model = getattr( self.desi_release_module, modeltable )
                    tab = bintables[ hdumap[modeltable]['hdu'] ]

                    data = { str(col).lower(): list( tab['col'] ) for col in tab.columns }
                    data['cumultile_id'] = [ cumultile.id ] * len(tab)

                    if hdumap[modeltable]['duplicates'] == 'update':
                        upsert = True
                        assume_no_conflict = False
                    elif hdumap[modeltable]['duplicates'] == 'skip':
                        upsert = False
                        assume_no_conflict = False
                    elif hdumap[modeltable]['duplicates'] == 'error':
                        upsert = False
                        # OK, this is weird, but if you want an error on conflict, it turns
                        #  out you have to say upsert=False and assume_no_conflict=True.
                        assume_no_conflict = True

                    model.bulk_insert_or_upsert( data, dbcon=dbcon, upsert=upsert,
                                                 assume_no_conflict=assume_no_conflict, nocommit=True )

                dbcon.commit()

        # Done.  Return any mismatches form the parsing.
        return parseinfo

    # ======================================================================

    def import_healpix( self, survey, program, healpix ):
        # The error checking that's in import_tile_night_petal is not here
        #   because currently the healpix hdu map doesn't have any ignore or expect
        #   set, so we are assuming that the schema is always the same.
        direc = self.basehealpixdir / survey / program / str(healpix // 100) / str(healpix)
        if not direc.is_dir():
            raise FileNotFoundError( f"{str(direc)} isn't an existing directory" )
        filetoread = direc / f'redrock-{survey}-{program}-{healpix}.fits'
        if not filetoread.is_file():
            raise FileNotFoundError( f"{str(filetoread)} isn't an existing regular file" )

        if str(filetoread)[0:6] != "/data/":
            raise ValueError( f'Trying to reading file {str(filetoread)} which doesn\'t start with /data/!' )
        relfilepath = str(filetoread)[6:]

        with fits.open( filetoread, memmap=False ) as hdul:
            rrver = RRVersion( hdul[0].header['RRVER'] )
        hdumap = rrver.get_healpix_hdu_map()

        with desidb.db.DBCon() as dbcon:
            baseclass = getattr( self.desi_release_module, 'Healpix' )
            baseclass._load_table_meta( dbcon=dbcon )

            if not self.donotload:
                res = dbcon.execute( f"SELECT * FROM {baseclass.__tableschema__}.{baseclass.__tablename__} "
                                     f"WHERE healpix=%(healpix)s AND survey=%(survey)s AND program=%(program)s" )
                if len(res) > 0:
                    raise TopLevelEntryExistsError( f'Entry already exists: healpix={healpix}, '
                                                    f'survey={survey}, program={program}' )

            hdumap, bintables, parseinfo = self._read_and_verify_fits( filetoread, hdumap, rrver )

            if not self.donotload:
                healpixobj = baseclass( id=uuid.uuid4(), healpix=healpix, survey=survey, program=program,
                                        filename=relfilepath, dbcon=dbcon )
                healpixobj.insert( nocommit=True, refresh=False )

                for modeltable in hdumap.keys():
                    model = getattr( self.desi_release_module, modeltable )
                    tab = bintables[ hdumap[modeltable]['hdu'] ]

                    data = { str(col).lower(): list( tab['col'] ) for col in tab.columns }
                    data['healpix_id'] = [ healpixobj.id ] * len(tab)

                    if hdumap[modeltable]['duplicates'] == 'update':
                        upsert = True
                        assume_no_conflict = False
                    elif hdumap[modeltable]['duplicates'] == 'skip':
                        upsert = False
                        assume_no_conflict = False
                    elif hdumap[modeltable]['duplicates'] == 'error':
                        upsert = False
                        assume_no_conflict = True

                    model.bulk_insert_or_upsert( data, dbcon=dbcon, upsert=upsert,
                                                 assume_no_conflict=assume_no_conflict, nocommit=True )

                dbcon.commit()

            # Done.  Return any mismatches form the parsing.
            return parseinfo

    # ======================================================================

    def build_schema_mismatch_info( self, data, loginfo=[] ):
        loginfo = loginfo.copy()
        loginfo.append( f'DESI Release: {str(self.desi_release)}' )
        loginfo.append( f'Redrock version: {data["rrver"]}' )
        if len( data['missingdatablock'] ) > 0:
            loginfo.append( f"Missing HDUs: {data['missingdatablock']}" )
        if len( data['extradatablock'] ) > 0:
            loginfo.append( f"Unexpected HDUs: {data['extradatablock']}" )
        for model, smm in data['models'].items():
            if ( ( len( smm['indatabutshouldnotbe'] ) > 0 ) or
                 ( len( smm['missingfromdata'] ) > 0 ) or
                 ( len( smm['coltypemismatch'] ) > 0 ) ):
                loginfo.append( f"MODEL: {model}" )
                if len( smm['indatabutshouldnotbe'] ) > 0:
                    loginfo.append( f"...Unknown data columns: {smm['indatabutshouldnotbe']}" )
                if len( smm['missingfromdata'] ) > 0:
                    loginfo.append( f"...(Non-fatal) missing data columns: {smm['missingfromdata']}" )
                if len( smm['coltypemismatch'] ) > 0:
                    for col in smm['coltypemismatch']:
                        loginfo.append( f"...{col} datatype mismatch; "
                                        f"is {smm['datatypes'][col]} in the data, and "
                                        f"{smm['modeltypes'][col]} in the model." )
        return loginfo


    # ======================================================================

    def print_schema_mismatch( self, data, loginfo=[], subject=None ):
        loginfo = self._build_schema_mismatch_info( data, loginfo=loginfo )
        DBLogger.error( "\n".join( loginfo ) + "\n" )
        if ( self.emailto is not None ) and ( not self.noemail ):
            emailmsg = email.message.EmailMessage()
            emailmsg['To'] = self.emailto
            emailmsg['From'] = self.emailfrom
            if subject is not None:
                emailmsg['Subject'] = subject
            else:
                emailmsg['Subject'] = "Message from DesiDB importredrock command"
            emailmsg.set_content( "\n".join( loginfo ) + "\n" )
            with SMTP( "smtp.lbl.gov" ) as smtp:
                smtp.send_message( emailmsg )

    # ======================================================================

    def load_tile_night_directory( self, tile, night ):
        for petal in range (0,10):
            try:
                # Assumes that we've mounted /global/cfs/cdirs/desi to /data
                data = self.import_tile_night_petal( tile, night, petal )
            except SchemaMismatchError as e:
                loginfo = [ f"Schema mismatch error in tile {tile}, night {night}, petal {petal}" ]
                self.print_schema_mismatch( e.data, loginfo, subject="DesiDB Schema Mismatch" )
                raise e
            except FileNotFoundError as e:
                DBLogger.warning( f"FileNotFoundError for tile {tile}, night {night}, "
                                  f"petal {petal}, skipping: {str(e)}" )
                continue
            except TopLevelEntryExistsError:
                DBLogger.warning( f"cumulative_tiles already exists for tile {tile} "
                                  f"night {night}, petal {petal}, skipping." )
                continue
            DBLogger.info( f"Imported tile {tile:6d}, night {night}, petal {petal}" )
            DBLogger.debug( "\n".join( self._build_schema_mismatch_info( data ) ) )


    # ======================================================================

    def load_tile_directory( self, tile, nightge=None, nightlt=None ):
        tiledir = self.basetiledir / str(tile)
        if not tiledir.is_dir():
            raise RuntimeError( f"Tiles directory {str(tiledir)} isn't a directory" )
        for night in tiledir.iterdir():
            if not self.datematch.search( night.name ):
                DBLogger.warning( "Subdirectory {night.name} doesn't match yyyymmdd, skippng" )
            else:
                nightge = 0 if nightge is None else int(nightge)
                nightlt = 9999999 if nightlt is None else nightlt
                if ( int(night.name) < nightge ) or ( int(night.name) >= nightlt ):
                    continue
                self.load_tile_night_directory( tile, int(night.name) )


    # ======================================================================

    def load_all_tiles_newer_than( self, nightge, nightlt=None, onlytile=None ):
        if nightlt is None:
            nightlt = 999999
        toload = []
        DBLogger.debug( "Going through all tile directories to find yyyymmdd subdirectories..." )
        for tiledir in self.basetiledir.iterdir():
            if self.numbersmatch.search( tiledir.name ) and tiledir.is_dir():
                itile = int( tiledir.name )
                # ****
                # This next bit is for debugging only, to skip most directories for speed
                if ( onlytile is not None ) and ( itile != int(onlytile) ):
                    continue
                # ****
                for night in tiledir.iterdir():
                    if self.datematch.search( night.name ):
                        inight = int( night.name )
                        if inight >= nightge and inight < nightlt:
                            toload.append( ( inight, itile ) )
        DBLogger.debug( f"Made list of {len(toload)} yyyymmdd directories." )

        # Go from older nights to newer nights
        toload.sort()

        DBLogger.info( f"Loading {len(toload)} total tile/night directories" )
        ndone = 0
        for inight, itile in toload:
            DBLogger.info( f"Loaded {ndone} of {len(toload)} tile/nights" )
            self.load_tile_night_directory( itile, inight )
            ndone += 1

    # ======================================================================

    def load_healpixd100_directory( self, healpixd100, survey, program ):
        if self.basehealpixdir is None:
            raise FileNotFoundError( f"Healpix directories aren't known for {self.desi_release}" )
        direc = self.basehealpixdir / survey / program / str(healpixd100)
        if not direc.is_dir():
            raise FileNotFoundError( f"Healpix directory {str(direc)} isn't a directory" )
        for healpix in direc.iterdir():
            if not self.numbersmatch.search( healpix.name ):
                DBLogger.warning( "subdirectory {str(healpix)} isn't all numbers, skipping" )
            else:
                try:
                    data = self.import_healpix( survey, program, int(healpix.name) )
                except SchemaMismatchError as e:
                    loginfo = [ f"Schemamismatch error for surve {survey}, "
                                f"program {program}, healpix {healpix.name}" ]
                    self._print_schema_mismatch( e.data, loginfo, subject="DesiDB Schema Mismatch" )
                    raise e
                except FileNotFoundError:
                    DBLogger.error( f"Healpix FITS redrock file for survey={survey}, program={program}, "
                                    f"healpix={healpix.name} not found!  Skipping." )
                    continue
                except TopLevelEntryExistsError:
                    DBLogger.warning( f"Healpix entry already exists: survey={survey}, program={program}, "
                                      f"healpix={healpix.name}.  Skipping." )
                    continue
                DBLogger.info( f"Imported healpix {healpix.name}, survey {survey}, program {program}" )
                DBLogger.debug( "\n".join( self._build_schema_mismatch_info( data ) ) )
        DBLogger.info( f"Imported healpix//100 directory {str(direc)}" )

    # =====================================================================

    def load_healpix_survey_program( self, survey, program ):
        direc = self.basehealpixdir / survey / program
        if not direc.is_dir():
            raise FileNotFoundError( f"Healpix program directory {str(direc)} isn't a directory." )
        for healpixd100 in direc.iterdir():
            if self.numbersmatch.search( healpixd100.name ) and ( int(healpixd100.name) < 1000 ):
                self.load_healpixd100_directory( healpixd100.name, survey, program )
                DBLogger.info( f"Imported healpix program directory {direc}" )
            else:
                DBLogger.warning( f"Subdirectory {str(healpixd100)} isn't a number 0-999, skipping." )


    # =====================================================================

    def load_healpix_survey( self, survey ):
        direc = self.basehealpixdir / survey
        if not direc.is_dir():
            raise FileNotFoundError( "Healpix survey directory {str(direc)} isn't a direcgtory" )
        for programdir in direc.itercir():
            if programdir.is_dir():
                self.load_healpix_survey_program( survey, programdir.name )


# ======================================================================

def main():
    parser = argparse.ArgumentParser( 'importredrock.py',
                                      description="Import redrock files into desidb-rr",
                                      formatter_class=argparse.ArgumentDefaultsHelpFormatter )
    parser.add_argument( '-r', '--release', required=True, help="DESI Relese to load (daily, loa, etc.)" )
    parser.add_argument( '-t', '--tile', default=None, type=int,
                         help="Load all petals of all nights of this tile from <base>/tiles/cumulative" )
    parser.add_argument( '-n', '--tiles-newer', default=None, type=int,
                         help=( "yyyymmdd ; load all tiles in subdirectories of this date or newer (>=). "
                                "With --tile, only in that tile subdirectory otherwise for all tiles" ) )
    parser.add_argument( '-o', '--tiles-older', default=None, type=int,
                         help=( "yyyymmdd ; use with --tiles-newer ; only load tiles in subdirectories "
                                "that are older than this date (<)." ) )
    parser.add_argument( "-a", '--auto-newer', default=False, action='store_true',
                         help=( "Automatcially load everything that is in a yyyymmdd directory that's "
                                "equal to or newer than the latest yyyymmdd found in the database. "
                                "Do not combine with --tiles-newer or --tile, OK to use with --tiles-older" ) )
    parser.add_argument( '-s', '--survey', default=None, type=str,
                         help="Load healpix for this survey (e.g. 'main', 'sv1', 'sv2', or 'sv3')" )
    parser.add_argument( '-p', '--program', default=None, type=str,
                         help="Load healpix for this program (requires --survey; default: all for survey)" )
    parser.add_argument( '-d', '--healpixd100', default=None, type=int,
                         help=( 'Healpix / 100 (e.g. 381 loads all healpix 38100 through 38199 ). '
                                'requires --survey and --program; default: load all' ) )
    parser.add_arguments( '-v', '--verbose', action='store_true', default=False,
                          help="Show debug log info" )
    parser.add_argument( '--verify-only', default=False, action='store_true',
                         help="Don't actually load, just verify that files work." )
    parser.add_argument( '--no-email', default=False, action='store_true',
                         help="Don't send email on failures." )

    args = parser.parse_args()

    if args.verbose:
        DBLogger.setLevel( logging.DEBUG )
    else:
        DBLogger.setLevel( logging.INFO )

    loader = DESILoader( args.release, args.verify_only, args.no_email )

    if args.tile is not None:
        loader.load_tile_directory( args.tile, args.tiles_newer )
    else:
        if args.auto_newer or ( args.tiles_newer is not None ):
            if args.tiles_newer is not None:
                if args.options_newer:
                    raise ValueError( "Don't use --auto-newer and --tiles-newer togehter." )
                startdate = int( args.tiles_newer )
            else:
                raise NotImplementedError( "Rob, you need to implement this." )
            enddate = None if args.tiles_older is None else int( args.tiles_older )
            loader.load_all_tiles_newer_than( startdate, enddate )

    if args.survey is not None:
        if args.program is not None:
            if args.healpixd100 is not None:
                loader.load_healpixd100_directory( args.healpixd100, args.survey, args.program )
            else:
                loader.load_healpix_survey_program( args.survey, args.program )
        else:
            loader.load_healpix_survey( args.survey )


# ======================================================================

if __name__ == "__main__":
    main()
