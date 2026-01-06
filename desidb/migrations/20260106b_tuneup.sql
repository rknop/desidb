-- Assumes no data loaded as does not preserve data

ALTER TABLE loa.healpix_fibermap ADD COLUMN coadd_numtile smallint;
ALTER TABLE loa.healpix_fibermap RENAME COLUMN mean_psf_to_fiber_spectflux TO mean_psf_to_fiber_specflux;
ALTER TABLE loa.healpix_fibermap DROP COLUMN desiname;
ALTER TABLE loa.healpix_fibermap ADD COLUMN desiname text;

ALTER TABLE loa.healpix_tsnr2 RENAME COLUMN tsnr2_gpbackup TO tsnr2_gpbbackup;
ALTER TABLE loa.healpix_tsnr2 RENAME COLUMN tsnr2_gpbackup_b TO tsnr2_gpbbackup_b;
ALTER TABLE loa.healpix_tsnr2 RENAME COLUMN tsnr2_gpbackup_r TO tsnr2_gpbbackup_r;
ALTER TABLE loa.healpix_tsnr2 RENAME COLUMN tsnr2_gpbackup_z TO tsnr2_gpbbackup_z;
ALTER TABLE loa.healpix_tsnr2 RENAME COLUMN tsnr2_gpbright TO tsnr2_gpbbright;
ALTER TABLE loa.healpix_tsnr2 RENAME COLUMN tsnr2_gpbright_b TO tsnr2_gpbbright_b;
ALTER TABLE loa.healpix_tsnr2 RENAME COLUMN tsnr2_gpbright_r TO tsnr2_gpbbright_r;
ALTER TABLE loa.healpix_tsnr2 RENAME COLUMN tsnr2_gpbright_z TO tsnr2_gpbbright_z;
ALTER TABLE loa.healpix_tsnr2 RENAME COLUMN tsnr2_gpdark TO tsnr2_gpbdark;
ALTER TABLE loa.healpix_tsnr2 RENAME COLUMN tsnr2_gpdark_b TO tsnr2_gpbdark_b;
ALTER TABLE loa.healpix_tsnr2 RENAME COLUMN tsnr2_gpdark_r TO tsnr2_gpbdark_r;
ALTER TABLE loa.healpix_tsnr2 RENAME COLUMN tsnr2_gpdark_z TO tsnr2_gpbdark_z;
