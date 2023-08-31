import sys
import re
import pathlib
import copy
import numpy
import pandas
from django.core.exceptions import FieldDoesNotExist
import django.db
from django.db import IntegrityError
from psycopg2.errors import UniqueViolation
from astropy.io import fits

import desidb.settings

from db.management.commands._import import _fits_bintables_to_pandas, _pandas_to_postgresql_model
from db.management.commands._import import TopLevelEntryExistsError, EntryExistsError, SchemaMismatchError

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
                                'duplicates': 'error'
            },
            'TilesFibermap': { 'hdu': 'FIBERMAP',
                               'skipcheck': None,
                               'duplicates': 'update',
                               'conflict_update': "(cumultile_id,targetid)"
            },
            'TilesExpFibermap': { 'hdu': 'EXP_FIBERMAP',
                                  'skipcheck': [ 'tileid',  'petal_loc', 'night', 'expid' ],
                                  'duplicates': 'skip' },
            'TilesTSNR2': { 'hdu': 'TSNR2',
                            'skipcheck': None,
                            'duplicates': 'error' }
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

def _read_and_verify_fits( filepath, models, hdumap, rrver ):
    # I feel a bit queasy about this
    typematch = {
        'bool'  : [ django.db.models.BooleanField ],
        'uint8' : [ django.db.models.SmallIntegerField ],
        'float32' : [ django.db.models.FloatField ],
        'float64' : [ django.db.models.FloatField ],
        'int16' : [ django.db.models.SmallIntegerField, django.db.models.IntegerField,
                    django.db.models.BigIntegerField ],
        'int32' : [ django.db.models.IntegerField, django.db.models.BigIntegerField ],
        'int64' : [ django.db.models.BigIntegerField ],
        'object' : [ django.db.models.CharField ]
    }
    django_system_fields = [ 'id' ]

    bintables = _fits_bintables_to_pandas( filepath )
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

    # Wrangle around the input tables using the "map" information in hdumao.
    # This is because earlier versions of Redrock had some stuff in different HDUs from later
    # versions, and we want to have a single schema for the model....
    #
    # ROB TODO: As written, it's possible that this could leave us with a table where
    # two columns have the same name.  I *think* Pandas represents this as an embedded
    # DataFrame, and will cause code crashes.
    for modeltable in hdumap.keys():
        hdu = hdumap[modeltable]['hdu']
        for col, mapping in hdumap[modeltable]['map'].items():
            if mapping['otherhdu'] not in bintables.keys():
                parseinfo['missingdatablock'].add( mapping['otherhdu'] )
                schemaok = False
                continue
            maindf = bintables[hdu]
            otherdf = bintables[mapping['otherhdu']]
            maindf.set_index( mapping['matchcolumn'], inplace=True )
            othercol = otherdf.set_index( mapping['otherhdumatchcolumn'] )[ mapping['column'] ]
            othercol.name = col
            if mapping['typeconv'] is not None:
                othercol = othercol.astype( mapping['typeconv'] )
            maindf = pandas.concat( [ maindf, othercol ], axis=1 )
            maindf.reset_index(inplace=True)
            bintables[hdu] = maindf

    # Deduplicate if necessary
    for modeltable in hdumap.keys():
        modmap = hdumap[modeltable]
        if 'deduplication' in modmap.keys():
            df = bintables[ modmap['hdu'] ].groupby( modmap['deduplication'] ).aggregate( 'first' ).reset_index()
            bintables[ modmap['hdu'] ] = df
            
    # Verify that either all expected columns are there or no ignored columns are there,
    #   and that dataytypes between FITS and Django match
    for modeltable in hdumap.keys():
        model = getattr( models, modeltable )
        if hdumap[modeltable]['hdu'] not in bintables.keys():
            # This will have been flagged as an error in parseinfo above, so just skip and punt
            continue
        df = bintables[ hdumap[modeltable]['hdu'] ]
        parseinfo['models'][modeltable] = {
            'datablock' : hdumap[modeltable]['hdu'],
            'missingfrommodel': set(),
            'missingfromdata': set(),
            'coltypemismatch': set(),
            'datatypes': {},
            'modeltypes': {}
        }
        smm = parseinfo['models'][modeltable]

        # Go through the FITS columns and make sure that we expect each one of them,
        # and that the data types match.
        # sys.stderr.write( f'Working on {modeltable}; ignore is {hdumap[modeltable]["ignore"]}\n' )
        for datacol in df.columns:
            if datacol in django_system_fields:
                raise RuntimeError( f"Coding assumption error; fits column {datacol} "
                                    f"matches a django system column" )
            datatype = str( df[datacol].dtype )
            smm['datatypes'][datacol] = datatype
            if ( hdumap[modeltable]['ignore'] is not None ) and ( datacol in hdumap[modeltable]['ignore'] ):
                continue
            if ( hdumap[modeltable]['expect'] is not None ) and ( datacol not in hdumap[modeltable]['expect'] ):
                continue

            try:
                dbcol = model._meta.get_field( datacol )
                if datatype not in typematch.keys():
                    raise RuntimeError( f"Unknown type for FITS column {datacol}: {fitstype}" )
                if type(dbcol) not in typematch[datatype]:
                    smm['coltypemismatch'].add( datacol )
                    schemaok = False
            except FieldDoesNotExist as ex:
                # sys.stderr.write( f'We have an uh-oh at {datacol}\n' )
                smm['missingfrommodel'].add( datacol )
                schemaok = False

        # Go through the Model and check which things are missing from the FITS file
        # (Don't have to check datatypes, as we've already looked at all FITS columns.)
        # This won't be considered an error unless the column is not nullable.
        for field in model._meta.get_fields():
            smm['modeltypes'][field.name] = str( type(field) )
            if field.name in django_system_fields:
                continue
            if type(field) == django.db.models.ForeignKey:
                # Making the assumption here that the only foreign keys
                # are the ones that I've manually defined, and not thing
                # that should be tagged with an id in one HDU
                continue

            if field.name not in df.columns:
                smm['missingfromdata'].add( field.name )
                if not field.null:
                    schemaok = False
                        
    # Raise an exception if there was a fatal parseinfo
    if not schemaok:
        # import pdb; pdb.set_trace()
        raise SchemaMismatchError( parseinfo )

    return hdumap, bintables, parseinfo

