USE acid_simulator;

-- Run this only if your existing transactions table does not already have completed_at.
ALTER TABLE transactions ADD COLUMN completed_at TIMESTAMP NULL DEFAULT NULL;
