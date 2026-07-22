---
id: STK-REDIS
title: Redis/Valkey
family: STK
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: [redis]
triggers:
  - redis
  - valkey
  - elasticache
  - cache
  - caching
  - cache-aside
  - ttl
  - rate limit
  - session store
  - distributed lock
requires: []
verification:
  - cmd: "sh -c '! grep -rnIE \"[.]keys[(][^)]\" src app lib 2>/dev/null | grep -q .'"
    expect: "exit 0 — no KEYS-pattern calls in production code (dict.keys() takes no args, so it never matches)"
    layer: G
    rules: [STK-REDIS-03]
  - cmd: "attest: nothing that cannot be lost lives only in redis/valkey — every cached or queued datum has a durable source or destination"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-REDIS-01]
  - cmd: "attest: every key written gets a ttl, or its keyspace is listed with a reason in GOVERNANCE.md"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-REDIS-02]
  - cmd: "attest: maxmemory-policy is set deliberately for this workload (allkeys-lru pure cache / noeviction + alarm otherwise)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-REDIS-04]
  - cmd: "attest: the cache-aside invalidation strategy (ttl-only vs explicit delete-on-write, and where) is documented in the project"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-REDIS-05]
  - cmd: "attest: deployed redis is managed valkey/elasticache (local dev uses the compose fragment)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-REDIS-06]
    tiers: [T3, T4]
  - cmd: "attest: key names follow {app}:{entity}:{id} (deviations documented)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-REDIS-07]
  - cmd: "attest: any distributed lock uses set nx px with expiry and the operation tolerates lock expiry (or db-level locking was chosen instead)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-REDIS-08]
last_review: 2026-07-22
---

# Redis/Valkey (STK-REDIS)

## Abstract

Redis (deployed as Valkey/ElastiCache) is a cache and ephemeral coordination layer —
never the only home of data you can't lose; that is this standard's load-bearing rule.
Everything else follows from treating the keyspace as disposable: every key gets a TTL
(memory leaks are key leaks), `maxmemory-policy` is chosen consciously, `KEYS` never
runs in prod (`SCAN` does), names follow `{app}:{entity}:{id}`, cache-aside comes with
a written invalidation strategy, and distributed locks are used with eyes open or not
at all (prefer database-level locks — ARC-CONCURRENCY). Local dev: compose fragment in
`templates/scaffolds/data/redis/`.

## Normative Rules

### STK-REDIS-01 — Redis MUST NOT be the only home of data you cannot afford to lose

**Tiers**: all required — **Layer**: A (attestation)

The design test: "if the keyspace vanished right now, is anything lost beyond latency
and recomputation?" The answer must be no. Caches rebuild from the source of truth
(SQLite/Postgres/DynamoDB); sessions may die (users re-log-in — at T4 judge whether
that's acceptable); rate-limit counters reset. Queues and jobs whose loss matters go
to SQS (durable, at-least-once) — a Redis list is not a durable queue even with AOF;
delivery semantics live in ARC-CONCURRENCY. Persistence settings (RDB/AOF) are an
optimization for warm restarts, never the durability story.

### STK-REDIS-02 — Every key MUST have a TTL unless its keyspace is explicitly exempted

**Tiers**: all required — **Layer**: A (attestation)

Memory leaks in Redis are key leaks: keys written once and never expired accumulate
until eviction or OOM. Every `SET`/`HSET`/`ZADD` path sets an expiry (`SET … EX n`, or
`EXPIRE` in the same pipeline). A keyspace that genuinely must persist (e.g. a
long-lived counter) is listed in `GOVERNANCE.md` with its reason — that written
exemption is the "explicitly argued otherwise". Spot-check live: `redis-cli --scan`
sampled through `TTL` should show few `-1`s outside exempted prefixes.

### STK-REDIS-03 — `KEYS` MUST NOT run in production code; iterate with `SCAN`

**Tiers**: all required — **Layer**: G

`KEYS pattern` is O(N) over the whole keyspace and blocks the single-threaded server —
on a shared cache it's a self-inflicted outage. Use cursor-based `SCAN`/`SSCAN`/
`HSCAN` (client libraries expose `scan_iter`-style helpers). Needing keyspace
iteration on a hot path at all is a smell: keep an index set (`SADD` at write time)
instead of pattern-matching your way to your own data. `KEYS` is tolerable only in
interactive debugging against local dev.

### STK-REDIS-04 — `maxmemory-policy` MUST be chosen consciously per workload

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Never run on defaults you haven't read. Pure cache → `allkeys-lru` (evict anything,
recompute on miss — the scaffold compose sets this). Mixed cache + must-not-evict
coordination keys → either split into two instances, or `volatile-lru` with TTLs on
exactly the evictable keys. `noeviction` (the ElastiCache/Valkey default) is correct
only when writes failing loudly at the memory ceiling is the behavior you want — and
then a memory alarm exists (OPS-ALERTS). Set `maxmemory` explicitly in
non-containerized local dev too, or the policy never fires.

### STK-REDIS-05 — Cache-aside MUST come with an explicit, documented invalidation strategy

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

The read path is standard (get → miss → load from source → `SET EX`). The design work
is invalidation, and it is written down in the project's `CLAUDE.md` or README, per
cached entity: TTL-only (staleness bounded by expiry — fine for most read-mostly
data), or delete-on-write (`DEL` the key in the same code path that updates the source
of truth). "We'll invalidate where needed" is not a strategy; unlisted cached entities
are bugs waiting to be reported as "stale data".

### STK-REDIS-06 — Deployed Redis MUST be managed Valkey/ElastiCache

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

