import re
import pathlib
import copy
import astropy
import astropy.table
from astropy.io import fits
from django.core.exceptions import FieldDoesNotExist
import django.db

class EntryExistsError(RuntimeError):
    def __init__( self, *args, **kwargs ):
        super().__init__( self, *args, **kwargs )

class SchemaMismatchError(RuntimeError):
    def __init__( self, data, *args, **kwargs ):
        """data needs to be a dictionary:
        filepath : Full path to the file read
        hdunotinfits : set of HDU names expected to be found in the FITS that weren't there
        extrahduinfits : set of HDU Binary tables in the FITS files that we didn't expect
        models:
          <key is one of Redshifts, Fibermap, ExpFibermap, or TSNR2>
          <value is a dictionary>:
              HDU : Name of HDU that (mostly) corresponds to the table, or None if not present
                      (Note: even if none, one of the other HDUs may have this table in moved).
              missingfrommodel : set of columns that were in the HDU but not the model
              missingfrom hdu : set of columsn that were in the model but not the HDU
              coltypemismatch : set of columns where HDU and table didn't match
              fitstypes : dictionary of column -> type from FITS file
              modeltypes : dictionary of column -> type from database
        """
        super().__init__( *args, **kwargs )
        self.data = data

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
            ignore : set of columns that should be ignored (expect all others; 'expect' should be None)
            expect : set of columns that we should expect (ignore all others; 'ignore' should be None)
            map : dictionary of FITS column : model column for things renamed

        All FITS column names have been converted to lower case.

        """

        if ( self.major == 0 ) and ( self.minor < 14 ):
            raise ValueError( f"Don't know how to deal with redrock version {self.major}.{self.minor}" )
        if ( self.major == 0 ) and ( self.minor == 14 ):
            return {
                'Redshifts': {
                    'hdu' : 'ZBEST',
                    'ignore' : set(),
                    'expect' : None,
                    'map': {}
                },
                'Fibermap': {
                    'hdu' : 'FIBERMAP',
                    'ignore' : { 'fiber_ra', 'fiber_dec', 'fiber_x', 'fiber_y', 'delta_x', 'delta_y',
                                 'night', 'exptime', 'num_iter', 'psf_to_fiber_specflux', 'expid',
                                 'fiberstatus', 'mjd' }
                    'expect' : None,
                    'map': {}
                },
                'ExpFibermap': {
                    'hdu' : 'FIBERMAP'
                    'ignore' : None,
                    'expect' :  { 'fiber_ra', 'fiber_dec', 'fiber_x', 'fiber_y', 'delta_x', 'delta_y',
                                 'night', 'exptime', 'num_iter', 'psf_to_fiber_specflux', 'expid',
                                 'fiberstatus', 'mjd' }
                }
            }
        else:
            # Default: expect full schema match
            return {
                'Redshifts': { 'hdu': 'REDSHIFTS', ignore: set(), expect: None, map: {} },
                'Fibermap': { 'hdu': 'FIBERMAP', ignore: set(), expect: None, map: {} },
                'ExpFibermap': { 'hdu': 'EXP_FIBERMAP', ignore: set(), expect: None, map: {} },
                'TSNR2': { 'hdu', 'TSNR2', ignore: set(), expect: None, map: {} }
            }
                                 
                    

# ======================================================================
        
def _parse_fits_columns( tab ):
    fitscolumns = []
    fitstypes = {}
    for col in tab.colnames:
        if len( tab[col].shape ) > 2:
            raise RuntimeError( f"Don't know how to deal with shape {tab[col].shape} columns" )
        elif len( tab[col].shape ) == 2:                    
            for i in range( tab[col].shape[1] ):
                fitscolumns.append( f'{col.lower()}_{i}' )
                fitstypes[ f'{col.lower()}_{i}' ] = str( tab[col].dtype )
        else:
            fitscolumns.append( col.lower() )
            fitstypes[ col.lower() ] = str( tab[col].dtype )
    return fitscolumns, fitstypes

# ======================================================================

def _import_fits( filepath, tileid, petal, night, models, cumulative=True, donotload=False, ignoreexists=True ):
    """Returns a dictionary that's the same thing passed to SchemaMismatchError.

    ROB TODO : right now I don't use the "map" elements from get_hdu_map.  FIX THAT.
    """

    cumper = "Cumulative" if cumulative_or_pernight else "Pernight"
    baseclass = getattr( models, f'Redrock{cumper}' )
    if ( not donotload ) or ( not ignoreexists ):
        current = baseclass.objects.filter( tileid=tileid ).filter( petal=petal ).filter( night=night )
        if len(current) > 0:
            raise EntryExistsError( f'Entry already exists: tile={tileid}, petal={petal}, night={nightid}' )

    # I REALLY need to figure ot a way to normalize numpy datatypes.  Right now I'm using
    # whatever I get from the datatype on an astropy Table, and I'm not sure it's
    # going to always be consistent.
    typematch = {
        'uint8' : django.db.models.SmallIntegerField,
        '>i8' : django.db.models.BigIntegerField,
        '>i4' : django.db.models.IntegerField,
        '>i2' : django.db.models.SmallIntegerField,
        '>f4' : django.db.models.FloatField,
        '>f8' : django.db.models.FloatField,
        '<U'  : django.db.models.CharField
    }
    typeconv = {
        'uint8': int,
        '>i8': int,
        '>i4': int,
        '>i2': int,
        '>f4': float,
        '>f8': float,
        '<U' : str
    }
    django_system_fields = [ 'id' ]

    with fits.open( filepath, memmap=False ) as hdulist:
        rrver = RRVersion( hdulist[0].header['RRVER'] )
        hdumap = rrver.get_hdu_map()
        schemaok = True
        schemamismatch = {
            'filepath' : str(filepath),
            'hdunotinfits' : set(),
            'extrahduinfits' : set(),
            'models' : {}
        }

        # Check to see if there are unexpected HDUs
        extnames_seen = set()
        hdus = {}
        for hdu in hdulist:
            extname = hdu.name
            if isinstance( hdu, fits.hdu.table.BinTableHDU ):
                if extname in extnames_seen:
                    raise RuntimeError( f'Extenson {extname} shows up in the fits file more than once' )
                extnames_seen.add( extname )
                found = False
                for modeltable in hdumap.keys():
                    if hdumap[modeltable].hdu == extname:
                        found = True
                        hdus[modeltable] = hdu
                if not found:
                    schemamismatch['extrahduinfits'].add( extname )
                    schemaok = False

        # Make sure we found all expected HDUs
        for modeltable in hdumap.keys():
            if modeltable not in hdus.keys():
                schemamismatch['hdunotinfits'].add( hdumap[modeltable]['hdu'] )
                schemaok = False
                    

        # Verify that either all expected columns are there or no ignored columns are there,
        #   and that dataytypes between FITS and Django match
        for modeltable in hdumap.keys():
            model = getattr( models, f'{cumper}modeltable' )
            hdu = hdus[ hdumap[modeltable]['hdu'] ]
            schemamismatch['models'][modeltable] = {
                'HDU' : hdu.name,
                'missingfrommodel': set(),
                'missingfromhdu': set(),
                'coltypemismatch': set(),
                'fitstypes': {},
                'modeltypes': {}
            }
            smm = schemamismatch['models'][modeltable]

            tab = astropy.table.Table( hdu.data )
            fitscolumns, fitstypes = _parse_fits_columns( tab )

            # Go through the FITS columns and make sure that we expect each one of them,
            # and that the data types match.
            for fitscol in fitscolumns:
                if fitscol in django_system_fields:
                    raise RuntimeError( f"Coding assumption error; fits column {fitscol} "
                                        f"matches a django system column" )
                fitstype = fitstypes[ fitscol ]
                smm['fitstypes'][fitscol] = fitstype
                if ( hdumap[modeltable]['ignore'] is not None ) and ( fitscol in hdumap[modeltable]['ignore'] ):
                    continue
                if ( hdumap[modeltable]['expect'] is not None ) and ( fitscol not in hdumap[modeltable]['expect'] ):
                    continue

                try:
                    dbcol = model._meta.get_field( fitscol )
                    if fitstype[0:2] == "<U":
                        fitstype = "<U"
                    if fitstype not in typematch.keys():
                        raise RuntimeError( f"Unknown type for FITS column {fitscol}: {fitstype}" )
                    if type(dbcol) != typematch[fitstype]:
                        smm['coltypemismatch'].add( fitscol )
                        schemaisok = False
                except FieldDoesNotExist as ex:
                    smm['missingfrommodel'].add( fitscol )
                    schemaisok = False


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
                if field.name not in fitscolumns:
                    smm['missingfromhdu'].add( field.name )
                    if not field.null:
                        schemaok = False
                        
        # Raise an exception if there was a fatal schemamismatch
        if not schemaok:
            raise SchemaMismatchError( schemamismatch )

        # If we get this far, then we believe that the FITS file and the database model match.
        # Start loading.

        if not donotload:
            redrock = baseclass( tileid=tileid, petal=petal, night=night )
            redrock.save()

            for modeltable in hdumap.keys():
                model = getattr( models, f'{cumper}modeltable' )
                hdu = hdus[ hdumap[modeltable]['hdu'] ]

                tab = astropy.table.Table( hdu.data )
                kwargs = { 'redrock_file': redrock }
                for row in tab:
                    for col in row.colnames:
                        if ( ( hdumap[modeltable]['ignore'] is not None )
                             and ( col.lower() in hdumap[modeltable]['ignore'] ) ):
                            continue
                        if ( ( hdumap[modeltable]['expect'] is not None )
                             and ( col.lower() not in hdumap[modeltable]['expect'] ) ):
                            continue
                        
                        fitstype = str( tab[col].dtype )
                        if fitstype[0:2] == "<U":
                            fitstype = "<U"
                        # We can be sure that len will be 0 or 1 here
                        # because of an exception above when checking
                        # the table
                        if len( row[col].shape ) == 1:
                            for i in range(row[col].shape[0]):
                                kwargs[ f'{col.lower()}_{i}' ] = typeconv[fitstype](row[col][i])
                        else:
                            kwargs[ col.lower() ] = typeconv[fitstype]( row[col] )

                        newobject = model( **kwargs )
                        newobject.save()

    # Done.  Return any mismatches form the parsing.
                        
    return schemamismatch

# ======================================================================

def import_tile_night_petal( basedir, tileid, night, petal, models, cumulative=True, donotload=False ):
    """Try to import a redrock-*.fits or zbest-*.fits file into the database.

    basedir should be a "tiles" subdirectory of some sort, containing all the tileid subdirectories.
    tileid, night, petal are integers
    models is the Django namespace that has all the model classes
    cumulative: if "True", will name models starting with Cumulative, else starting with Pernight
    donotload: if "True", won't actually load anything, just see if schema match
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
    return _import_fits( filetoread, tileid, petal, night, cumulative=cumulative, donotload=donotload )
    
                 
