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

    
class Redrock(models.Model):
    """Encapsulates one redrock-{petal}-{tile}-thru{night}.fits file"""
    tileid = models.IntegerField()
    petal = models.SmallIntegerField()
    night = models.IntegerField()

    class Meta:
        abstract = True
        ordering = [ "tileid", "petal", "night" ]
        unique_together = [ [ 'tileid', 'petal', 'night' ] ]
        index_together = [ [ 'tileid', 'petal', 'night' ] ]
        
    
class Redshifts(models.Model):
    """HDU 1, "Redshifts" """
    targetid = models.BigIntegerField()
    chi2 = models.FloatField()
    coeff_0 = models.FloatField()
    coeff_1 = models.FloatField()
    coeff_2 = models.FloatField()
    coeff_3 = models.FloatField()
    coeff_4 = models.FloatField()
    coeff_5 = models.FloatField()
    coeff_6 = models.FloatField()
    coeff_7 = models.FloatField()
    coeff_8 = models.FloatField()
    coeff_9 = models.FloatField()
    z = models.FloatField()
    zerr = models.FloatField()
    zwarn = models.BigIntegerField()
    npixels = models.BigIntegerField()
    spectype = models.CharField( max_length=6 )
    subtype = models.CharField( max_length=20 )
    ncoeff = models.BigIntegerField()
    deltachi2 = models.FloatField()

    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # redrock_file = models.ForeignKey( Redrock, on_delete=models.CASCADE )

    class Meta:
        abstract = True
        indexes = [
            LongNameBTreeIndex( fields=['targetid'], name="idx_%(class)s_targetid" )
        ]
    
class Fibermap(models.Model):
    """HDU 2, "Fibermap" """
    targetid = models.BigIntegerField()
    petal_loc = models.SmallIntegerField()
    device_loc = models.IntegerField()
    location = models.BigIntegerField()
    fiber = models.IntegerField()
    coadd_fiberstatus = models.IntegerField()
    target_ra = models.FloatField()
    target_dec = models.FloatField()
    pmra = models.FloatField()
    pmdec = models.FloatField()
    ref_epoch = models.FloatField()
    lambda_ref = models.FloatField()
    fa_target = models.BigIntegerField()
    fa_type = models.SmallIntegerField()
    objtype = models.CharField( max_length=3 )
    fiberassign_x = models.FloatField()
    fiberassign_y = models.FloatField()
    priority = models.IntegerField()
    subpriority = models.FloatField()
    obsconditions = models.IntegerField()
    release = models.SmallIntegerField()
    brickid = models.IntegerField()
    brick_objid = models.IntegerField
    morphtype = models.CharField( max_length=4 )
    flux_g = models.FloatField()
    flux_r = models.FloatField()
    flux_z = models.FloatField()
    flux_ivar_g = models.FloatField()
    flux_ivar_r = models.FloatField()
    flux_ivar_z = models.FloatField()
    maskbits = models.SmallIntegerField()
    ref_id = models.BigIntegerField()
    ref_cat = models.CharField( max_length=2 )
    gaia_phot_g_mean_mag = models.FloatField()
    gaia_phot_bp_mean_mag = models.FloatField()
    gaia_phot_rp_mean_mag = models.FloatField()
    parallax = models.FloatField()
    brickname = models.CharField( max_length=8 )
    ebv = models.FloatField()
    flux_w1 = models.FloatField()
    flux_w2 = models.FloatField()
    flux_ivar_w1 = models.FloatField()
    flux_ivar_w2 = models.FloatField()
    fiberflux_g = models.FloatField()
    fiberflux_r = models.FloatField()
    fiberflux_z = models.FloatField()
    fibertotflux_g = models.FloatField()
    fibertotflux_r = models.FloatField()
    fibertotflux_z = models.FloatField()
    sersic = models.FloatField()
    shape_r = models.FloatField()
    shape_e1 = models.FloatField()
    shape_e2 = models.FloatField()
    photsys = models.CharField( max_length=1 )
    priority_init = models.BigIntegerField()
    numobs_init = models.BigIntegerField()
    desi_target = models.BigIntegerField()
    bgs_target = models.BigIntegerField()
    mws_target = models.BigIntegerField()
    scnd_target = models.BigIntegerField()
    plate_ra = models.FloatField()
    plate_dec = models.FloatField()
    tileid = models.IntegerField()
    coadd_numexp = models.SmallIntegerField()
    coadd_exptime = models.FloatField()
    coadd_numnight = models.SmallIntegerField()
    coadd_numtile = models.SmallIntegerField()
    mean_delta_x = models.FloatField()
    rms_delta_x = models.FloatField()
    mean_delta_y = models.FloatField()
    rms_delta_y = models.FloatField()
    mean_fiber_ra = models.FloatField()
    std_fiber_ra = models.FloatField()
    mean_fiber_dec = models.FloatField()
    std_fiber_dec = models.FloatField()
    mean_psf_to_fiber_specflux = models.FloatField()
    mean_fiber_x = models.FloatField()
    mean_fiber_y = models.FloatField()

    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # redrock_file = models.ForeignKey( Redrock, on_delete=models.CASCADE )

    class Meta:
        abstract = True
        indexes = [
            LongNameBTreeIndex( fields=['targetid'], name="idx_%(class)s_targetid" ),
            LongNameBTreeIndex( fields=['tileid'], name="idx_%(class)s_tileid" ),
            LongNameBTreeIndex( fields=['petal_loc'], name="idx_%(class)s_petal_loc" ),
            LongNameBTreeIndex( q3c_ang2ipix('target_ra', 'target_dec'),
                          name='idx_%(class)s_q3c_target' ),
            LongNameBTreeIndex( q3c_ang2ipix('mean_fiber_ra', 'mean_fiber_dec'),
                          name='idx_%(class)s_q3c_meanfiber' )
        ]
            
            
