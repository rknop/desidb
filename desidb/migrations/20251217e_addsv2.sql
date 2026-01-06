ALTER TABLE daily.tiles_fibermap ADD COLUMN sv2_bgs_target bigint;
ALTER TABLE daily.tiles_fibermap ADD COLUMN sv2_mws_target bigint;
ALTER TABLE daily.tiles_fibermap ADD COLUMN sv2_desi_target bigint;
ALTER TABLE daily.tiles_fibermap ADD COLUMN sv2_scnd_target bigint;
ALTER TABLE loa.tiles_fibermap ADD COLUMN sv2_bgs_target bigint;
ALTER TABLE loa.tiles_fibermap ADD COLUMN sv2_mws_target bigint;
ALTER TABLE loa.tiles_fibermap ADD COLUMN sv2_desi_target bigint;
ALTER TABLE loa.tiles_fibermap ADD COLUMN sv2_scnd_target bigint;
