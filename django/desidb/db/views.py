import json
import django.views
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
import desidb.settings
import psycopg2
import psycopg2.extras


# ======================================================================
# A low-level query interface.
#
# This is very scary, of course, so make sure desi is a readonly user in
# the database!

@method_decorator(login_required, name='dispatch')
class RunSQLQuery(django.views.View):
    def post( self, request, *args, **kwargs ):
        data = json.loads( request.body )
        if not 'query' in data:
            raise ValueError( "Must pass a query" )
        subdict = {}
        if 'subdict' in data:
            subdict = data['subdict']
        with open( "/secrets/desidb_desi_postgres_password" ) as ifp:
            dbpassword = ifp.readline()
        dbpassword.strip()
        dbinfo = desidb.settings.DATABASES['default']
        dbname = dbinfo['NAME']
        dbhost = dbinfo['HOST']
        dbport = dbinfo['PORT']
        dbuser = 'desi'
        dbconn = psycopg2.connect( dbname=dbname, host=dbhost, port=dbport,
                                   user=dbuser, password=dbpassword,
                                   cursor_factory=psycopg2.extras.RealDictCursor )
        # sys.stderr.write( f'Query is {data["query"]}, subdict is {subdict}\n' )
        cursor = dbconn.cursor()
        cursor.execute( data['query'], subdict )
        return JsonResponse( { 'status': 'ok', 'rows': cursor.fetchall() } )
