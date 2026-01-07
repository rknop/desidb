import sys
import io
import pathlib
import argparse
import uuid
import logging

from astropy.io import fits
import astropy.table

from desidb.logger import DBLogger
from desidb.db import DBCon, Static_PV
from desidb.importtools import SchemaMismatchError

class PVLoader:

    def read_and_verify_fits( self ):
        typematch = {
            'bool'  : [ 'boolean' ],
            '>f4' : [ 'real' ],
            '>f8' : [ 'double precision' ],
            '>i2' : [ 'smallint' ],
            '>i4' : [ 'integer', 'bigint' ],
            '>i8' : [ 'bigint' ],
            '<U3' : [ 'text' ],
            '<U8' : [ 'text' ],
        }

        with fits.open( pathlib.Path( self.basedir) / self.filename ) as hdulist:
            tab = astropy.table.Table( hdulist[1].data )

        # Make sure all columns in the FITS fil are in the database table, and that datatypes match
        Static_PV._load_table_meta()

        parseinfo = {
            'filename': self.filename,
            'missingfromdata': set(),
            'indatabutshouldnotbe': set(),
            'coltypemismatch': set(),
            'datatypes': {},
            'modeltypes': {}
        }
        schemaok = True
        
        for datacol in tab.columns:
            datatype = str( tab[datacol].dtype )
            if datatype not in typematch.keys():
                raise RuntimeError( f"Unknown type for FITS column {datacol}: {datatype}" )
            parseinfo['datatypes'][datacol] = datatype

            if str(datacol).lower() not in Static_PV._tablemeta:
                parseinfo['indatabutshouldnotbe'].add( datacol )
                schemaok = False
                continue

            pgtype = Static_PV._tablemeta[ datacol.lower() ][ 'data_type' ]

            ok = False
            for possible_pgtype in typematch[ datatype ]:
                if pgtype == possible_pgtype:
                    ok = True
                    break
            if not ok:
                parseinfo['coltypemismatch'].add( datacol )
                schemaok = False

        # Look for things in the database table that are missing from the FITS file
        for field in Static_PV._tablemeta:
            pgtype = Static_PV._tablemeta[field]['data_type']
            parseinfo['modeltypes'][field] = pgtype

            # pvfile_id won't be there yet
            if field == 'pvfile_id':
                continue

            tabfield = str(field).upper()
            if tabfield not in tab.columns:
                # TODO : worry that 'YES'/'NO' is not universal psycopg / postgres!!
                parseinfo['missingfromdata'].add( tabfield )
                if Static_PV._tablemeta[field]['is_nullable'] != 'YES':
                    schemaok = False

        if not schemaok:
            raise SchemaMismatchError( parseinfo )

        return tab, parseinfo


    def get_pvfile_id( self, filename ):
        with DBCon( dictcursor=True ) as dbcon:
            dbcon.execute( "LOCK TABLE static.pvfile" )
            rows = dbcon.execute( "SELECT * FROM static.pvfile WHERE filename=%(name)s",
                                  { 'name': filename } )
            isnew = False
            if len(rows) == 0:
                pvfileid = uuid.uuid4()
                dbcon.execute( "INSERT INTO static.pvfile(id, filename) VALUES(%(id)s, %(name)s)",
                               { 'id': pvfileid, 'name': filename } )
                dbcon.commit()
                isnew = True
            elif len(rows) == 1:
                pvfileid = rows[0]['id']
            else:
                raise RuntimeError( "This should never happen." )
            
        return pvfileid, isnew


    def __call__( self ):
        # FITS tables are found in /global/cfs/cdirs/desi/science/td/pv/desi_pv/savepath_dr9_corr
        # At one point I was told to load:
        #  pv_tf.fits
        #  pv_fp.fits
        #  pv_sga.fits
        #  pv_ext.fits
        parser = argparse.ArgumentParser( 'loadpv.py',
                                          description="Load into the static.pv table",
                                          formatter_class=argparse.ArgumentDefaultsHelpFormatter )
        parser.add_argument( '-f', '--filename', required=True,
                             help="FITS table to load relative to basedir" )
        parser.add_argument( '-b', '--basedir', required=True,
                             help=( "Base path to search for files; this should be wherever "
                                    "/global/cfs/cdirs/desicollab/science/td is mounted in the container." ) )
        parser.add_argument( '-v', '--verbose', action='store_true', default=False,
                             help="Show debug logs (default: only up to info)" )
        parser.add_argument( '--verify-only', action='store_true', default=False,
                             help="Only verify file consistency, don't actually load." )
        args = parser.parse_args()

        if args.verbose:
            DBLogger.setLevel( logging.DEBUG )
        else:
            DBLogger.setLevel( logging.INFO )

        self.verify_only = args.verify_only
        self.basedir = args.basedir
        self.filename = args.filename

        try:
            tab, parseinfo = self.read_and_verify_fits()
            if len( parseinfo['missingfromdata'] ) > 0:
                DBLogger.warning( f"(Non-fatal) Missing from data file: {','.join( parseinfo['missingfromdata'] )}" )
            if len( parseinfo['indatabutshouldnotbe'] ) > 0:
                DBLogger.warning( f"(Non-fatal) Unknown column in data file: "
                                  f"{','.join( parseinfo['indatabutshouldnotbe'] )}" )
            if len( parseinfo['coltypemismatch'] ) > 0:
                DBLogger.warning( f"(Non-fatal) Column type mismatch: {','.join( parseinfo['coltypemismatch'] )}" )
        except SchemaMismatchError as smme:
            parseinfo = smme.data
            strio = io.StringIO()
            strio.write( f"Schema mismatch error for {parseinfo['filename']}:\n" )
            if len( parseinfo['missingfromdata'] ) > 0:
                strio.write( f"  Missing from data file: {','.join( parseinfo['missingfromdata'] )}\n" )
            if len( parseinfo['indatabutshouldnotbe'] ) > 0:
                strio.write( f"  Unknown column(s) in data file: {','.join( parseinfo['indatabutshouldnotbe'] )}\n" )
            if len( parseinfo['coltypemismatch'] ) > 0:
                strio.write( f"  Type mismatch: {','.join( parseinfo['coltypemismatch'] )}\n" )
            DBLogger.error( strio.getvalue() )
            sys.exit( 1 )

        if not args.verify_only:
            pvfileid, isnew = self.get_pvfile_id( self.filename )
            if isnew:
                DBLogger.info( f"Loading {len(tab)} rows into the database..." )
                data = { str(col).lower(): list( tab[col] ) for col in tab.columns }
                data['pvfile_id'] = [ pvfileid ] * len(tab)
                Static_PV.bulk_insert_or_upsert( data, die_on_conflict=True )
                DBLogger.info( "...done" )
            else:
                DBLogger.info( f"{self.filename} has already been loaded, not loading again." )
        

# ======================================================================

if __name__ == "__main__":
    loader = PVLoader()
    loader()
