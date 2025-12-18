CREATE SCHEMA IF NOT EXISTS daily AUTHORIZATION postgres;
GRANT USAGE ON SCHEMA daily TO desi;
ALTER DEFAULT PRIVILEGES IN SCHEMA daily GRANT SELECT ON TABLES TO desi;

CREATE TABLE daily.cumulative_tiles(
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tileid    integer NOT NULL,
  petal     smallint NOT NULL,
  night     integer NOT NULL,
  filename  text NOT NULL DEFAULT ''
);
CREATE UNIQUE INDEX unique_tile ON daily.cumulative_tiles( tileid, petal, night );
CREATE INDEX idx_cumutile_tileid ON daily.cumulative_tiles( tileid );
CREATE INDEX idx_cumutile_petal ON daily.cumulative_tiles( petal );
CREATE INDEX idx_cumutile_night ON daily.cumulative_tiles( night );
CREATE INDEX idx_cumutile_filename ON daily.cumulative_tiles( filename );


CREATE TABLE daily.tiles_redshifts(
  targetid     bigint NOT NULL,
  z            double precision,
  zerr         double precision,
  zwarn        bigint,
  chi2         double precision,
  coeff        double precision[10],
  fitmethod    varchar[4],
  npixels      bigint,
  spectype     varchar[6],
  subtype      varchar[20],
  ncoeff       bigint,
  deltachi2    double precision,
  cumultile_id UUID NOT NULL
);
ALTER TABLE daily.tiles_redshifts ADD PRIMARY KEY ( targetid, cumultile_id );
CREATE INDEX idx_tiles_redshifts_z ON daily.tiles_redshifts( z );
CREATE INDEX idx_tiles_redshifts_zwarn ON daily.tiles_redshifts( zwarn );
CREATE INDEX idx_tiles_redshifts_targetid ON daily.tiles_redshifts( targetid );
CREATE INDEX idx_tiles_redshifts_cumultile_id ON daily.tiles_redshifts( cumultile_id );
ALTER TABLE daily.tiles_redshifts ADD CONSTRAINT fk_tiles_redshifts_cumultile
  FOREIGN KEY( cumultile_id ) REFERENCES daily.cumulative_tiles( id ) ON DELETE RESTRICT;


CREATE TABLE daily.tiles_fibermap(
 targetid                    bigint NOT NULL,
 petal_loc                   smallint NOT NULL,
 device_loc                  integer NOT NULL,
 location                    bigint,
 fiber                       integer NOT NULL,
 coadd_fiberstatus           integer,
 target_ra                   double precision,
 target_dec                  double precision,
 desiname                    text,
 pmra                        real,
 pmdec                       real,
 ref_epoch                   real,
 lambda_ref                  real,
 fa_target                   bigint,
 fa_type                     smallint,
 objtype                     varchar[3],
 fiberassign_x               real,
 fiberassign_y               real,
 priority                    integer,
 subpriority                 double precision,
 obsconditions               integer,
 release                     smallint,
 brickname                   varchar[8],
 brickid                     integer,
 brick_objid                 integer,
 morphtype                   varchar[4],
 ebv                         real,
 flux_g                      real,
 flux_r                      real,
 flux_z                      real,
 flux_w1                     real,
 flux_w2                     real,
 flux_ivar_g                 real,
 flux_ivar_r                 real,
 flux_ivar_z                 real,
 flux_ivar_w1                real,
 flux_ivar_w2                real,
 fiberflux_g                 real,
 fiberflux_r                 real,
 fiberflux_z                 real,
 fibertotflux_g              real,
 fibertotflux_r              real,
 fibertotflux_z              real,
 maskbits                    smallint,
 sersic                      real,
 shape_r                     real,
 shape_e1                    real,
 shape_e2                    real,
 ref_id                      bigint,
 ref_cat                     varchar[2],
 gaia_phot_g_mean_mag        real,
 gaia_phot_bp_mean_mag       real,
 gaia_phot_rp_mean_mag       real,
 parallax                    real,
 photsys                     varchar[1],
 priority_init               bigint,
 numobs_init                 bigint,
 desi_target                 bigint,
 bgs_target                  bigint,
 mws_target                  bigint,
 scnd_target                 bigint,
 sv3_bgs_target              bigint,
 sv3_mws_target              bigint,
 sv3_desi_target             bigint,
 sv3_scnd_target             bigint,
 plate_ra                    double precision,
 plate_dec                   double precision,
 tileid                      integer,
 coadd_numexp                smallint,
 coadd_exptime               real,
 coadd_numnight              smallint,
 coadd_numtile               smallint,
 mean_delta_x                real,
 rms_delta_x                 real,
 mean_delta_y                real,
 rms_delta_y                 real,
 mean_psf_to_fiber_specflux  real,
 mean_fiber_x                real,
 mean_fiber_y                real,
 mean_fiber_ra               double precision,
 std_fiber_ra                real,
 mean_fiber_dec              double precision,
 std_fiber_dec               real,
 min_mjd                     double precision,
 max_mjd                     double precision,
 mean_mjd                    double precision,
 cumultile_id                UUID NOT NULL
);
ALTER TABLE daily.tiles_fibermap ADD PRIMARY KEY( cumultile_id, targetid );
CREATE INDEX idx_tiles_fibermap_targetid ON daily.tiles_fibermap( targetid );
CREATE INDEX idx_tiles_fibermap_tileid ON daily.tiles_fibermap( tileid );
CREATE INDEX idx_tiles_fibermap_petal_loc ON daily.tiles_fibermap( petal_loc );
CREATE INDEX idx_tiles_fibermap_device_loc ON daily.tiles_fibermap( device_loc );
CREATE INDEX idx_tiles_fibermap_target_q3c ON daily.tiles_fibermap(public.q3c_ang2ipix(target_ra, target_dec));
CREATE INDEX idx_tiles_fibermap_fiber_q3c ON daily.tiles_fibermap(public.q3c_ang2ipix(mean_fiber_ra, mean_fiber_dec));
CREATE INDEX idx_tiles_fibermap_cumultile_id ON daily.tiles_fibermap( cumultile_id );
ALTER TABLE daily.tiles_fibermap ADD CONSTRAINT fk_tiles_fibermap_cumultile
  FOREIGN KEY( cumultile_id ) REFERENCES daily.cumulative_tiles( id ) ON DELETE RESTRICT;


