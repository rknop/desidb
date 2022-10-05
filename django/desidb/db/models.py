from django.db import models
import django.contrib.postgres.indexes as indexes
from django.utils.functional import cached_property

class q3c_ang2ipix(models.Func):
    function = "q3c_ang2ipix"

# A hack so that I can have index names that go up to
#   the 63 characters postgres allows, instead of the
#   30 that django allows
class LongNameBTreeIndex(indexes.BTreeIndex):
    @cached_property
    def max_name_length(self):
        return 63 - len(models.Index.suffix) + len(self.suffix)

# Allow for a 4-byte real

class RealField(models.FloatField):
    description = "4-byte float"
    def db_type(self, connection):
        return 'real'
    
# ======================================================================
# Base Classes that are extended separately for tiles and healpix files

class Redshifts(models.Model):
    targetid = models.BigIntegerField( null=False )
    chi2 = models.FloatField( null=True )
    coeff_0 = models.FloatField( null=True )
    coeff_1 = models.FloatField( null=True )
    coeff_2 = models.FloatField( null=True )
    coeff_3 = models.FloatField( null=True )
    coeff_4 = models.FloatField( null=True )
    coeff_5 = models.FloatField( null=True )
    coeff_6 = models.FloatField( null=True )
    coeff_7 = models.FloatField( null=True )
    coeff_8 = models.FloatField( null=True )
    coeff_9 = models.FloatField( null=True )
    z = models.FloatField( null=True )
    zerr = models.FloatField( null=True )
    zwarn = models.BigIntegerField( null=True )
    npixels = models.BigIntegerField( null=True )
    spectype = models.CharField( max_length=6, null=True )
    subtype = models.CharField( max_length=20, null=True )
    ncoeff = models.BigIntegerField( null=True )
    deltachi2 = models.FloatField( null=True )

    class Meta:
        abstract = True


