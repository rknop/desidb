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

from db.management.commands._import import _fits_bintables_to_pandas, EntryExistsError, SchemaMismatchError

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

        It's a dictionary.  Each key is one of the database models:
        Redshifts, Fibermap, ExpFibermap, or TSNR2.  The Values are:
            hdu : name of the HDU that has the information for this table
            duplicates : 'error', 'skip', 'verify', 'update', 'updateonce'
            ignore : set of columns that should be ignored (expect all others; 'expect' should be None)
            expect : set of columns that we should expect (ignore all others; 'ignore' should be None)
            map : dictionary.  Keys are Django columns, values are dictionary:
                matchcolumn : column in main HDU for this table that must match:
                otherhdumatchcolumn : column in other HDU
                otherhdu : name of other HDU
                column : column in other HDU with information

        All FITS column names have been converted to lower case.

        """

        # Default: expect full schema match
        hdumap = {
            'TilesRedshifts': { 'hdu': 'REDSHIFTS', 'duplicates': 'error' },
            'TilesFibermap': { 'hdu': 'FIBERMAP', 'duplicates': 'error' },
            'TilesExpFibermap': { 'hdu': 'EXP_FIBERMAP', 'duplicates': 'skip' },
            'TilesTSNR2': { 'hdu': 'TSNR2', 'duplicates': 'error' }
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
                    'duplicates': 'error',
                    'ignore': { 'numexp', 'numtile' },
                    'expect' : None,
                    'map': {}
                },
                'TilesFibermap': {
                    'hdu' : 'FIBERMAP',
                    'duplicates': 'skip',
                    'ignore' : { 'fiber_ra', 'fiber_dec', 'fiber_x', 'fiber_y', 'delta_x', 'delta_y',
                                 'night', 'exptime', 'num_iter', 'psf_to_fiber_specflux', 'expid',
                                 'fiberstatus', 'mjd',
                                 'sv2_bgs_target', 'sv2_scnd_target', 'sv2_desi_target', 'sv2_mws_target' },
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
                    }
                },
                'TilesExpFibermap': {
                    'hdu' : 'FIBERMAP',
                    'duplicates': 'skip',
                    'ignore' : None,
                    'expect' :  { 'targetid', 'tileid', 'petal_loc', 'fiber',
                                  'fiber_ra', 'fiber_dec', 'fiber_x', 'fiber_y', 'delta_x', 'delta_y',
                                  'night', 'exptime', 'num_iter', 'psf_to_fiber_specflux', 'expid',
                                  'fiberstatus', 'mjd' },
                    'map' : {}
                }
            }
        elif ( self.major == 0 ) and ( self.minor == 15 ):
            hdumap['TilesFibermap']['ignore'].update( ('sv2_mws_target', 'sv2_scnd_target',
                                                       'sv2_desi_target', 'sv2_bgs_target' ) )

        return hdumap


    def get_healpix_hdu_map( self ):
        hdumap = {
            'HealpixRedshifts': { 'hdu': 'REDSHIFTS', 'duplicates': 'error' },
            'HealpixFibermap': { 'hdu': 'FIBERMAP', 'duplicates': 'error' },
            'HealpixExpFibermap': { 'hdu': 'EXP_FIBERMAP', 'duplicates': 'skip' },
            'HealpixTSNR2': { 'hdu': 'TSNR2', 'duplicates': 'error' }
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
        'uint8' : django.db.models.SmallIntegerField,
        'float32' : django.db.models.FloatField,
        'float64' : django.db.models.FloatField,
        'int16' : django.db.models.SmallIntegerField,
        'int32' : django.db.models.IntegerField,
        'int64' : django.db.models.BigIntegerField,
        'object'  : django.db.models.CharField
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
                if type(dbcol) != typematch[datatype]:
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

def _actually_load( df, hdumap, modeltable, kwargs, model ):
    # ANNOYING PANDAS NOTE
    # If you do for i, row in df.iterrows(), then everything in row
    #   gets converted to a float... which is a disaster, especially
    #   for bigints.  If you want to do iteration like this, you have
    #   to be more careful.
    # I know that the pandas dogma is that you should never
    #   iterate through rows, but I'm not feeling clever enough
    #   to properly integrate pandas and django here.  Somewhere
    #   inside there is going to be iteration anyway, so it
    #   seems foolish to make it more complicated when basic
    #   iteration just makes sense.  Perhaps a pandas DataFrame
    #   isn't the right data structure, but it was very
    #   convenient for merging above.
    for i in range( len(df) ):
        for col in df.columns:
            if ( ( hdumap[modeltable]['ignore'] is not None )
                 and ( col in hdumap[modeltable]['ignore'] ) ):
                continue
            if ( ( hdumap[modeltable]['expect'] is not None )
                 and ( col not in hdumap[modeltable]['expect'] ) ):
                continue
            kwargs[col] = df[col].values[i]
        try:
            newobject = model( **kwargs )
            newobject.save()
        except UniqueViolation as e:
            # I'm not sure whether this (a pyscopg2 error) or
            # IntegrityError (a django error) is what will pop
            # up
            if hdumap[modeltable]['duplicates'] == 'error':
                raise e
            elif hdumap[modeltable]['duplicates'] == 'skip':
                continue
            else:
                raise Exception( f"hdumap['{modeltable}']['duplicates'] has unknown value!" )
        except IntegrityError as e:
            if 'violates unique constraint' in str(e):
                if hdumap[modeltable]['duplicates'] == 'error':
                    import pdb; pdb.set_trace()
                    raise e
                elif hdumap[modeltable]['duplicates'] == 'skip':
                    continue
                else:
                    raise Exception( f"hdumap['{modeltable}']['duplicates'] has unknown value!" )
            else:
                raise e
        except Exception as e:
            sys.stderr.write( "OMG\n" )
            import pdb; pdb.set_trace()
            sys.stderr.write( "...\n" )

# ======================================================================

def import_tile_night_petal( basedir, tileid, night, petal, models, donotload=False ):
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

    with fits.open( filetoread, memmap=False ) as hdul:
        rrver = RRVersion( hdul[0].header['RRVER'] )
    hdumap = rrver.get_tiles_hdu_map()
    
    baseclass = getattr( models, 'CumulativeTiles' )
    if not donotload:
        current = baseclass.objects.filter( tileid=tileid ).filter( petal=petal ).filter( night=night )
        if len(current) > 0:
            raise EntryExistsError( f'Entry already exists: tile={tileid}, petal={petal}, night={night}' )

    hdumap, bintables, parseinfo = _read_and_verify_fits( filetoread, models, hdumap, rrver ) 
        
    if not donotload:
        # I'm assuming that no other process is loading at the same time.  We checked way up
        # at the top that this entry didn't already exist.  If multiple processes are doing
        # this at once, I'm writing in a race condition here....
        cumultile = baseclass( tileid=tileid, petal=petal, night=night )
        cumultile.save()

        for modeltable in hdumap.keys():
            model = getattr( models, modeltable )
            df = bintables[ hdumap[modeltable]['hdu'] ]

            kwargs = { 'cumultile': cumultile }
            _actually_load( df, hdumap, modeltable, kwargs, model )

    # Done.  Return any mismatches form the parsing.
    return parseinfo

# ======================================================================

def import_healpix( basedir, survey, program, healpix, models, donotload=False ):
    basedir = pathlib.Path( basedir )
    direc = basedir / survey / program / str(healpix // 100) / str(healpix)
    if not direc.is_dir():
        raise FileNotFoundError( f"{str(direc)} isn't an existing directory" )
    filetoread = direc / f'redrock-{survey}-{program}-{healpix}.fits'
    if not filetoread.is_file():
        raise FileNotFoundError( f"{str(filetoread)} isn't an existing regular file" )

    with fits.open( filetoread, memmap=False ) as hdul:
        rrver = RRVersion( hdul[0].header['RRVER'] )
    hdumap = rrver.get_healpix_hdu_map()

    baseclass = getattr( models, 'Healpix' )
    if not donotload:
        current = baseclass.objects.filter( healpix=healpix ).filter( survey=survey ).filter( program=program )
        if len(current) > 0:
            raise EntryExistsError( f'Entry already exists: healpix={healpix}, survey={survey}, program={program}' )

    hdumap, bintables, parseinfo = _read_and_verify_fits( filetoread, models, hdumap, rrver )

    if not donotload:
        healpixobj = baseclass( healpix=healpix, survey=survey, program=program )
        healpixobj.save()

        for modeltable in hdumap.keys():
            model = getattr( models, modeltable )
            df = bintables[ hdumap[modeltable]['hdu'] ]

            kwargs = { 'healpix': healpixobj }
            _actually_load( df, hdumap, modeltable, kwargs, model )
            
    # Done.  Return any mismatches form the parsing.
    return parseinfo
