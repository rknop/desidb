import sys
import re
import random
import string
import numpy
import pandas
import sqlalchemy
import astropy
from astropy.io import fits
from astropy.table import Table

import desidb.settings

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
              missingfrommodel : set of columns that were in the HDU but not the model
              missingfromdata  : set of columsn that were in the model but not the HDU
              coltypemismatch : set of columns where HDU and table didn't match
              datatypes : dictionary of column -> types parsed to Pandas from the FITS file
              modeltypes : dictionary of column -> type from database
        """
        super().__init__( *args, **kwargs )
        self.data = data

# ======================================================================
        
def _astropy_table_to_pandas( tab ):
    data = {}
    for col in tab.colnames:
        if len( tab[col].shape ) > 2:
            raise RuntimeError( f"Don't know how to deal with shape {tab[col].shape} columns" )
        elif len( tab[col].shape ) == 2:
            for i in range( tab[col].shape[1] ):
                tab.add_column( numpy.array( [ arr[i] for arr in tab[col] ] ), name=f'{col.lower()}_{i}' )
            tab.remove_column( col )
        else:
            tab.rename_column( col, col.lower() )
        
    return tab.to_pandas()

# ======================================================================

def _fits_bintables_to_pandas( fitsfile ):
    """Pass it the path to a fits file.

    Reads the FITS file.  Returns a dictionary of Extname: DataFrame for
    all bintables in the file.  For cases where the bintable had an
    array element, replace it with a bunch of individual elements that
    have _0, _1, etc. appended to the column names.

    """

    with fits.open( fitsfile, memmap=False ) as hdulist:
        bintables = {}
        for hdu in hdulist:
            if isinstance( hdu, fits.hdu.BinTableHDU ):
                if hdu.name in bintables.keys():
                    raise RuntimeError( f'Extension {hdu.name} shows up in the FITS file '
                                        f'{str(fitsfile)} more than once.' )
                df = _astropy_table_to_pandas( astropy.table.Table( hdu.data ) )
                bintables[ hdu.name ] = df

    return bintables

# ======================================================================

def _pandas_to_postgresql_model( df, model, duplicates, conflict_update=None, logger=None ):
    """Store date in a pandas DataFrame to the database in desidb.settings.DATABASES['default']

    df — pandas DataFrame
    model — django model
    duplicates — if "update", will update existing rows with the values from df
                 otherwise, will do pandas to_sql "append"
    """

    # Frankenstein's monster was not fiction.  Stitching together
    # Pandas, Django, and Postgresql here is a case study in trying to
    # use libraries but then layering on other gigantically heavy
    # libraries because the two libraries you really want don't play
    # nicely together.  This, folks, is modern programming, and it's
    # only going to get worse.  The Unix epoch being underneath all of
    # the computer code millenia from now in Vinge's "A Deepenss in the
    # Sky" becomes all that much more plausible.

    # Even this next line by itself indicates that the whole "hey, isn't
    # it great, Django abstracts out all the database details for you!"
    # thing does not live up to its promise.  No matter how nice of a
    # bow you put on it, your code is always spaghetti underneath.
    dbinfo = desidb.settings.DATABASES['default']
    engine = sqlalchemy.create_engine( f'postgresql://{dbinfo["USER"]}:{dbinfo["PASSWORD"]}'
                                       f'@{dbinfo["HOST"]}:{dbinfo["PORT"]}/{dbinfo["NAME"]}' )

    # And then *these* lines... don't get me started.  (More started.)
    # Well, OK, I'm started.  I suppose you could say "it's your fault
    # for creating tables with '"."' in the name."  I did this so that I
    # could put tables in different Postgresql schema.  You might say
    # "don't try to use Postgresql schema, because Django doesn't
    # support them".  But, the fact is, I want to be able to use this
    # database directly outside of Django as well, and because there are
    # multiple data releases that have the same tables, Postgresql
    # schemas is the obvious way to go!  So, then, you might say, "Well,
    # don't use Django if you don't want the underlying database to be
    # opqaue".  Perhaps.  There is a part of me that does think I should
    # be reinventing the wheel so I can get just a wheel.
    match = re.search( '^(.*)"."(.*)$', model._meta.db_table )
    schema = match.group(1)
    tablename = match.group(2)

    # logger.debug( f'Working on <model>' )
    try:
        if duplicates == "update":
            # The notion of "just using" pandas to_sql was so nice... until
            # I realized that that works for insert, but not update.  Sigh.

            skipcolumns = set()
            for field in model._meta.fields:
                if ( field.unique ):
                    skipcolumns.add( field.name )
            for uniques in model._meta.unique_together:
                for fieldname in uniques:
                    skipcolumns.add( fieldname )

            if ( conflict_update is not None ) and ( len(skipcolumns) > 0 ):
                conflicttext = f" ON CONFLICT {conflict_update} DO UPDATE SET "
                first = True
                for field in model._meta.fields:
                    if not field.name in skipcolumns:
                        if first:
                            first = False
                        else:
                            conflicttext += ","
                        conflicttext += f" {field.name}=EXCLUDED.{field.name}"
            else:
                conflicttext = ""
            # ... but it's not even that easy.  Since Django is using a
            #   primary key that auto updates from a sequence, we need
            #   to make sure not to include the primary key column in
            #   the insert into the main table from the temp table.
            # selectcolumns = ""
            # first = True
            # for field in model._meta.fields:
            #     if not field.primary_key:
            #         if first:
            #             first = False
            #         else:
            #             selectcolumns += ","
            #         selectcolumns += field.name
            # insertcolumns = f"({selectcolumns})"
            insertcolumns = ""
            selectcolumns = "*"
                        
            barf = "".join( random.sample( string.ascii_lowercase, 10 ) )
            with engine.connect() as dbcon:
                # I would like to use CREATE TEMP TABLE, but I haven't figured out how to
                #   get all the session stuff to work right with sqlalchemy and pandas;
                #   there's also the issue of schema, which doesn't work with CREATE TEMP TABLE.
                sql = f"CREATE TABLE {schema}.{tablename}_{barf} ( LIKE {schema}.{tablename} INCLUDING DEFAULTS )"
                dbcon.execute( sqlalchemy.text( sql ) )
                df.to_sql( f'{tablename}_{barf}', schema=schema, con=dbcon, if_exists="append", index=False )
                result = dbcon.execute( sqlalchemy.text( f"INSERT INTO {schema}.{tablename}{insertcolumns} "
                                                         f"SELECT {selectcolumns} FROM {schema}.{tablename}_{barf} "
                                                         f"{conflicttext}" ) )
                sql = f"DROP TABLE {schema}.{tablename}_{barf}"
                dbcon.execute( sqlalchemy.text( sql ) )
                if logger is not None:
                    logger.debug( f'Loaded {result.rowcount} of {len(df)} rows into {tablename}' )
        else:
            # logger.debug( 'Loading table {tablename}' )
            df.to_sql( tablename, schema=schema, con=engine, if_exists="append", index=False )
            if logger is not None:
                logger.debug( f'Loaded {len(df)} rows into {tablename}' )
    except Exception as e:
        sys.stderr.write( "Something bad has happened.\n" )
        import pdb; pdb.set_trace()
        sys.stderr.write( "Uh huh." )
