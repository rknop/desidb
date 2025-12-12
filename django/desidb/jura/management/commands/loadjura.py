import db.management.commands.loaddata
import jura.models

class Command(db.management.commands.loaddata.Command):
    basetiledir = "/data/jura/tiles/cumulative"
    basehealpixdir = "/data/jura/healpix"
    models = jura.models
