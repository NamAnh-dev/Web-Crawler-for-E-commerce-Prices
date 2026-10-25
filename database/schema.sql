-- EcomCheck database (SQLite).
-- One search = one row in search_runs = a snapshot of the market at that time.

CREATE TABLE IF NOT EXISTS search_runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword        TEXT    NOT NULL,
    product_count  INTEGER NOT NULL DEFAULT 0,
    notes          TEXT,                     -- e.g. a source that was skipped
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL REFERENCES search_runs(id) ON DELETE CASCADE,
    source          TEXT    NOT NULL,        -- Tiki / Lazada / Shopee
    product_id      TEXT    NOT NULL,        -- id on the source website
    name            TEXT    NOT NULL,
    brand           TEXT,
    seller          TEXT,
    category        TEXT    NOT NULL,        -- from the source, e.g. "Chuột Chơi Game"
    price           INTEGER NOT NULL,        -- VND
    original_price  INTEGER NOT NULL,        -- VND, equals price when there is no discount
    discount_pct    INTEGER NOT NULL DEFAULT 0,
    sold            INTEGER NOT NULL DEFAULT 0,
    rating          REAL,                    -- 1-5, NULL = not rated yet
    review_count    INTEGER NOT NULL DEFAULT 0,
    image_url       TEXT,
    product_url     TEXT,
    price_flag      TEXT    NOT NULL DEFAULT 'normal',  -- low / normal / high (IQR rule)
    deal_score      REAL,                    -- 0-100, NULL for unusual prices
    UNIQUE (run_id, source, product_id)
);

CREATE INDEX IF NOT EXISTS idx_products_run ON products(run_id);
