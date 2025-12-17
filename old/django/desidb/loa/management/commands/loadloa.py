import db.management.commands.loaddata
import loa.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/spectro/redux/loa/tiles/cumulative"
    basehealpixdir = "/data/spectro/redux/loa/healpix"
    models = loa.models
