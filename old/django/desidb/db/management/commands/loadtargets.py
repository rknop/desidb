import sys
import os
import re
import io
import pathlib
import logging
import numpy
import django.db.models
from django.core.management.base import BaseCommand, CommandError
from db.management.commands._import import _fits_bintables_to_pandas, _pandas_to_postgresql_model, SchemaMismatchError
from django.core.exceptions import FieldDoesNotExist
import db.models
from db.models import TargetFiles, MainTargets, SV1Targets, SV2Targets, SV3Targets, BackupTargets

_fitsmatch = re.compile( '.fits(.fz)?$' )

class Command(BaseCommand):
    def __init__( self, logger=None, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        if logger is None:
            logger = logging.getLogger("main")
            logout = logging.StreamHandler( sys.stderr )
            logger.addHandler( logout )
            formatter = logging.Formatter( f'[%(asctime)s - %(levelname)s] - %(message)s',
                                           datefmt='%Y-%m-%d %H:%M:%S' )
            logout.setFormatter( formatter )
            logger.setLevel( logging.INFO )
        self.logger = logger

    def add_arguments( self, parser ):
        parser.add_argument( '-d', '--dir', required=True,
                             help="Load this .fits file, or load all .fits files underneath this directory" )
        parser.add_argument( '-s', '--survey', default=None,
                             help='Survey; one of main, sv1, sv2, sv3, backup, or missing-1.0.0' )
        parser.add_argument( '-w', '--whenobs', required=True, help="whenobs (bright, dark, or backup)" )
        parser.add_argument( '--secondary', default=False, action='store_true',
                             help="Store to SecondaryTargets table (otherwise, MainTargets table)" )
        parser.add_argument( '--skip-existing', action='store_true', default=False,
                             help="Don't load the file if it's already in the targetfiles table." )
        parser.add_argument( '--verify-only', default=False, action='store_true',
                             help="Don't actually load, just verify that files work." )


    def _load_secondary_fits( self, filepath, whenobs=None, verify_only=False, skip_existing=False ):
        raise NotImplementedError( "Secondary loading not yet implemented" )
        

    def _load_main_fits( self, filepath, survey=None, whenobs=None, verify_only=False, skip_existing=False ):
        # Check to see if the file already exists
        if skip_existing:
            curtf = TargetFiles.objects.all().filter( filename=str(filepath) )
            if len(curtf) > 0:
                return False

        dfs = _fits_bintables_to_pandas( filepath )
        # We want to look at the "TARGETS" HDU
        df = dfs['TARGETS']
        # Add the survey and whenobs columns
        df['survey'] = survey
        df['whenobs'] = whenobs

        surveymodel = { "main" : MainTargets,
                        "sv1": SV1Targets,
                        "sv2": SV2Targets,
                        "sv3": SV3Targets,
                        "backup": BackupTargets,
                        # "missing-1.0.0": (Figure this out)
        }
        if survey in surveymodel.keys():
            model = surveymodel[survey]
        else:
            raise ValueError( f"Invalid survey {survey}" )

        # Add the "targetfiles" entry
        if verify_only:
            df['targetfile_id'] = numpy.int32( -1 )
        else:
            tf = TargetFiles.objects.get_or_create( filename=str(filepath) )[0]
            df['targetfile_id'] = numpy.int32( tf.id )
        
        # Verify column match
        typematch = {
            'bool' : [ django.db.models.BooleanField ],
            'uint8' : [ django.db.models.SmallIntegerField ],
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
        _pandas_to_postgresql_model( df, model, duplicates=None, logger=self.logger )

        return True
        
    def _load_directory( self, direc, model=None, survey=None, whenobs=None, secondary=False,
                         verify_only=False, skip_existing=False, nloaded=0 ):
        global _fitsmatch
        
        if survey is None:
            raise ValueError( "Must specify a survey" )
        if whenobs is None:
            raise ValueError( "Must specify a whenobs" )

        if direc.is_file():
            if _fitsmatch.search( direc.name ):
                self.logger.info( f'Loading FITS file {direc.name}...' )
                if secondary:
                    did = self._load_secondary_fits( direc, whenobs=whenobs, verify_only=verify_only,
                                                     skip_existing=skip_existing )
                else:
                    did = self._load_main_fits( direc, survey=survey, whenobs=whenobs, verify_only=verify_only,
                                                skip_existing=skip_existing )
                if did:
                    nloaded += 1
                else:
                    self.logger.info( f'Skipped already-existing file {str(direc)}' )
            else:
                self.logger.debug( f'Skipping non-fits file {direc.name}' )
        else:
            if direc.is_dir():
                self.logger.info( f'Loading files in {direc}' )
                for f in direc.iterdir():
                    nloaded = self._load_directory( f, survey=survey, whenobs=whenobs, nloaded=nloaded,
                                                    secondary=secondary, verify_only=verify_only,
                                                    skip_existing=skip_existing )
                    self.logger.info( f'Loaded {nloaded} FITS files so far.' )
            else:
                self.logger.warning( f'{str(direc)} is neither a file nor a directory....' )

        return nloaded
                
    def handle( self, **options ):
        if options['verbosity'] > 1:
            self.logger.setLevel( logging.DEBUG )
        elif options['verbosity'] == 0:
            self.logger.setLevel( logging.WARNING )
        else:
            self.logger.setLevel( logging.INFO )

        direc = pathlib.Path( options["dir"] )
            
        if options['survey'] not in ( 'main', 'sv1', 'sv2', 'sv3', 'backup', 'missing-1.0.0' ):
            raise ValueError( 'Invalid survey' )
        try:
            n = self._load_directory( direc, survey=options['survey'], secondary=options["secondary"],
                                      whenobs=options["whenobs"], verify_only=options["verify_only"],
                                      skip_existing=options["skip_existing"] )
            self.logger.info( f'Loaded {n} FITS files.' )
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
                self.logger.error( err.getvalue() )

