ALTER TABLE static.pv DROP CONSTRAINT pv_pkey;
ALTER TABLE static.pv ADD PRIMARY KEY (objid, brickid, pointingid);
CREATE INDEX idx_pv_brickid ON static.pv( brickid );
