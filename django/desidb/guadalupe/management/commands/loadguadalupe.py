import db.management.commands.loaddata
import guadalupe.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/guadalupe/tiles/cumulative"
    basehealpixdir = "/data/guadalupe/healpix"
    models = guadalupe.models