class Fibermap(models.Model):
    targetid = models.BigIntegerField( null=False )
    coadd_fiberstatus = models.IntegerField( null=True )
    target_ra = models.FloatField( null=True )
    target_dec = models.FloatField( null=True )
    pmra = models.FloatField( null=True )
    pmdec = models.FloatField( null=True )
    ref_epoch = models.FloatField( null=True )
    fa_target = models.BigIntegerField( null=True )
    fa_type = models.SmallIntegerField( null=True )
    objtype = models.CharField( max_length=3, null=True )
    numtarget = models.SmallIntegerField( null=True )
    subpriority = models.FloatField( null=True )
    obsconditions = models.IntegerField( null=True )
    release = models.IntegerField( null=True )
    brickid = models.IntegerField( null=True )
    brick_objid = models.IntegerField( null=True )
    blobdist = models.FloatField( null=True )
    fiberflux_ivar_g = models.FloatField( null=True )
    fiberflux_ivar_r = models.FloatField( null=True )
    fiberflux_ivar_z = models.FloatField( null=True )
    morphtype = models.CharField( max_length=4, null=True )
    flux_g = models.FloatField( null=True )
    flux_r = models.FloatField( null=True )
    flux_z = models.FloatField( null=True )
    flux_ivar_g = models.FloatField( null=True )
    flux_ivar_r = models.FloatField( null=True )
    flux_ivar_z = models.FloatField( null=True )
    maskbits = models.SmallIntegerField( null=True )
    ref_id = models.BigIntegerField( null=True )
    ref_cat = models.CharField( max_length=2, null=True )
    gaia_phot_g_mean_mag = models.FloatField( null=True )
    gaia_phot_bp_mean_mag = models.FloatField( null=True )
    gaia_phot_rp_mean_mag = models.FloatField( null=True )
    parallax = models.FloatField( null=True )
    brickname = models.CharField( max_length=8, null=True )
    ebv = models.FloatField( null=True )
    flux_w1 = models.FloatField( null=True )
    flux_w2 = models.FloatField( null=True )
    flux_ivar_w1 = models.FloatField( null=True )
    flux_ivar_w2 = models.FloatField( null=True )
    fiberflux_g = models.FloatField( null=True )
    fiberflux_r = models.FloatField( null=True )
    fiberflux_z = models.FloatField( null=True )
    fibertotflux_g = models.FloatField( null=True )
    fibertotflux_r = models.FloatField( null=True )
    fibertotflux_z = models.FloatField( null=True )
    sersic = models.FloatField( null=True )
    shape_r = models.FloatField( null=True )
    shape_e1 = models.FloatField( null=True )
    shape_e2 = models.FloatField( null=True )
    photsys = models.CharField( max_length=1, null=True )
    sv1_desi_target = models.BigIntegerField( null=True )
    sv1_bgs_target = models.BigIntegerField( null=True )
    sv1_mws_target = models.BigIntegerField( null=True )
    sv1_scnd_target = models.BigIntegerField( null=True )
    sv2_desi_target = models.BigIntegerField( null=True )
    sv2_bgs_target = models.BigIntegerField( null=True )
    sv2_mws_target = models.BigIntegerField( null=True )
    sv2_scnd_target = models.BigIntegerField( null=True )
    sv3_desi_target = models.BigIntegerField( null=True )
    sv3_bgs_target = models.BigIntegerField( null=True )
    sv3_mws_target = models.BigIntegerField( null=True )
    sv3_scnd_target = models.BigIntegerField( null=True )
    cmx_target = models.BigIntegerField( null=True) 
    priority_init = models.BigIntegerField( null=True )
    numobs_init = models.BigIntegerField( null=True )
    desi_target = models.BigIntegerField( null=True )
    bgs_target = models.BigIntegerField( null=True )
    mws_target = models.BigIntegerField( null=True )
    hpxpixel = models.BigIntegerField( null=True )
    scnd_target = models.BigIntegerField( null=True )
    plate_ra = models.FloatField( null=True )
    plate_dec = models.FloatField( null=True )
    coadd_numexp = models.SmallIntegerField( null=True )
    coadd_exptime = models.FloatField( null=True )
    coadd_numnight = models.SmallIntegerField( null=True )
    coadd_numtile = models.SmallIntegerField( null=True )
    mean_delta_x = models.FloatField( null=True )
    rms_delta_x = models.FloatField( null=True )
    mean_delta_y = models.FloatField( null=True )
    rms_delta_y = models.FloatField( null=True )
    mean_fiber_ra = models.FloatField( null=True )
    std_fiber_ra = models.FloatField( null=True )
    mean_fiber_dec = models.FloatField( null=True )
    std_fiber_dec = models.FloatField( null=True )
    mean_psf_to_fiber_specflux = models.FloatField( null=True )
    
    class Meta:
        abstract = True


class ExpFibermap(models.Model):
    targetid = models.BigIntegerField( null=False )
    priority = models.IntegerField( null=True )
    subpriority = models.FloatField( null=True )
    night = models.IntegerField( null=False )
    expid = models.IntegerField( null=False )
    mjd = models.FloatField( null=True )
    tileid = models.IntegerField( null=False )
    exptime = models.FloatField( null=True )
    petal_loc = models.SmallIntegerField( null=False )
    device_loc = models.IntegerField( null=True )
    location = models.BigIntegerField( null=True )
    fiber = models.IntegerField( null=False )
    fiberstatus = models.IntegerField( null=True )
    fiberassign_x = models.FloatField( null=True )
    fiberassign_y = models.FloatField( null=True )
    lambda_ref = models.FloatField( null=True )
    plate_ra = models.FloatField( null=True )
    plate_dec = models.FloatField( null=True )
    num_iter = models.BigIntegerField( null=True )
    fiber_x = models.FloatField( null=True )
    fiber_y = models.FloatField( null=True )
    delta_x = models.FloatField( null=True )
    delta_y = models.FloatField( null=True )
    fiber_ra = models.FloatField( null=True )
    fiber_dec = models.FloatField( null=True )
    psf_to_fiber_specflux = models.FloatField( null=True )

    class Meta:
        abstract = True


