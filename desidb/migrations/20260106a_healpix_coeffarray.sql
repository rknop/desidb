-- This assumes nothing is loaded into the table yet, as it does not preserve data.
ALTER TABLE loa.healpix_redshifts DROP COLUMN coeff_0;
ALTER TABLE loa.healpix_redshifts DROP COLUMN coeff_1;
ALTER TABLE loa.healpix_redshifts DROP COLUMN coeff_2;
ALTER TABLE loa.healpix_redshifts DROP COLUMN coeff_3;
ALTER TABLE loa.healpix_redshifts DROP COLUMN coeff_4;
ALTER TABLE loa.healpix_redshifts DROP COLUMN coeff_5;
ALTER TABLE loa.healpix_redshifts DROP COLUMN coeff_6;
ALTER TABLE loa.healpix_redshifts DROP COLUMN coeff_7;
ALTER TABLE loa.healpix_redshifts DROP COLUMN coeff_8;
ALTER TABLE loa.healpix_redshifts DROP COLUMN coeff_9;
ALTER TABLE loa.healpix_redshifts ADD COLUMN coeff double precision[10];
