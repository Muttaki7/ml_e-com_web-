"""Minimal demo catalog used by the hosted bootstrap when a database is empty."""
from urllib.parse import quote
from xml.sax.saxutils import escape

CATEGORIES = [
    ("Electronics", "electronics", ["Mobile Phones", "Laptops", "Accessories"]),
    ("Fashion", "fashion", ["Men's Clothing", "Women's Clothing", "Shoes"]),
    ("Home & Living", "home-living", ["Kitchen", "Furniture", "Decor"]),
    ("Groceries", "groceries", ["Rice & Flour", "Spices", "Snacks"]),
    ("Beauty", "beauty", ["Skincare", "Makeup"]),
]

PRODUCTS = [
    ("Samsung Galaxy A55", "Electronics", "Mobile Phones", 320, 389, 45, True),
    ("Xiaomi Redmi Note 13", "Electronics", "Mobile Phones", 180, 229, 80, True),
    ("Acer Aspire 5 Laptop", "Electronics", "Laptops", 450, 549, 25, True),
    ("Anker PowerBank 20000mAh", "Electronics", "Accessories", 18, 24, 120, False),
    ("Men's Cotton Shirt", "Fashion", "Men's Clothing", 6, 9, 200, False),
    ("Women's Summer Dress", "Fashion", "Women's Clothing", 12, 18, 150, True),
    ("Sports Shoes Unisex", "Fashion", "Shoes", 9, 14, 90, True),
    ("Non-stick Fry Pan", "Home & Living", "Kitchen", 4, 7, 70, False),
    ("Jasmine Rice 10kg", "Groceries", "Rice & Flour", 18, 21, 300, False),
    ("Spicy Snack Mix", "Groceries", "Snacks", 0.35, 0.55, 500, False),
    ("Gentle Face Wash", "Beauty", "Skincare", 1.8, 2.99, 200, False),
    ("Matte Lipstick", "Beauty", "Makeup", 3.5, 5.5, 100, True),
]

_IMAGE_GRADIENTS = [
    ("#0ea5e9", "#4f46e5"),
    ("#10b981", "#0d9488"),
    ("#f43f5e", "#f97316"),
    ("#8b5cf6", "#7c3aed"),
    ("#f59e0b", "#eab308"),
    ("#06b6d4", "#0284c7"),
]


def demo_image(name: str, index: int) -> str:
    """Self-contained SVG placeholder so the hosted demo has product art
    without relying on an external image host or the ephemeral Render disk."""
    start, end = _IMAGE_GRADIENTS[index % len(_IMAGE_GRADIENTS)]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800">'
        "<defs>"
        f'<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{start}"/>'
        f'<stop offset="1" stop-color="{end}"/>'
        "</linearGradient>"
        "</defs>"
        '<rect width="800" height="800" fill="url(#g)"/>'
        '<circle cx="400" cy="330" r="165" fill="rgba(255,255,255,0.16)"/>'
        '<text x="400" y="405" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" '
        f'font-size="210" font-weight="700" fill="#ffffff">{escape(name[:1].upper())}</text>'
        '<text x="400" y="590" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" '
        f'font-size="42" font-weight="600" fill="#ffffff">{escape(name)}</text>'
        '<text x="400" y="660" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" '
        'font-size="24" fill="rgba(255,255,255,0.75)">GlobalShop demo</text>'
        "</svg>"
    )
    return "data:image/svg+xml," + quote(svg)