class TSNR2(models.Model):
    targetid = models.BigIntegerField( null=False )
    tsnr2_gpbdark_b = models.FloatField( null=True )
    tsnr2_elg_b = models.FloatField( null=True )
    tsnr2_gpbbright_b = models.FloatField( null=True )
    tsnr2_lya_b = models.FloatField( null=True )
    tsnr2_bgs_b = models.FloatField( null=True )
    tsnr2_gpbbackup_b = models.FloatField( null=True )
    tsnr2_qso_b = models.FloatField( null=True )
    tsnr2_lrg_b = models.FloatField( null=True )
    tsnr2_gpbdark_r = models.FloatField( null=True )
    tsnr2_elg_r = models.FloatField( null=True )
    tsnr2_gpbbright_r = models.FloatField( null=True )
    tsnr2_lya_r = models.FloatField( null=True )
    tsnr2_bgs_r = models.FloatField( null=True )
    tsnr2_gpbbackup_r = models.FloatField( null=True )
    tsnr2_qso_r = models.FloatField( null=True )
    tsnr2_lrg_r = models.FloatField( null=True )
    tsnr2_gpbdark_z = models.FloatField( null=True )
    tsnr2_elg_z = models.FloatField( null=True )
    tsnr2_gpbbright_z = models.FloatField( null=True )
    tsnr2_lya_z = models.FloatField( null=True )
    tsnr2_bgs_z = models.FloatField( null=True )
    tsnr2_gpbbackup_z = models.FloatField( null=True )
    tsnr2_qso_z = models.FloatField( null=True )
    tsnr2_lrg_z = models.FloatField( null=True )
    tsnr2_gpbdark = models.FloatField( null=True )
    tsnr2_elg = models.FloatField( null=True )
    tsnr2_gpbbright = models.FloatField( null=True )
    tsnr2_lya = models.FloatField( null=True )
    tsnr2_bgs = models.FloatField( null=True )
    tsnr2_gpbbackup = models.FloatField( null=True )
    tsnr2_qso = models.FloatField( null=True )
    tsnr2_lrg = models.FloatField( null=True )
    
    class Meta:
        abstract = True


# ======================================================================
# Classes for tiles files
    
class CumulativeTiles(models.Model):
    """Encapsulates one redrock-{petal}-{tile}-thru{night}.fits file"""
    tileid = models.IntegerField( null=False )
    petal = models.SmallIntegerField( null=False )
    night = models.IntegerField( null=False )
    filename = models.TextField( null=False, default="" )
    
    class Meta:
        abstract = True
        ordering = [ "tileid", "petal", "night" ]
        unique_together = [ [ 'tileid', 'petal', 'night' ] ]
        index_together = [ [ 'tileid', 'petal', 'night' ] ]


class CumulativeTilesRedshifts(Redshifts):
    """HDU 1, "Redshifts" """

    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

    class Meta(Redshifts.Meta):
        abstract = True
        indexes = [
            LongNameBTreeIndex( fields=['targetid'], name="idx_%(app_label)s_%(class)s_targetid" )
        ]
        unique_together = [ [ 'cumultile', 'targetid' ] ]
    
class CumulativeTilesFibermap(Fibermap):
    """HDU 2, "Fibermap" """
    petal_loc = models.SmallIntegerField( null=False )
    device_loc = models.IntegerField( null=False )
    location = models.BigIntegerField( null=True )
    fiber = models.IntegerField( null=False )
    lambda_ref = models.FloatField( null=True )
    fiberassign_x = models.FloatField( null=True )
    fiberassign_y = models.FloatField( null=True )
    priority = models.IntegerField( null=True )
    tileid = models.IntegerField( null=True )
    mean_fiber_x = models.FloatField( null=True )
    mean_fiber_y = models.FloatField( null=True )

    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

    class Meta(Fibermap.Meta):
        abstract = True
        indexes = [
            LongNameBTreeIndex( fields=['targetid'], name="idx_%(app_label)s_%(class)s_targetid" ),
            LongNameBTreeIndex( fields=['tileid'], name="idx_%(app_label)s_%(class)s_tileid" ),
            LongNameBTreeIndex( fields=['petal_loc'], name="idx_%(app_label)s_%(class)s_petal_loc" ),
            LongNameBTreeIndex( q3c_ang2ipix('target_ra', 'target_dec'),
                          name='idx_%(app_label)s_%(class)s_q3c_target' ),
            LongNameBTreeIndex( q3c_ang2ipix('mean_fiber_ra', 'mean_fiber_dec'),
                          name='idx_%(app_label)s_%(class)s_q3c_meanfiber' )
        ]
        unique_together = [ [ 'cumultile', 'targetid' ] ]


