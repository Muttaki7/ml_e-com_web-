from typing import List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks, Query
from app.api.deps import require_permission
from app.ml.demand_forecast import (
    predict_product_demand,
    compute_intelligence_score,
    run_batch_forecast,
)

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


@router.get("/demand/{product_id}")
async def product_demand(
    product_id: str,
    admin: dict = Depends(require_permission("ml.view_predictions")),
):
    return await predict_product_demand(product_id)


@router.get("/intelligence/{product_id}")
async def product_intelligence(
    product_id: str,
    admin: dict = Depends(require_permission("ml.view_predictions")),
):
    return await compute_intelligence_score(product_id)


@router.post("/forecast/batch")
async def batch_forecast(
    background_tasks: BackgroundTasks,
    limit: int = Query(30, ge=1, le=200),
    admin: dict = Depends(require_permission("ml.run_analysis", "ml.train_model")),
):
    """Run demand forecasts for many products (async-friendly)."""
    # For production use Celery; here we run in background task of FastAPI
    async def _job():
        await run_batch_forecast(limit)

    background_tasks.add_task(_job)
    return {
        "message": f"Batch forecast started for up to {limit} products",
        "status": "queued",
    }


@router.get("/recommendations/purchase")
async def smart_purchase_recommendations(
    limit: int = Query(20, ge=1, le=100),
    admin: dict = Depends(require_permission("ml.view_predictions", "inventory.view")),
):
    from app.core.database import get_db
    from bson import ObjectId
    db = get_db()
    products = await db.products.find({
        "status": "active",
        "predicted_demand_30d": {"$exists": True},
    }).sort("predicted_demand_30d", -1).limit(limit).to_list(limit)

    recs = []
    for p in products:
        pred = p.get("predicted_demand_30d") or 0
        stock = p.get("stock_quantity") or 0
        if pred > stock:
            recs.append({
                "product_id": str(p["_id"]),
                "name": p.get("name"),
                "current_stock": stock,
                "predicted_30d": pred,
                "recommended_purchase": int(pred - stock + p.get("min_stock_level", 5)),
                "trend": p.get("demand_trend"),
                "reason": "Predicted demand exceeds available stock",
            })
    return recs


@router.get("/models")
async def list_models(admin: dict = Depends(require_permission("ml.view_predictions"))):
    """Model registry placeholder – in production store versions in DB."""
    return [
        {
            "name": "demand_forecast_v1",
            "version": "1.0.0",
            "method": "moving_average_trend",
            "status": "active",
            "description": "Simple robust forecast for sparse retail data across markets",
        },
        {
            "name": "product_intelligence_v1",
            "version": "1.0.0",
            "method": "weighted_score",
            "status": "active",
        },
    ]