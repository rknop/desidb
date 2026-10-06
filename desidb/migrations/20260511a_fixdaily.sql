-- That was stupid... I did [] instead of () on varchar

ALTER TABLE daily.tiles_redshifts ALTER COLUMN fitmethod TYPE varchar(4);
ALTER TABLE daily.tiles_redshifts ALTER COLUMN spectype TYPE varchar(6);
ALTER TABLE daily.tiles_redshifts ALTER COLUMN subtype TYPE varchar(20);

ALTER TABLE daily.tiles_fibermap ALTER COLUMN objtype TYPE varchar(3);
ALTER TABLE daily.tiles_fibermap ALTER COLUMN brickname TYPE varchar(8);
ALTER TABLE daily.tiles_fibermap ALTER COLUMN morphtype TYPE varchar(4);
ALTER TABLE daily.tiles_fibermap ALTER COLUMN ref_cat TYPE varchar(2);
ALTER TABLE daily.tiles_fibermap ALTER COLUMN photsys TYPE varchar(1);