class CumulativeTilesExpFibermap(ExpFibermap):
    """HDU 3, "Exp_Fibermap" """

    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

    class Meta(ExpFibermap.Meta):
        abstract = True
        indexes = [
            LongNameBTreeIndex( fields=['targetid'], name="idx_%(app_label)s_%(class)s_targetid" ),
            LongNameBTreeIndex( fields=['tileid'], name="idx_%(app_label)s_%(class)s_tileid" ),
            LongNameBTreeIndex( fields=['petal_loc'], name="idx_%(app_label)s_%(class)s_petal_loc" ),
            LongNameBTreeIndex( fields=['night'], name="idx_%(app_label)s_%(class)s_night" ),
            LongNameBTreeIndex( q3c_ang2ipix('fiber_ra', 'fiber_dec'), name='idx_%(app_label)s_%(class)s_q3c_fiber' )
        ]
        unique_together = [ [ 'cumultile', 'targetid', 'night', 'expid' ] ]


class CumulativeTilesTSNR2(TSNR2):
    """HDU_r, "TSNR2" """

    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # cumultile = models.ForeignKey( CumulativeTiles, on_delete=models.CASCADE )

    class Meta(TSNR2.Meta):
        abstract = True
        indexes = [  
          LongNameBTreeIndex( fields=['targetid'], name="idx_%(app_label)s_%(class)s_targetid" ),
        ]
        unique_together = [ [ 'cumultile', 'targetid' ] ]

# ======================================================================
# Classes for healpix files

class Healpix(models.Model):
    healpix = models.IntegerField( null=False )
    survey = models.TextField( null=False )
    program = models.TextField( null=False )
    filename = models.TextField( null=False, default="" )

    class Meta:
        abstract = True
        ordering = [ "survey", "program", "healpix" ]
        unique_together = [ [ "survey", "program", "healpix" ] ]
        indexes = [
            LongNameBTreeIndex( fields=['healpix'], name="idx_%(app_label)s_%(class)s_targetid" ),
        ]

class HealpixRedshifts(Redshifts):

    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # healpix = models.ForeignKey( Healpix, on_delete=models.CASCADE )

    class Meta(Redshifts.Meta):
        abstract = True
        indexes = [
            LongNameBTreeIndex( fields=['targetid'], name="idx_%(app_label)s_%(class)s_targetid" )
        ]
        unique_together = [ [ 'healpix', 'targetid' ] ]

class HealpixFibermap(Fibermap):

    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # healpix = models.ForeignKey( Healpix, on_delete=models.CASCADE )

    class Meta(Fibermap.Meta):
        abstract = True
        indexes = [
            LongNameBTreeIndex( fields=['targetid'], name="idx_%(app_label)s_%(class)s_targetid" ),
            LongNameBTreeIndex( q3c_ang2ipix('target_ra', 'target_dec'),
                          name='idx_%(app_label)s_%(class)s_q3c_target' ),
            LongNameBTreeIndex( q3c_ang2ipix('mean_fiber_ra', 'mean_fiber_dec'),
                          name='idx_%(app_label)s_%(class)s_q3c_meanfiber' )
        ]
        unique_together = [ [ 'healpix', 'targetid' ] ]

class HealpixExpFibermap(ExpFibermap):

    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # healpix = models.ForeignKey( Healpix, on_delete=models.CASCADE )

    class Meta(ExpFibermap.Meta):
        abstract = True
        indexes = [
            LongNameBTreeIndex( fields=['targetid'], name="idx_%(app_label)s_%(class)s_targetid" ),
            LongNameBTreeIndex( fields=['tileid'], name="idx_%(app_label)s_%(class)s_tileid" ),
            LongNameBTreeIndex( fields=['petal_loc'], name="idx_%(app_label)s_%(class)s_petal_loc" ),
            LongNameBTreeIndex( fields=['night'], name="idx_%(app_label)s_%(class)s_night" ),
            LongNameBTreeIndex( q3c_ang2ipix('fiber_ra', 'fiber_dec'), name='idx_%(app_label)s_%(class)s_q3c_fiber' )
        ]
        unique_together = [ [ 'healpix', 'targetid', 'night', 'expid' ] ]


