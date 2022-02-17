import numpy
import pandas
import astropy
from astropy.io import fits
from astropy.table import Table

class EntryExistsError(RuntimeError):
    def __init__( self, *args, **kwargs ):
        super().__init__( self, *args, **kwargs )

class SchemaMismatchError(RuntimeError):
    def __init__( self, data, *args, **kwargs ):
        """data needs to be a dictionary:
        filepath : String, full path to the file read (or array of strings)
        missingdatablock : set of data blocks (BinTable HDU extension names)
                           expected to be found in the data that weren't there
        extradatablock : set of data blocks (BinTable HDU extension names)
                         that were in the data that we didn't expect
        models:
          <key is database model that was expected>
          <value is a dictionary>:
              datablock : Name of HDU that (mostly) corresponds to the table, or None if not present
                         (Note: even if none, one of the other HDUs may have this table in moved).
              missingfrommodel : set of columns that were in the HDU but not the model
              missingfromdata  : set of columsn that were in the model but not the HDU
              coltypemismatch : set of columns where HDU and table didn't match
              datatypes : dictionary of column -> types parsed to Pandas from the FITS file
              modeltypes : dictionary of column -> type from database
        """
        super().__init__( *args, **kwargs )
        self.data = data

# ======================================================================
        
def _astropy_table_to_pandas( tab ):
    data = {}
    for col in tab.colnames:
        if len( tab[col].shape ) > 2:
            raise RuntimeError( f"Don't know how to deal with shape {tab[col].shape} columns" )
        elif len( tab[col].shape ) == 2:
            for i in range( tab[col].shape[1] ):
                tab.add_column( numpy.array( [ arr[i] for arr in tab[col] ] ), name=f'{col.lower()}_{i}' )
            tab.remove_column( col )
        else:
            tab.rename_column( col, col.lower() )
        
    return tab.to_pandas()

# ======================================================================

def _fits_bintables_to_pandas( fitsfile ):
    """Pass it the path to a fits file.

    Reads the FITS file.  Returns a dictionary of Extname: DataFrame for
    all bintables in the file.  For cases where the bintable had an
    array element, replace it with a bunch of individual elements that
    have _0, _1, etc. appended to the column names.

    """

    with fits.open( fitsfile, memmap=False ) as hdulist:
        bintables = {}
        for hdu in hdulist:
            if isinstance( hdu, fits.hdu.BinTableHDU ):
                if hdu.name in bintables.keys():
                    raise RuntimeError( f'Extension {hdu.name} shows up in the FITS file '
                                        f'{str(fitsfile)} more than once.' )
                df = _astropy_table_to_pandas( astropy.table.Table( hdu.data ) )
                bintables[ hdu.name ] = df

    return bintables
