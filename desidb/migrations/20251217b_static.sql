CREATE SCHEMA IF NOT EXISTS static AUTHORIZATION postgres;
GRANT USAGE ON SCHEMA static TO desi;
ALTER DEFAULT PRIVILEGES IN SCHEMA static GRANT SELECT ON TABLES TO desi;

CREATE TABLE static.fp(
 objid      bigint,
 brickid    integer,
 brickname  text,
 ra         double precision,
 dec        double precision,
 pmra       real,
 pmdec      real,
 ref_epoch  real,
 override   boolean,
 pvtype     text,
 pvpriority integer,
 pointingid bigint,
 sga_id     bigint
);
ALTER TABLE static.fp ADD PRIMARY KEY( objid, brickid );


CREATE TABLE static.mosthosts(
 id                      uuid PRIMARY KEY NOT NULL DEFAULT gen_random_uuid(),
 sn_name_sp              text not null,
 hostnum                 smallint not null,
 ra                      double precision not null,
 dec                     double precision not null,
 origin                  text,
 sn_type                 text,
 sn_z                    real,
 sn_ra                   double precision,
 sn_dec                  double precision,
 sn_name                 text,
 sn_name_ptf             text,
 sn_name_iau             text,
 sn_name_tns             text,
 program                 text,
 ls_id_dr9               bigint,
 dec_dr9                 double precision,
 ra_dr9                  double precision,
 ref_id_dr9              bigint,
 brickid_dr9             integer,
 ref_cat_dr9             text,
 type_dr9                text,
 dist_arcsec_dr9         real,
 sep_in_radius_dr9       real,
 sep_in_radius_sigma_dr9 real,
 fiberflux_g_dr9         real,
 fiberflux_r_dr9         real,
 fiberflux_z_dr9         real,
 fibertotflux_g_dr9      real,
 fibertotflux_r_dr9      real,
 fibertotflux_z_dr9      real,
 dchisq_1_dr9            real,
 dchisq_2_dr9            real,
 dchisq_3_dr9            real,
 dchisq_4_dr9            real,
 dchisq_5_dr9            real,
 ra_ivar_dr9             real,
 dec_ivar_dr9            double precision,
 dered_flux_g_dr9        real,
 dered_flux_r_dr9        real,
 dered_flux_w1_dr9       real,
 dered_flux_w2_dr9       real,
 dered_flux_w3_dr9       real,
 dered_flux_w4_dr9       real,
 dered_flux_z_dr9        real,
 flux_ivar_g_dr9         real,
 flux_ivar_r_dr9         real,
 flux_ivar_w1_dr9        real,
 flux_ivar_w2_dr9        real,
 flux_ivar_w3_dr9        real,
 flux_ivar_w4_dr9        real,
 flux_ivar_z_dr9         real,
 fracflux_g_dr9          real,
 fracflux_r_dr9          real,
 fracflux_w1_dr9         real,
 fracflux_w2_dr9         real,
 fracflux_w3_dr9         real,
 fracflux_w4_dr9         real,
 fracflux_z_dr9          real,
 fracin_g_dr9            real,
 fracin_r_dr9            real,
 fracin_z_dr9            real,
 fracmasked_g_dr9        real,
 fracmasked_r_dr9        real,
 fracmasked_z_dr9        real,
 sga_id_sga              bigint,
 sga_galaxy_sga          text,
 galaxy_sga              text,
 ra_sga                  double precision,
 dec_sga                 double precision,
 ra_leda_sga             double precision,
 dec_leda_sga            double precision,
 morphtype_sga           text,
 pa_leda_sga             text,
 d25_leda_sga            text,
 ba_leda_sga             text,
 z_leda_sga              text,
 ref_sga                 text,
 group_id_sga            integer,
 group_name_sga          text,
 group_ra_sga            double precision,
 group_dec_sga           double precision,
 group_diameter_sga      real,
 d26_sga                 real,
 d26_ref_sga             text
);
CREATE INDEX idx_mosthosts_q3c ON static.mosthosts (public.q3c_ang2ipix(ra, "dec"));
CREATE INDEX idx_mosthosts_q3c_sn ON static.mosthosts (public.q3c_ang2ipix(sn_ra, sn_dec));
CREATE INDEX idx_mosthosts_q3c_dr9 ON static.mosthosts (public.q3c_ang2ipix(ra_dr9, dec_dr9));
CREATE INDEX idx_mosthosts_sn_name_iau ON static.mosthosts (sn_name_iau);
CREATE INDEX idx_mosthosts_sn_name ON static.mosthosts (sn_name);
CREATE INDEX idx_mosthosts_sn_name_ptf ON static.mosthosts (sn_name_ptf);
CREATE INDEX idx_mosthosts_sn_name_sp ON static.mosthosts (sn_name_sp);
CREATE INDEX idx_mosthosts_sn_name_tns ON static.mosthosts (sn_name_tns);


