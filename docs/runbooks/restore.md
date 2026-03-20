# DB Restore Runbook

Quick reference for restoring PostgreSQL from a backup dump.
For full backup documentation see [db-backup-restore.md](./db-backup-restore.md).

---

## Restore Checklist

- [ ] Identify the target backup file
- [ ] Stop the application containers
- [ ] Drop and recreate the database
- [ ] Run `pg_restore`
- [ ] Restart the application
- [ ] Verify row counts and health endpoint

---

## Step 1 — List available backups

```bash
docker compose exec backup ls -lh /backups/daily/
docker compose exec backup ls -lh /backups/weekly/
docker compose exec backup ls -lh /backups/monthly/
```

Choose the most recent clean backup. Example: `2026-03-20.dump`.

---

## Step 2 — Stop application (prevent writes during restore)

```bash
docker compose stop backend frontend
```

---

## Step 3 — Terminate active DB connections and recreate the database

```bash
docker compose exec postgres psql -U postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity \
   WHERE datname = 'the_wealth' AND pid <> pg_backend_pid();"

docker compose exec postgres psql -U postgres -c \
  "DROP DATABASE IF EXISTS the_wealth;"

docker compose exec postgres psql -U postgres -c \
  "CREATE DATABASE the_wealth OWNER postgres;"
```

---

## Step 4 — Copy backup file and restore

```bash
# Pull the dump out of the backup container
BACKUP_FILE="2026-03-20.dump"   # <-- change to the file you identified in Step 1

docker cp $(docker compose ps -q backup):/backups/daily/${BACKUP_FILE} ./restore.dump

# Push into the postgres container
docker cp ./restore.dump $(docker compose ps -q postgres):/tmp/restore.dump

# Run pg_restore
docker compose exec postgres pg_restore \
  -U postgres \
  -d the_wealth \
  --no-owner \
  --role=postgres \
  /tmp/restore.dump

# Clean up temp files
docker compose exec postgres rm /tmp/restore.dump
rm restore.dump
```

### Restore from weekly or monthly backup

Same steps — change the source path:

```bash
# Weekly
docker cp $(docker compose ps -q backup):/backups/weekly/2026-12.dump ./restore.dump

# Monthly
docker cp $(docker compose ps -q backup):/backups/monthly/2026-03.dump ./restore.dump
```

---

## Step 5 — Restart the application

```bash
docker compose start backend frontend
```

---

## Step 6 — Verify

```bash
# Health endpoint
curl http://localhost:8000/health

# Row counts in key tables
docker compose exec postgres psql -U postgres -d the_wealth -c \
  "SELECT schemaname, tablename, n_live_tup \
   FROM pg_stat_user_tables \
   ORDER BY n_live_tup DESC;"
```

Expected: `users`, `portfolios`, `holdings`, `transactions` all have non-zero row counts.

---

## Restore to an isolated test container (non-destructive verification)

```bash
# 1. Start a temporary postgres instance
docker run -d --name restore_test \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=the_wealth_test \
  postgres:16-alpine

# 2. Copy and restore the latest daily backup
LATEST=$(docker compose exec backup ls /backups/daily/ | sort | tail -1 | tr -d '\r')
docker cp $(docker compose ps -q backup):/backups/daily/${LATEST} ./test.dump
docker cp ./test.dump restore_test:/tmp/restore.dump
docker exec restore_test pg_restore \
  -U postgres \
  -d the_wealth_test \
  --no-owner \
  /tmp/restore.dump

# 3. Spot-check row counts
docker exec restore_test psql -U postgres -d the_wealth_test -c \
  "SELECT schemaname, tablename, n_live_tup \
   FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"

# 4. Tear down
docker rm -f restore_test
rm test.dump
```

Record the test result in `docs/runbooks/restore-test-log.md`.

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `pg_restore: error: could not connect` | Wrong host or DB name | Check `POSTGRES_HOST`, `POSTGRES_DB` env vars |
| `pg_restore: error: role does not exist` | Missing role | `CREATE ROLE <role> LOGIN;` before restore |
| `ERROR: database "the_wealth" already exists` | Step 3 not completed | Re-run `DROP DATABASE` then `CREATE DATABASE` |
| Dump file is 0 bytes | Failed backup | Use the next most recent file; investigate backup logs |

Backup logs:

```bash
docker compose exec backup tail -100 /backups/backup.log
```
