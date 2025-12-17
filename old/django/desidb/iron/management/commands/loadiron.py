import db.management.commands.loaddata
import iron.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/spectro/redux/iron/tiles/cumulative"
    basehealpixdir = "/data/spectro/redux/iron/healpix"
    models = iron.models
