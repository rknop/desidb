import db.management.commands.loaddata
import himalayas.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/himalayas/tiles/cumulative"
    basehealpixdir = "/data/himalayas/healpix"
    models = himalayas.models
