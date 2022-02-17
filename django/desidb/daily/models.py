import sys
from django.db import models
import db.models


class Redrock(db.models.Redrock):

    class Meta(db.models.Redrock.Meta):
        db_table = 'daily"."redrock'


class Redshifts(db.models.Redshifts):

    redrock_file = models.ForeignKey( Redrock, on_delete=models.CASCADE )

    class Meta(db.models.Redshifts.Meta):
        db_table = 'daily"."redshifts'


class Fibermap(db.models.Fibermap):

    redrock_file = models.ForeignKey( Redrock, on_delete=models.CASCADE )

    class Meta(db.models.Fibermap.Meta):
        db_table = 'daily"."fibermap'

class ExpFibermap(db.models.ExpFibermap):

    redrock_file = models.ForeignKey( Redrock, on_delete=models.CASCADE )

    class Meta(db.models.ExpFibermap.Meta):
        db_table = 'daily"."expfibermap'


class TSNR2(db.models.TSNR2):

    redrock_file = models.ForeignKey( Redrock, on_delete=models.CASCADE )

    class Meta(db.models.TSNR2.Meta):
        db_table = 'daily"."tsnr2'