CREATE TABLE daily.tiles_expfibermap(
  targetid               bigint NOT NULL,
  priority               integer,
  subpriority            double precision,
  night                  integer NOT NULL,
  expid                  integer NOT NULL,
  MJD                    double precision,
  tileid                 integer NOT NULL,
  exptime                double precision,
  petal_loc              smallint NOT NULL,
  device_loc             integer NOT NULL,
  location               bigint,
  fiber                  integer NOT NULL,
  fiberstatus            integer NOT NULL,
  fiberassign_x          real,
  fiberassign_y          real,
  lambda_ref             real,
  plate_ra               double precision,
  plate_dec              double precision,
  num_iter               bigint,
  fiber_x                double precision,
  fiber_y                double precision,
  delta_x                double precision,
  delta_y                double precision,
  fiber_ra               double precision,
  fiber_dec              double precision,
  psf_to_fiber_specflux  double precision,
  in_coadd_b             boolean,
  in_coadd_r             boolean,
  in_coadd_z             boolean,
  cumultile_id           UUID NOT NULL
);
ALTER TABLE daily.tiles_expfibermap ADD PRIMARY KEY ( cumultile_id, targetid, night, expid );
CREATE INDEX idx_tiles_expfibermap_targetid ON daily.tiles_expfibermap( targetid );
CREATE INDEX idx_tiles_expfibermap_night ON daily.tiles_expfibermap( night );
CREATE INDEX idx_tiles_expfibermap_petal_loc ON daily.tiles_expfibermap( petal_loc );
CREATE INDEX idx_tiles_expfibermap_petal_tileid ON daily.tiles_expfibermap( tileid );
CREATE INDEX idx_tiles_expfibermap_fiber_q3c ON daily.tiles_expfibermap (public.q3c_ang2ipix( fiber_ra, fiber_dec ));
CREATE INDEX idx_tiles_expfibermap_cumultile_id ON daily.tiles_expfibermap( cumultile_id );
ALTER TABLE daily.tiles_expfibermap ADD CONSTRAINT fk_tiles_expfibermap_cumultile
  FOREIGN KEY( cumultile_id ) REFERENCES daily.cumulative_tiles( id ) ON DELETE RESTRICT;


CREATE TABLE daily.tiles_tsnr2(
  targetid            bigint NOT NULL,
  tsnr2_bgs_b         real,
  tsnr2_elg_b         real,
  tsnr2_gpbbackup_b   real,
  tsnr2_gpbbright_b   real,
  tsnr2_gpbdark_b     real,
  tsnr2_lrg_b         real,
  tsnr2_lya_b         real,
  tsnr2_qso_b         real,
  tsnr2_elg_r         real,
  tsnr2_bgs_r         real,
  tsnr2_gpbbackup_r   real,
  tsnr2_gpbbright_r   real,
  tsnr2_gpbdark_r     real,
  tsnr2_lrg_r         real,
  tsnr2_lya_r         real,
  tsnr2_qso_r         real,
  tsnr2_bgs_z         real,
  tsnr2_elg_z         real,
  tsnr2_gpbbackup_z   real,
  tsnr2_gpbbright_z   real,
  tsnr2_gpbdark_z     real,
  tsnr2_lrg_z         real,
  tsnr2_lya_z         real,
  tsnr2_qso_z         real,
  tsnr2_bgs           real,
  tsnr2_elg           real,
  tsnr2_gpbbackup     real,
  tsnr2_gpbbright     real,
  tsnr2_gpbdark       real,
  tsnr2_lrg           real,
  tsnr2_lya           real,
  tsnr2_qso           real,
  cumultile_id        UUID NOT NULL
);
ALTER TABLE daily.tiles_tsnr2 ADD PRIMARY KEY( cumultile_id, targetid );
CREATE INDEX idx_tiles_tsnr2_targetid ON daily.tiles_tsnr2( targetid );
CREATE INDEX idx_tiles_tsnr2_cumultile_id ON daily.tiles_tsnr2( cumultile_id );
ALTER TABLE daily.tiles_tsnr2 ADD CONSTRAINT fk_tiles_tsnr2_cumultile
  FOREIGN KEY( cumultile_id ) REFERENCES daily.cumulative_tiles( id ) ON DELETE RESTRICT;