class ExpFibermap(models.Model):
    """HDU 3, "Exp_Fibermap" """
    targetid = models.BigIntegerField()
    priority = models.IntegerField()
    subpriority = models.FloatField()
    night = models.IntegerField()
    expid = models.IntegerField()
    mjd = models.FloatField()
    tileid = models.IntegerField()
    exptime = models.FloatField()
    petal_loc = models.SmallIntegerField()
    device_loc = models.IntegerField()
    location = models.BigIntegerField()
    fiber = models.IntegerField()
    fiberstatus = models.IntegerField()
    fiberassign_x = models.FloatField()
    fiberassign_y = models.FloatField()
    lambda_ref = models.FloatField()
    plate_ra = models.FloatField()
    plate_dec = models.FloatField()
    num_iter = models.BigIntegerField()
    fiber_x = models.FloatField()
    fiber_y = models.FloatField()
    delta_x = models.FloatField()
    delta_y = models.FloatField()
    fiber_ra = models.FloatField()
    fiber_dec = models.FloatField()
    psf_to_fiber_specflux = models.FloatField()

    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # redrock_file = models.ForeignKey( Redrock, on_delete=models.CASCADE )

    class Meta:
        abstract = True
        indexes = [
            LongNameBTreeIndex( fields=['targetid'], name="idx_%(class)s_targetid" ),
            LongNameBTreeIndex( fields=['tileid'], name="idx_%(class)s_tileid" ),
            LongNameBTreeIndex( fields=['petal_loc'], name="idx_%(class)s_petal_loc" ),
            LongNameBTreeIndex( fields=['night'], name="idx_%(class)s_night" ),
            LongNameBTreeIndex( q3c_ang2ipix('fiber_ra', 'fiber_dec'), name='idx_%(class)s_q3c_fiber' )
        ]

class TSNR2(models.Model):
    """HDU_r, "TSNR2" """
    targetid = models.BigIntegerField()
    gpbdark_b = models.FloatField()
    elg_b = models.FloatField()
    gpbbright_b = models.FloatField()
    lya_b = models.FloatField()
    bgs_b = models.FloatField()
    gpbbackup_b = models.FloatField()
    qso_b = models.FloatField()
    lrg_b = models.FloatField()
    gpbdark_r = models.FloatField()
    elg_r = models.FloatField()
    gpbbright_r = models.FloatField()
    lya_r = models.FloatField()
    bgs_r = models.FloatField()
    gpbbackup_r = models.FloatField()
    qso_r = models.FloatField()
    lrg_r = models.FloatField()
    gpbdark_z = models.FloatField()
    elg_z = models.FloatField()
    gpbbright_z = models.FloatField()
    lya_z = models.FloatField()
    bgs_z = models.FloatField()
    gpbbackup_z = models.FloatField()
    qso_z = models.FloatField()
    lrg_z = models.FloatField()
    gpbdark = models.FloatField()
    elg = models.FloatField()
    gpbbright = models.FloatField()
    lya = models.FloatField()
    bgs = models.FloatField()
    gpbbackup = models.FloatField()
    qso = models.FloatField()
    lrg = models.FloatField()
    
    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # redrock_file = models.ForeignKey( Redrock, on_delete=models.CASCADE )

    class Meta:
        abstract = True
        indexes = [  
          LongNameBTreeIndex( fields=['targetid'], name="idx_%(class)s_targetid" ),
        ]
    
