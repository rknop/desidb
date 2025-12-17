import db.management.commands.loaddata
import everest.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/spectro/redux/everest/tiles/cumulative"
    basehealpixdir = "/data/spectro/redux/everest/healpix"
    models = everest.models
