import sys
import os
import requests
import json

def main():
    # Set the variables url, username, and password.
    # username will be "desi", and password will be the
    # standard desi password.  (I read it from a secrets file.)
    
    url = "http://desidb.desidb.production.svc.spin.nersc.org"
    with open( os.path.join( os.getenv("HOME"), "secrets", "decatdb_desi_desi" ) ) as ifp:
        username, password = ifp.readline().strip().split()
    # username = 'desi'
    # password = '<standard desi password>'
        
    # First, log in.  Because of Django's prevention against cross-site
    # scripting attacks, there is some dancing about you have to do in
    # order to make sure it always gets the right "csrftoken" header.

    rqs = requests.session()
    resp = rqs.get( f'{url}/accounts/login/' )
    resp = rqs.post( f'{url}/accounts/login/',
                     data={ "username": username,
                            "password": password,
                            "csrfmiddlewaretoken": rqs.cookies['csrftoken'] } )
    # Check login success here....
    csrfheader = { 'X-CSRFToken': rqs.cookies['csrftoken'] }

    # Next, send your query, passing the csrfheader with each request
    # You send the query as a json-encoded dictionary with two fields:
    #   'query' : the SQL query, with %(name)s for things that should
    #                be substituted.  (This is standard psycopg2.)
    #   'subdict' : a dictionary of substitutions for %(name)s things in your query
    #
    # The backend is to this web API call is readonly, so you can't
    # bobby tables this.  However, this does give you the freedom to
    # read anything from the tables if you know the schema.
    # (Some relevant schema are at the bottom.)
    
    # query = ( 'SELECT f.targetid,f.tileid,f.petal_loc,f.objtype,'
    #           '       f.target_ra,f.target_dec,e.mjd,e.expid,e.fiber_x,e.fiber_y '
    #           'FROM everest.tiles_fibermap f '
    #           'INNER JOIN everest.tiles_expfibermap e '
    #           'ON f.targetid=e.targetid AND f.tileid=e.tileid AND f.petal_loc=e.petal_loc '
    #           'WHERE q3c_radial_query(target_ra,target_dec,%(ra)s,%(dec)s,%(radius)s) '
    #           'ORDER BY e.mjd' )
    query = ( 'SELECT f.targetid,f.tileid,f.petal_loc,f.objtype,'
              '       f.target_ra,f.target_dec,r.z,r.zerr,r.zwarn,r.spectype '
              'FROM everest.tiles_fibermap f '
              'INNER JOIN everest.tiles_redshifts r '
              'ON f.cumultile_id=r.cumultile_id AND f.targetid=r.targetid '
              'WHERE q3c_radial_query(f.target_ra,f.target_dec,%(ra)s,%(dec)s,%(radius)s) ' )
    subdict = { "ra": 149.204442579316, "dec": 1.84153681664887, "radius": 1./3600. }
    result = rqs.post( f'{url}/db/runsqlquery', headers=csrfheader,
                       json={ 'query': query, 'subdict': subdict } )


    # Look at the response.  It will be a JSON encoded dict with two fields:
    #  { 'status': 'ok',
    #    'rows': [...] }
    # where rows has the rows returned by the SQL query; each element of the row
    # is a dict.  There's probably a more efficient way to return this. (base64 encoded Pandas?)

    if result.status_code != 200:
        sys.stderr.write( f"ERROR: got status code {result.status_code} ({result.reason})\n" )
    else:
        data = json.loads( result.text )
        if ( 'status' not in data ) or ( data['status'] != 'ok' ):
            sys.stderr.write( "Got unexpected response" )
        else:
            print( f'Got {len(data["rows"])} rows' )
            for row in data['rows']:
                print( '==============================' )
                print( json.dumps( row, indent=4 ) )

# ======================================================================
if __name__ == "__main__":
    main()
