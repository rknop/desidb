CREATE SCHEMA IF NOT EXISTS loa AUTHORIZATION postgres;
GRANT USAGE ON SCHEMA loa TO desi;
ALTER DEFAULT PRIVILEGES IN SCHEMA loa GRANT SELECT ON TABLES TO desi;

CREATE TABLE loa.cumulative_tiles(
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tileid    integer NOT NULL,
  petal     smallint NOT NULL,
  night     integer NOT NULL,
  filename  text NOT NULL DEFAULT ''
);
CREATE UNIQUE INDEX idx_unique_tile ON loa.cumulative_tiles( tileid, petal, night );


CREATE TABLE loa.tiles_redshifts(
  targetid     bigint NOT NULL,
  z            double precision,
  zerr         double precision,
  zwarn        bigint,
  chi2         double precision,
  coeff_0      double precision,
  coeff_1      double precision,
  coeff_2      double precision,
  coeff_3      double precision,
  coeff_4      double precision,
  coeff_5      double precision,
  coeff_6      double precision,
  coeff_7      double precision,
  coeff_8      double precision,
  coeff_9      double precision,
  fitmethod    varchar[4],
  npixels      bigint,
  spectype     varchar[6],
  subtype      varchar[20],
  ncoeff       bigint,
  deltachi2    double precision,
  cumultile_id UUID NOT NULL
);
ALTER TABLE loa.tiles_redshifts ADD PRIMARY KEY ( targetid, cumultile_id );
CREATE INDEX idx_tiles_redshifts_z ON loa.tiles_redshifts( z );
CREATE INDEX idx_tiles_redshifts_zwarn ON loa.tiles_redshifts( zwarn );
CREATE INDEX idx_tiles_redshifts_targetid ON loa.tiles_redshifts( targetid );
CREATE INDEX idx_tiles_redshifts_cumultile_id ON loa.tiles_redshifts( cumultile_id );
ALTER TABLE loa.tiles_redshifts ADD CONSTRAINT fk_tiles_redshifts_cumultile
  FOREIGN KEY( cumultile_id ) REFERENCES loa.cumulative_tiles( id ) ON DELETE RESTRICT;


