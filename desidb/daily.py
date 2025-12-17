from desidb.db import DBBase


class CumulativeTiles( DBBase ):
    __tablename__ = "cumulative_tiles"
    __tableschema__ = "daily"
    _tablemeta = None
    _pk = [ 'id' ]


class TilesRedshifts( DBBase ):
    __tablename__ = "tiles_redshifts"
    __tableschema__ = "daily"
    _tablemeta = None
    _pk = [ 'targetid', 'cumultile_id' ]


class TilesFibermap( DBBase ):
    __tablename__ = "tiles_fibermap"
    __tableschema__ = "daily"
    _tablemeta = None
    _pk = [ 'cumultile_id', 'targetid' ]


class TilesExpFibermap( DBBase ):
    __tablename__ = "tiles_expfibermap"
    __tableschema__ = "daily"
    _tablemeta = None
    _pk = [ 'cumultile_id', 'targetid', 'nibht', 'expid' ]


class TilesTSNR2( DBBase ):
    __tablename__ = "tiles_tsnr2"
    __tableschema__ = "daily"
    _tablemeta = None
    _pk = [ 'cumultile_id', 'targetid' ]

