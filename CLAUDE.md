# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI microservice for analyzing Ubiquiti wireless network devices. Connects via SSH to devices, queries UISP API for device data, and uses OpenAI LLM (gpt-4o-mini) to generate NOC recommendations for wireless access points.

## Development Commands

### Local Development

```bash
# Install dependencies
poetry install

# Run application (auto-loads .env)
python app_fast_api/main.py

# Run with Uvicorn directly
uvicorn app_fast_api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
# Build and run
docker compose up --build

# View logs
docker compose logs -f

# Stop
docker compose down

# API access: http://localhost:7657
# Docs: http://localhost:7657/docs
```

### Required Environment Variables (.env)

```
UISP_BASE_URL=https://your-uisp-url/
UISP_TOKEN=your-token
OPENAI_API_KEY=sk-proj-...
LLM_MODEL=gpt-4o-mini
DATABASE_URL=mysql+pymysql://user:pass@host:port/db
LOG_LEVEL=INFO
```

## Architecture

### Layered Design

```
Routes (API endpoints)
  → Services (business logic)
    → Repositories (data access)
      → Database (SQLAlchemy ORM)
```

### Core Analysis Workflow

The main endpoint is `POST /api/v1/stations/analyze`:

1. **AnalyzeStationsServices** orchestrates the workflow:
   - `match_device_data()`: Query UISP API by IP/MAC
   - `ping_device_seconds()`: SSH connectivity test (10s)
   - `scan_and_match_aps_direct()`: Scan nearby APs via SSH
   - `get_device_data()`: Extract device metrics from UISP

2. **LLMService**: Send collected data to OpenAI for analysis

3. **UbiquitiDataService**: Save results to MySQL
   - Creates DeviceAnalysis record
   - Creates ScanResult records (one per discovered AP)

### Key Services

**UbiquitiSSHClient** (`services/ubiquiti_ssh_client.py`, 883 lines)
- All SSH operations: ping, iwlist scanning, device config
- Uses asyncssh for non-blocking connections
- Frequency band enable/disable operations

**SSHAuthService** (`services/ssh_auth_service.py`)
- Automatic credential fallback
- Tries user credentials first, then 4 defaults from `utils/constans.py`
- Handles timeouts gracefully

**UISPService** (`services/uisp_services.py`)
- UISP (Ubiquiti ISP Platform) API client
- Device inventory and metrics

**LLMService** (`services/llm_services.py`)
- OpenAI integration for NOC recommendations

**UNMSAlertingService** (`services/alerting_services.py`)
- Event-driven alerting system for UNMS site monitoring
- Automatically detects site outages (>95% devices down)
- Creates/resolves alerts based on site health
- `/nms/api/v2.1/sites` endpoint integration

**AlertEventService** (`services/alerting_services.py`)
- Manual event management (create, acknowledge, resolve, delete)
- Supports custom events with severity levels

### Database Models

#### Device Analysis Models

**DeviceAnalysis** - Main analysis record
- Indexed on device_ip, device_mac
- Fields: signal, frequency, CPU/RAM, capacity, utilization, ping metrics
- Stores LLM output: summary, recommendations, diagnosis
- Cascade deletes: scan_results, frequency_changes

**ScanResult** - Discovered APs (related to DeviceAnalysis)
- BSSID, SSID, signal, channel, frequency
- Matching fields: is_our_ap, match_type, confidence

**FrequencyChange** - SSH operation tracking
- operation_type: enable/disable
- frequency_band: ac/m5/m2
- operation_status: success/failed/pending

#### Alerting Models

**SiteMonitoring** - UNMS site data
- Indexed on site_id (UNMS UUID)
- Tracks device counts, outage percentage, contact info
- `is_site_down` calculated based on outage_percentage
- Relationship: alerts (cascade delete)

**AlertEvent** - Event-driven alerts
- Types: site_outage, site_degraded, device_outage, custom
- Severities: critical, high, medium, low, info
- Status workflow: active → acknowledged → resolved
- Auto-resolution when site recovers
- Tracks acknowledgment and resolution metadata

### Repository Pattern

