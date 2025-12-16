import db.management.commands.loaddata
import iron.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/iron/tiles/cumulative"
    basehealpixdir = "/data/iron/healpix"
    models = iron.models