The deployed default is ElastiCache (Valkey engine — cheaper, drop-in, actively
developed post-license-change); a solo dev does not operate Redis servers
(STK-PG-01's reasoning applies verbatim). Smallest node size first — a cache that
matters at scale will say so in metrics (OPS-FINOPS, C6 budget alarm before deploy).
In-transit encryption + AUTH token on anything beyond a private-subnet toy
(SEC-SECRETS for the token). Local dev runs the `valkey` compose fragment.

### STK-REDIS-07 — Key names SHOULD follow `{app}:{entity}:{id}`

**Tiers**: all advisory — **Layer**: A (attestation)

Colon-delimited, app-prefixed: `mytool:user:42`, `mytool:session:abc123`,
`mytool:ratelimit:login:1.2.3.4`. The app prefix makes shared instances safe and
`SCAN mytool:*` surgical; the entity segment is what TTL exemptions (STK-REDIS-02)
and invalidation docs (STK-REDIS-05) refer to. Keep segments lowercase; no spaces; ids
last.

### STK-REDIS-08 — Distributed locks: prefer database-level locking; Redis locks only with `SET NX PX` and expiry-tolerance

**Tiers**: all advisory — **Layer**: A (attestation)

First choice at this house's scale: the durable store's own primitives — Postgres
advisory locks / `SELECT … FOR UPDATE`, DynamoDB conditional writes, SQLite's
single-writer nature (ARC-CONCURRENCY). If a Redis lock is genuinely warranted:
`SET key token NX PX ms`, release via a compare-token-then-delete Lua script, and —
the fencing caveat — accept that a lock can expire while its holder still runs, so the
protected operation must itself be idempotent or conditionally guarded
(ARC-IDEMPOTENCY). If that sentence doesn't hold for your operation, don't use a Redis
lock. Redlock across nodes is out of scope at this scale.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `! grep -rnIE "[.]keys[(][^)]" src app lib 2>/dev/null \| grep -q .` | no pattern-arg `.keys(` calls in prod code | STK-REDIS-03 |
| 2–8 | attestation checklist (one per rule; -06 at T3+) | explicit yes recorded | STK-REDIS-01, -02, -04, -05, -06, -07, -08 |

**Remediation:** `.keys(` hit → replace with `scan_iter` (or an index set written at
`SET` time) · TTL audit shows persistent keys → add `EX` at write, or list the prefix
with a reason in `GOVERNANCE.md` · OOM / eviction surprises → set `maxmemory` +
policy per STK-REDIS-04 and check for TTL-less keyspaces first · stale-data report →
the entity was missing from the invalidation doc; add it and pick TTL-only vs
delete-on-write.

## Worked Example

Local dev via `templates/scaffolds/data/redis/` (valkey compose pinned to
`allkeys-lru`, `REDIS_URL` env fragment). Cache-aside with the conventions applied:

```python
import json, os, redis

r = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)

def get_user(user_id: int) -> dict:
    key = f"mytool:user:{user_id}"              # STK-REDIS-07
    if (cached := r.get(key)) is not None:
        return json.loads(cached)
    user = load_user_from_db(user_id)           # durable source of truth (STK-REDIS-01)
    r.set(key, json.dumps(user), ex=300)        # TTL always (STK-REDIS-02)
    return user

def update_user(user_id: int, fields: dict) -> None:
    save_user_to_db(user_id, fields)
    r.delete(f"mytool:user:{user_id}")          # delete-on-write (STK-REDIS-05)
```

Invalidation doc line for this entity (in the project README):
`user — cache-aside, 300s TTL, delete-on-write in update_user()`.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Redis list as the job queue for must-run work | `BRPOP`'d job lost on crash; AOF ≠ delivery guarantee | SQS for durable queues (STK-REDIS-01, ARC-CONCURRENCY) |
| Redis as primary store "temporarily" | Eviction/restart silently deletes production data | Durable store + cache-aside (STK-REDIS-01) |
| `SET` without `EX` "just for now" | Keyspace grows until OOM or surprise eviction | TTL on every write (STK-REDIS-02) |
| `KEYS user:*` in a request handler | Blocks the event loop for the whole keyspace | `SCAN` / index sets (STK-REDIS-03) |
| Default eviction policy, unread | `noeviction` write failures at the ceiling, or silent evictions you assumed away | Choose policy per workload (STK-REDIS-04) |
| Cache written by many paths, invalidated by vibes | Stale reads that no test catches | Documented per-entity strategy (STK-REDIS-05) |
| `SETNX` + separate `EXPIRE` for a lock | Crash between the two = permanent lock | Atomic `SET NX PX` (STK-REDIS-08) |
| Redis lock guarding a non-idempotent effect | Lock expiry → two holders → double side effect | DB-level lock or idempotent op (STK-REDIS-08) |
| Self-hosted Redis on EC2 at T3 | Unpatched, unmonitored, single point of failure | ElastiCache Valkey (STK-REDIS-06) |

## References

- Valkey docs / AWS ElastiCache for Valkey — the deployed default and its pricing edge
  over Redis-engine ElastiCache (STK-REDIS-06).
- Redis docs: `SCAN` vs `KEYS`, eviction policies (`maxmemory-policy`) — the operational
  facts behind STK-REDIS-03/-04.
- Redis docs: distributed locks page + Kleppmann, "How to do distributed locking" — the
  fencing-token argument for why lock expiry must be tolerated (STK-REDIS-08).
- AWS "Caching patterns" (cache-aside) — the read/write pattern STK-REDIS-05 assumes.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
