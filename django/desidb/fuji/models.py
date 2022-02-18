import sys
from django.db import models
import db.models

class CumulativeTiles(db.models.CumulativeTiles):

    class Meta(db.models.CumulativeTiles.Meta):
        db_table = 'fuji"."cumulative_tiles'


class TilesRedshifts(db.models.CumulativeTilesRedshifts):

    cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

    class Meta(db.models.CumulativeTilesRedshifts.Meta):
        db_table = 'fuji"."tiles_redshifts'


class TilesFibermap(db.models.CumulativeTilesFibermap):
    sv3_desi_target = models.BigIntegerField( null=True )
    sv3_bgs_target = models.BigIntegerField( null=True )
    sv3_mws_target = models.BigIntegerField( null=True )
    sv3_scnd_target = models.BigIntegerField( null=True )
    
    cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

    class Meta(db.models.CumulativeTilesFibermap.Meta):
        db_table = 'fuji"."tiles_fibermap'

class TilesExpFibermap(db.models.CumulativeTilesExpFibermap):

   cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

   class Meta(db.models.CumulativeTilesExpFibermap.Meta):
        db_table = 'fuji"."tiles_expfibermap'


class TilesTSNR2(db.models.CumulativeTilesTSNR2):

    cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

    class Meta(db.models.CumulativeTilesTSNR2.Meta):
        db_table = 'fuji"."tiles_tsnr2'

# ========================================

class Healpix(db.models.Healpix):

    class Meta(db.models.Healpix.Meta):
        db_table = 'fuji"."healpix'

        
class HealpixRedshifts(db.models.HealpixRedshifts):

    healpix = models.ForeignKey( Healpix, on_delete=models.CASCADE )

    class Meta(db.models.HealpixRedshifts.Meta):
        db_table = 'fuji"."healpix_redshifts'


class HealpixFibermap(db.models.HealpixFibermap):

    healpix = models.ForeignKey( Healpix, on_delete=models.CASCADE )

    class Meta(db.models.HealpixFibermap.Meta):
        db_table = 'fuji"."healpix_fibermap'

        
class HealpixExpFibermap(db.models.HealpixExpFibermap):
    
    healpix = models.ForeignKey( Healpix, on_delete=models.CASCADE )

    class Meta(db.models.HealpixExpFibermap.Meta):
        db_table = 'fuji"."healpix_expfibermap'

        
class HealpixTSNR2(db.models.HealpixTSNR2):

    healpix = models.ForeignKey( Healpix, on_delete=models.CASCADE )

    class Meta(db.models.HealpixTSNR2.Meta):
        db_table = 'fuji"."healpix_tsnr2'
        
