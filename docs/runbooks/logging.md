# Logging Runbook

## Overview

The application uses three complementary logging mechanisms:

| Layer | Tool | Purpose |
|-------|------|---------|
| Stdout | structlog (dev: console, prod: JSON) | Container runtime logs |
| File | RotatingFileHandler → `/var/log/the-wealth/app.log` | Persistent disk logs |
| Aggregation | Dozzle | Real-time web UI for searching/filtering container logs |
| Error tracking | Sentry | Exception capture and alerting |

---

## Accessing Logs

### 1. CLI — tail live logs

```bash
# All services
docker compose logs -f

# Backend only
docker compose logs -f backend

# Last 200 lines
docker compose logs --tail=200 backend
```

### 2. Dozzle Web UI (real-time)

Dozzle listens on `127.0.0.1:9999` (localhost only). Access it via an SSH tunnel:

```bash
# From your local machine
ssh -L 9999:localhost:9999 <your-server>
```

Then open `http://localhost:9999` in a browser.

- Select a container from the sidebar to stream its logs
- Use the search bar to filter by keyword (e.g., `ERROR`, `request_id`)
- Multi-container view available via "+" button

**Credentials** are set via `DOZZLE_USERNAME` / `DOZZLE_PASSWORD` in the root `.env`.

### 3. File logs on disk (persistent)

Backend logs are written to a named Docker volume `backend_logs`, mounted at `/var/log/the-wealth/` inside the container.

```bash
# Find the volume's host path
docker volume inspect the-wealth_backend_logs

# Stream the log file directly
docker compose exec backend tail -f /var/log/the-wealth/app.log

# Pretty-print JSON log entries
docker compose exec backend tail -f /var/log/the-wealth/app.log | jq .
```

---

## Log Rotation

Files are rotated by `RotatingFileHandler`:

| Setting | Default | Env var |
|---------|---------|---------|
| Max file size | 10 MB | `LOG_MAX_BYTES` |
| Backup files kept | 5 | `LOG_BACKUP_COUNT` |

Total maximum disk usage: ~60 MB (`10 MB × (1 + 5)`).

Rotated files: `app.log`, `app.log.1`, …, `app.log.5`.

To change the retention policy, update the values in `backend/.env` and restart:

```bash
docker compose restart backend
```

---

## Log Format

**Production** (file + stdout): JSON

```json
{
  "event": "request completed",
  "method": "GET",
  "path": "/api/portfolio",
  "status_code": 200,
  "process_time_ms": 42.3,
  "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "logger": "app.middleware.metrics",
  "level": "info",
  "timestamp": "2026-03-28T12:00:00.000000Z"
}
```

**Development** (stdout only): coloured console output.

---

## Searching Logs

### Filter by request ID

Every HTTP request receives a unique `request_id` (returned in the `X-Request-ID` response header). Use it to trace all log lines for a single request:

```bash
docker compose logs backend | grep '"request_id": "YOUR-UUID"'
# or with jq:
docker compose logs backend | jq 'select(.request_id == "YOUR-UUID")'
```

### Filter by log level

```bash
docker compose logs backend | jq 'select(.level == "error")'
```

---

## Docker Log Driver

The `backend` service is configured with Docker's `json-file` log driver with rotation:

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "5"
```

This caps Docker's own log files at ~60 MB independently of the application-level rotation.

---

## Sentry

Unhandled exceptions are captured by Sentry (production only). Configure the DSN:

- Root `.env`: `NEXT_PUBLIC_SENTRY_DSN=https://...`  (frontend build arg)
- `backend/.env`: `SENTRY_DSN=https://...`  (backend runtime)

Sentry is disabled when the DSN is empty or `NODE_ENV !== "production"`.
