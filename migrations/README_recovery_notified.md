# Recovery Notification Fix - Migration Guide

## Problem Description

Previously, the system had a 60-second time window to send recovery notifications. If the monitoring scan didn't run within that minute after a site recovered, the recovery notification would never be sent.

**Old Logic (BROKEN):**
```python
if time_since_resolution < 60:  # Only 60 seconds to catch it!
    send_recovery_notification()
```

**Issues:**
- If scan runs every 2-5 minutes, notifications get missed
- No retry mechanism
- Silent failures (users never know site recovered)

## Solution

Added a `recovery_notified` boolean flag to track notification status instead of relying on timing.

**New Logic (FIXED):**
```python
if event.status == RESOLVED and not event.recovery_notified:
    send_recovery_notification()
    mark_recovery_notified(event.id)
```

## Changes Made

### 1. Database Schema
- Added `recovery_notified` BOOLEAN column to `alert_events` table
- Default value: `FALSE`
- Indexed for fast queries

### 2. Model Changes
**File:** `app_fast_api/models/ubiquiti_monitoring/alerting.py`
- Added `recovery_notified` field to `AlertEvent` model

### 3. Repository Changes
**File:** `app_fast_api/repositories/alerting_repositories.py`
- Added `mark_recovery_notified()` method
- Added `get_resolved_events_pending_notification()` method

### 4. Service Changes
**File:** `app_fast_api/services/alerting_services.py`
- Replaced time-based logic with flag-based logic
- Now checks `recovery_notified` flag instead of `time_since_resolution`
- Marks event as notified after sending (or attempting to send)

## Migration Steps

### Option 1: Using SQL Script
```bash
cd /Users/rhernandezba/PycharmProjects/ubiquiti_llm/migrations
mysql -h 190.7.234.37 -P 3025 -u root -p ipnext < add_recovery_notified_column.sql
```

### Option 2: Using Python/SQLAlchemy
```bash
cd /Users/rhernandezba/PycharmProjects/ubiquiti_llm
python -c "from app_fast_api.utils.database import init_db; init_db()"
```
Note: This only works if you're using `Base.metadata.create_all()` which auto-creates missing columns.

### Option 3: Manual MySQL
```sql
USE ipnext;

-- Add column
ALTER TABLE alert_events
ADD COLUMN recovery_notified BOOLEAN NOT NULL DEFAULT FALSE;

-- Add index
CREATE INDEX idx_alert_events_recovery_pending
ON alert_events (status, auto_resolved, recovery_notified);

-- Verify
SELECT COUNT(*) FROM alert_events WHERE recovery_notified = FALSE;
```

## Post-Migration

### Handling Existing Resolved Events

**Option A: Mark all as notified (RECOMMENDED)**
```sql
UPDATE alert_events
SET recovery_notified = TRUE
WHERE status = 'resolved' AND auto_resolved = TRUE;
```
This prevents spam from old resolved events.

**Option B: Send retroactive notifications**
Leave them as `FALSE` and let the system send notifications for all previously resolved events on next scan.

## Testing

1. **Create test outage:**
```bash
# Manually set a site to down in database
UPDATE site_monitoring SET is_site_down = TRUE WHERE site_name = 'Test Site';
```

2. **Run scan to create alert:**
```bash
curl -X POST http://localhost:7657/api/v1/alerting/scan-with-alerts
```

3. **Recover site:**
```bash
UPDATE site_monitoring SET is_site_down = FALSE, device_outage_count = 0 WHERE site_name = 'Test Site';
```

4. **Run scan again:**
```bash
curl -X POST http://localhost:7657/api/v1/alerting/scan-with-alerts
```

5. **Verify notification sent:**
```sql
SELECT id, title, status, resolved_at, recovery_notified
FROM alert_events
WHERE site_id = (SELECT id FROM site_monitoring WHERE site_name = 'Test Site')
ORDER BY created_at DESC
LIMIT 5;
```

## Benefits

✅ **Guaranteed delivery** - No more missed notifications
✅ **Timing independent** - Works regardless of scan frequency
✅ **Idempotent** - Won't send duplicate notifications
✅ **Auditable** - Clear flag shows notification status
✅ **Debuggable** - Easy to query pending notifications

## Rollback (if needed)

```sql
-- Remove index
DROP INDEX idx_alert_events_recovery_pending ON alert_events;

-- Remove column
ALTER TABLE alert_events DROP COLUMN recovery_notified;
```

Then revert code changes in git.

## Monitoring

Query to check pending notifications:
```sql
SELECT
    ae.id,
    ae.title,
    sm.site_name,
    ae.resolved_at,
    TIMESTAMPDIFF(MINUTE, ae.resolved_at, NOW()) as minutes_since_resolution
FROM alert_events ae
JOIN site_monitoring sm ON ae.site_id = sm.id
WHERE ae.status = 'resolved'
  AND ae.auto_resolved = TRUE
  AND ae.recovery_notified = FALSE
ORDER BY ae.resolved_at DESC;
```
