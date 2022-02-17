import re
import pathlib
import copy
import numpy
import pandas
from django.core.exceptions import FieldDoesNotExist
import django.db
from psycopg2.errors import UniqueViolation

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

    def get_hdu_map( self ):
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

        if ( self.major == 0 ) and ( self.minor < 14 ):
            raise ValueError( f"Don't know how to deal with redrock version {self.major}.{self.minor}" )
        if ( self.major == 0 ) and ( self.minor == 14 ):
            return {
                'Redshifts': {
                    'hdu' : 'ZBEST',
                    'duplicates': 'error',
                    'expect' : None,
                    'map': {}
                },
                'Fibermap': {
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
                            'column': 'numexp'
                            },
                        'coadd_numtile': {
                            'matchcolumn' : '[targetid'],
                            'otherhdumatchcolumn' : ['targetid'],
                            'otherhdu' : 'ZBEST',
                            'column' : 'numtile'
                        }
                    }
                },
                'ExpFibermap': {
                    'hdu' : 'FIBERMAP',
                    'duplicates': 'error'
                    'ignore' : None,
                    'expect' :  { 'targetid', 'fiber_ra', 'fiber_dec', 'fiber_x', 'fiber_y', 'delta_x', 'delta_y',
                                  'night', 'exptime', 'num_iter', 'psf_to_fiber_specflux', 'expid',
                                  'fiberstatus', 'mjd' },
                    'map' : {}
                }
            }
        else:
            # Default: expect full schema match
            hdumap = {
                'Redshifts': { 'hdu': 'REDSHIFTS', 'duplicates': 'error' },
                'Fibermap': { 'hdu': 'FIBERMAP', 'duplicates': 'error' },
                'ExpFibermap': { 'hdu': 'EXP_FIBERMAP', 'duplicates': 'skip' },
                'TSNR2': { 'hdu': 'TSNR2', 'duplicates': 'updateonce' }
            }
            for key, val in hdumap.items():
                val['duplicates'] = 'error'
                val['ignore'] = set()
                val['expect'] = None
                val['map'] = {}
            return hdumap
                    

# ======================================================================

def _import_fits( filepath, tileid, petal, night, models, donotload=False, ignoreuniqueexception=False ):
    """Returns a dictionary that's the same thing passed to SchemaMismatchError.
    """

    baseclass = getattr( models, 'Redrock' )
    if not donlotload:
        current = baseclass.objects.filter( tileid=tileid ).filter( petal=petal ).filter( night=night )
        if len(current) > 0:
            raise EntryExistsError( f'Entry already exists: tile={tileid}, petal={petal}, night={night}' )

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

    primary_header, bintables = _fits_bintables_to_pandas( filepath )
    rrver = RRVersion( primary_header['RRVER'] )
    hdumap = rrver.get_hdu_map()
    parseinfo = {
        'filepath': str(filepath),
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
        hdu = hduman[modeltable]['hdu']
        for mapping in hdumap[modeltable]['map']:
            if mapping['otherhdu'] not in bintables.keys():
                parseinfo['missingdatablock'].add( mapping['otherhdu'] )
                schemaok = False
                continue
            maindf = bintables[hdu]
            otherdf = bintables[mapping['otherhdu']]
            maindf.set_index( mapping['matchcolumn'], inplace=True )
            otherdf.set_index( mapping['otherhdumatchcolumn'], inplace=True )
            maindf = pandas.concat( maindf, otherdf[ mapping['column'] ], axis=1 )
            maindf.reset_index(inplace=True)
            otherdif.reset_index(inplace=True)
            bintables[hdu] = maindf
            
    # Verify that either all expected columns are there or no ignored columns are there,
    #   and that dataytypes between FITS and Django match
    for modeltable in hdumap.keys():
        model = getattr( models, modeltable )
        if hdumap[modeltable]['hdu'] not in hdus.keys():
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
            raise SchemaMismatchError( parseinfo )

        # If we get this far, then we believe that the FITS file and the database model match.
        # (At least, we really hope.)
        # Start loading, and weep if it crashes partway through.

        if not donotload:
            # I'm assuming that no other process is loading at the same time.  We checked way up
            # at the top that this entry didn't already exist.  If multiple processes are doing
            # this at once, I'm writing in a race condition here....
            redrock = baseclass( tileid=tileid, petal=petal, night=night )
            redrock.save()
            
            for modeltable in hdumap.keys():
                model = getattr( models, modeltable )
                df = bintables[ hdumap[modeltable]['hdu'] ]

                kwargs = { 'redrock_file': redrock }
                for i, row in df.iterrows():
                    for col in row.keys():
                        if ( ( hdumap[modeltable]['ignore'] is not None )
                             and ( col in hdumap[modeltable]['ignore'] ) ):
                            continue
                        if ( ( hdumap[modeltable]['expect'] is not None )
                             and ( col not in hdumap[modeltable]['expect'] ) ):
                            continue
                        kwargs[col] = row[col]
                    try:
                        newobject = model( **kwargs )
                        newobject.save()
                    except UniqueViolation as e:
                        if hdumap[modeltable]['duplicates'] == 'error':
                            raise e
                        elif hdumap[modeltable]['duplicates'] == 'skip':
                            continue
                        else:
                            raise Exception( f"hdumap['{modeltable}']['duplicates'] has unknown value!" )
                    except Exception as e:
                        import pdb; pdb.set_trace()

    # Done.  Return any mismatches form the parsing.
    return parseinfo

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
        raise FileNotFoundError( f"{direc.name} isn't a directory" )
    zbest = direc / f'zbest-{petal}-{tileid}-{"thru" if cumulative else ""}{night}.fits'
    redrock = direc / f'zbest-{petal}-{tileid}-{"thru" if cumulative else ""}{night}.fits'
    filetoread = None
    if redrock.is_file():
        filetoread = redrock
    elif zbest.is_file():
        filetoread = zbest
    else:
        raise FileNotFoundError( f"Did not find {redrock} or {zbest}" )
    return _import_fits( filetoread, tileid, petal, night, models, donotload=donotload )
    
                 
