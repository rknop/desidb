import db.management.commands.loaddata
import himalayas.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/spectro/redux/himalayas/tiles/cumulative"
    basehealpixdir = "/data/spectro/redux/himalayas/healpix"
    models = himalayas.models
