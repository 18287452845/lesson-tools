"""Shared launch and startup-recovery helpers for durable batch checkpoints."""
import logging

from ..config import settings
from ..models.database import db
from .background_runner import run_in_background
from .batch_processor import BatchTaskProcessor


logger = logging.getLogger(__name__)


def launch_batch_task(task_id: str, hours_per_lesson: int, task_type: str = "normal") -> None:
    processor = BatchTaskProcessor(
        provider=settings.ai_provider,
        api_key=settings.get_active_api_key(),
        model=settings.get_active_model(),
        hours_per_lesson=hours_per_lesson,
    )
    is_draft = task_type == "draft"
    run_in_background(
        processor.process_batch_task(task_id, is_draft_mode=is_draft),
        name=f"{'draft' if is_draft else 'batch'}-task-{task_id}",
    )


async def recover_interrupted_batch_tasks() -> int:
    """Resume persisted pending/stale-processing tasks after an app restart."""
    rows = await db.fetch_all(
        """
        SELECT id, hours_per_lesson, task_type FROM batch_tasks
        WHERE status IN ('pending', 'processing') ORDER BY created_at
        """
    )
    for row in rows:
        await db.execute(
            "UPDATE batch_tasks SET status = 'pending', error_message = NULL WHERE id = ?",
            (row["id"],), commit=True,
        )
        launch_batch_task(
            row["id"], int(row["hours_per_lesson"] or 2), row["task_type"] or "normal"
        )
    if rows:
        logger.info("Recovered %s interrupted batch tasks", len(rows))
    return len(rows)
