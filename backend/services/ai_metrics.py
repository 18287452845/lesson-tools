"""AI token-cost accounting and deterministic lesson-content quality scoring."""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from ..models.database import db


logger = logging.getLogger(__name__)

# USD per million tokens. Defaults mirror provider pricing published 2026-08-12.
# The calculation is explicitly an estimate; provider invoices remain authoritative.
PRICE_USD_PER_MTOK = {
    "deepseek-v4-flash": {"input": 0.14, "cached_input": 0.0028, "output": 0.28},
    "deepseek-v4-pro": {"input": 0.435, "cached_input": 0.003625, "output": 0.87},
    "claude-sonnet-4-20250514": {"input": 3.0, "cached_input": 0.30, "output": 15.0},
}


def estimate_cost(
    model: str, prompt_tokens: int, completion_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    rates = PRICE_USD_PER_MTOK.get(model)
    if not rates:
        return 0.0
    cached = min(max(cached_input_tokens, 0), max(prompt_tokens, 0))
    uncached = max(prompt_tokens - cached, 0)
    return round(
        (uncached * rates["input"] + cached * rates["cached_input"]
         + max(completion_tokens, 0) * rates["output"]) / 1_000_000,
        8,
    )


async def record_ai_usage(
    *, provider: str, model: str, status: str, prompt_tokens: int,
    completion_tokens: int, cached_input_tokens: int = 0,
    latency_ms: int = 0, operation: str = "generate",
    error_message: Optional[str] = None,
) -> None:
    # Provider unit tests must never pollute a developer's real analytics DB.
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    try:
        await db.execute(
            """
            INSERT INTO ai_usage_metrics (
                id, provider, model, operation, status, prompt_tokens,
                cached_input_tokens, completion_tokens, total_tokens,
                estimated_cost, latency_ms, error_message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()), provider, model, operation, status,
                prompt_tokens, cached_input_tokens, completion_tokens,
                prompt_tokens + completion_tokens,
                estimate_cost(model, prompt_tokens, completion_tokens, cached_input_tokens),
                latency_ms, error_message, datetime.now().isoformat(),
            ), commit=True,
        )
    except Exception:
        logger.warning("Unable to persist AI usage metric", exc_info=True)


def evaluate_lesson_quality(content: Any) -> tuple[float, dict[str, float]]:
    data = content.model_dump() if hasattr(content, "model_dump") else dict(content or {})
    goals = data.get("teaching_goals") or {}
    goal_count = sum(len(value or []) for value in goals.values()) if isinstance(goals, dict) else 0
    completeness = sum(
        1 for value in (
            goals, data.get("key_points"), data.get("difficult_points"),
            data.get("teaching_steps"), data.get("homework"), data.get("blackboard_design"),
        ) if value
    ) / 6 * 30

    steps = [step for step in (data.get("teaching_steps") or []) if isinstance(step, dict)]
    structure = min(len(steps) / 5, 1) * 15 + min(goal_count / 5, 1) * 10
    interactive = [
        step for step in steps if step.get("teacher_activity") and step.get("student_activity")
    ]
    interaction = (len(interactive) / len(steps) * 20) if steps else 0
    durations = []
    for step in steps:
        match = re.search(r"\d+", str(step.get("duration") or ""))
        if match:
            durations.append(int(match.group()))
    time_design = 15 if len(durations) == len(steps) and sum(durations) > 0 else 7 if durations else 0
    activity_chars = sum(
        len(str(step.get("teacher_activity") or ""))
        + len(str(step.get("student_activity") or "")) for step in steps
    )
    actionability = min(activity_chars / 800, 1) * 10
    dimensions = {
        "completeness": round(completeness, 1),
        "structure": round(structure, 1),
        "interaction": round(interaction, 1),
        "time_design": round(time_design, 1),
        "actionability": round(actionability, 1),
    }
    return round(sum(dimensions.values()), 1), dimensions


async def record_quality(source_type: str, source_id: str, content: Any) -> float:
    score, dimensions = evaluate_lesson_quality(content)
    if os.getenv("PYTEST_CURRENT_TEST"):
        return score
    await db.execute(
        """
        INSERT INTO content_quality_metrics
            (id, source_type, source_id, score, dimensions, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()), source_type, source_id, score,
            json.dumps(dimensions, ensure_ascii=False), datetime.now().isoformat(),
        ), commit=True,
    )
    return score
