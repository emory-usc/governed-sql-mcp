-- Base tables. These are NEVER published to a model.
-- Only the views in 02_views.sql are exposed.

CREATE TABLE IF NOT EXISTS customers (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    region      TEXT NOT NULL,
    manager_id  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id             TEXT PRIMARY KEY,
    customer_id    TEXT NOT NULL REFERENCES customers(id),
    account_type   TEXT NOT NULL,
    balance        REAL NOT NULL,
    account_number TEXT NOT NULL
);
