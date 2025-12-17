import db.management.commands.loaddata
import daily.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/spectro/redux/daily/tiles/cumulative"
    basehealpixdir = None
    models = daily.models
