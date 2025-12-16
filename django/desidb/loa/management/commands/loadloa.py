import db.management.commands.loaddata
import loa.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/loa/tiles/cumulative"
    basehealpixdir = "/data/loa/healpix"
    models = loa.models
