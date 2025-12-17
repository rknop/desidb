import sys
import re
import pathlib
import importlib
import copy
import numpy

from psycopg2.errors import UniqueViolation
from astropy.io import fits
import astropy.table

from desidb.logger import DBLogger

# ======================================================================
    
class RRVersion:
    verparse = re.compile( '^([0-9]+)\.([0-9]+)\.([0-9]+)(\.(.*))?$' )

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
                               'conflict_update': "(cumultile_id,targetid)"
                               'customfields': [ 'cumultile_id' ]
            },
            'TilesExpFibermap': { 'hdu': 'EXP_FIBERMAP',
                                  'skipcheck': [ 'tileid',  'petal_loc', 'night', 'expid' ],
                                  'duplicates': 'skip',
                                  'customfields': [ 'cumultile_id' ]
                                 },
            'TilesTSNR2': { 'hdu': 'TSNR2',
                            'skipcheck': None,
                            'duplicates': 'error'
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
                    'customfields': [ 'cumultile_id' ]
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
                    'customfields': [ 'cumultile_id' ]
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
                    'customfields': [ 'cumultile_id' ]
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

def _read_and_verify_fits( filepath, desi_release, hdumap, rrver ):
    # I feel a bit queasy about this
    typematch = {
        'bool'  : [ 'boolean' ]
        'uint8' : [ 'smallint' ],
        'float32' : [ 'real' ],
        'float64' : [ 'double precision' ],
        'int16' : [ 'smallint' ],
        'int32' : [ 'integer' ],
        'int64' : [ 'bigint' ],
        'object' : [ ( 'ARRAY', 'character varying' ) ]
    }

    desi_release_module = importlib.import_module( desi_release )

    bintables = {}
    with fits.open( filepath ) as hdulist:
        for hdu in hdulist:
            if isinstance( hdu, fits.hdu.BinTableHDU ):
                if hdu.name in bintables.keys():
                    raise RuntimeError( f"Extension {hdu.name} shows up in the FITS file "
                                        f"{fitsfiles} more than once." )
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
        model = getattr( desi_release_module, modeltable )
        model._load_table_meta()
        if hdumap[modeltable]['hdu'] not in bintables.keys():
            # This will have been flagged as an error in parseinfo above, so just skip and punt
            continue
        tab = bintables[ hdumap[modeltable]['hdu'] ]
        parseinfo['models'][modeltable] = {
            'datablock' : hdumap[modeltable]['hdu'],
            'missingfrommodel': set(),
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
                raise RuntimeError( f"Unknown type for FITS column {datacol}: {fitstype}" )
            smm['datatypes'][datacol] = datatype

            if ( hdumap[modeltable]['ignore'] is not None ) and ( datacol in hdumap[modeltable]['ignore'] ):
                continue
            if ( hdumap[modeltable]['expect'] is not None ) and ( datacol not in hdumap[modeltable]['expect'] ):
                continue

            if lc(datacol) not in model._tablemeta:
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

            tabfield = uc( field )

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

def import_tile_night_petal( basedir, desi_release, tileid, night, petal, donotload=False, logger=None ):
    """Try to import a redrock-*.fits or zbest-*.fits file into the database.

    * basedir should be a "tiles" subdirectory of some sort, containing all the tileid subdirectories.
    * desi_release is a string like "loa" or "daily"
    * tileid, night, petal are integers
    * donotload: if "True", won't actually load anything, just see if schema match

    Returns a dictionary with various information about HDUs form the
    fits files, columns not found in the fits file, and datatypes.
    Raises a SchemaMismatchError if expected HDUs were missing from the
    FITS file, if there were unexpected HDUs in the FITS file, if there
    were unexpected columns in the fits files, if necessary columns in
    the FITS file were missing, or if the datatype from the FITS file
    didn't match what was expected from the model.

    """
    basedir = pathlib.Path( basedir )
    direc = basedir / str(tileid) / str(night)
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
        desi_release_module = importlib.import_module( desi_release )
        baseclass = getattr( desi_release_module, 'CumulativeTiles' )
        baseclass._load_table_meta( dbcon=dbcon )

        if not donotload:
            res = dbcon.execute( f"SELECT * FROM {baseclass.__tableschema__}.{baseclass.__tablename__} "
                                 f"WHERE tileid=%(tileid)s AND petal=%(petal)s AND night=%(night)s" )
            if len(res) > 0:
                raise TopLevelEntryExistsError( f'Entry already exists: tile={tileid}, petal={petal}, night={night}' )

        hdumap, bintables, parseinfo = _read_and_verify_fits( filetoread, desi_release, hdumap, rrver )
        
        if not donotload:
            # I'm assuming that no other process is loading at the same time.  We checked way up
            # at the top that this entry didn't already exist.  If multiple processes are doing
            # this at once, I'm writing in a race condition here....
            cumultile = baseclass( tileid=tileid, petal=petal, night=night, filename=relfilepath, dbcon=dbcon )
            cumultile.insert()

            for modeltable in hdumap.keys():
                model = getattr( desi_release_module, modeltable )
                tab = bintables[ hdumap[modeltable]['hdu'] ]

                data = { lc('col'): list( tab['col'] ) for col in tab.columns }
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

def import_healpix( basedir, desi_release, survey, program, healpix, donotload=False, logger=None ):
    # The error checking that's in import_tile_night_petal is not here
    #   because currently the healpix hdu map doesn't have any ignore or expect
    #   set, so we are assuming that the schema is always the same.
    basedir = pathlib.Path( basedir )
    direc = basedir / survey / program / str(healpix // 100) / str(healpix)
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
        desi_release_module = importlib.import_module( desi_release )
        baseclass = getattr( desi_release_module, 'Healpix' )
        baseclass._load_table_meta( dbcon=dbcon )
    
        if not donotload:
            res = dbcon.execute( f"SELECT * FROM {baseclass.__tableschema__}.{baseclass.__tablename__} "
                                 f"WHERE healpix=%(healpix)s AND survey=%(survey)s AND program=%(program)s" )
            if len(res) > 0:
                raise TopLevelEntryExistsError( f'Entry already exists: healpix={healpix}, '
                                                f'survey={survey}, program={program}' )

    hdumap, bintables, parseinfo = _read_and_verify_fits( filetoread, models, hdumap, rrver )

    if not donotload:
        ROB YOU ARE HERE
        healpixobj = baseclass( healpix=healpix, survey=survey, program=program, filename=relfilepath, dbcon=dbcon )
        healpixobj.insert()

        for modeltable in hdumap.keys():
            model = getattr( models, modeltable )
            df = bintables[ hdumap[modeltable]['hdu'] ]

            kwargs = { 'healpix': healpixobj }
            _actually_load( df, hdumap, modeltable, kwargs, model,
                            idcolumn='healpix_id', idvalue=healpixobj.id,
                            logger=logger )
            
    # Done.  Return any mismatches form the parsing.
    return parseinfo