All repositories in `repositories/`:
- `ubiquiti_repositories.py`: DeviceAnalysisRepository, ScanResultRepository, FrequencyChangeRepository
- `alerting_repositories.py`: SiteMonitoringRepository, AlertEventRepository

Implement interfaces from `interfaces/`.

## Critical Implementation Details

### SSH Credential Fallback

Default credentials in `app_fast_api/utils/constans.py`:
```python
ubitiqui_password = [
    {"user": "ubnt", "password": "B8d7f9ub1234!"},
    {"user": "ubnt", "password": "B8d7f9ub"},
    {"user": "ubnt", "password": "b8d7f9ub"},
    {"user": "ubnt", "password": "B8d7f9ub1234"},
]
```

**Always use SSHAuthService** - it tries user credentials first, then falls back automatically.

### Frequency Band Constants

`ac_m5_device_frencuency` in `constans.py`: 5GHz frequencies (4920-6100 MHz in 5 MHz steps) for AC/M5 devices.

### Database Migration

On startup (`app_fast_api/main.py`):
- Checks `SHOW TABLES LIKE 'device_analysis'`
- Runs `init_db()` if tables don't exist
- Application continues even if DB unavailable (warning logged)

### Routes

- `analyze_station_routes.py`: `/api/v1/stations/analyze` (main workflow)
- `ssh_test.py`: `/ssh-test/connect`, `/ssh-test/command` (testing)
- `feedback_routes.py`: `/api/v1/feedback/*`
- `logs_routes.py`: `/api/v1/logs/*`
- `alerting_routes.py`: `/api/v1/alerting/*` (site monitoring & event management)

## Deployment

### CI/CD (GitHub Actions)

On push to `main`:
1. SSH to VPS (190.7.234.37:7657)
2. Pull/clone to `/opt/ubiquiti-llm`
3. Generate `.env` from secrets
4. `docker compose down && build --no-cache && up -d`

Production API: http://190.7.234.37:7657

## Alerting System

Event-driven system for monitoring UNMS sites. See `ALERTING_SYSTEM.md` for full documentation.

**Key endpoints:**
- `POST /api/v1/alerting/scan-sites` - Scan all sites, auto-create alerts
- `GET /api/v1/alerting/events/active` - Get active alerts
- `POST /api/v1/alerting/events/{id}/acknowledge` - Acknowledge event
- `POST /api/v1/alerting/events/{id}/resolve` - Resolve event

**Auto-detection logic:**
- Site DOWN: deviceOutageCount >= 95% of deviceCount → CRITICAL
- Site DEGRADED: deviceOutageCount >= 50% → HIGH
- Auto-resolves when site recovers

## When Modifying Code

### Adding Analysis Features
1. Add logic to AnalyzeStationsServices or new service
2. Add route in analyze_station_routes.py
3. Update DB models if needed
4. Update LLM prompt in LLMService if needed

### Adding Alerting Features
1. Extend EventType enum in `models/ubiquiti_monitoring/alerting.py`
2. Add logic to UNMSAlertingService
3. Update routes in alerting_routes.py
4. Test with `/api/v1/alerting/scan-sites`

### Adding SSH Commands
1. Add method to UbiquitiSSHClient
2. Use SSHAuthService.try_ssh_connection() for fallback
3. Parse output, return structured data

### Database Changes
1. Update models in `models/ubiquiti_monitoring/`
2. Update schemas in `schema/ubiquiti_schemas.py` (Marshmallow)
3. Update repository methods
4. Test locally - migration is automatic but verify

### Logging
Use `get_logger(__name__)` from `utils/logger.py`. LOG_LEVEL controls verbosity.

## Testing

No formal test suite. Test via:
- Swagger UI at `/docs`
- SSH test endpoint: `/ssh-test/command`
- Manual integration testing

## Notes

- **All services use singleton pattern** - inject via constructors
- **Always use async/await** for SSH, HTTP, DB operations
- **Never bypass SSHAuthService** - it handles credential fallback
- **CORS allows all origins** (`*`) - consider restricting in production
- **UISP responses are large and nested** - use UISPService helper methods
- **Schema validation**: Use Marshmallow before DB persistence