# DB Backup & Restore Runbook

## Overview

PostgreSQL backups run daily at 02:00 server time via the `backup` Docker Compose service.
Backups are stored in the `postgres_backups` Docker volume and follow this retention policy:

| Cadence | Kept | Schedule |
|---------|------|----------|
| Daily   | 7    | Every day |
| Weekly  | 4    | Every Sunday |
| Monthly | 3    | 1st of each month |

Backup files use the PostgreSQL custom format (`-Fc`) which is compressed and supports
selective restore.

---

## Backup Location

Inside the `backup` container, backups are written to `/backups/`:

```
/backups/
  daily/
    2026-03-19.dump
    2026-03-18.dump
    ...
  weekly/
    2026-12.dump
    ...
  monthly/
    2026-03.dump
    ...
  backup.log          ← cron output (append-only)
```

On the host, these files live in the `postgres_backups` named volume.

To find the volume mount path on the host:

```bash
docker inspect postgres_backups | grep Mountpoint
```

---

## Verifying Backups

### Check the backup log

```bash
docker compose exec backup tail -50 /backups/backup.log
```

### List backup files

```bash
docker compose exec backup ls -lh /backups/daily/ /backups/weekly/ /backups/monthly/
```

### Run a manual backup immediately

```bash
docker compose exec backup sh -c \
  "chmod +x /usr/local/bin/backup-postgres.sh && /usr/local/bin/backup-postgres.sh"
```

---

## Restore Procedure

### Step 1 — Identify the backup file to restore

```bash
docker compose exec backup ls -lh /backups/daily/
# Example output:
#   -rw-r--r--    1 root     root     2.3M Mar 19 02:00 2026-03-19.dump
```

Choose the most recent clean backup.

### Step 2 — Stop the application to prevent writes during restore

```bash
docker compose stop backend frontend
```

### Step 3 — Drop and recreate the target database

```bash
docker compose exec postgres psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'the_wealth' AND pid <> pg_backend_pid();"
docker compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS the_wealth;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE the_wealth OWNER postgres;"
```

### Step 4 — Restore the dump

Copy the backup from the backup container to the postgres container and restore:

```bash
# Get the backup out of the backup container
docker cp $(docker compose ps -q backup):/backups/daily/2026-03-19.dump ./restore.dump

# Copy into the postgres container
docker cp ./restore.dump $(docker compose ps -q postgres):/tmp/restore.dump

# Run pg_restore
docker compose exec postgres pg_restore \
  -U postgres \
  -d the_wealth \
  --no-owner \
  --role=postgres \
  /tmp/restore.dump

# Clean up temp file
docker compose exec postgres rm /tmp/restore.dump
rm restore.dump
```

### Step 5 — Restart the application

```bash
docker compose start backend frontend
```

### Step 6 — Verify

```bash
# Check backend health
curl http://localhost:8000/health

# Spot-check row counts
docker compose exec postgres psql -U postgres -d the_wealth -c \
  "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"
```

---

## Periodic Restore Test Schedule

Run a restore test at least **once per month** to validate backup integrity:

1. Spin up an isolated postgres container:
   ```bash
   docker run -d --name restore_test \
     -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=the_wealth_test \
     postgres:16-alpine
   ```

2. Restore the latest backup into it:
   ```bash
   docker cp $(docker compose ps -q backup):/backups/daily/$(date +%Y-%m-%d).dump ./test.dump
   docker cp ./test.dump restore_test:/tmp/restore.dump
   docker exec restore_test pg_restore -U postgres -d the_wealth_test \
     --no-owner /tmp/restore.dump
   ```

3. Verify row counts:
   ```bash
   docker exec restore_test psql -U postgres -d the_wealth_test -c \
     "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"
   ```

4. Tear down:
   ```bash
   docker rm -f restore_test
   rm test.dump
   ```

Record the test result and date in the team wiki or a `docs/runbooks/restore-test-log.md` file.

---

## Environment Variables

The backup service is configured via environment variables in `docker-compose.yml` or `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `postgres` | Postgres hostname (Docker service name) |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `POSTGRES_DB` | `the_wealth` | Database name |
| `BACKUP_DIR` | `/backups` | Destination directory inside backup container |
| `BACKUP_KEEP_DAILY` | `7` | Daily backups to retain |
| `BACKUP_KEEP_WEEKLY` | `4` | Weekly backups to retain |
| `BACKUP_KEEP_MONTHLY` | `3` | Monthly backups to retain |

Override defaults in `backend/.env`:

```env
BACKUP_KEEP_DAILY=14
BACKUP_KEEP_WEEKLY=8
BACKUP_KEEP_MONTHLY=6
```

---

## External Storage (Future)

The backup script currently stores files on the local Docker volume only.
To add off-site S3 / GCS / R2 uploads, see `docs/plan/manual-tasks.md` under
**P0 — DB Backup External Storage**.
