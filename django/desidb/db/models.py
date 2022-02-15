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
    tileid = models.IntegerField( null=False )
    petal = models.SmallIntegerField( null=False )
    night = models.IntegerField( null=False )

    class Meta:
        abstract = True
        ordering = [ "tileid", "petal", "night" ]
        unique_together = [ [ 'tileid', 'petal', 'night' ] ]
        index_together = [ [ 'tileid', 'petal', 'night' ] ]
        
    
class Redshifts(models.Model):
    """HDU 1, "Redshifts" """
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
    spectype = models.CharField( max_length=6 )
    subtype = models.CharField( max_length=20 )
    ncoeff = models.BigIntegerField( null=True )
    deltachi2 = models.FloatField( null=True )

    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # redrock_file = models.ForeignKey( Redrock, on_delete=models.CASCADE )

    class Meta:
        abstract = True
        indexes = [
            LongNameBTreeIndex( fields=['targetid'], name="idx_%(class)s_targetid" )
        ]
    
class Fibermap(models.Model):
    """HDU 2, "Fibermap" """
    targetid = models.BigIntegerField( null=False )
    petal_loc = models.SmallIntegerField( null=False )
    device_loc = models.IntegerField( null=False )
    location = models.BigIntegerField( null=True )
    fiber = models.IntegerField( null=False )
    coadd_fiberstatus = models.IntegerField( null=True )
    target_ra = models.FloatField( null=True )
    target_dec = models.FloatField( null=True )
    pmra = models.FloatField( null=True )
    pmdec = models.FloatField( null=True )
    ref_epoch = models.FloatField( null=True )
    lambda_ref = models.FloatField( null=True )
    fa_target = models.BigIntegerField( null=True )
    fa_type = models.SmallIntegerField( null=True )
    objtype = models.CharField( max_length=3 )
    fiberassign_x = models.FloatField( null=True )
    fiberassign_y = models.FloatField( null=True )
    priority = models.IntegerField( null=True )
    subpriority = models.FloatField( null=True )
    obsconditions = models.IntegerField( null=True )
    release = models.SmallIntegerField( null=True )
    brickid = models.IntegerField( null=True )
    brick_objid = models.IntegerField( null=True )
    morphtype = models.CharField( max_length=4 )
    flux_g = models.FloatField( null=True )
    flux_r = models.FloatField( null=True )
    flux_z = models.FloatField( null=True )
    flux_ivar_g = models.FloatField( null=True )
    flux_ivar_r = models.FloatField( null=True )
    flux_ivar_z = models.FloatField( null=True )
    maskbits = models.SmallIntegerField( null=True )
    ref_id = models.BigIntegerField( null=True )
    ref_cat = models.CharField( max_length=2 )
    gaia_phot_g_mean_mag = models.FloatField( null=True )
    gaia_phot_bp_mean_mag = models.FloatField( null=True )
    gaia_phot_rp_mean_mag = models.FloatField( null=True )
    parallax = models.FloatField( null=True )
    brickname = models.CharField( max_length=8 )
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
    photsys = models.CharField( max_length=1 )
    priority_init = models.BigIntegerField( null=True )
    numobs_init = models.BigIntegerField( null=True )
    sv3_desi_target = models.BigIntegerField( null=True )
    sv3_bgs_target = models.BigIntegerField( null=True )
    sv3_mws_target = models.BigIntegerField( null=True )
    sv3_scnd_target = models.BigIntegerField( null=True )
    desi_target = models.BigIntegerField( null=True )
    bgs_target = models.BigIntegerField( null=True )
    mws_target = models.BigIntegerField( null=True )
    plate_ra = models.FloatField( null=True )
    plate_dec = models.FloatField( null=True )
    tileid = models.IntegerField( null=True )
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
    mean_fiber_x = models.FloatField( null=True )
    mean_fiber_y = models.FloatField( null=True )

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
    targetid = models.BigIntegerField( null=False )
    priority = models.IntegerField( null=True )
    subpriority = models.FloatField( null=True )
    night = models.IntegerField( null=False )
    expid = models.IntegerField( null=True )
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
    targetid = models.BigIntegerField( null=False )
    gpbdark_b = models.FloatField( null=True )
    elg_b = models.FloatField( null=True )
    gpbbright_b = models.FloatField( null=True )
    lya_b = models.FloatField( null=True )
    bgs_b = models.FloatField( null=True )
    gpbbackup_b = models.FloatField( null=True )
    qso_b = models.FloatField( null=True )
    lrg_b = models.FloatField( null=True )
    gpbdark_r = models.FloatField( null=True )
    elg_r = models.FloatField( null=True )
    gpbbright_r = models.FloatField( null=True )
    lya_r = models.FloatField( null=True )
    bgs_r = models.FloatField( null=True )
    gpbbackup_r = models.FloatField( null=True )
    qso_r = models.FloatField( null=True )
    lrg_r = models.FloatField( null=True )
    gpbdark_z = models.FloatField( null=True )
    elg_z = models.FloatField( null=True )
    gpbbright_z = models.FloatField( null=True )
    lya_z = models.FloatField( null=True )
    bgs_z = models.FloatField( null=True )
    gpbbackup_z = models.FloatField( null=True )
    qso_z = models.FloatField( null=True )
    lrg_z = models.FloatField( null=True )
    gpbdark = models.FloatField( null=True )
    elg = models.FloatField( null=True )
    gpbbright = models.FloatField( null=True )
    lya = models.FloatField( null=True )
    bgs = models.FloatField( null=True )
    gpbbackup = models.FloatField( null=True )
    qso = models.FloatField( null=True )
    lrg = models.FloatField( null=True )
    
    # These don't seem to work in abstract classes, so we have to copy to each derived class
    # redrock_file = models.ForeignKey( Redrock, on_delete=models.CASCADE )

    class Meta:
        abstract = True
        indexes = [  
          LongNameBTreeIndex( fields=['targetid'], name="idx_%(class)s_targetid" ),
        ]
    
