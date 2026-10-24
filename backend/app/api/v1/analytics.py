from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from app.core.database import get_db
from app.api.deps import require_permission
from app.api.v1.settings import get_store_meta

router = APIRouter(prefix="/analytics", tags=["Analytics & BI"])


@router.get("/dashboard")
async def dashboard_kpis(admin: dict = Depends(require_permission("reports.view"))):
    db = get_db()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    pipeline_sales = [
        {"$match": {"status": {"$nin": ["cancelled", "refunded"]}}},
        {"$group": {
            "_id": None,
            "total_sales": {"$sum": "$total"},
            "total_orders": {"$sum": 1},
            "total_cost": {"$sum": {"$sum": {"$map": {
                "input": "$items",
                "as": "i",
                "in": {"$multiply": ["$$i.purchase_price", "$$i.quantity"]},
            }}}},
        }},
    ]
    sales = await db.orders.aggregate(pipeline_sales).to_list(1)
    sales = sales[0] if sales else {}

    today_sales = await db.orders.aggregate([
        {"$match": {"created_at": {"$gte": today_start}, "status": {"$nin": ["cancelled"]}}},
        {"$group": {"_id": None, "sum": {"$sum": "$total"}, "count": {"$sum": 1}}},
    ]).to_list(1)

    month_sales = await db.orders.aggregate([
        {"$match": {"created_at": {"$gte": month_start}, "status": {"$nin": ["cancelled"]}}},
        {"$group": {"_id": None, "sum": {"$sum": "$total"}, "count": {"$sum": 1}}},
    ]).to_list(1)

    total_customers = await db.customers.count_documents({})
    total_products = await db.products.count_documents({"status": "active"})
    low_stock = await db.products.count_documents({
        "status": "active",
        "$expr": {"$lte": ["$stock_quantity", "$min_stock_level"]},
    })
    pending_orders = await db.orders.count_documents({"status": "pending"})

    total_revenue = sales.get("total_sales", 0) or 0
    total_cost = sales.get("total_cost", 0) or 0
    gross_profit = total_revenue - total_cost

    return {
        "currency": (await get_store_meta())["currency"],
        "total_sales": round(total_revenue, 2),
        "today_sales": round((today_sales[0]["sum"] if today_sales else 0), 2),
        "monthly_sales": round((month_sales[0]["sum"] if month_sales else 0), 2),
        "total_orders": sales.get("total_orders", 0),
        "today_orders": today_sales[0]["count"] if today_sales else 0,
        "pending_orders": pending_orders,
        "total_customers": total_customers,
        "total_products": total_products,
        "low_stock_products": low_stock,
        "gross_profit": round(gross_profit, 2),
        "profit_margin_percent": round((gross_profit / total_revenue * 100) if total_revenue else 0, 2),
    }


@router.get("/sales-by-day")
async def sales_by_day(
    days: int = Query(30, ge=7, le=365),
    admin: dict = Depends(require_permission("reports.view")),
):
    db = get_db()
    start = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"created_at": {"$gte": start}, "status": {"$nin": ["cancelled", "refunded"]}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "sales": {"$sum": "$total"},
            "orders": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    rows = await db.orders.aggregate(pipeline).to_list(days + 1)
    return [{"date": r["_id"], "sales": round(r["sales"], 2), "orders": r["orders"]} for r in rows]


@router.get("/profit-by-category")
async def profit_by_category(admin: dict = Depends(require_permission("finance.view"))):
    db = get_db()
    # Simplified: join via product category
    pipeline = [
        {"$match": {"status": {"$nin": ["cancelled", "refunded"]}}},
        {"$unwind": "$items"},
        {"$lookup": {
            "from": "products",
            "localField": "items.product_id",
            "foreignField": "_id",
            "as": "prod",
        }},
        {"$unwind": {"path": "$prod", "preserveNullAndEmptyArrays": True}},
        {"$group": {
            "_id": "$prod.category_id",
            "revenue": {"$sum": "$items.line_total"},
            "cost": {"$sum": {"$multiply": ["$items.purchase_price", "$items.quantity"]}},
        }},
        {"$lookup": {
            "from": "categories",
            "localField": "_id",
            "foreignField": "_id",
            "as": "cat",
        }},
        {"$unwind": {"path": "$cat", "preserveNullAndEmptyArrays": True}},
    ]
    rows = await db.orders.aggregate(pipeline).to_list(100)
    out = []
    for r in rows:
        rev = r.get("revenue", 0) or 0
        cost = r.get("cost", 0) or 0
        profit = rev - cost
        out.append({
            "category": (r.get("cat") or {}).get("name") or "Uncategorized",
            "revenue": round(rev, 2),
            "cost": round(cost, 2),
            "profit": round(profit, 2),
            "margin_percent": round((profit / rev * 100) if rev else 0, 2),
        })
    return sorted(out, key=lambda x: x["profit"], reverse=True)


@router.get("/business-intelligence")
async def business_intelligence(admin: dict = Depends(require_permission("reports.view", "ml.view_predictions"))):
    """Business Intelligence Center answers."""
    db = get_db()
    # Top profitable products (approx)
    pipeline = [
        {"$match": {"status": {"$nin": ["cancelled"]}}},
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.product_id",
            "name": {"$first": "$items.name"},
            "revenue": {"$sum": "$items.line_total"},
            "cost": {"$sum": {"$multiply": ["$items.purchase_price", "$items.quantity"]}},
            "qty": {"$sum": "$items.quantity"},
        }},
        {"$project": {
            "name": 1,
            "revenue": 1,
            "cost": 1,
            "qty": 1,
            "profit": {"$subtract": ["$revenue", "$cost"]},
        }},
        {"$sort": {"profit": -1}},
        {"$limit": 10},
    ]
    top_profit = await db.orders.aggregate(pipeline).to_list(10)

    low_stock = await db.products.find({
        "status": "active",
        "$expr": {"$lte": ["$stock_quantity", "$min_stock_level"]},
    }).limit(10).to_list(10)

    insights = []
    if top_profit:
        meta = await get_store_meta()
        insights.append(f"Most profitable product: {top_profit[0].get('name')} ({meta['currency']} {top_profit[0].get('profit', 0):,.0f})")
    if low_stock:
        insights.append(f"{len(low_stock)} products are at or below minimum stock level.")

    return {
        "top_profitable_products": [
            {
                "product_id": str(p["_id"]),
                "name": p.get("name"),
                "revenue": round(p.get("revenue", 0), 2),
                "profit": round(p.get("profit", 0), 2),
                "qty_sold": p.get("qty"),
            }
            for p in top_profit
        ],
        "low_stock_alerts": [
            {
                "id": str(p["_id"]),
                "name": p.get("name"),
                "stock": p.get("stock_quantity"),
                "min_level": p.get("min_stock_level"),
            }
            for p in low_stock
        ],
        "insights": insights,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }