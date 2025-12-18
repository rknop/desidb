from desidb.db import DBBase


class CumulativeTiles( DBBase ):
    __tablename__ = "cumulative_tiles"
    __tableschema__ = "loa"
    _tablemeta = None
    _pk = [ 'id' ]


class TilesRedshifts( DBBase ):
    __tablename__ = "tiles_redshifts"
    __tableschema__ = "loa"
    _tablemeta = None
    _pk = [ 'targetid', 'cumultile_id' ]


class TilesFibermap( DBBase ):
    __tablename__ = "tiles_fibermap"
    __tableschema__ = "loa"
    _tablemeta = None
    _pk = [ 'cumultile_id', 'targetid' ]


class TilesExpFibermap( DBBase ):
    __tablename__ = "tiles_expfibermap"
    __tableschema__ = "loa"
    _tablemeta = None
    _pk = [ 'cumultile_id', 'targetid', 'nibht', 'expid' ]


class TilesTSNR2( DBBase ):
    __tablename__ = "tiles_tsnr2"
    __tableschema__ = "loa"
    _tablemeta = None
    _pk = [ 'cumultile_id', 'targetid' ]


class Healpix( DBBase ):
    __tablename__ = "healpix"
    __tableschema__ = "loa"
    _tablemeta = None
    _pk = [ 'id' ]


class HealPixRedshifts( DBBase ):
    __tablename__ = "healpix_redshifts"
    __tableschema__ = "loa"
    _tablemeta = None
    _pk = [ 'healpix_id', 'targetid' ]


class HealPixFibermap( DBBase ):
    __tablename__ = "healpix_fibermap"
    __tableschema__ = "loa"
    _tablemeta = None
    _pk = [ 'healpix_id', 'targetid' ]


class HealPixExpFibermap( DBBase ):
    __tablename__ = "heapix_expfibermap"
    __tableschema__ = "loa"
    _tablemeta = None
    _pk = [ 'healpix_id', 'targetid', 'night', 'expid' ]


class HealpixTSNR2( DBBase ):
    __tablename__ = "healpix_tsnr2"
    __tableschema__ = "loa"
    _tablemeta = None
    _pk = [ 'healpix_id', 'targetid' ]