# ======================================================================

def _actually_load( df, hdumap, modeltable, kwargs, model, idcolumn, idvalue, logger=None ):

    # For efficiency, the "skipcheck" field of hdumap gives us a set of
    # columns to group things by and load all at once.
    #
    # We're going to assume that if something already exists in the
    # database with the same combination of values in skipcheck as are
    # found in columns in this dataframe, then we don't have to load any
    # of this dataframe.  In practice, I use this for ExpFibermap.  If
    # the same object is observed on a later date, it will include all
    # observations of that tile/target in the EXP_FIBERMAP HDU of the
    # FITS files, the latest of which is only new; the earlier ones are
    # copies of stuff already in the database.  So, I do the skipcheck
    # to see if should skip loading blocks of ExpFibermap that (at least
    # partially) already exist.
    #
    # If skipcheck is None, we load the whole dataframe in one go.
    
    # This isn't perfect.  It's conceivable that a dataframe might
    # prevously have been partially loaded, and we want here to load the
    # rest of it.  But, checking row by row is going to be a lot slower,
    # so for efficiency I'm just doing it at once here.
    
    # Clean up the dataframe to what's expected
    if hdumap[modeltable]['expect'] is not None:
        cols = [ col for col in df.columns if col in hdumap[modeltable]['expect'] ]
        df = df[ cols ].copy()
    elif hdumap[modeltable]['ignore'] is not None:
        cols = [ col for col in df.columns if col not in hdumap[modeltable]['ignore'] ]
        df = df[ cols ].copy()
    else:
        df = df.copy()

    # And, yeah, I have to actually look at the opaque hidden primary id key
    # created by Django, since I'm not using the Django idiom to add
    # rows to the database here.
    # $10 says that none of this code comes close to working with a future
    # version of Django.
    df[idcolumn] = idvalue
        
    skipcheck = hdumap[modeltable]['skipcheck']
    duplicates = hdumap[modeltable]['duplicates']
    conflict_update = ( hdumap[modeltable]['conflict_update']
                        if 'conflict_update' in hdumap[modeltable].keys()
                        else None )
    if skipcheck is None:
        _pandas_to_postgresql_model( df, model, duplicates, conflict_update=conflict_update, logger=logger )
    else:
        dexdf = df[skipcheck].groupby(skipcheck).first().reset_index()
        # sys.stderr.write( f"Dividing {modeltable} into {len(dexdf)} subset.\n" )
        for i in range(len(dexdf)):
            row = dexdf.iloc[i]
            kwargs = {}
            for col in skipcheck:
                kwargs[col] = row[col]
                # There's probably a "to_dict" method I should be using here
            existing = model.objects.filter( **kwargs )

            if existing.count() > 0:
                if hdumap[modeltable]['duplicates'] == 'skip':
                    if logger is not None:
                        logger.info( f'Already have entries for {modeltable} with {kwargs}, skipping insert.' )
                else:
                    raise EntryExistsError( f'Already have entries for {modeltable} with {kwargs}' )

            # This next line is very pythonic and pandastic, but it's not *clear*
            subdf = df[ sum( [ df[k]==v for k, v in kwargs.items() ] ) == len(kwargs) ]
            # sys.stderr.write( f"Loading {len(subdf)} values for subset {i}\n" )
            _pandas_to_postgresql_model( subdf, model, duplicates, conflict_update=conflict_update, logger=logger )


