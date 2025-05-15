-- Add a JSON column for holding “limit” metadata on overrides
ALTER TABLE stat_overrides
  ADD COLUMN override_limits TEXT;
