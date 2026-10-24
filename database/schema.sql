-- ============================================================================
-- GlobalShop reference schema (PostgreSQL 14+)
--
-- Runtime datastore: MongoDB 7 through the Motor async driver.
-- This file is a normalized, SQL-readable mirror of the MongoDB collections
-- for review, analytics tooling, and database documentation. The application
-- does not execute it and there is no SQL/ORM layer in the runtime.
--
-- Source of truth:
--   backend/app/core/database.py       collection indexes
--   backend/app/schemas/*.py           API request/response contracts
--   backend/app/api/v1/*.py            stored document fields and defaults
--   backend/app/services/*.py          auth, invoice, and payment writes
--
-- Normalization choices:
--   * MongoDB ObjectId (24 hex characters) is represented as TEXT.
--   * Embedded documents/arrays are represented as JSONB.
--   * Money is NUMERIC(14,2) here; the API currently stores floats.
--   * BSON UTC datetimes are represented as TIMESTAMPTZ.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- categories (collection: categories)
-- Self-referencing tree. Runtime soft delete sets status = 'deleted'.
-- Runtime field "order" is represented as sort_order here.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    parent_id   TEXT REFERENCES categories (id) ON DELETE SET NULL,
    description TEXT,
    image       TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive', 'deleted')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_categories_parent_id ON categories (parent_id);
CREATE INDEX IF NOT EXISTS ix_categories_status ON categories (status);

-- ----------------------------------------------------------------------------
-- suppliers (collection: suppliers)
-- Reserved for the purchasing module; the current public API does not expose it.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS suppliers (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    email          TEXT,
    phone          TEXT,
    contact_person TEXT,
    address        JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes          TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_suppliers_email ON suppliers (email);

-- ----------------------------------------------------------------------------
-- products (collection: products)
-- stock_quantity/reserved are the live checkout counters. The inventory table
-- is a per-warehouse mirror used by inventory screens and transfers.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id                    TEXT PRIMARY KEY,
    name                  TEXT NOT NULL,
    slug                  TEXT NOT NULL,
    sku                   TEXT NOT NULL UNIQUE,
    barcode               TEXT,
    description           TEXT,
    specifications        JSONB NOT NULL DEFAULT '{}'::jsonb,
    category_id           TEXT REFERENCES categories (id) ON DELETE SET NULL,
    brand                 TEXT,
    purchase_price        NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (purchase_price >= 0),
    selling_price         NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (selling_price >= 0),
    discount_percent      NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (discount_percent BETWEEN 0 AND 100),
    tax_percent           NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (tax_percent BETWEEN 0 AND 100),
    stock_quantity        INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    min_stock_level       INTEGER NOT NULL DEFAULT 5 CHECK (min_stock_level >= 0),
    reserved              INTEGER NOT NULL DEFAULT 0 CHECK (reserved >= 0),
    supplier_id           TEXT REFERENCES suppliers (id) ON DELETE SET NULL,
    images                JSONB NOT NULL DEFAULT '[]'::jsonb,
    videos                JSONB NOT NULL DEFAULT '[]'::jsonb,
    variants              JSONB NOT NULL DEFAULT '[]'::jsonb,
    tags                  JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_featured           BOOLEAN NOT NULL DEFAULT FALSE,
    is_best_seller        BOOLEAN NOT NULL DEFAULT FALSE,
    status                TEXT NOT NULL DEFAULT 'active'
                          CHECK (status IN ('active', 'inactive', 'deleted')),
    intelligence_score    NUMERIC(5,2),
    demand_trend          TEXT,
    predicted_demand_30d  NUMERIC(14,2),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_products_slug ON products (slug);
CREATE INDEX IF NOT EXISTS ix_products_category_id ON products (category_id);
CREATE INDEX IF NOT EXISTS ix_products_status ON products (status);
CREATE INDEX IF NOT EXISTS ix_products_search
    ON products USING GIN (
        to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(description, ''))
    );

-- ----------------------------------------------------------------------------
-- inventory (collection: inventory)
-- MongoDB's unique (product_id, warehouse_id) index allows one NULL warehouse
-- per product; the expression index below reproduces that behavior.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory (
    id           TEXT PRIMARY KEY,
    product_id   TEXT NOT NULL REFERENCES products (id) ON DELETE CASCADE,
    warehouse_id TEXT,
    quantity     INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    reserved     INTEGER NOT NULL DEFAULT 0 CHECK (reserved >= 0),
    min_level    INTEGER NOT NULL DEFAULT 0 CHECK (min_level >= 0),
    stock_status TEXT CHECK (stock_status IN ('in_stock', 'low_stock', 'out_of_stock')),
    updated_at   TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_inventory_product_warehouse
    ON inventory (product_id, COALESCE(warehouse_id, ''));
CREATE INDEX IF NOT EXISTS ix_inventory_stock_status ON inventory (stock_status);

-- ----------------------------------------------------------------------------
-- customers (collection: customers)
-- two_factor shape:
--   {"enabled": bool, "secret": "BASE32", "backup_codes": ["$2b$..."], "pending": bool}
-- pending_2fa shape: {"jti": "...", "expires_at": "..."}
-- addresses is an array of shipping-address objects.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id                         TEXT PRIMARY KEY,
    full_name                  TEXT NOT NULL,
    email                      TEXT NOT NULL UNIQUE,
    phone                      TEXT,
    password_hash              TEXT NOT NULL,
    status                     TEXT NOT NULL DEFAULT 'active'
                               CHECK (status IN ('active', 'disabled', 'pending')),
    addresses                  JSONB NOT NULL DEFAULT '[]'::jsonb,
    two_factor                 JSONB,
    pending_2fa                JSONB,
    failed_login_attempts      INTEGER NOT NULL DEFAULT 0,
    lockout_until              TIMESTAMPTZ,
    two_factor_failed_attempts INTEGER NOT NULL DEFAULT 0,
    two_factor_locked_until    TIMESTAMPTZ,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                 TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_customers_phone ON customers (phone);

-- ----------------------------------------------------------------------------
-- admins (collection: admins)
-- Roles and permissions are defined in backend/app/core/constants.py.
-- Main Admin (is_main_admin = true) is protected by service-level checks.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admins (
    id                         TEXT PRIMARY KEY,
    full_name                  TEXT NOT NULL,
    email                      TEXT NOT NULL UNIQUE,
    phone                      TEXT,
    password_hash              TEXT NOT NULL,
    role                       TEXT NOT NULL CHECK (role IN (
                                   'main_admin', 'admin', 'manager', 'sales_manager',
                                   'inventory_manager', 'accountant', 'purchase_manager',
                                   'customer_support', 'warehouse_staff',
                                   'delivery_manager', 'marketing_manager', 'analyst',
                                   'network_admin'
                               )),
    permissions                JSONB NOT NULL DEFAULT '[]'::jsonb,
    two_factor_required        BOOLEAN NOT NULL DEFAULT TRUE,
    two_factor                 JSONB,
    pending_2fa                JSONB,
    is_main_admin              BOOLEAN NOT NULL DEFAULT FALSE,
    status                     TEXT NOT NULL DEFAULT 'active'
                               CHECK (status IN ('active', 'disabled', 'pending')),
    failed_login_attempts      INTEGER NOT NULL DEFAULT 0,
    lockout_until              TIMESTAMPTZ,
    two_factor_failed_attempts INTEGER NOT NULL DEFAULT 0,
    two_factor_locked_until    TIMESTAMPTZ,
    must_change_password       BOOLEAN NOT NULL DEFAULT FALSE,
    created_by                 TEXT,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                 TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_admins_role ON admins (role);

-- ----------------------------------------------------------------------------
-- orders (collection: orders)
-- items is an array: {product_id, name, sku, quantity, unit_price,
--                     line_total, purchase_price}
-- shipping_address: {full_name, phone, country, state?, city,
--                    address_line, postal_code?}
-- history is an append-only array of {status, at, by}.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id                     TEXT PRIMARY KEY,
    order_number           TEXT NOT NULL UNIQUE,
    customer_id            TEXT NOT NULL REFERENCES customers (id) ON DELETE RESTRICT,
    items                  JSONB NOT NULL,
    subtotal               NUMERIC(14,2) NOT NULL DEFAULT 0,
    discount               NUMERIC(14,2) NOT NULL DEFAULT 0,
    delivery_charge        NUMERIC(14,2) NOT NULL DEFAULT 0,
    tax                    NUMERIC(14,2) NOT NULL DEFAULT 0,
    total                  NUMERIC(14,2) NOT NULL DEFAULT 0,
    currency               CHAR(3) NOT NULL,
    shipping_address       JSONB NOT NULL,
    payment_method         TEXT NOT NULL CHECK (payment_method IN (
                               'cod', 'card', 'paypal', 'bkash', 'nagad', 'rocket'
                           )),
    payment_status         TEXT NOT NULL DEFAULT 'pending' CHECK (payment_status IN (
                               'pending', 'paid', 'failed', 'refunded',
                               'cod_pending', 'cod_collected'
                           )),
    payment_transaction_id TEXT,
    status                 TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
                               'pending', 'confirmed', 'processing', 'packed',
                               'shipped', 'out_for_delivery', 'delivered',
                               'cancelled', 'returned', 'refunded'
                           )),
    notes                  TEXT,
    stock_committed        BOOLEAN NOT NULL DEFAULT FALSE,
    stock_released         BOOLEAN NOT NULL DEFAULT FALSE,
    invoice_generated_at   TIMESTAMPTZ,
    history                JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_orders_customer_id ON orders (customer_id);
CREATE INDEX IF NOT EXISTS ix_orders_status ON orders (status);
CREATE INDEX IF NOT EXISTS ix_orders_created_at ON orders (created_at);
CREATE INDEX IF NOT EXISTS ix_orders_payment_status ON orders (payment_status);

-- ----------------------------------------------------------------------------
-- payments (collection: payments)
-- One document per payment initiation; callbacks update the matching row.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    id                TEXT PRIMARY KEY,
    order_id          TEXT NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    method            TEXT NOT NULL CHECK (method IN (
                          'cod', 'card', 'paypal', 'bkash', 'nagad', 'rocket'
                      )),
    amount            NUMERIC(14,2) NOT NULL CHECK (amount >= 0),
    status            TEXT NOT NULL DEFAULT 'pending',
    transaction_id    TEXT,
    provider_response JSONB NOT NULL DEFAULT '{}'::jsonb,
    callback          JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments (order_id);

-- ----------------------------------------------------------------------------
-- site_settings (collection: site_settings)
-- Singleton document with _id = "core". JSON columns hold the nested store,
-- banner, posters, delivery, payments, and company objects. Defaults are
-- deep-merged in backend/app/api/v1/settings.py.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS site_settings (
    id         TEXT PRIMARY KEY CHECK (id = 'core'),
    store      JSONB NOT NULL DEFAULT '{}'::jsonb,
    banner     JSONB NOT NULL DEFAULT '{}'::jsonb,
    posters    JSONB NOT NULL DEFAULT '[]'::jsonb,
    delivery   JSONB NOT NULL DEFAULT '{}'::jsonb,
    payments   JSONB NOT NULL DEFAULT '{}'::jsonb,
    company    JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_by TEXT,
    updated_at TIMESTAMPTZ
);

-- ----------------------------------------------------------------------------
-- refresh_tokens (collection: refresh_tokens)
-- MongoDB has a TTL index on expires_at. SQL deployments need a scheduled
-- cleanup job because PostgreSQL has no native TTL.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         BIGSERIAL PRIMARY KEY,
    user_id    TEXT NOT NULL,
    token_type TEXT NOT NULL CHECK (token_type IN ('admin', 'customer')),
    token_jti  TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_refresh_tokens_expires_at ON refresh_tokens (expires_at);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id);

-- ----------------------------------------------------------------------------
-- audit_logs (collection: audit_logs)
-- Append-only security and business audit trail.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id          BIGSERIAL PRIMARY KEY,
    actor_id    TEXT,
    actor_type  TEXT NOT NULL CHECK (actor_type IN ('admin', 'customer', 'system')),
    action      TEXT NOT NULL,
    target_type TEXT,
    target_id   TEXT,
    details     JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip          INET,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_id ON audit_logs (actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at);

COMMIT;

-- ----------------------------------------------------------------------------
-- Runtime indexes created by backend/app/core/database.py:
--   customers.email (unique), customers.phone
--   admins.email (unique), admins.role
--   products.sku (unique), products.slug, products text(name, description),
--   products.category_id, products.status
--   categories.slug (unique), categories.parent_id
--   orders.order_number (unique), orders.customer_id, orders.status,
--   orders.created_at, orders.payment_status
--   inventory.(product_id, warehouse_id) (unique), inventory.stock_status
--   suppliers.email
--   audit_logs.actor_id, audit_logs.created_at
--   refresh_tokens.token_jti (unique), refresh_tokens.expires_at (TTL)
-- ----------------------------------------------------------------------------
