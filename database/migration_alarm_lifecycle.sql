-- Migration: Alarm Lifecycle Management
-- Adds lifecycle metadata columns, indexes, and status constraint to network_alarms

ALTER TABLE network_alarms ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE network_alarms ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE network_alarms ADD COLUMN IF NOT EXISTS acknowledged_by VARCHAR(100);
ALTER TABLE network_alarms ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_network_alarms_acknowledged_at ON network_alarms (acknowledged_at);
CREATE INDEX IF NOT EXISTS idx_network_alarms_resolved_at ON network_alarms (resolved_at);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_network_alarms_status'
    ) THEN
        ALTER TABLE network_alarms
        ADD CONSTRAINT chk_network_alarms_status
        CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED'));
    END IF;
END $$;
