from django.db import models

import sys
from django.db import models
import db.models


class CumulativeTiles(db.models.CumulativeTiles):

    class Meta(db.models.CumulativeTiles.Meta):
        db_table = 'jura"."cumulative_tiles'
        indexes = [ models.Index( fields=[ 'tileid', 'petal', 'night' ],
                                  name='cumtile_idx_tpn_jura' ) ]


class TilesRedshifts(db.models.CumulativeTilesRedshifts):

    cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

    # Column added in early 2024-06
    fitmethod = models.CharField( max_length=4, null=True )

    class Meta(db.models.CumulativeTilesRedshifts.Meta):
        db_table = 'jura"."tiles_redshifts'


class TilesFibermap(db.models.CumulativeTilesFibermap):

    cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

    # Columns were added somewhere around 2023-06-08
    firstnight = models.IntegerField( null=True )
    lastnight = models.IntegerField( null=True )
    min_mjd = models.FloatField( null=True )
    mean_mjd = models.FloatField( null=True )
    max_mjd = models.FloatField( null=True )

    # Columns added in 2024-02
    # 2024-09-05 : When loading Jura, at least some
    #   of these had 48A instead of 22A in the FITS
    #   table definition.  Just make it a text field
    #   so we don't have to worry about it.

    desiname = models.TextField( null=True )

    class Meta(db.models.CumulativeTilesFibermap.Meta):
        db_table = 'jura"."tiles_fibermap'

class TilesExpFibermap(db.models.CumulativeTilesExpFibermap):

   cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

   class Meta(db.models.CumulativeTilesExpFibermap.Meta):
        db_table = 'jura"."tiles_expfibermap'


class TilesTSNR2(db.models.CumulativeTilesTSNR2):

    cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

    class Meta(db.models.CumulativeTilesTSNR2.Meta):
        db_table = 'jura"."tiles_tsnr2'


# ========================================

class Healpix(db.models.Healpix):

    class Meta(db.models.Healpix.Meta):
        db_table = 'jura"."healpix'

        
class HealpixRedshifts(db.models.HealpixRedshifts):

    healpix = models.ForeignKey( Healpix, on_delete=models.CASCADE )

    # Columns added in Jura
    fitmethod = models.CharField( max_length=4, null=True )
    
    class Meta(db.models.HealpixRedshifts.Meta):
        db_table = 'jura"."healpix_redshifts'


class HealpixFibermap(db.models.HealpixFibermap):
    

    healpix = models.ForeignKey( Healpix, on_delete=models.CASCADE )

    # Columns added in Jura
    desiname = models.TextField( null=True )
    min_mjd = models.FloatField( null=True )
    max_mjd = models.FloatField( null=True )
    mean_mjd = models.FloatField( null=True )
    
    class Meta(db.models.HealpixFibermap.Meta):
        db_table = 'jura"."healpix_fibermap'

        
class HealpixExpFibermap(db.models.HealpixExpFibermap):
    
    healpix = models.ForeignKey( Healpix, on_delete=models.CASCADE )

    class Meta(db.models.HealpixExpFibermap.Meta):
        db_table = 'jura"."healpix_expfibermap'

        
class HealpixTSNR2(db.models.HealpixTSNR2):

    healpix = models.ForeignKey( Healpix, on_delete=models.CASCADE )

    class Meta(db.models.HealpixTSNR2.Meta):
        db_table = 'jura"."healpix_tsnr2'
