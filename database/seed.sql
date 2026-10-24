-- ============================================================================
-- GlobalShop demo catalog for the SQL reference schema (PostgreSQL 14+)
--
-- Runtime seeding is done by scripts/seed.py (local demo) or
-- python -m app.cli.bootstrap (hosted demo catalog). The application uses
-- MongoDB, not this file.
--
-- This seed intentionally contains only the catalog and storefront settings.
-- Admin and customer accounts are never seeded here: credentials and password
-- hashes are created by the application bootstrapping/CLI and stay out of SQL.
--
-- IDs are stable, 24-character ObjectId-style strings so the rows map cleanly
-- to documents in MongoDB. All statements are idempotent.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- Categories: 5 roots + 14 children
-- ----------------------------------------------------------------------------
INSERT INTO categories (id, name, slug, parent_id, sort_order, status, created_at, updated_at) VALUES
    ('64f000000000000000000001', 'Electronics',       'electronics',        NULL,                          0, 'active', now(), now()),
    ('64f000000000000000000002', 'Fashion',           'fashion',            NULL,                          1, 'active', now(), now()),
    ('64f000000000000000000003', 'Home & Living',     'home-living',        NULL,                          2, 'active', now(), now()),
    ('64f000000000000000000004', 'Groceries',         'groceries',          NULL,                          3, 'active', now(), now()),
    ('64f000000000000000000005', 'Beauty',            'beauty',             NULL,                          4, 'active', now(), now()),
    ('64f000000000000000000006', 'Mobile Phones',     'mobile-phones',      '64f000000000000000000001',    0, 'active', now(), now()),
    ('64f000000000000000000007', 'Laptops',           'laptops',            '64f000000000000000000001',    1, 'active', now(), now()),
    ('64f000000000000000000008', 'Accessories',       'accessories',        '64f000000000000000000001',    2, 'active', now(), now()),
    ('64f000000000000000000009', 'Men''s Clothing',    'mens-clothing',      '64f000000000000000000002',    0, 'active', now(), now()),
    ('64f000000000000000000010', 'Women''s Clothing',  'womens-clothing',    '64f000000000000000000002',    1, 'active', now(), now()),
    ('64f000000000000000000011', 'Shoes',             'shoes',              '64f000000000000000000002',    2, 'active', now(), now()),
    ('64f000000000000000000012', 'Kitchen',           'kitchen',            '64f000000000000000000003',    0, 'active', now(), now()),
    ('64f000000000000000000013', 'Furniture',         'furniture',          '64f000000000000000000003',    1, 'active', now(), now()),
    ('64f000000000000000000014', 'Decor',             'decor',              '64f000000000000000000003',    2, 'active', now(), now()),
    ('64f000000000000000000015', 'Rice & Flour',      'rice-flour',         '64f000000000000000000004',    0, 'active', now(), now()),
    ('64f000000000000000000016', 'Spices',            'spices',             '64f000000000000000000004',    1, 'active', now(), now()),
    ('64f000000000000000000017', 'Snacks',            'snacks',             '64f000000000000000000004',    2, 'active', now(), now()),
    ('64f000000000000000000018', 'Skincare',          'skincare',           '64f000000000000000000005',    0, 'active', now(), now()),
    ('64f000000000000000000019', 'Makeup',            'makeup',             '64f000000000000000000005',    1, 'active', now(), now())
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------------------
-- Products: the 12 demo products used by the hosted bootstrap.
-- Images are generated at runtime by the bootstrap (inline SVG data URLs) or
-- uploaded through the admin UI, so the SQL seed keeps the image arrays empty.
-- ----------------------------------------------------------------------------
INSERT INTO products (
    id, name, slug, sku, description, category_id, brand,
    purchase_price, selling_price, discount_percent, tax_percent,
    stock_quantity, min_stock_level, reserved, images, videos, variants, tags,
    is_featured, is_best_seller, status, created_at, updated_at
) VALUES
    ('65a000000000000000000001', 'Samsung Galaxy A55', 'samsung-galaxy-a55', 'DEMO-0001',
     'Quality Samsung Galaxy A55 with fast local and international delivery.',
     '64f000000000000000000006', 'Samsung', 320.00, 389.00, 0, 0,
     45, 5, 0, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '["electronics", "mobile phones"]'::jsonb,
     TRUE, TRUE, 'active', now() - interval '60 days', now()),

    ('65a000000000000000000002', 'Xiaomi Redmi Note 13', 'xiaomi-redmi-note-13', 'DEMO-0002',
     'Quality Xiaomi Redmi Note 13 with fast local and international delivery.',
     '64f000000000000000000006', 'Xiaomi', 180.00, 229.00, 0, 0,
     80, 8, 0, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '["electronics", "mobile phones"]'::jsonb,
     TRUE, TRUE, 'active', now() - interval '58 days', now()),

    ('65a000000000000000000003', 'Acer Aspire 5 Laptop', 'acer-aspire-5-laptop', 'DEMO-0003',
     'Quality Acer Aspire 5 Laptop with fast local and international delivery.',
     '64f000000000000000000007', 'Acer', 450.00, 549.00, 0, 0,
     25, 5, 0, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '["electronics", "laptops"]'::jsonb,
     TRUE, TRUE, 'active', now() - interval '56 days', now()),

    ('65a000000000000000000004', 'Anker PowerBank 20000mAh', 'anker-powerbank-20000mah', 'DEMO-0004',
     'Quality Anker PowerBank 20000mAh with fast local and international delivery.',
     '64f000000000000000000008', 'Anker', 18.00, 24.00, 0, 0,
     120, 12, 0, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '["electronics", "accessories"]'::jsonb,
     FALSE, FALSE, 'active', now() - interval '54 days', now()),

    ('65a000000000000000000005', 'Men''s Cotton Shirt', 'mens-cotton-shirt', 'DEMO-0005',
     'Quality Men''s Cotton Shirt with fast local and international delivery.',
     '64f000000000000000000009', 'Men''s', 6.00, 9.00, 0, 0,
     200, 20, 0, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '["fashion", "men''s clothing"]'::jsonb,
     FALSE, FALSE, 'active', now() - interval '52 days', now()),

    ('65a000000000000000000006', 'Women''s Summer Dress', 'womens-summer-dress', 'DEMO-0006',
     'Quality Women''s Summer Dress with fast local and international delivery.',
     '64f000000000000000000010', 'Women''s', 12.00, 18.00, 0, 0,
     150, 15, 0, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '["fashion", "women''s clothing"]'::jsonb,
     TRUE, TRUE, 'active', now() - interval '50 days', now()),

    ('65a000000000000000000007', 'Sports Shoes Unisex', 'sports-shoes-unisex', 'DEMO-0007',
     'Quality Sports Shoes Unisex with fast local and international delivery.',
     '64f000000000000000000011', 'Sports', 9.00, 14.00, 0, 0,
     90, 9, 0, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '["fashion", "shoes"]'::jsonb,
     TRUE, TRUE, 'active', now() - interval '48 days', now()),

    ('65a000000000000000000008', 'Non-stick Fry Pan', 'non-stick-fry-pan', 'DEMO-0008',
     'Quality Non-stick Fry Pan with fast local and international delivery.',
     '64f000000000000000000012', 'Non-stick', 4.00, 7.00, 0, 0,
     70, 7, 0, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '["home & living", "kitchen"]'::jsonb,
     FALSE, FALSE, 'active', now() - interval '46 days', now()),

    ('65a000000000000000000009', 'Jasmine Rice 10kg', 'jasmine-rice-10kg', 'DEMO-0009',
     'Quality Jasmine Rice 10kg with fast local and international delivery.',
     '64f000000000000000000015', 'Jasmine', 18.00, 21.00, 0, 0,
     300, 30, 0, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '["groceries", "rice & flour"]'::jsonb,
     FALSE, FALSE, 'active', now() - interval '44 days', now()),

    ('65a000000000000000000010', 'Spicy Snack Mix', 'spicy-snack-mix', 'DEMO-0010',
     'Quality Spicy Snack Mix with fast local and international delivery.',
     '64f000000000000000000017', 'Spicy', 0.35, 0.55, 0, 0,
     500, 50, 0, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '["groceries", "snacks"]'::jsonb,
     FALSE, FALSE, 'active', now() - interval '42 days', now()),

    ('65a000000000000000000011', 'Gentle Face Wash', 'gentle-face-wash', 'DEMO-0011',
     'Quality Gentle Face Wash with fast local and international delivery.',
     '64f000000000000000000018', 'Gentle', 1.80, 2.99, 0, 0,
     200, 20, 0, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '["beauty", "skincare"]'::jsonb,
     FALSE, FALSE, 'active', now() - interval '40 days', now()),

    ('65a000000000000000000012', 'Matte Lipstick', 'matte-lipstick', 'DEMO-0012',
     'Quality Matte Lipstick with fast local and international delivery.',
     '64f000000000000000000019', 'Matte', 3.50, 5.50, 0, 0,
     100, 10, 0, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '["beauty", "makeup"]'::jsonb,
     TRUE, TRUE, 'active', now() - interval '38 days', now())
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------------------
-- Inventory: one default warehouse row per product (warehouse_id NULL)
-- ----------------------------------------------------------------------------
INSERT INTO inventory (id, product_id, warehouse_id, quantity, reserved, min_level, stock_status, updated_at) VALUES
    ('66b000000000000000000001', '65a000000000000000000001', NULL, 45,  0, 5,  'in_stock', now()),
    ('66b000000000000000000002', '65a000000000000000000002', NULL, 80,  0, 8,  'in_stock', now()),
    ('66b000000000000000000003', '65a000000000000000000003', NULL, 25,  0, 5,  'in_stock', now()),
    ('66b000000000000000000004', '65a000000000000000000004', NULL, 120, 0, 12, 'in_stock', now()),
    ('66b000000000000000000005', '65a000000000000000000005', NULL, 200, 0, 20, 'in_stock', now()),
    ('66b000000000000000000006', '65a000000000000000000006', NULL, 150, 0, 15, 'in_stock', now()),
    ('66b000000000000000000007', '65a000000000000000000007', NULL, 90,  0, 9,  'in_stock', now()),
    ('66b000000000000000000008', '65a000000000000000000008', NULL, 70,  0, 7,  'in_stock', now()),
    ('66b000000000000000000009', '65a000000000000000000009', NULL, 300, 0, 30, 'in_stock', now()),
    ('66b000000000000000000010', '65a000000000000000000010', NULL, 500, 0, 50, 'in_stock', now()),
    ('66b000000000000000000011', '65a000000000000000000011', NULL, 200, 0, 20, 'in_stock', now()),
    ('66b000000000000000000012', '65a000000000000000000012', NULL, 100, 0, 10, 'in_stock', now())
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------------------
-- Storefront settings singleton (defaults from backend/app/api/v1/settings.py)
-- ----------------------------------------------------------------------------
INSERT INTO site_settings (
    id, store, banner, posters, delivery, payments, company, updated_by, updated_at
) VALUES (
    'core',
    $json${"country":"US","currency":"USD","currency_symbol":"$","timezone":"UTC"}$json$::jsonb,
    $json${
        "badge": "AI-powered pricing & stock forecasting",
        "title": "Shop smarter, anywhere in the world",
        "subtitle": "Products from trusted sellers. Cash on Delivery - delivered to 200+ countries and territories.",
        "images": []
    }$json$::jsonb,
    $json$[
        {"title":"Big Sale","subtitle":"Up to 50% off electronics","accent":"from-rose-500 to-orange-400","visible":true,"images":[]},
        {"title":"Best Price","subtitle":"Everyday low prices","accent":"from-emerald-500 to-teal-400","visible":true,"images":[]},
        {"title":"Free Delivery","subtitle":"On orders above the set threshold","accent":"from-sky-500 to-cyan-400","visible":true,"images":[]},
        {"title":"New Arrivals","subtitle":"Fresh collection every week","accent":"from-indigo-500 to-violet-400","visible":true,"images":[]}
    ]$json$::jsonb,
    $json${"local_charge":5.0,"international_charge":25.0,"free_delivery_enabled":true,"free_delivery_threshold":50.0}$json$::jsonb,
    $json${
        "methods": [
            {"id":"cod","label":"Cash on Delivery","enabled":true},
            {"id":"card","label":"Credit / Debit Card","enabled":false},
            {"id":"paypal","label":"PayPal","enabled":false},
            {"id":"bkash","label":"bKash (Bangladesh)","enabled":false},
            {"id":"nagad","label":"Nagad (Bangladesh)","enabled":false},
            {"id":"rocket","label":"Rocket (Bangladesh)","enabled":false}
        ]
    }$json$::jsonb,
    $json${
        "name": "Global Commerce + ERP",
        "address": "",
        "support_email": "support@example.com",
        "support_phone": ""
    }$json$::jsonb,
    NULL,
    now()
)
ON CONFLICT DO NOTHING;

COMMIT;

-- ============================================================================
-- Intentionally omitted:
--   * admins and customers (created by scripts/seed.py or app.cli.bootstrap;
--     passwords and 2FA secrets must never be committed)
--   * orders and payments (generated through checkout or the demo seed script)
--   * audit_logs and refresh_tokens (runtime-only security data)
-- ============================================================================
