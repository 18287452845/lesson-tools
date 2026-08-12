"""AI cost, reliability, and generated-content quality dashboard API."""
import json

from fastapi import APIRouter, Query

from ..models.database import db
from ..services.ai_metrics import PRICE_USD_PER_MTOK


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/ai/summary")
async def ai_summary(days: int = Query(30, ge=1, le=365)):
    interval = f"-{days} days"
    total = await db.fetch_one(
        """
        SELECT COUNT(*) AS calls,
               COALESCE(SUM(total_tokens), 0) AS total_tokens,
               COALESCE(SUM(estimated_cost), 0) AS estimated_cost,
               COALESCE(AVG(latency_ms), 0) AS avg_latency_ms,
               COALESCE(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END), 0) AS successes
        FROM ai_usage_metrics WHERE created_at >= datetime('now', ?)
        """, (interval,),
    )
    by_model = await db.fetch_all(
        """
        SELECT provider, model, COUNT(*) AS calls, SUM(total_tokens) AS total_tokens,
               SUM(estimated_cost) AS estimated_cost,
               AVG(latency_ms) AS avg_latency_ms
        FROM ai_usage_metrics WHERE created_at >= datetime('now', ?)
        GROUP BY provider, model ORDER BY estimated_cost DESC
        """, (interval,),
    )
    daily = await db.fetch_all(
        """
        SELECT substr(created_at, 1, 10) AS date, COUNT(*) AS calls,
               SUM(total_tokens) AS total_tokens, SUM(estimated_cost) AS estimated_cost
        FROM ai_usage_metrics WHERE created_at >= datetime('now', ?)
        GROUP BY substr(created_at, 1, 10) ORDER BY date
        """, (interval,),
    )
    result = dict(total or {})
    calls = int(result.get("calls", 0))
    result["success_rate"] = round(int(result.get("successes", 0)) / calls * 100, 1) if calls else 0
    result["estimated_cost"] = round(float(result.get("estimated_cost", 0)), 6)
    return {
        "period_days": days, "summary": result,
        "by_model": [dict(row) for row in by_model],
        "daily": [dict(row) for row in daily],
        "pricing": PRICE_USD_PER_MTOK,
        "cost_notice": "基于 API usage 和当前单价估算，最终以服务商账单为准。",
    }


@router.get("/quality/summary")
async def quality_summary(days: int = Query(30, ge=1, le=365)):
    rows = await db.fetch_all(
        """
        SELECT score, dimensions, source_type, created_at
        FROM content_quality_metrics WHERE created_at >= datetime('now', ?)
        ORDER BY created_at DESC LIMIT 500
        """, (f"-{days} days",),
    )
    dimensions: dict[str, list[float]] = {}
    scores = []
    recent = []
    for row in rows:
        scores.append(float(row["score"]))
        values = json.loads(row["dimensions"] or "{}")
        for key, value in values.items():
            dimensions.setdefault(key, []).append(float(value))
        if len(recent) < 20:
            recent.append(dict(row))
    return {
        "count": len(scores),
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "pass_rate": round(sum(score >= 80 for score in scores) / len(scores) * 100, 1) if scores else 0,
        "dimensions": {
            key: round(sum(values) / len(values), 1) for key, values in dimensions.items()
        },
        "recent": recent,
    }
