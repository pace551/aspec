# Access Patterns — {project}

Filled in BEFORE the table exists (STK-DDB-01). Every read/write the application
performs is a row here; the key design below is derived from the rows, and a new query
need means a new row first, then (maybe) a new GSI — never a Scan.

## Patterns

| # | Access pattern | Operation | Key condition | Notes |
|---|---|---|---|---|
| 1 | {e.g. Get user profile} | GetItem | `PK=USER#<id>`, `SK=PROFILE` | |
| 2 | {e.g. List user's orders, newest first} | Query | `PK=USER#<id>`, `SK begins_with ORDER#`, `ScanIndexForward=false` | SK carries ISO timestamp |
| 3 | {e.g. Get order by id alone} | Query GSI1 | `GSI1PK=ORDER#<id>` | |
| 4 | {…} | | | |

## Derived key design

- Table: single table, `PK` (S) / `SK` (S). Billing: on-demand (STK-DDB-02).
- Entity key recipes:
  - `USER#<id>` / `PROFILE` — user profile item
  - `USER#<id>` / `ORDER#<created_iso>#<order_id>` — order item (pattern 2 sort order)
- GSIs (each justified by a pattern row above):
  - `GSI1`: `GSI1PK=ORDER#<id>` — pattern 3
- TTL attribute: `expires_at` (epoch seconds) on {which item types} (STK-DDB-05), or "none".
- Large payloads: {attribute} holds an S3 pointer, never the blob (STK-DDB-07).