class HealpixTSNR2(TSNR2):
    """HDU_r, "TSNR2" """

    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # healpix = models.ForeignKey( Healpix, on_delete=models.CASCADE )

    class Meta(TSNR2.Meta):
        abstract = True
        indexes = [  
          LongNameBTreeIndex( fields=['targetid'], name="idx_%(app_label)s_%(class)s_targetid" ),
        ]
        unique_together = [ [ 'healpix', 'targetid' ] ]


# ======================================================================
# Loaded from a directory like target/catalogs/dr9/1.1.1/main/resolve/dark
# Database fields corresponding to directories:
#
# survey is "main", "sv1", "sv2", "sv3", or "missing-1.0.0"
# whenobs will be "bright", "dark", or "backup"
#
# Note that /targets is a mount of
#   /global/cfs/cdirs/desi/target
#
# Directories that I intend to search to load these tables
# /targets/catalogs/dr9/0.51.0/targets/sv1/resolve      (SV1Targets)
# /targets/catalogs/dr9/0.53.0/targets/sv2/resolve      (SV2Targets)
# /targets/catalogs/dr9/0.57.0/targets/sv3/resolve      (SV3Targets)
# /targets/catalogs/dr9/1.1.1/targets/main/resolve      (MainTargets - bright and dark)
# /targets/catalogs/gaiadr2/2.2.0/targets/main/resolve  (BackupTargets)
# TBD (missing-1.0.0)
#
# Everything else is out of the FITS files

class TargetFiles(models.Model):
    id = models.AutoField( primary_key=True )
    filename = models.TextField()

    class Meta:
        db_table = 'general"."targetfiles'
        constraints = [
            models.UniqueConstraint( fields=['filename'], name='unique_targetfiles' )
        ]
        
