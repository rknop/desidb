import db.management.commands.loaddata
import fuji.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/fuji/tiles/cumulative"
    basehealpixdir = "/data/fuji/healpix"
    models = fuji.models
