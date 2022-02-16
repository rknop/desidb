import sys
from django.db import models
import db.models


class RedrockCumulative(db.models.Redrock):

    class Meta(db.models.Redrock.Meta):
        db_table = 'daily"."redrock_cumulative'


class CumulativeRedshifts(db.models.Redshifts):

    redrock_file = models.ForeignKey( RedrockCumulative, on_delete=models.CASCADE )

    class Meta(db.models.Redshifts.Meta):
        db_table = 'daily"."cumulative_redshifts'


class CumulativeFibermap(db.models.Fibermap):

    redrock_file = models.ForeignKey( RedrockCumulative, on_delete=models.CASCADE )

    class Meta(db.models.Fibermap.Meta):
        db_table = 'daily"."cumulative_fibermap'

class CumulativeExpFibermap(db.models.ExpFibermap):

    redrock_file = models.ForeignKey( RedrockCumulative, on_delete=models.CASCADE )

    class Meta(db.models.ExpFibermap.Meta):
        db_table = 'daily"."cumulative_expfibermap'


class CumulativeTSNR2(db.models.TSNR2):

    redrock_file = models.ForeignKey( RedrockCumulative, on_delete=models.CASCADE )

    class Meta(db.models.TSNR2.Meta):
        db_table = 'daily"."cumulative_tsnr2'
