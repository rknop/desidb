ALTER TABLE static.pv DROP CONSTRAINT pv_pkey;
ALTER TABLE static.pv ADD PRIMARY KEY (objid, brickid, pointingid, pvtype);
