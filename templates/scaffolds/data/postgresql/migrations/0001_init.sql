-- 0001_init — baseline skeleton (dbmate format; alembic/drizzle projects transcribe).
-- House rules: timestamptz only (STK-PG-06); every FK indexed (STK-PG-04).

-- migrate:up
CREATE TABLE example (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- migrate:down
DROP TABLE example;