CREATE TABLE static.mtl(
 id                             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 ra                             double precision,
 dec                            double precision,
 ref_epoch                      real,
 parallax                       real,
 pmra                           real,
 pmdec                          real,
 targetid                       bigint,
 sv3_desi_target                bigint,
 sv3_bgs_target                 bigint,
 sv3_mws_target                 bigint,
 subpriority                    double precision,
 obsconditions                  integer,
 priority_init                  bigint,
 numobs_init                    bigint,
 sv3_scnd_target                bigint,
 numobs_more                    bigint,
 numobs                         bigint,
 z                              double precision,
 zwarn                          bigint,
 ztileid                        integer,
 target_state                   text,
 timestamp                      text,
 version                        text,
 priority                       bigint,
 run                            text,
 program                        text,
 lunation                       text,
 flux_g                         real,
 flux_r                         real,
 flux_z                         real,
 gaia_phot_g_mean_mag           real,
 gaia_phot_bp_mean_mag          real,
 gaia_phot_rp_mean_mag          real,
 gaia_astrometric_excess_noise  real,
 scnd_order                     integer,
 checker                        text,
 too_type                       text,
 too_prio                       text,
 oclayer                        text,
 mjd_begin                      double precision,
 mjd_end                        double precision,
 tooid                          bigint
);
CREATE INDEX idx_mtl_q3c ON static.mtl( public.q3c_ang2ipix( ra, "dec" ) );
CREATE INDEX idx_mtl_targetid ON static.mtl( targetid );



CREATE TABLE static.pv(
 objid      bigint,
 brickid    integer,
 brickname  text,
 ra         double precision,
 dec        double precision,
 pmra       real,
 pmdec      real,
 ref_epoch  real,
 override   boolean,
 pvtype     text,
 pvpriority integer,
 pointingid bigint,
 sga_id     bigint
);
ALTER TABLE static.pv ADD PRIMARY KEY( objid, brickid );
CREATE INDEX idx_pv_objid ON static.pv( objid );
CREATE INDEX idx_pv_pvtype ON static.pv( pvtype );
CREATE INDEX idx_pv_q3c ON static.pv( public.q3c_ang2ipix( ra, "dec" ) );
CREATE INDEX idx_pv_sga_id ON static.pv( sga_id );



CREATE TABLE static.secondary(
 id                             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 ra                             double precision,
 dec                            double precision,
 pmra                           real,
 pmdec                          real,
 ref_epoch                      real,
 override                       boolean,
 flux_g                         real,
 flux_r                         real,
 flux_z                         real,
 parallax                       real,
 gaia_phot_g_mean_mag           real,
 gaia_phot_bp_mean_mag          real,
 gaia_phot_rp_mean_mag          real,
 gaia_astrometric_excess_noise  real,
 targetid                       bigint,
 sv3_desi_target                bigint,
 sv3_scnd_target                bigint,
 scnd_order                     integer,
 desitarget_v                   text,
 run                            text,
 program                        text,
 lunation                       text,
 desi_target                    bigint,
 scnd_target                    bigint
);
CREATE INDEX idx_secondary_q3c ON static.secondary( public.q3c_ang2ipix( ra, "dec" ) );
CREATE INDEX idx_secondary_targetid ON static.secondary( targetid );


CREATE TABLE static.sga(
 sga_id          bigint PRIMARY KEY,
 sga_galaxy      text,
 galaxy          text,
 pgc             bigint,
 ra_leda         double precision,
 dec_leda        double precision,
 morphtype       text,
 pa_leda         real,
 d25_leda        real,
 ba_leda         real,
 z_leda          real,
 sb_d25_leda     real,
 mag_leda        real,
 byhand          boolean,
 ref             text,
 group_id        bigint,
 group_name      text,
 group_mult      integer,
 group_primary   boolean,
 group_ra        double precision,
 group_dec       double precision,
 group_diameter  real,
 brickname       text,
 ra              double precision,
 dec             double precision,
 d26             real,
 d26_ref         text,
 pa              real,
 ba              real,
 ra_moment       double precision,
 dec_moment      double precision,
 sma_moment      real
);
CREATE INDEX idx_sga_q3c ON static.sga( public.q3c_ang2ipix( ra, "dec" ) );
CLUSTER static.sga USING idx_sga_q3c;