class Targets(models.Model):
    id = models.BigAutoField( primary_key=True )
    targetid = models.BigIntegerField( )
    # ForeignKeys don't seem to work in abstract classes, so put it in the derived class
    # targetfile = models.ForeignKey( TargetFiles, on_delete=models.CASCADE )
    whenobs = models.TextField( null=True )
    survey = models.TextField( null=True )
    release = models.SmallIntegerField( null=True )
    brickid = models.IntegerField( null=True )
    brickname = models.CharField( max_length=8, null=True )
    brick_objid = models.IntegerField( null=True )
    morphtype = models.CharField( max_length=4, null=True )
    ra = models.FloatField()
    ra_ivar = RealField( null=True )
    dec = models.FloatField()
    dec_ivar = RealField( null=True )
    # dchisq_0 = RealField( null=True )
    # dchisq_1 = RealField( null=True )
    # dchisq_2 = RealField( null=True )
    # dchisq_3 = RealField( null=True )
    # dchisq_4 = RealField( null=True )
    # ebv = RealField( null=True )
    flux_g = RealField( null=True )
    flux_r = RealField( null=True )
    flux_z = RealField( null=True )
    flux_ivar_g = RealField( null=True )
    flux_ivar_r = RealField( null=True )
    flux_ivar_z = RealField( null=True )
    # mw_transmission_g = RealField( null=True )
    # mw_transmission_r = RealField( null=True )
    # mw_transmission_z = RealField( null=True )
    # fracflux_g = RealField( null=True )
    # fracflux_r = RealField( null=True )
    # fracflux_z = RealField( null=True )
    # fracmasked_g = RealField( null=True )
    # fracmasked_r = RealField( null=True )
    # fracmasked_z = RealField( null=True )
    # fracin_g = RealField( null=True )
    # fracin_r = RealField( null=True )
    # fracin_z = RealField( null=True )
    # nobs_g = models.SmallIntegerField( null=True )
    # nobs_r = models.SmallIntegerField( null=True )
    # nobs_z = models.SmallIntegerField( null=True )
    # psfdepth_g = RealField( null=True )
    # psfdepth_r = RealField( null=True )
    # psfdepth_z = RealField( null=True )
    # galdepth_g = RealField( null=True )
    # galdepth_r = RealField( null=True )
    # galdepth_z = RealField( null=True )
    # flux_w1 = RealField( null=True )
    # flux_w2 = RealField( null=True )
    # flux_w3 = RealField( null=True )
    # flux_w4 = RealField( null=True )
    # flux_ivar_w1 = RealField( null=True )
    # flux_ivar_w2 = RealField( null=True )
    # flux_ivar_w3 = RealField( null=True )
    # flux_ivar_w4 = RealField( null=True )
    # mw_transmission_w1 = RealField( null=True )
    # mw_transmission_w2 = RealField( null=True )
    # mw_transmission_w3 = RealField( null=True )
    # mw_transmission_w4 = RealField( null=True )
    # allmask_g = models.SmallIntegerField( null=True )
    # allmask_r = models.SmallIntegerField( null=True )
    # allmask_z = models.SmallIntegerField( null=True )
    # fiberflux_g = RealField( null=True )
    # fiberflux_r = RealField( null=True )
    # fiberflux_z = RealField( null=True )
    # fibertotflux_g = RealField( null=True )
    # fibertotflux_r = RealField( null=True )
    # fibertotflux_z = RealField( null=True )
    # ref_epoch = RealField( null=True )
    # wisemask_w1 = models.SmallIntegerField( null=True )
    # wisemask_w2 = models.SmallIntegerField( null=True )
    # maskbits = models.SmallIntegerField( null=True )
    # # These are array parameters, so I'd need to break them out,
    # # and including them would double the size of the table.
    # # lc_flux_w1 = RealField( null=True )
    # # lc_flux_w2 = RealField( null=True )
    # # lc_flux_ivar_w1 = RealField( null=True )
    # # lc_flux_ivar_w2 = RealField( null=True )
    # # lc_nobs_w1 = models.SmallIntegerField( null=True )
    # # lc_nobs_w2 = models.SmallIntegerField( null=True )
    # # lc_mjd_w1 = models.FloatField( null=True )
    # # lc_mjd_w2 = models.FloatField( null=True )
    shape_r = RealField( null=True )
    shape_e1 = RealField( null=True )
    shape_e2 = RealField( null=True )
    shape_r_ivar = RealField( null=True )
    shape_e1_ivar = RealField( null=True )
    shape_e2_ivar = RealField( null=True )
    sersic = RealField( null=True )
    sersic_ivar = RealField( null=True )
    ref_id = models.BigIntegerField( null=True )
    ref_cat = models.CharField( max_length=2, null=True )
    # gaia_phot_g_mean_mag = RealField( null=True )
    # gaia_phot_g_mean_flux_over_error = RealField( null=True )
    # gaia_phot_bp_mean_mag = RealField( null=True )
    # gaia_phot_bp_mean_flux_over_error = RealField( null=True )
    # gaia_phot_rp_mean_mag = RealField( null=True )
    # gaia_phot_rp_mean_flux_over_error = RealField( null=True )
    # gaia_phot_bp_rp_excess_factor = RealField( null=True )
    # gaia_astrometric_excess_noise = RealField( null=True )
    # gaia_duplicated_source = models.BooleanField( null=True )
    # gaia_astrometric_sigma5d_max = RealField( null=True )
    # gaia_astrometric_params_solved = models.FloatField( null=True )
    parallax = RealField( null=True )
    parallax_ivar = RealField( null=True )
    pmra = RealField( null=True )
    pmra_ivar = RealField( null=True )
    pmdec = RealField( null=True )
    pmdec_ivar = RealField( null=True )
    photsys = models.CharField( max_length=1, null=True )
    desi_target = models.BigIntegerField( null=True )
    bgs_target = models.BigIntegerField( null=True )
    mws_target = models.BigIntegerField( null=True )
    subpriority = models.FloatField( null=True )
    obsconditions = models.BigIntegerField( null=True )
    priority_init = models.BigIntegerField( null=True )
    numobs_init = models.BigIntegerField( null=True )
    scnd_target = models.BigIntegerField( null=True )
    hpxpixel = models.BigIntegerField( null=True )

    class Meta:
        abstract = True
        unique_together = [ [ 'targetid', 'whenobs', 'survey' ] ]
        indexes = [
            LongNameBTreeIndex( fields=['targetid'], name='idx_%(class)s_targetid' ),
            LongNameBTreeIndex( fields=['survey'], name='idx_%(class)s_survey' ),
            LongNameBTreeIndex( fields=['desi_target'], name='idx_%(class)s_desi_target' ),
            LongNameBTreeIndex( fields=['bgs_target'], name='idx_%(class)s_bgs_target' ),
            LongNameBTreeIndex( fields=['mws_target'], name='idx_%(class)s_mws_target' ),
            LongNameBTreeIndex( fields=['scnd_target'], name='idx_%(class)s_scnd_target' ),
            LongNameBTreeIndex( fields=['hpxpixel'], name='idx_%(class)s_hpxpixel' ),
            LongNameBTreeIndex( q3c_ang2ipix( 'ra', 'dec' ), name='idx_%(class)s_q3c' ),
        ]