CREATE TABLE loa.tiles_fibermap(
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
 plate_ra                    double precision,
 plate_dec                   double precision,
 tileid                      integer,
 coadd_numexp                smallint,
 coadd_exptime               real,
 coadd_numnight              smallint,
 coadd_numtile               smallint,
 mean_delta_x                real,
 rms_delta_x                 real,
 mean_deltay_y               real,
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
ALTER TABLE loa.tiles_fibermap ADD PRIMARY KEY( cumultile_id, targetid );
CREATE INDEX idx_tiles_fibermap_targetid ON loa.tiles_fibermap( targetid );
CREATE INDEX idx_tiles_fibermap_tileid ON loa.tiles_fibermap( tileid );
CREATE INDEX idx_tiles_fibermap_petal_loc ON loa.tiles_fibermap( petal_loc );
CREATE INDEX idx_tiles_fibermap_device_loc ON loa.tiles_fibermap( device_loc );
CREATE INDEX idx_tiles_fibermap_target_q3c ON loa.tiles_fibermap(public.q3c_ang2ipix(target_ra, target_dec));
CREATE INDEX idx_tiles_fibermap_fiber_q3c ON loa.tiles_fibermap(public.q3c_ang2ipix(mean_fiber_ra, mean_fiber_dec));
CREATE INDEX idx_tiles_fibermap_cumultile_id ON loa.tiles_fibermap( cumultile_id );
ALTER TABLE loa.tiles_fibermap ADD CONSTRAINT fk_tiles_fibermap_cumultile
  FOREIGN KEY( cumultile_id ) REFERENCES loa.cumulative_tiles( id ) ON DELETE RESTRICT;


CREATE TABLE loa.tiles_expfibermap(
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
ALTER TABLE loa.tiles_expfibermap ADD PRIMARY KEY ( cumultile_id, targetid, night, expid );
CREATE INDEX idx_tiles_expfibermap_targetid ON loa.tiles_expfibermap( targetid );
CREATE INDEX idx_tiles_expfibermap_night ON loa.tiles_expfibermap( night );
CREATE INDEX idx_tiles_expfibermap_petal_loc ON loa.tiles_expfibermap( petal_loc );
CREATE INDEX idx_tiles_expfibermap_petal_tileid ON loa.tiles_expfibermap( tileid );
CREATE INDEX idx_tiles_expfibermap_fiber_q3c ON loa.tiles_expfibermap (public.q3c_ang2ipix( fiber_ra, fiber_dec ));
CREATE INDEX idx_tiles_expfibermap_cumultile_id ON loa.tiles_expfibermap( cumultile_id );
ALTER TABLE loa.tiles_expfibermap ADD CONSTRAINT fk_tiles_expfibermap_cumultile
  FOREIGN KEY( cumultile_id ) REFERENCES loa.cumulative_tiles( id ) ON DELETE RESTRICT;


CREATE TABLE loa.tiles_tsnr2(
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
  tsnr2_gpbdark       real,
  tsnr2_lrg           real,
  tsnr2_lya           real,
  tsnr2_qso           real,
  cumultile_id        UUID NOT NULL
);
ALTER TABLE loa.tiles_tsnr2 ADD PRIMARY KEY( cumultile_id, targetid );
CREATE INDEX idx_tiles_tsnr2_targetid ON loa.tiles_tsnr2( targetid );
CREATE INDEX idx_tiles_tsnr2_cumultile_id ON loa.tiles_tsnr2( cumultile_id );
ALTER TABLE loa.tiles_tsnr2 ADD CONSTRAINT fk_tiles_tsnr2_cumultile
  FOREIGN KEY( cumultile_id ) REFERENCES loa.cumulative_tiles( id ) ON DELETE RESTRICT;


CREATE TABLE loa.healpix(
  id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  healpix  integer NOT NULL,
  survey   text NOT NULL,
  program  text NOT NULL,
  filename text NOT NULL
);
CREATE UNIQUE INDEX idx_healpix_unique ON loa.healpix( survey, program, healpix );
CREATE INDEX idx_healpix_healpix ON loa.healpix( healpix );
CREATE INDEX idx_healpix_filename ON loa.healpix( filename );


CREATE TABLE loa.healpix_redshifts(
  targetid     bigint NOT NULL,
  z            double precision,
  zerr         double precision,
  zwarn        bigint,
  chi2         double precision,
  coeff_0      double precision,
  coeff_1      double precision,
  coeff_2      double precision,
  coeff_3      double precision,
  coeff_4      double precision,
  coeff_5      double precision,
  coeff_6      double precision,
  coeff_7      double precision,
  coeff_8      double precision,
  coeff_9      double precision,
  fitmethod    varchar[4],
  npixels      bigint,
  spectype     varchar[6],
  subtype      varchar[20],
  ncoeff       bigint,
  deltachi2    double precision,
  healpix_id   UUID NOT NULL
);
ALTER TABLE loa.healpix_redshifts ADD PRIMARY KEY ( healpix_id, targetid );
CREATE INDEX idx_healpix_redshifts_healpix_id ON loa.healpix_redshifts( healpix_id );
CREATE INDEX idx_healpix_redshifts_target_id ON loa.healpix_redshifts( targetid );
ALTER TABLE loa.healpix_redshifts ADD CONSTRAINT fk_healpix_redshifts_healpix
  FOREIGN KEY( healpix_id ) REFERENCES loa.healpix( id );


CREATE TABLE loa.healpix_fibermap(
  targetid                    bigint NOT NULL,
  coadd_fiberstatus           integer,
  target_ra                   double precision,
  target_dec                  double precision,
  desiname                    varchar[22],
  pmra                        real,
  pmdec                       real,
  ref_epoch                   real,
  fa_target                   bigint,
  fa_type                     smallint,
  objtype                     varchar[3],
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
  plate_ra                    double precision,
  plate_dec                   double precision,
  coadd_numexp                smallint,
  coadd_exptime               real,
  coadd_numnight              smallint,
  mean_delta_x                real,
  rms_delta_x                 real,
  mean_delta_y                real,
  rms_delta_y                 real,
  mean_psf_to_fiber_spectflux real,
  mean_fiber_ra               double precision,
  std_fiber_ra                real,
  mean_fiber_dec              double precision,
  std_fiber_dec               real,
  min_mjd                     double precision,
  max_mjd                     double precision,
  mean_mjd                    double precision,
  healpix_id                  UUID NOT NULL
);
ALTER TABLE loa.healpix_fibermap ADD PRIMARY KEY( healpix_id, targetid );
CREATE INDEX idx_healpix_fibermap_healpix ON loa.healpix_fibermap( healpix_id );
CREATE INDEX idx_healpix_fibermap_targetid ON loa.healpix_fibermap( targetid );
CREATE INDEX idx_healpix_fibermap_q3c_meanfiber ON loa.healpix_fibermap( public.q3c_ang2ipix( mean_fiber_ra,
                                                                                                  mean_fiber_dec ) );
CREATE INDEX idx_healpix_fibermap_q3c_target ON loa.healpix_fibermap( public.q3c_ang2ipix( target_ra, target_dec ) );
ALTER TABLE loa.healpix_fibermap ADD CONSTRAINT fk_healpix_fibermap_healpix
  FOREIGN KEY( healpix_id ) REFERENCES loa.healpix(id);


CREATE TABLE loa.healpix_expfibermap(
  targetid               bigint NOT NULL,
  priority               integer,
  subpriority            double precision,
  night                  integer NOT NULL,
  expid                  integer NOT NULL,
  mjd                    double precision,
  tileid                 integer,
  exptime                double precision,
  petal_loc              smallint,
  device_loc             smallint,
  location               bigint,
  fiber                  integer,
  fiberstatus            integer,
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
  healpix_id             UUID NOT NULL
);
ALTER TABLE loa.healpix_expfibermap ADD PRIMARY KEY( healpix_id, targetid, night, expid );
CREATE INDEX idx_healpix_expfibermap_targetid ON loa.healpix_expfibermap( targetid );
CREATE INDEX idx_healpix_expfibermap_tileid ON loa.healpix_expfibermap( tileid );
CREATE INDEX idx_healpix_expfibermap_night ON loa.healpix_expfibermap( night );
CREATE INDEX idx_healpix_expfibermap_petal_loc ON loa.healpix_expfibermap( petal_loc );
CREATE INDEX idx_healpix_expfibermap_fiber_q3c ON loa.healpix_expfibermap( public.q3c_ang2ipix( fiber_ra,
                                                                                                    fiber_dec ) );
CREATE INDEX idx_healpix_expfibermap_healpix ON loa.healpix_expfibermap( healpix_id );
ALTER TABLE loa.healpix_expfibermap ADD CONSTRAINT fk_healpix_expfibermap_healpix
  FOREIGN KEY( healpix_id ) REFERENCES loa.healpix( id );


CREATE TABLE loa.healpix_tsnr2(
  targetid            bigint NOT NULL,
  tsnr2_bgs_b         real,
  tsnr2_elg_b         real,
  tsnr2_gpbackup_b    real,
  tsnr2_gpbright_b    real,
  tsnr2_gpdark_b      real,
  tsnr2_lrg_b         real,
  tsnr2_lya_b         real,
  tsnr2_qso_b         real,
  tsnr2_bgs_r         real,
  tsnr2_elg_r         real,
  tsnr2_gpbackup_r    real,
  tsnr2_gpbright_r    real,
  tsnr2_gpdark_r      real,
  tsnr2_lrg_r         real,
  tsnr2_lya_r         real,
  tsnr2_qso_r         real,
  tsnr2_bgs_z         real,
  tsnr2_elg_z         real,
  tsnr2_gpbackup_z    real,
  tsnr2_gpbright_z    real,
  tsnr2_gpdark_z      real,
  tsnr2_lrg_z         real,
  tsnr2_lya_z         real,
  tsnr2_qso_z         real,
  tsnr2_bgs           real,
  tsnr2_elg           real,
  tsnr2_gpbackup      real,
  tsnr2_gpbright      real,
  tsnr2_gpdark        real,
  tsnr2_lrg           real,
  tsnr2_lya           real,
  tsnr2_qso           real,
  healpix_id          UUID NOT NULL
);
ALTER TABLE loa.healpix_tsnr2 ADD PRIMARY KEY( healpix_id, targetid );
CREATE INDEX idx_healpix_tsnr2_targetid ON loa.healpix_tsnr2( targetid );
CREATE INDEX idx_healpix_tsnr2_healpix ON loa.healpix_tsnr2( healpix_id );
ALTER TABLE loa.healpix_tsnr2 ADD CONSTRAINT fk_healpix_tsnr2_healpix
  FOREIGN KEY( healpix_id ) REFERENCES loa.healpix( id );
