import db.management.commands.loaddata
import everest.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/everest/tiles/cumulative"
    basehealpixdir = "/data/everest/healpix"
    models = everest.models
