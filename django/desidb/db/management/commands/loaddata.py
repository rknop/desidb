import sys
import os
import re
import pathlib
import logging
from smtplib import SMTP
import email.message
from django.core.management.base import BaseCommand, CommandError
from db.management.commands._importredrock import import_tile_night_petal, import_healpix
from db.management.commands._import import SchemaMismatchError, TopLevelEntryExistsError

class Command(BaseCommand):
    # If these next three aren't overridden, then the code will error out somewhere
    basetiledir = None        # Like "/data/everest/tiles/cumulative"
    basehealpixdir = None     # Like "/data/everest/healpix"
    models = None             # Like everest.models

    emailfrom = "raknop@lbl.gov"
    emailto = "raknop@lbl.gov"       # Override with None to disable email

    datematch = re.compile( '^[0-9]{8}$' )
    numbersmatch = re.compile( '^[0-9]+$' )

    def __init__( self, logger=None, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        if logger is None:
            logger = logging.getLogger( "main" )
            logout = logging.StreamHandler( sys.stderr )
            logger.addHandler( logout )
            logout.setFormatter( logging.Formatter( f'[%(asctime)s - %(levelname)s] - %(message)s' ) )
            logger.setLevel( logging.INFO )
        self.logger = logger


    def add_arguments( self, parser ):
        parser.add_argument( '-t', '--tile', default=None, type=int,
                             help="Load all petals of all nights of this tile from <base>/tiles/cumulative" )
        parser.add_argument( '-n', '--tiles-newer', default=None, type=int,
                             help=( "yyyymmdd ; load all tiles in subdirectories of this date or newer. "
                                    "With --tile, only in that tile subdirectory otherwise for all tiles" ) )
        parser.add_argument( '-s', '--survey', default=None, type=str,
                             help="Load healpix for this survey (e.g. 'main', 'sv1', 'sv2', or 'sv3')" )
        parser.add_argument( '-p', '--program', default=None, type=str,
                             help="Load healpix for this program (requires --survey; default: all for survey)" )
        parser.add_argument( '-d', '--healpixd100', default=None, type=int,
                             help=( 'Healpix / 100 (e.g. 381 loads all healpix 38100 through 38199 ). '
                                    'requires --survey and --program; default: load all' ) )
        parser.add_argument( '--verify-only', default=False, action='store_true',
                             help="Don't actually load, just verify that files work." )

    def _build_schema_mismatch_info( self, data, loginfo=[] ):
        loginfo = loginfo.copy()
        loginfo.append( f'Models: {str(self.models)}' )
        loginfo.append( f'Redrock version: {data["rrver"]}' )
        if len( data['missingdatablock'] ) > 0:
            loginfo.append( f"Missing HDUs: {data['missingdatablock']}" )
        if len( data['extradatablock'] ) > 0:
            loginfo.append( f"Unexpected HDUs: {data['extradatablock']}" )
        for model, smm in data['models'].items():
            if ( ( len( smm['missingfrommodel'] ) > 0 ) or
                 ( len( smm['missingfromdata'] ) > 0 ) or
                 ( len( smm['coltypemismatch'] ) > 0 ) ):
                loginfo.append( f"MODEL: {model}" )
                if len( smm['missingfrommodel'] ) > 0:
                    loginfo.append( f"...Missing model columns: {smm['missingfrommodel']}" )
                if len( smm['missingfromdata'] ) > 0:
                    loginfo.append( f"...(Non-fatal) missing data columns: {smm['missingfromdata']}" )
                if len( smm['coltypemismatch'] ) > 0:
                    for col in smm['coltypemismatch']:
                        loginfo.append( f"...{col} datatype mismatch; "
                                        f"is {smm['datatypes'][col]} in the data, and "
                                        f"{smm['modeltypes'][col]} in the model." )
        return loginfo
                        
    def _print_schema_mismatch( self, data, loginfo=[], subject=None, noemail=False ):
        loginfo = self._build_schema_mismatch_info( data, loginfo=loginfo )
        self.logger.error( "\n".join( loginfo ) + "\n" )
        if self.emailto is not None and not noemail:
            emailmsg = email.message.EmailMessage()
            emailmsg['To'] = self.emailto
            emailmsg['From'] = self.emailfrom
            if subject is not None:
                emailmsg['Subject'] = subject
            else:
                emailmsg['Subject'] = "Message from DesiDB loaddata Command"
            emailmsg.set_content( "\n".join( loginfo ) + "\n" )
            with SMTP( "smtp.lbl.gov" ) as smtp:
                smtp.send_message( emailmsg )


    def _load_tile_night_directory( self, tile, night ):    
        for petal in range(0, 10):
            try:
                data = import_tile_night_petal( self.basetiledir, tile, night, petal, self.models,
                                                donotload=self.donotload, logger=self.logger )
            except SchemaMismatchError as e:
                loginfo = [ f"Schema mismatch error in tile {tile}, night {night}, petal {petal}" ]
                self._print_schema_mismatch( e.data, loginfo, subject="DesidDB Schema Mismatch" )
                raise e
            except FileNotFoundError as e:
                self.logger.warning( f"FileNotFoundError for tile {tile}, night {night}, "
                                     f"petal {petal}: {str(e)}" )
                continue
            self.logger.info( f"Imported tile {tile:6d}, night {night}, petal {petal}" )
            self.logger.debug( "\n".join( self._build_schema_mismatch_info( data ) ) )

    def _load_tile_directory( self, tile, nightge=None ):
        tiledir = pathlib.Path( self.basetiledir ) / str(tile)
        if not tiledir.is_dir():
            raise Exception( f"Tiles directory {str(tiledir)} isn't a directory" )
        for night in tiledir.iterdir():
            if not self.datematch.search( night.name ):
                self.logger.warning( "Subdirectory {night.name} doesn't match yyyymmdd, skipping" )
            else:
                if ( nightge is not None ) and ( int(night.name) < int(nightge) ):
                    continue
                self._load_tile_night_directory( tile, int(night.name) )


    def _load_all_tiles_newer_than( self, nightge ):
        basedir = pathlib.Path( self.basetiledir )
        toload = []
        if not basedir.is_dir():
            raise RuntimeError( f"{str(basedir)} is not a directory" )
        self.logger.debug( f"Going though all tile directories to find yyyymmdd subdirectories..." )
        for tiledir in basedir.iterdir():
            if self.numbersmatch.search( tiledir.name ) and tiledir.is_dir():
                itile = int(tiledir.name)
                for night in tiledir.iterdir():
                    if self.datematch.search( night.name ):
                        inight = int(night.name)
                        if inight >= nightge:
                            toload.append( ( inight, itile ) )
        self.logger.debug( f"...made list of {len(toload)} yyyymmdd directories." )

        # Go from older nights to newer nights
        toload.sort()

        self.logger.info( f"Loading {len(toload)} total tile/night directories" )
        ndone = 0
        for inight, itile in toload:
            self.logger.info( f"Loaded {ndone} of {len(toload)} tile/nights" )
            self._load_tile_night_directory( itile, inight )
            ndone += 1


    def _load_healpixd100_directory( self, healpixd100, survey, program ):
        if self.basehealpixdir is None:
            raise FileNotFoundError( "Healpix directories aren't known" )
        direc = pathlib.Path( self.basehealpixdir ) / survey / program / str(healpixd100)
        if not direc.is_dir():
            raise FileNotFoundError( "Healpix directory {str(direc)} isn't a directory" )
        for healpix in direc.iterdir():
            if not self.numbersmatch.search( healpix.name ):
                self.logger.warning( "subdirectory {str(healpix)} isn't all numbers, skipping" )
            else:
                try:
                    data = import_healpix( self.basehealpixdir, survey, program, int(healpix.name), self.models,
                                           donotload=self.donotload, logger=self.logger )
                except SchemaMismatchError as e:
                    loginfo = [ f"Schema mismatch error for survey {survey}, "
                                f"program {program}, healpix {healpix.name}" ]
                    self._print_schema_mismatch( e.data, loginfo, subject="DesiDB Schema Mismatch" )
                    raise e
                except FileNotFoundError as e:
                    self.logger.error( f'Healpix FITS redrock file for survey={survey}, program={program}, '
                                       f'healpix={healpix.name} not found!  Skipping.' )
                    continue
                except TopLevelEntryExistsError as e:
                    self.logger.warning( f'Healpix entry already exists: survey={survey}, program={program}, '
                                         f'healpix={healpix.name}.  Skipping.' )
                    continue
                self.logger.info( f"Imported healpix {healpix.name}, survey {survey}, program {program}" )
                self.logger.debug( "\n".join( self._build_schema_mismatch_info( data ) ) )
        self.logger.info( f"Imported healpix//100 directory {str(direc)}" )


    def _load_healpix_survey_program( self, survey, program ):
        direc = pathlib.Path( self.basehealpixdir ) / survey / program
        if not direc.is_dir():
            raise FileNotFoundError( "Healpix program directory {str(direc)} isn't a directory" )
        for healpixd100 in direc.iterdir():
            if self.numbersmatch.search( healpixd100.name) and ( int(healpixd100.name) < 1000 ):
                self._load_healpixd100_directory( healpixd100.name, survey, program )
                self.logger.info( f"Imported healpix program directory {direc}" )
            else:
                self.logger.warning( f"Subdirectory {str(healpixd100)} isn't a number 0-999, skipping" )


    def _load_healpix_survey( self, survey ):
        direc = pathlib.Path( self.basehealpixdir ) / survey
        if not direc.is_dir():
            raise FileNotFoundError( "Healpix survey directory {str(direc)} isn't a directory" )
        for programdir in direc.iterdir():
            if programdir.is_dir():
                self._load_healpix_survey_program( survey, programdir.name )


    def handle( self, **options ):
        self.donotload = options['verify_only']
        
        if options['verbosity'] > 1:
            self.logger.setLevel( logging.DEBUG )
        elif options['verbosity'] == 0:
            self.logger.setLevel( logging.WARNING )
        else:
            self.logger.setLevel( logging.INFO )

        if self.models is None:
            raise NotImplementedError( "Need to call a subclass of db.management.commands.loaddata.Command" )

        if ( options['tile'] is not None ):
            self._load_tile_directory( options['tile'], nightge=options['tiles_newer'] )
        else:
            if options['tiles_newer'] is not None:
                 startdate = int( options['tiles_newer'] )
                 self._load_all_tiles_newer_than( startdate )

        if options['survey'] is not None:
            if options['program'] is not None:
                if options['healpixd100'] is not None:
                    self._load_healpixd100_directory( options['healpixd100'], options['survey'], options['program'] )
                else:
                    self._load_healpix_survey_program( options['survey'], options['program'] )
            else:
                self._load_healpix_survey( options['survey'] )
