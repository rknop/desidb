import pathlib
import argparse
import logging
import uuid

import psycopg.sql

from astropy.io import fits
import astropy.table

import desidb.db
from desidb.db import DBCon
from desidb.logger import DBLogger

class TargetLoader:

    _fitsmatch = re.compile( '.fits(.fz)?$' )

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )


    def _load_secondary_fits( self, filepath, whenobs=None, verify_only=False, skip_existing=False ):
        raise NotImplementedError( "Secondary loading not yet implemented" )
        

    def load_main_fits( self, filepath ):
        # Check to see if the file already exists
        if skip_existing:
            with DBCon() as dbcon:
                rows, cols = dbcon.execute( "SELECT * FROM targetfiles WHERE filename=%(name)",
                                            { 'filename': str(filepath) } )
                if len( rows ) > 0:
                    return False

        bintables = {}
        with fits.open( filepath ) as hdulist:
            for hdu in hdulist:
                if isinstance( hdu, fits.hdu.BinTableHDU ):
                    if hdu.name in bintables.keys():
                                                raise RuntimeError( f"Extension {hdu.name} shows up in the FITS file "
                                            f"{filepath} more than once." )
                    bintables[ hdu.name ] = astropy.table.Table( hdu.data )

        # We want to look at the "TARGETS" HDU
        tab = bintables[ 'TARGETS' ]
        # Add the survey and whenobs columns
        tab.add_column( self.survey, name='survey' )
        tab.add_column( self.whenobs, name='whenobs' )

        surveymodel = { "main" : desidb.db.General_MainTargets,
                        # "sv1": desidb.db.General_SV1Targets,
                        # "sv2": desidb.db.General_SV2Targets,
                        "sv3": desidb.db.General_SV3Targets,
                        # "backup": desidb.db.General_BackupTargets,
        }
        if survey in surveymodel.keys():
            model = surveymodel[survey]
        else:
            raise ValueError( f"Invalid survey {survey}" )

        # Add the "targetfiles" entry if necessary
        if self.verify_only:
            targetfileid = uuid.uuid4()
        else:
            with DBCon( dictcursor=True ) as dbcon:
                dbcon.execute( "LOCK TABLE general.targetfiles" )
                rows = dbcon.execute( "SELECT * FROM general.targetfiles WHERE filename=%(name)",
                                      { 'name': str(filepath) } )
                if len(rows) > 1:
                    raise RuntimeError( "This should never happen." )
                elif len(rows) == 1:
                    targetfileid = rows[0]['id']
                else:
                    targetfileid = uuid.uuid4()
                    dbcon.execute( "INSERT INTO general.targetfiles(id,filename) VALUES (%(id),%(name))",
                                   { 'id': targetfileid, 'name': str(filepath) } )
                    dbcon.commit()

        tab.add_column( str(targetfileid), name='targetfile_id' )
        
        # Verify column match
        typematch = {
            'bool' : [ 'boolean' ],
            'uint8' : [ 'smallint' ],
            '>f4' : [ 'real' ],
            '>f8' : [ 'double precision' ],
            '>i16' : [ 
            'float32' : [ db.models.RealField ],
            'float64' : [ django.db.models.FloatField ],
            'int16' : [ django.db.models.SmallIntegerField ],
            'int32' : [ django.db.models.IntegerField, django.db.models.fields.AutoField ],
            'int64' : [ django.db.models.BigIntegerField ],
            'object' : [ django.db.models.CharField, django.db.models.TextField ]
        }
        missingfromdf = set()
        missingfrommodel = set()
        typemismatch = set()
        modeltypes = {}
        datatypes = {}
        keepcolumns = set()
        okmissingdatasvx = set( ( 'desi_target', 'bgs_target', 'scnd_target', 'mws_target' ) )
        schemaok = True
        for dbfield in model._meta.get_fields():
            # Skip the auto-generated primary key, we
            # don't want that in the pandas dataframe
            if dbfield.name == 'id':
                continue
            if type(dbfield) == django.db.models.fields.related.ForeignKey:
                dbfield_name = f'{dbfield.name}_id'
                modeltypes[ dbfield_name ] = type( dbfield.target_field )
            else:
                dbfield_name = dbfield.name
                modeltypes[ dbfield.name ] = type(dbfield)
            if dbfield_name not in df.columns:
                missingfromdf.add( dbfield_name )
                if not ( ( survey in ( 'sv1', 'sv2', 'sv3' ) ) and ( dbfield_name in okmissingdatasvx ) ):
                    schemaok = False
        for column in df.columns:
            datatype = str( df[column].dtype )
            datatypes[ column ] = datatype
            if datatype not in typematch.keys():
                raise RuntimeError( f'Unknown type for FITS column {column}: {datatype}' )
            try:
                dbcol = model._meta.get_field( column )
                keepcolumns.add( column )
                if type(dbcol) == django.db.models.fields.related.ForeignKey:
                    dbtype = type( dbcol.target_field )
                else:
                    dbtype = type( dbcol )
                if dbtype not in typematch[datatype]:
                    typemismatch.add( column )
                    schemaok = False
            except FieldDoesNotExist as ex:
                pass
                # missingfrommodel.add( column )
                # schemaok = False
                # The database has way fewer columns than the FITS files by design

        # Filter out the columns that we don't want to save to the database
        df = df[ keepcolumns ]
                
        if not schemaok:
            smm = {
                'filepath': filepath,
                'missingdatablock': set(),
                'extradatablock': set(),
                'models': {
                    str( model ) : {
                        'missingfrommodel': missingfrommodel,
                        'missingfromdata': missingfromdf,
                        'coltypemismatch': typemismatch,
                        'datatypes': datatypes,
                        'modeltypes': modeltypes }
                    }
                }
            raise SchemaMismatchError( smm )

        # Don't continue if we're just verifying
        if verify_only:
            return True

        # duplicates=None will cause a crash if a unique constraint is violated
        _pandas_to_postgresql_model( df, model, duplicates=None )

        return True
        
    def load_directory( self, direc ):
        if survey is None:
            raise ValueError( "Must specify a survey" )
        if whenobs is None:
            raise ValueError( "Must specify a whenobs" )

        if direc.is_file():
            if self._fitsmatch.search( direc.name ):
                DBLogger.info( f'Loading FITS file {direc.name}...' )
                if secondary:
                    did = self.load_secondary_fits( direc )
                else:
                    did = self.load_main_fits( direc )

                if did:
                    nloaded += 1
                else:
                    DBLogger.info( f'Skipped already-existing file {str(direc)}' )

            else:
                DBLogger.debug( f'Skipping non-fits file {direc.name}' )

        else:
            if direc.is_dir():
                DBLogger.info( f'Loading files in {direc}' )
                for f in direc.iterdir():
                    nloaded += self._load_directory( f )
                    DBLogger.info( f'Loaded {nloaded} FITS files so far.' )
            else:
                DBLogger.warning( f'{str(direc)} is neither a file nor a directory....' )

        return nloaded


    def __call__():
        parser = argparse.ArgumentParser( 'loadtargets.py',
                                          description="Load the target tables in the general schema",
                                          formatter_class=argparse.ArgumentDefaultsHelpFormatter )
        parser.add_argument( '-d', '--dir', required=True,
                             help="Load this .fits file, or load all .fits files underneath this directory" )
        parser.add_argument( '-s', '--survey', default=None,
                             help='Survey; one of main, sv1, sv2, sv3, backup, or missing-1.0.0' )
        parser.add_argument( '-w', '--whenobs', required=True, help="whenobs (bright, dark, or backup)" )
        parser.add_argument( '--secondary', default=False, action='store_true',
                             help="Store to secondarytargets table (otherwise, maintargets table)" )
        parser.add_argument( '--skip-existing', action='store_true', default=False,
                             help="Don't load the file if it's already in the targetfiles table." )
        parser.add_argument( '--verify-only', default=False, action='store_true',
                             help="Don't actually load, just verify that files work." )
        parser.add_argument( '-v', '--verbose', default=False, action='store_true',
                             help="Show debug log info (default: just info)" )

        args = parser.parse_args()

        if args.verbose:
            DBLogger.setLevel( logging.DEBUG )
        else:
            DBLogger.setLevel( logging.INFO )

        self.survey = args.survey
        self.secondayr = args.secondary
        self.whenobs = args.whenobs
        self.verify_only = args.verify_only
        self.skip_existing = args.skip_existing
        
        if self.survey not in ( 'main', 'sv1', 'sv2', 'sv3', 'backup', 'missing-1.0.0' ):
            raise ValueError( 'Invalid survey' )
        try:
            nloaded = self.load_directory( pathlib.Path(args.dir) )
            DBLogger.info( f'Loaded {n} FITS files.' )
        except SchemaMismatchError as smm:
            err = io.StringIO()
            err.write( f'Schema mismatch error for file {smm.data["filepath"]}\n' )
            for model, info in smm.data["models"].items():
                err.write( f'  Model {model}:\n' )
                err.write( f'    Missing from model: {info["missingfrommodel"]}\n' )
                err.write( f'    Missing from data: {info["missingfromdata"]}\n' )
                for col in info["coltypemismatch"]:
                    err.write( f'    {col} is {info["datatypes"][col]} in data but '
                               f'{info["modeltypes"][col]} in model' )
                DBLogger.error( err.getvalue() )



# ======================================================================

def main():
    loader = TargetLoader()
    loader()

if __name__ == "__main__":
    main()
