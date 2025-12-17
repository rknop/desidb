import sys
import re
import pathlib
from daily import models

def hack():
    basedir = pathlib.Path( "/data/daily/tiles/cumulative" )
    did = 0
    for tile in basedir.iterdir():
        sys.stderr.write( f"Did {did} tile directories.\n" )
        did += 1
        if tile.is_dir() and re.search( '^[0-9]+$', tile.name ):
            for yyyymmdd in tile.iterdir():
                if yyyymmdd.is_dir() and re.search ( '^[0-9]{8}$', yyyymmdd.name ):
                    for petal in range(0, 10):
                        filetoread = yyyymmdd / f"redrock-{petal}-{tile.name}-thru{yyyymmdd.name}.fits"
                        if not filetoread.is_file():
                            filetoread = yyyymmdd / f"zbest-{petal}-{tile.name}-thru{yyyymmdd.name}.fits"
                            if not filetoread.is_file():
                                sys.stderr.write( f"No file found for "
                                                  f"tile {tile.name} night {yyyymmdd.name} petal {petal}\n" )
                                continue
                        kwargs = { 'tileid': int(tile.name), 'night': int(yyyymmdd.name), 'petal': petal }
                        obj = models.CumulativeTiles.objects.filter( **kwargs )
                        if len(obj) == 0:
                            sys.stderr.write( f'ERROR: No database entry for '
                                              f'tile {tile.name} night {yyyymmdd.name} petal {petal}\n' )
                        elif len(obj) > 1:
                            sys.stderr.write( f'ERROR: >1 database entry for '
                                              f'tile {tile.name} night {yyyymmdd.name} petal {petal}\n' )
                        else:
                            obj[0].filename = str(filetoread)[6:]
                            obj[0].save()
                            # sys.stderr.write( f'Setting filename to {str(filetoread)[6:]} for '
                            #                       f'tile {tile.name} night {yyyymmdd.name} petal {petal}\n' )

                                              
