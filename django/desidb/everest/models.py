from django.db import models
import db.models

class RedrockCumulative(db.models.Redrock):

    class Meta(db.models.Redrock.Meta):
        db_table = 'everest"."redrock_cumulative'


class CumulativeRedshifts(db.models.Redshifts):

    redrock_file = models.ForeignKey( RedrockCumulative, on_delete=models.CASCADE )

    class Meta(db.models.Redshifts.Meta):
        db_table = 'everest"."cumulative_redshifts'


class CumulativeFibermap(db.models.Fibermap):

    redrock_file = models.ForeignKey( RedrockCumulative, on_delete=models.CASCADE )

    class Meta(db.models.Fibermap.Meta):
        db_table = 'everest"."cumulative_fibermap'


class CumulativeExpFibermap(db.models.ExpFibermap):

    redrock_file = models.ForeignKey( RedrockCumulative, on_delete=models.CASCADE )

    class Meta(db.models.ExpFibermap.Meta):
        db_table = 'everest"."cumulative_expfibermap'


class CumulativeTSNR2(db.models.TSNR2):

    redrock_file = models.ForeignKey( RedrockCumulative, on_delete=models.CASCADE )

    class Meta(db.models.TSNR2.Meta):
        db_table = 'everest"."cumulative_tsnr2'



class RedrockPernight(db.models.Redrock):

    class Meta(db.models.Redrock.Meta):
        db_table = 'everest"."redrock_pernight'


class PernightRedshifts(db.models.Redshifts):

    redrock_file = models.ForeignKey( RedrockPernight, on_delete=models.CASCADE )

    class Meta(db.models.Redshifts.Meta):
        db_table = 'everest"."pernight_redshifts'


class PernightFibermap(db.models.Fibermap):

    redrock_file = models.ForeignKey( RedrockPernight, on_delete=models.CASCADE )

    class Meta(db.models.Fibermap.Meta):
        db_table = 'everest"."pernight_fibermap'


class PernightExpFibermap(db.models.ExpFibermap):

    redrock_file = models.ForeignKey( RedrockPernight, on_delete=models.CASCADE )

    class Meta(db.models.ExpFibermap.Meta):
        db_table = 'everest"."pernight_expfibermap'


class PernightTSNR2(db.models.TSNR2):

    redrock_file = models.ForeignKey( RedrockPernight, on_delete=models.CASCADE )

    class Meta(db.models.TSNR2.Meta):
        db_table = 'everest"."pernight_tsnr2'
        
