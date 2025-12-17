import db.management.commands.loaddata
import guadalupe.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/dr1/guadalupe/tiles/cumulative"
    basehealpixdir = "/dr1/guadalupe/healpix"
    models = guadalupe.models
