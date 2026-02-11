-- Migration: Add recovery_notified column to alert_events table
-- Date: 2026-02-11
-- Description: Adds a flag to track if recovery notifications have been sent
--              This prevents missing recovery notifications due to timing issues

-- Add the new column with default value FALSE
ALTER TABLE alert_events
ADD COLUMN recovery_notified BOOLEAN NOT NULL DEFAULT FALSE;

-- Create index for faster queries on pending notifications
CREATE INDEX idx_alert_events_recovery_pending
ON alert_events (status, auto_resolved, recovery_notified)
WHERE status = 'resolved' AND auto_resolved = TRUE AND recovery_notified = FALSE;

-- Optional: Update existing resolved events to prevent duplicate notifications
-- Uncomment if you want to mark all existing resolved events as already notified
-- UPDATE alert_events
-- SET recovery_notified = TRUE
-- WHERE status = 'resolved' AND auto_resolved = TRUE;

-- Verify the migration
SELECT
    COUNT(*) as total_resolved,
    SUM(CASE WHEN recovery_notified = FALSE THEN 1 ELSE 0 END) as pending_notification
FROM alert_events
WHERE status = 'resolved' AND auto_resolved = TRUE;
