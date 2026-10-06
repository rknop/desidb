CREATE TABLE static.pvfile(
   id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   filename  text,
   load_time timestamp with time zone DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_pvfile_filename ON static.pvfile( filename );

ALTER TABLE static.pv ADD COLUMN pvfile_id UUID NOT NULL;
CREATE INDEX idx_pv_pvfile ON static.pv( pvfile_id );
ALTER TABLE static.pv ADD CONSTRAINT fk_pv_pvfile
  FOREIGN KEY( pvfile_id ) REFERENCES static.pvfile( id ) ON DELETE RESTRICT;