class MainTargets(Targets):
    targetfile = models.ForeignKey( TargetFiles, on_delete=models.CASCADE )

    class Meta(Targets.Meta):
        db_table = 'general"."maintargets'
        
class SV1Targets(Targets):
    targetfile = models.ForeignKey( TargetFiles, on_delete=models.CASCADE )

    class Meta(Targets.Meta):
        db_table = 'general"."sv1targets'
        
class SV2Targets(Targets):
    targetfile = models.ForeignKey( TargetFiles, on_delete=models.CASCADE )

    class Meta(Targets.Meta):
        db_table = 'general"."sv2targets'
        
class SV3Targets(Targets):
    targetfile = models.ForeignKey( TargetFiles, on_delete=models.CASCADE )

    class Meta(Targets.Meta):
        db_table = 'general"."sv3targets'
        
class BackupTargets(Targets):
    targetfile = models.ForeignKey( TargetFiles, on_delete=models.CASCADE )

    class Meta(Targets.Meta):
        db_table = 'general"."backuptargets'
        
        
# ======================================================================
# dbid is internally generated.  I don't have confidence for Secondary
# targets that targetid will be unique.
#
# Loaded from a file like target/catalogs/dr9/1.1.1/targets/main/secondary/dark/targets-dark-secondary.fits
# Database fields corresponding to directories:
#   catalog : dr9
#   catver : 1.1.1
#   whenobs : dark
#
# I *think *whenobs* is only 'bright' or 'dark'
#
# Everything else is from the FITS files
#
# Directories I intend to search to fill this:
# target/catalogs/dr9/1.1.1/targets/main/secondary
# target/catalogs/dr9/1.1.1/targets/main2/secondary
#
# There will be more in the future.

class SecondaryTargets(models.Model):
    dbid = models.BigAutoField( primary_key=True )
    targetfile = models.ForeignKey( TargetFiles, on_delete=models.CASCADE, null=True )
    catalog = models.TextField( null=True )
    catver = models.TextField( null=True )
    whenobs = models.TextField( null=True )
    ra = models.FloatField()
    dec = models.FloatField()
    pmra = RealField( null=True )
    pmdec = RealField( null=True )
    ref_epoch = RealField( null=True )
    override = models.BooleanField( null=True )
    flux_g = RealField( null=True )
    flux_r = RealField( null=True )
    flux_z = RealField( null=True )
    parallax = RealField( null=True )
    # gaia_phot_g_mean_mag = RealField( null=True )
    # gaia_phot_bp_mean_mag = RealField( null=True )
    # gaia_phot_rp_mean_mag = RealField( null=True )
    # gaia_astrometric_excess_noise = RealField( null=True )
    targetid = models.BigIntegerField( null=True )
    desi_target = models.BigIntegerField( null=True )
    scnd_target = models.BigIntegerField( null=True )
    scnd_order = models.IntegerField( null=True )
    subpriority = models.FloatField( null=True )
    obsconditions = models.BigIntegerField( null=True )
    priority_init = models.BigIntegerField( null=True )
    numobs_init = models.BigIntegerField( null=True )

    class Meta:
        db_table = '"general"."secondarytargets"'
        unique_together = [ [ 'catalog', 'catver', 'targetid' ] ]
        indexes = [
            LongNameBTreeIndex( fields=['catalog', 'catver', 'whenobs'], name='idx_secondarytargets_direc' ),
            LongNameBTreeIndex( fields=['targetid'], name='idx_secondarytargets_targetid' ),
            LongNameBTreeIndex( fields=['desi_target'], name='idx_secondarytargets_desi_target' ),
            LongNameBTreeIndex( fields=['scnd_target'], name='idx_secondarytargets_scnd_target' ),
            LongNameBTreeIndex( q3c_ang2ipix( 'ra', 'dec' ), name='idx_secondarytargets_q3c' ),
        ]
    

    
