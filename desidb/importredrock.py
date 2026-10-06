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
from desidb.importtools import EntryExistsError, TopLevelEntryExistsError, SchemaMismatchError

# ======================================================================

class RRVersion:
    verparse = re.compile( r'^([0-9]+)\.([0-9]+)\.([0-9]+)(\.(.*))?$' )
    filenameparse = re.compile( r'.*thru([0-9]{8}).fits' )
    
    def __init__( self, versionstring, filepath ):
        match = self.verparse.search( versionstring )
        if match is None:
            raise RuntimeError( f'Failed to parse redrock version string {versionstring}' )
        self.major = int(match.group(1))
        self.minor = int(match.group(2))
        self.stepping = int(match.group(3))
        self.tag = match.group(5)

        # Because there are schema changes without the version changing, we have to
        #   know the date of the file so we can code that in.  WARNING THIS WILL BREAK
        #   NEXT TIME YOU IMPORT A RELEASE.  At that point, everything will have the
        #   same schema, so any detection based on date of exposure is going to be wrong.
        #   Probably at the code that gates on night, also add a gate on RRVer Figure it out then.
        mat = self.filenameparse.search( str(filepath) )
        if mat is None:
            DBLogger.warning( f"Failed to parse {filepath} for .*thru([0-9]{9}.fits'" )
            self.night_from_filename = 0
        else:
            self.night_from_filename = int( mat.group(1) )

    # @classmethod def version_compare( versionstring ):
    

    def get_tiles_hdu_map( self ):
        """A mapping of stuff in the FITS files to the database model.

        This started fairly clean, and has become kind of a mess because
        of having to deal with various special-case schema changes.

        It's a dictionary.  Each key is one of the database models:
        Redshifts, Fibermap, ExpFibermap, or TSNR2.  The Values are:
            hdu : name of the HDU that has the information for this table
            duplicates : 'error', 'skip', 'update'
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
                                'duplicates': 'error',
                                'customfields': [ 'cumultile_id' ]
            },
            'TilesFibermap': { 'hdu': 'FIBERMAP',
                               'duplicates': 'update',
                               'conflict_update': "(cumultile_id,targetid)",
                               'customfields': [ 'cumultile_id' ]
            },
            'TilesExpFibermap': { 'hdu': 'EXP_FIBERMAP',
                                  'duplicates': 'skip',
                                  'customfields': [ 'cumultile_id' ]
                                 },
            'TilesTSNR2': { 'hdu': 'TSNR2',
                            'duplicates': 'error',
                            'customfields': [ 'cumultile_id' ]
                           }
        }
        for key, val in hdumap.items():
            val['rename'] = None
            val['ignore'] = None
            val['expect'] = None
            val['typeconv'] = None
            val['map'] = {}

        if ( self.major == 0 ) and ( self.minor < 14 ):
            raise ValueError( f"Don't know how to deal with redrock version {self.major}.{self.minor}" )
        if ( self.major == 0 ) and ( self.minor == 14 ):
            return {
                'TilesRedshifts': {
                    'hdu' : 'ZBEST',
                    'duplicates': 'error',
                    'rename': {},
                    'typeconv': { 'ZWARN': '>i4',
                                  'COEFF': '>f4',
                                  'ZERR': '>f4',
                                  'CHI2': '>f4',
                                  'NCOEFF': '>i2',
                                  'NPIXELS': '>i4',
                                  'DELTACHI2': '>f4'
                                 },
                    'ignore': { 'NUMEXP', 'NUMTILE' },
                    'expect' : None,
                    'customfields': [ 'cumultile_id' ],
                    'map': {}
                },
                'TilesFibermap': {
                    'hdu' : 'FIBERMAP',
                    'duplicates': 'update',
                    'conflict_update': "(cumultile_id,targetid)",
                    'rename': { 'MJD': 'MEAN_MJD' },
                    'typeconv': { 'RELEASE': '>i2' },
                    'ignore': { 'FIBERFLUX_IVAR_G', 'FIBERFLUX_IVAR_R', 'FIBERFLUX_IVAR_Z', 'NIGHT',
                                'HPXPIXEL', 'NUMTARGET', 'BLOBDIST', 'EXPID', 'FIBERSTATUS', 'NUM_ITER',
                                'FIBER_RA', 'FIBER_DEC', 'FIBER_X', 'FIBER_Y', 'DELTA_X', 'DELTA_Y',
                                'EXPTIME', 'PSF_TO_FIBER_SPECFLUX' },
                    'expect' : None,
                    'customfields': [ 'cumultile_id' ],
                    'map': {
                        'COADD_NUMEXP': {
                            'matchcolumn' : 'TARGETID',
                            'otherhdumatchcolumn' : 'TARGETID',
                            'otherhdu' : 'ZBEST',
                            'column': 'NUMEXP',
                            'typeconv': '>i2',
                            },
                        'COADD_NUMTILE': {
                            'matchcolumn' : 'TARGETID',
                            'otherhdumatchcolumn' : 'TARGETID',
                            'otherhdu' : 'ZBEST',
                            'column' : 'NUMTILE',
                            'typeconv': '>i2',
                        }
                    },
                    'deduplication': [ 'TARGETID' ]
                },
                'TilesExpFibermap': {
                    'hdu' : 'FIBERMAP',
                    'duplicates': 'skip',
                    'rename': {},
                    'typeconv': {},
                    'ignore' : None,
                    'expect' :  { 'TARGETID', 'TILEID', 'PETAL_LOC', 'FIBER', 'DEVICE_LOC',
                                  'FIBER_RA', 'FIBER_DEC', 'FIBER_X', 'FIBER_Y', 'DELTA_X', 'DELTA_Y',
                                  'NIGHT', 'EXPTIME', 'NUM_ITER', 'PSF_TO_FIBER_SPECFLUX', 'EXPID',
                                  'FIBERSTATUS', 'MJD' },
                    'customfields': [ 'cumultile_id' ],
                    'map' : {}
                }
            }
        # THIS IS INCREDIBLY ANNOYING.
        # Images on 2026-01-20 with RRVER '0.21.0.dev1160' had PSF_TO_FIBER_SPECFLUX as TFORM D
        # Images on 2026-01-25 with RRVER '0.21.0.dev1160' had PSF_TO_FIBER_SPECFLUX as TFORM E
        # COULDN'T YOU AT LEAST BUMP THE VERSION IF YOU CHANGE THE SCHEMA??????????????
        else:
            if self.night_from_filename > 20260120:
                hdumap['TilesExpFibermap']['typeconv'] = { 'PSF_TO_FIBER_SPECFLUX': '>f8' }

            if self.night_from_filename > 20260219:
                # I tried to migrate the database to conver to the new types,
                #   but Postgres yelled at me about an underflow in one zerr value.
                # So, just keep them at their bigger sizes, and convert the new data.
                hdumap['TilesRedshifts']['typeconv'] = { 'ZWARN': '>i8',
                                                         'COEFF': '>f8',
                                                         'ZERR': '>f8',
                                                         'CHI2': '>f8',
                                                         'NCOEFF': '>i8',
                                                         'NPIXELS': '>i8',
                                                         'DELTACHI2': '>f8'
                                                        }

        return hdumap


    def get_healpix_hdu_map( self ):
        hdumap = {
            'HealpixRedshifts': { 'hdu': 'REDSHIFTS',
                                  'duplicates': 'error',
                                  'customfields': [ 'healpix_id' ],
                                 },
            'HealpixFibermap': { 'hdu': 'FIBERMAP',
                                 'duplicates': 'error',
                                 'customfields': [ 'healpix_id' ],
                                },
            'HealpixExpFibermap': { 'hdu': 'EXP_FIBERMAP',
                                    'duplicates': 'skip',
                                    'customfields': [ 'healpix_id' ],
                                   },
            'HealpixTSNR2': { 'hdu': 'TSNR2',
                              'duplicates': 'error',
                              'customfields': [ 'healpix_id' ],
                             }
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
    releaseverify = re.compile( r'^[a-z0-9_]+$' )

    def __init__( self, desi_release, donotload=False, noemail=False ):
        if not self.releaseverify.search( desi_release ):
            raise ValueError( f"Invalid release {desi_release}, must just be [a-z0-9_]+" )
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
            '>f4' : [ 'real' ],
            '>f8' : [ 'double precision' ],
            '>i2' : [ 'smallint' ],
            '>i4' : [ 'integer' ],
            '>i8' : [ 'bigint' ],
            '<U1' : [ 'character varying' ],
            '<U2' : [ 'character varying' ],
            '<U3' : [ 'character varying' ],
            '<U4' : [ 'character varying' ],
            '<U6' : [ 'character varying' ],
            '<U8' : [ 'character varying' ],
            '<U20' : [ 'character varying' ],
            '<U22' : [ 'text' ]
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
            'rrver' : ( rrver.major, rrver.minor, rrver.stepping, rrver.tag ),
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

        # Rename columns and convert types as necessary
        for modeltable in hdumap.keys():
            if any( hdumap[modeltable][i] is not None for i in [ 'rename', 'typeconv' ] ):
                for modeltable in hdumap.keys():
                    hdu = hdumap[modeltable]['hdu']
                    if hdumap[modeltable]['rename'] is not None:
                        for oldname, newname in hdumap[modeltable]['rename'].items():
                            bintables[hdu].rename_column( oldname, newname )
                    if hdumap[modeltable]['typeconv'] is not None:
                        for col, typ in hdumap[modeltable]['typeconv'].items():
                            bintables[hdu][col] = bintables[hdu][col].astype( typ )
                
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
                if col in maintable.columns:
                    raise RuntimeError( f"{col} already in maintable.columns" )
                if mapping['column'] in maintable.columns:
                    raise RuntimeError( "I just generally don't know how to cope." )
                othertable = bintables[mapping['otherhdu']][ mapping['otherhdumatchcolumn'], mapping['column'] ]
                maintable = astropy.table.join( maintable, othertable,
                                                keys_left=mapping['matchcolumn'],
                                                keys_right=mapping['otherhdumatchcolumn'] )
                # astropy seems to have left in the _1 and _2 versions of the join key,
                #  which seems perverse to me
                if mapping['matchcolumn'] == mapping['otherhdumatchcolumn']:
                    maintable.remove_column( f'{mapping["matchcolumn"]}_2' )
                    maintable.rename_column( f'{mapping["matchcolumn"]}_1', mapping["matchcolumn"] )
                if mapping['column'] != col:
                    maintable.rename_column( f'{mapping["column"]}', col )

                if mapping['typeconv'] is not None:
                    maintable[col] = maintable[col].astype( mapping['typeconv'] )
                
                bintables[hdu] = maintable

        # Deduplicate if necessary
        for modeltable in hdumap.keys():
            modmap = hdumap[modeltable]
            if 'deduplication' in modmap.keys():
                bintables[ modmap['hdu'] ] = astropy.table.unique( bintables[ modmap['hdu'] ],
                                                                   keys=modmap['deduplication'] )

        # Verify that either all expected columns are there or no ignored columns are there,
        #   and that dataytypes between FITS and Django match.
        modeltables = {}
        for modeltable in hdumap.keys():
            model = getattr( self.desi_release_module, modeltable )
            model._load_table_meta()
            if hdumap[modeltable]['hdu'] not in bintables.keys():
                # This will have been flagged as an error in parseinfo above, so just skip and punt
                continue
            # Make a copy because are going to modify it, and at least sometimes the
            #   same HDU is used for more than one model table.
            tab = astropy.table.Table( bintables[ hdumap[modeltable]['hdu'] ] )
            modeltables[modeltable] = tab
            parseinfo['models'][modeltable] = {
                'datablock' : hdumap[modeltable]['hdu'],
                'missingfromdata': set(),
                'nonnullmissingfromdata': set(),
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
                if len( tab[datacol].shape) > 1:
                    nelems = tab[datacol].shape[1]
                else:
                    nelems = None
                if datatype not in typematch.keys():
                    raise RuntimeError( f"Unknown type for FITS column {datacol}: {datatype}" )
                smm['datatypes'][datacol] = datatype

                if ( hdumap[modeltable]['ignore'] is not None ) and ( datacol in hdumap[modeltable]['ignore'] ):
                    continue
                if ( hdumap[modeltable]['expect'] is not None ) and ( datacol not in hdumap[modeltable]['expect'] ):
                    continue

                if str(datacol).lower() not in model._tablemeta:
                    smm['indatabutshouldnotbe'].add( datacol )
                    schemaok = False
                    continue

                pgtype = model._tablemeta[datacol.lower()]['data_type']
                pgelemtype = model._tablemeta[datacol.lower()]['element_type']

                ok = False
                for possible_pgtype in typematch[ datatype ]:
                    if nelems is not None:
                        if (pgtype == 'ARRAY' ) and ( pgelemtype == possible_pgtype ):
                            # WORRY : verify length of array.  I don't see that in the Column Meta
                            ok = True
                            break
                    elif pgtype == possible_pgtype:
                        ok = True
                        break
                if not ok:
                    smm['coltypemismatch'].add( datacol )
                    schemaok = False

            # Drop ignored columns
            if hdumap[modeltable]['ignore'] is not None:
                curcols = list( tab.columns )
                for col in hdumap[modeltable]['ignore']:
                    if col in curcols:
                        tab.remove_column( col )

            # Drop not-expected columns:
            if hdumap[modeltable]['expect'] is not None:
                curcols = list( tab.columns )
                for col in curcols:
                    if col not in hdumap[modeltable]['expect']:
                        tab.remove_column( col )

            # Go through the Model and check which things are missing from the FITS file
            # (Don't have to check datatypes, as we've already looked at all FITS columns.)
            # This won't be considered an error unless the column is not nullable.
            for field in model._tablemeta:
                pgtype = model._tablemeta[field]['data_type']
                elemtype = model._tablemeta[field]['element_type']

                if elemtype is not None:
                    smm['modeltypes'][field] = pgtype
                else:
                    smm['modeltypes'][field] = ( pgtype, elemtype )

                tabfield = str(field).upper()

                if field in hdumap[modeltable]['customfields']:
                    if tabfield in tab.columns:
                        smm['indatabutshouldnotbe'].add( tabfield )
                        schemaok = False
                    continue

                if tabfield not in tab.columns:
                    # TODO : worry that 'YES'/'NO' is not universal psycopg / postgres!!
                    if model._tablemeta[field]['is_nullable'] != 'YES':
                        smm['nonnullmissingfromdata'].add( tabfield )
                        schemaok = False
                    else:
                        smm['missingfromdata'].add( tabfield )

        # Raise an exception if there was a fatal parseinfo
        if not schemaok:
            # import pdb; pdb.set_trace()
            raise SchemaMismatchError( parseinfo )

        return hdumap, modeltables, parseinfo

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
            rrver = RRVersion( hdul[0].header['RRVER'], filetoread )
        hdumap = rrver.get_tiles_hdu_map()

        with desidb.db.DBCon() as dbcon:
            baseclass = getattr( self.desi_release_module, 'CumulativeTiles' )
            baseclass._load_table_meta( dbcon=dbcon )

            if not self.donotload:
                rows, cols = dbcon.execute( f"SELECT * FROM {baseclass.__tableschema__}.{baseclass.__tablename__} "
                                            f"WHERE tileid=%(tileid)s AND petal=%(petal)s AND night=%(night)s",
                                            { 'tileid': tileid, 'petal': petal, 'night': night } )
                if len(rows) > 0:
                    raise TopLevelEntryExistsError( f'Entry already exists: tile={tileid}, '
                                                    f'petal={petal}, night={night}' )

            hdumap, bintables, parseinfo = self._read_and_verify_fits( filetoread, hdumap, rrver )

            if not self.donotload:
                # I'm assuming that no other process is loading at the same time.  We checked way up
                # at the top that this entry didn't already exist.  If multiple processes are doing
                # this at once, I'm writing in a race condition here....
                cumultile = baseclass( id=uuid.uuid4(), tileid=tileid, petal=petal, night=night,
                                       filename=relfilepath, dbcon=dbcon )
                cumultile.insert( nocommit=True, refresh=False, dbcon=dbcon )

                for modeltable in hdumap.keys():
                    model = getattr( self.desi_release_module, modeltable )
                    tab = bintables[ modeltable ]

                    data = { str(col).lower(): list( tab[col] ) for col in tab.columns }
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

                    q = model.bulk_insert_or_upsert( data, dbcon=dbcon, upsert=upsert,
                                                     assume_no_conflict=assume_no_conflict, nocommit=True )
                    dbcon.execute( q )
                    dbcon.execute( "DROP TABLE temp_bulk_upsert" )

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
                rows, cols = dbcon.execute( f"SELECT * FROM {baseclass.__tableschema__}.{baseclass.__tablename__} "
                                            f"WHERE healpix=%(healpix)s AND survey=%(survey)s AND program=%(program)s",
                                            { 'healpix': healpix, 'survey': survey, 'program': program } )
                if len(rows) > 0:
                    raise TopLevelEntryExistsError( f'Entry already exists: healpix={healpix}, '
                                                    f'survey={survey}, program={program}' )

            hdumap, bintables, parseinfo = self._read_and_verify_fits( filetoread, hdumap, rrver )

            if not self.donotload:
                healpixobj = baseclass( id=uuid.uuid4(), healpix=healpix, survey=survey, program=program,
                                        filename=relfilepath, dbcon=dbcon )
                healpixobj.insert( nocommit=True, refresh=False, dbcon=dbcon )

                for modeltable in hdumap.keys():
                    model = getattr( self.desi_release_module, modeltable )
                    tab = bintables[ modeltable ]

                    data = { str(col).lower(): list( tab[col] ) for col in tab.columns }
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

                    q = model.bulk_insert_or_upsert( data, dbcon=dbcon, upsert=upsert,
                                                     assume_no_conflict=assume_no_conflict, nocommit=True )
                    dbcon.execute( q )
                    dbcon.execute( "DROP TABLE temp_bulk_upsert" )

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
                 ( len( smm['nonnullmissingfromdata'] ) > 0 ) or
                 ( len( smm['missingfromdata'] ) > 0 ) or
                 ( len( smm['coltypemismatch'] ) > 0 ) ):
                loginfo.append( f"MODEL: {model}" )
                if len( smm['indatabutshouldnotbe'] ) > 0:
                    loginfo.append( f"...Unknown data columns: {smm['indatabutshouldnotbe']}" )
                if len( smm['nonnullmissingfromdata'] ) > 0:
                    loginfo.append( f"...(Fatal) missing data columns: {smm['nonnullmissingfromdata']}" )
                if len( smm['missingfromdata'] ) > 0:
                    loginfo.append( f"...(Non-fatal) missing data columns: {smm['missingfromdata']}" )
                if len( smm['coltypemismatch'] ) > 0:
                    for col in smm['coltypemismatch']:
                        loginfo.append( f"...{col} datatype mismatch; "
                                        f"is {smm['datatypes'][col]} in the data, and "
                                        f"{smm['modeltypes'][col.lower()]} in the model." )
        return loginfo


    # ======================================================================

    def print_schema_mismatch( self, data, loginfo=[], subject=None ):
        loginfo = self.build_schema_mismatch_info( data, loginfo=loginfo )
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
            DBLogger.debug( "\n".join( self.build_schema_mismatch_info( data ) ) )


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
                nightlt = 99999999 if nightlt is None else nightlt
                if ( int(night.name) < nightge ) or ( int(night.name) >= nightlt ):
                    continue
                self.load_tile_night_directory( tile, int(night.name) )


    # ======================================================================

    def load_all_tiles_newer_than( self, nightge, nightlt=None, onlytile=None ):
        if nightlt is None:
            nightlt = 99999999
        toload = []
        DBLogger.debug( "Going through all tile directories to find yyyymmdd subdirectories..." )
        for n, tiledir in enumerate( self.basetiledir.iterdir() ):
            if n % 200 == 0:
                DBLogger.debug( f"...searched {n} tile directories so far..." )
            if self.numbersmatch.search( tiledir.name ):
                itile = int( tiledir.name )
                # ****
                # This next bit is for debugging only, to skip most directories for speed
                if ( onlytile is not None ) and ( itile != int(onlytile) ):
                    continue
                # ****
                if tiledir.is_dir():
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
                    self.print_schema_mismatch( e.data, loginfo, subject="DesiDB Schema Mismatch" )
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
                DBLogger.debug( "\n".join( self.build_schema_mismatch_info( data ) ) )
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
        for programdir in direc.iterdir():
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
    parser.add_argument( '-v', '--verbose', action='store_true', default=False,
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
                if args.auto_newer:
                    raise ValueError( "Don't use --auto-newer and --tiles-newer togehter." )
                startdate = int( args.tiles_newer )
            else:
                with desidb.db.DBCon() as dbcon:
                    # No Bobby Tables worry here because the DESILoader constructor made sure
                    #   that desi_release is [a-z0-9_]+
                    rows, cols = dbcon.execute( f"SELECT MAX(night) FROM {loader.desi_release}.cumulative_tiles" )
                    if rows[0][0] is None:
                        startdate = 0
                    else:
                        startdate = rows[0][0]
            enddate = None if args.tiles_older is None else int( args.tiles_older )
            loader.load_all_tiles_newer_than( startdate, enddate )

    if args.survey is not None:
        if args.program is not None:
            if args.healpixd100 is not None:
                loader.load_healpixd100_directory( args.healpixd100, args.survey, args.program )
            else:
                loader.load_healpix_survey_program( args.survey, args.program )
        else:
            if args.healpixd100 is not None:
                raise ValueError( "--healpixd100 requires --program" )
            loader.load_healpix_survey( args.survey )


# ======================================================================

if __name__ == "__main__":
    main()
