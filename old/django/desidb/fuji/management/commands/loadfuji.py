import db.management.commands.loaddata
import fuji.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/spectro/redux/fuji/tiles/cumulative"
    basehealpixdir = "/data/spectro/redux/fuji/healpix"
    models = fuji.models
