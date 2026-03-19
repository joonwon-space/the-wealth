# Managed Infrastructure Evaluation

Evaluation of moving from self-hosted PostgreSQL and Redis to managed cloud services,
addressing the single-server resilience concern identified in the 2026-03-19 action plan.

---

## Context

Current state: PostgreSQL and Redis both run as Docker containers on a single server.
Risk: server hardware failure or accidental container removal causes full data loss and outage.

Managed services provide automatic backups, failover, and SLA guarantees without operational overhead.

---

## Managed PostgreSQL

### Options Evaluated

| Provider | Free Tier | Paid Starts | Pros | Cons |
|----------|-----------|-------------|------|------|
| **Supabase** | 500 MB / 2 projects | $25/mo | Postgres-native, REST/GraphQL APIs included, branching, generous free tier | Projects pause after 1 week of inactivity on free tier |
| **Neon** | 0.5 GB storage, 10 compute hours/mo | $19/mo | Serverless autoscaling, instant branching, cold-start is fast | Relatively new, fewer regions |
| **PlanetScale** | N/A (removed free tier) | $39/mo | MySQL-compatible (Vitess); **not Postgres** | Not compatible without schema migration |
| **Railway** | $5 credit/mo | Usage-based | Simple deploys, co-located with backend | Less feature-rich than Supabase/Neon |
| **Render** | 90-day free Postgres | $7/mo | Good DX, easy deploys | Postgres versions lag slightly |

### Recommendation

**Neon** for production:
- True serverless autoscaling — cost scales to zero during off-hours
- Database branching enables safe migrations (branch → run Alembic → test → merge)
- Compatible with the existing `asyncpg` / SQLAlchemy async stack (no driver change)
- `DATABASE_URL` format is identical to standard Postgres

Migration steps:
1. Create Neon project
2. `pg_dump the_wealth | psql <neon_connection_string>`
3. Update `DATABASE_URL` in backend `.env`
4. Verify via `alembic current` and smoke-test endpoints
5. Disable local postgres container (keep `postgres_data` volume as cold backup)

---

## Managed / Serverless Redis

### Options Evaluated

| Provider | Free Tier | Paid Starts | Pros | Cons |
|----------|-----------|-------------|------|------|
| **Upstash** | 10k commands/day, 256 MB | $0.2/100k commands | Serverless per-request billing, global replication, REST API | Latency slightly higher than self-hosted for burst workloads |
| **Redis Cloud** | 30 MB | $7/mo | Official Redis product, all modules | Free tier is small |
| **Railway Redis** | $5 credit/mo | Usage-based | Simple, same platform as backend | Less reliable than Redis Cloud |
| **Render Redis** | N/A | $10/mo | Co-located | No free tier |

### Recommendation

**Upstash** for this workload:
- The app uses Redis for KIS token caching (24h TTL) and SSE connection tracking — both are low-volume
- `< 10k commands/day` likely fits within free tier for personal use
- `REDIS_URL` format is `rediss://:<password>@<host>:6379` — identical to existing usage
- TLS required (enforced by Upstash) — no code change needed as `redis.asyncio` supports it

Migration steps:
1. Create Upstash Redis database
2. Copy connection string (`rediss://...`)
3. Update `REDIS_URL` in backend `.env`
4. Restart backend — KIS token will be fetched fresh on next request
5. Monitor Redis stats in Upstash console

---

## Decision Matrix

| Concern | Self-hosted | Managed |
|---------|-------------|---------|
| Data durability | Relies on Docker volume on single disk | Daily snapshots + multi-AZ replication |
| Auto-recovery from crash | `restart: unless-stopped` (added) | Managed failover (seconds) |
| Maintenance burden | Manual upgrades, WAL tuning | Zero operational overhead |
| Cost (personal project) | Server cost only | Free tier covers current load |
| Migration complexity | — | Low (connection string change) |

**Verdict:** Migrate to Neon + Upstash when moving to production deployment.
The Docker Compose setup (with backup service) remains valid for local development.

---

## Action Items

These require user action — see `docs/plan/manual-tasks.md`:

1. Create Neon project and run data migration
2. Create Upstash Redis instance
3. Update production `.env` with new connection strings
4. Validate in staging before cutting over production traffic
