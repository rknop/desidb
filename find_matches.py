import sys
import collections.abc
import numbers
import textwrap

import numpy as np
import psycopg
from psycopg import sql
import pyarrow
import pandas


def find_observed_targets( ras, decs, match_radius=1., release="daily", passwd=None ):
    """Given a list of coordinates, find the ones that have desi observations.

    Parameters
    ----------
      ras : sequence of float (e.g. list of float, or numpy array of float)
        RAs of the coordinates

      decs : sequence of float
        Decs of the coordinates

      match_radius : float, default 1.0
        How close the coordinates in the database must be to the passed
        coordinates to count as the same object, in arcseconds.

      release : str, default "daily"
        Which release to search

    Return
    ------
       found, observations

         found is an array of boolean, whether any observations were found
         observations is a pandas dataframe with columns:
            index : index into your ras and decs lists
            ra : from your list
            dec : from your list
            targetid : desi targetid
            petal_loc
            device_loc
            coadd_numnight
            mean_fiber_ra
            mean_fiber_dec

         The same index may show up more than once, if DESI has listed
         more than one target.  (This will happen if the target was in
         SV3 and main, for instance.)

         If there was no match, then many of the following columns will
         be None or <NA> or something like that.

         Ignore the columns "firstnight" and "lastnight", they aren't
         actually populated.

    """

    if passwd is None:
        raise ValueError( "Must pass desi password" )

    if ( ( not isinstance( ras, collections.abc.Sequence ) ) or
         ( not isinstance( decs, collections.abc.Sequence ) ) or
         ( len(ras) != len(decs) )
        ):
        raise ValueError( "ras and decs must be lists/arrays of the same length." )

    con = psycopg.connect( dbname="desidb", user="desi", password=passwd, host="desidb-rr.lbl.gov" )
    cursor = con.cursor()

    cursor.execute( "CREATE TEMP TABLE temp_ra_dec(dex int, ra double precision, dec double precision)" )
    with cursor.copy( "COPY temp_ra_dec(dex,ra,dec) FROM stdin" ) as copier:
        for i, (ra, dec) in enumerate( zip( ras, decs ) ):
            copier.write_row( [ i, ra, dec ] )

    q = sql.SQL( textwrap.dedent(
        """\
        SELECT i.dex, i.ra, i.dec, o.targetid, o.petal_loc, o.device_loc,
               o.coadd_numnight, o.firstnight, o.lastnight, o.mean_fiber_ra, o.mean_fiber_dec
        FROM temp_ra_dec i
        LEFT JOIN {release}.tiles_fibermap o
               ON q3c_join(i.ra, i.dec, o.mean_fiber_ra, o.mean_fiber_dec, {radius})
        """
    ) ).format( release=sql.Identifier(release), radius=match_radius/3600. )

    cursor.execute( q )
    rows = cursor.fetchall()

    con.close()

    pa = pyarrow.table( list(zip(*rows)), names=[ 'index', 'ra', 'dec', 'targetid', 'petal_loc', 'device_loc',
                                                  'coadd_numnight', 'firstnight', 'lastnight',
                                                  'mean_fiber_ra', 'mean_fiber_dec' ] )
    df = pa.to_pandas( types_mapper=pandas.ArrowDtype )
    foundindexes = df[ ~df.mean_fiber_ra.isna() ]['index'].unique()
    found = np.full( (len(ras),), False )
    found[ foundindexes ] = True

    return found, df


# ======================================================================
# main is just for testing

def main():
    ras = [ 279.08497764829053, 279.4297906828813, 180. ]
    decs = [ 36.83189461875713, 36.351102154326476, 42. ]

    found, observations = find_observed_targets( ras, decs, passwd=sys.argv[1] )
    import pdb; pdb.set_trace()
    pass


if __name__ == "__main__":
    main()
