import db.management.commands.loaddata
import jura.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/spectro/redux/jura/tiles/cumulative"
    basehealpixdir = "/data/spectro/redux/jura/healpix"
    models = jura.models