# ======================================================================
# NOTE : I've got the fact that the root directory is /data
# (mounted from /global/cfs/cdirs/desi/spectro/redux)
#  hardcoded below!  This is suboptimal.

def import_tile_night_petal( basedir, tileid, night, petal, models, donotload=False, logger=None ):
    """Try to import a redrock-*.fits or zbest-*.fits file into the database.

    * basedir should be a "tiles" subdirectory of some sort, containing all the tileid subdirectories.
    * tileid, night, petal are integers
    * models is the Django namespace that has all the model classes
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
    
    baseclass = getattr( models, 'CumulativeTiles' )
    if not donotload:
        current = baseclass.objects.filter( tileid=tileid ).filter( petal=petal ).filter( night=night )
        if len(current) > 0:
            raise TopLevelEntryExistsError( f'Entry already exists: tile={tileid}, petal={petal}, night={night}' )

    hdumap, bintables, parseinfo = _read_and_verify_fits( filetoread, models, hdumap, rrver ) 
        
    if not donotload:
        # I'm assuming that no other process is loading at the same time.  We checked way up
        # at the top that this entry didn't already exist.  If multiple processes are doing
        # this at once, I'm writing in a race condition here....
        cumultile = baseclass( tileid=tileid, petal=petal, night=night, filename=relfilepath )
        cumultile.save()

        for modeltable in hdumap.keys():
            model = getattr( models, modeltable )
            df = bintables[ hdumap[modeltable]['hdu'] ]

            kwargs = { 'cumultile': cumultile }
            try:
                _actually_load( df, hdumap, modeltable, kwargs, model,
                                idcolumn='cumultile_id', idvalue=cumultile.id,
                                logger=logger )
            except EntryExistsError as ex:
                if hdumap[modeltable]['duplicates'] == 'skip':
                    # ¯\_(ツ)_/¯
                    continue
                else:
                    raise ex

    # Done.  Return any mismatches form the parsing.
    return parseinfo

# ======================================================================

def import_healpix( basedir, survey, program, healpix, models, donotload=False, logger=None ):
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

    baseclass = getattr( models, 'Healpix' )
    if not donotload:
        current = baseclass.objects.filter( healpix=healpix ).filter( survey=survey ).filter( program=program )
        if len(current) > 0:
            raise TopLevelEntryExistsError( f'Entry already exists: healpix={healpix}, '
                                            f'survey={survey}, program={program}' )

    hdumap, bintables, parseinfo = _read_and_verify_fits( filetoread, models, hdumap, rrver )

    if not donotload:
        healpixobj = baseclass( healpix=healpix, survey=survey, program=program, filename=relfilepath )
        healpixobj.save()

        for modeltable in hdumap.keys():
            model = getattr( models, modeltable )
            df = bintables[ hdumap[modeltable]['hdu'] ]

            kwargs = { 'healpix': healpixobj }
            _actually_load( df, hdumap, modeltable, kwargs, model,
                            idcolumn='healpix_id', idvalue=healpixobj.id,
                            logger=logger )
            
    # Done.  Return any mismatches form the parsing.
    return parseinfo
