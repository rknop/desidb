
class EntryExistsError(RuntimeError):
    def __init__( self, *args, **kwargs ):
        super().__init__( self, *args, **kwargs )

class TopLevelEntryExistsError(EntryExistsError):
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
