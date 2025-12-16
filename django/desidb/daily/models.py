import sys
from django.db import models
import db.models


class CumulativeTiles(db.models.CumulativeTiles):

    class Meta(db.models.CumulativeTiles.Meta):
        db_table = 'daily"."cumulative_tiles'


class TilesRedshifts(db.models.CumulativeTilesRedshifts):

    cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

    # Column added in early 2024-06
    fitmethod = models.CharField( max_length=4, null=True )

    class Meta(db.models.CumulativeTilesRedshifts.Meta):
        db_table = 'daily"."tiles_redshifts'


class TilesFibermap(db.models.CumulativeTilesFibermap):

    cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

    # Columns were added somewhere around 2023-06-08
    firstnight = models.IntegerField( null=True )
    lastnight = models.IntegerField( null=True )
    min_mjd = models.FloatField( null=True )
    mean_mjd = models.FloatField( null=True )
    max_mjd = models.FloatField( null=True )

    # Columns added in 2024-02

    desiname = models.CharField( max_length=22, null=True )

    class Meta(db.models.CumulativeTilesFibermap.Meta):
        db_table = 'daily"."tiles_fibermap'

class TilesExpFibermap(db.models.CumulativeTilesExpFibermap):

   cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

   class Meta(db.models.CumulativeTilesExpFibermap.Meta):
        db_table = 'daily"."tiles_expfibermap'


class TilesTSNR2(db.models.CumulativeTilesTSNR2):

    cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

    class Meta(db.models.CumulativeTilesTSNR2.Meta):
        db_table = 'daily"."tiles_tsnr2'

