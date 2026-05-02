"""
Competition Module API endpoints.

Manages competition projects + their generated outputs (lesson plans / reports).
Outputs are produced by background tasks; clients poll progress via GET endpoints
or subscribe to SSE stream.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from ..config import settings
from ..models.database import get_db
from ..models.schemas import (
    CompetitionProject,
    CompetitionProjectCreate,
    CompetitionProjectUpdate,
    CompetitionProjectListResponse,
    CompetitionLessonPlanGenerateRequest,
    CompetitionReportGenerateRequest,
    CompetitionGenerateResponse,
    CompetitionOutput,
    CompetitionOutputListResponse,
    CompetitionLessonContent,
    CompetitionReportContent,
)
from ..services.competition_generator import CompetitionGenerator
from ..services.competition_renderer import CompetitionRenderer
from ..services.background_runner import run_in_background

logger = logging.getLogger(__name__)

router = APIRouter(tags=["competition"])


# ============================================================================
# Helper: row -> Pydantic
# ============================================================================


def _project_from_row(row) -> CompetitionProject:
    d = dict(row)
    if d.get("textbook_info"):
        try:
            d["textbook_info"] = json.loads(d["textbook_info"])
        except (json.JSONDecodeError, TypeError):
            d["textbook_info"] = None
    if d.get("context_data"):
        try:
            d["context_data"] = json.loads(d["context_data"])
        except (json.JSONDecodeError, TypeError):
            d["context_data"] = None
    return CompetitionProject(**d)


def _output_from_row(row) -> CompetitionOutput:
    d = dict(row)
    if d.get("generated_data"):
        try:
            d["generated_data"] = json.loads(d["generated_data"])
        except (json.JSONDecodeError, TypeError):
            d["generated_data"] = None
    return CompetitionOutput(**d)


# ============================================================================
# Project CRUD
# ============================================================================


@router.post("/competition/projects", response_model=CompetitionProject)
async def create_project(req: CompetitionProjectCreate):
    """Create a new competition project."""
    project_id = str(uuid4())
    now = datetime.now().isoformat()

    db = await get_db()
    await db.execute(
        """
        INSERT INTO competition_projects (
            id, name, competition_year, competition_region, competition_level,
            work_name, course_name, major_category, major_name, group_name,
            total_hours, hours_per_lesson, class_name, location,
            textbook_info, context_data, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            req.name,
            req.competition_year,
            req.competition_region,
            req.competition_level,
            req.work_name,
            req.course_name,
            req.major_category,
            req.major_name,
            req.group_name,
            req.total_hours,
            req.hours_per_lesson,
            req.class_name,
            req.location,
            json.dumps(req.textbook_info, ensure_ascii=False) if req.textbook_info else None,
            json.dumps(req.context_data, ensure_ascii=False) if req.context_data else None,
            now,
            now,
        ),
        commit=True,
    )

    row = await db.fetch_one(
        "SELECT * FROM competition_projects WHERE id = ?", (project_id,)
    )
    return _project_from_row(row)


@router.get("/competition/projects", response_model=CompetitionProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List all competition projects (most recent first)."""
    db = await get_db()
    count_row = await db.fetch_one(
        "SELECT COUNT(*) AS count FROM competition_projects"
    )
    total = count_row["count"] if count_row else 0

    offset = (page - 1) * limit
    rows = await db.fetch_all(
        """
        SELECT * FROM competition_projects
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )
    return CompetitionProjectListResponse(
        projects=[_project_from_row(r) for r in rows],
        total=total,
    )


@router.get("/competition/projects/{project_id}", response_model=CompetitionProject)
async def get_project(project_id: str):
    """Get a specific competition project."""
    db = await get_db()
    row = await db.fetch_one(
        "SELECT * FROM competition_projects WHERE id = ?", (project_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_from_row(row)


@router.patch("/competition/projects/{project_id}", response_model=CompetitionProject)
async def update_project(project_id: str, req: CompetitionProjectUpdate):
    """Update a competition project (partial)."""
    db = await get_db()
    existing = await db.fetch_one(
        "SELECT * FROM competition_projects WHERE id = ?", (project_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")

    fields = []
    params: list = []
    for key, value in req.model_dump(exclude_unset=True).items():
        if key in ("textbook_info", "context_data") and value is not None:
            value = json.dumps(value, ensure_ascii=False)
        fields.append(f"{key} = ?")
        params.append(value)

    if fields:
        fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(project_id)
        await db.execute(
            f"UPDATE competition_projects SET {', '.join(fields)} WHERE id = ?",
            tuple(params),
            commit=True,
        )

    row = await db.fetch_one(
        "SELECT * FROM competition_projects WHERE id = ?", (project_id,)
    )
    return _project_from_row(row)


@router.delete("/competition/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a competition project and all its outputs."""
    db = await get_db()
    row = await db.fetch_one(
        "SELECT id FROM competition_projects WHERE id = ?", (project_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete all outputs first (and their files)
    output_rows = await db.fetch_all(
        "SELECT output_file_path FROM competition_outputs WHERE project_id = ?",
        (project_id,),
    )
    for o in output_rows:
        path = o["output_file_path"]
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to delete output file {path}: {e}")

    await db.execute(
        "DELETE FROM competition_outputs WHERE project_id = ?",
        (project_id,),
        commit=True,
    )
    await db.execute(
        "DELETE FROM competition_projects WHERE id = ?",
        (project_id,),
        commit=True,
    )
    return {"message": "Project deleted", "project_id": project_id}


# ============================================================================
# Outputs (lesson plan / report generation)
# ============================================================================


@router.get(
    "/competition/projects/{project_id}/outputs",
    response_model=CompetitionOutputListResponse,
)
async def list_project_outputs(project_id: str):
    """List all outputs (lesson plans + reports) of a project."""
    db = await get_db()
    rows = await db.fetch_all(
        """
        SELECT * FROM competition_outputs
        WHERE project_id = ?
        ORDER BY created_at DESC
        """,
        (project_id,),
    )
    return CompetitionOutputListResponse(
        outputs=[_output_from_row(r) for r in rows],
        total=len(rows),
    )


@router.post(
    "/competition/projects/{project_id}/generate-lesson-plan",
    response_model=CompetitionGenerateResponse,
)
async def generate_lesson_plan(
    project_id: str,
    req: CompetitionLessonPlanGenerateRequest,
):
    """Trigger background generation of a competition lesson plan."""
    db = await get_db()
    project_row = await db.fetch_one(
        "SELECT * FROM competition_projects WHERE id = ?", (project_id,)
    )
    if not project_row:
        raise HTTPException(status_code=404, detail="Project not found")

    project = _project_from_row(project_row)
    expected_lessons = max(1, project.total_hours // project.hours_per_lesson)

    output_id = str(uuid4())
    now = datetime.now().isoformat()
    await db.execute(
        """
        INSERT INTO competition_outputs (
            id, project_id, output_type, status,
            progress_current, progress_total,
            topics_input, additional_requirements,
            created_at, updated_at
        ) VALUES (?, ?, 'lesson_plan', 'pending', 0, ?, ?, ?, ?, ?)
        """,
        (
            output_id,
            project_id,
            expected_lessons + 2,  # +2 for split + overall design
            req.topics_input,
            req.additional_requirements,
            now,
            now,
        ),
        commit=True,
    )

    run_in_background(
        _process_lesson_plan(output_id, project, req),
        name=f"competition-lesson-plan-{output_id}",
    )

    logger.info(f"Lesson plan generation started: {output_id}")
    return CompetitionGenerateResponse(output_id=output_id, status="pending")


@router.post(
    "/competition/projects/{project_id}/generate-report",
    response_model=CompetitionGenerateResponse,
)
async def generate_report(
    project_id: str,
    req: CompetitionReportGenerateRequest,
):
    """Trigger background generation of a teaching implementation report."""
    db = await get_db()
    project_row = await db.fetch_one(
        "SELECT * FROM competition_projects WHERE id = ?", (project_id,)
    )
    if not project_row:
        raise HTTPException(status_code=404, detail="Project not found")

    project = _project_from_row(project_row)

    output_id = str(uuid4())
    now = datetime.now().isoformat()
    await db.execute(
        """
        INSERT INTO competition_outputs (
            id, project_id, output_type, status,
            progress_current, progress_total,
            related_lesson_plan_id, additional_requirements,
            created_at, updated_at
        ) VALUES (?, ?, 'report', 'pending', 0, 2, ?, ?, ?, ?)
        """,
        (
            output_id,
            project_id,
            req.related_output_id,
            req.additional_requirements,
            now,
            now,
        ),
        commit=True,
    )

    run_in_background(
        _process_report(output_id, project, req),
        name=f"competition-report-{output_id}",
    )

    logger.info(f"Report generation started: {output_id}")
    return CompetitionGenerateResponse(output_id=output_id, status="pending")


@router.get("/competition/outputs/{output_id}", response_model=CompetitionOutput)
async def get_output(output_id: str):
    """Get current status / progress / data of a competition output."""
    db = await get_db()
    row = await db.fetch_one(
        "SELECT * FROM competition_outputs WHERE id = ?", (output_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Output not found")
    return _output_from_row(row)


@router.delete("/competition/outputs/{output_id}")
async def delete_output(output_id: str):
    """Delete an output (cancels if pending/processing)."""
    db = await get_db()
    row = await db.fetch_one(
        "SELECT * FROM competition_outputs WHERE id = ?", (output_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Output not found")

    status = row["status"]
    if status in ("pending", "processing"):
        await db.execute(
            "UPDATE competition_outputs SET status = 'cancelled', updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), output_id),
            commit=True,
        )
        return {"message": "Output cancelled", "output_id": output_id}

    file_path = row["output_file_path"]
    if file_path:
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to delete file {file_path}: {e}")

    await db.execute(
        "DELETE FROM competition_outputs WHERE id = ?", (output_id,), commit=True
    )
    return {"message": "Output deleted", "output_id": output_id}


@router.get("/competition/outputs/{output_id}/download")
async def download_output(output_id: str):
    """Download the generated docx file."""
    db = await get_db()
    row = await db.fetch_one(
        "SELECT * FROM competition_outputs WHERE id = ?", (output_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Output not found")
    if row["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Output not ready (status: {row['status']})",
        )
    file_path = row["output_file_path"]
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Output file missing on disk")

    return FileResponse(
        path=file_path,
        filename=Path(file_path).name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/competition/outputs/{output_id}/stream")
async def stream_output_progress(output_id: str):
    """SSE stream of output progress (polls DB and pushes updates)."""

    async def event_gen():
        last_payload = None
        terminal_states = {"completed", "failed", "cancelled"}
        while True:
            db = await get_db()
            row = await db.fetch_one(
                "SELECT * FROM competition_outputs WHERE id = ?",
                (output_id,),
            )
            if not row:
                yield f"event: error\ndata: {json.dumps({'message': 'Output not found'})}\n\n"
                return

            payload = {
                "status": row["status"],
                "progress_current": row["progress_current"],
                "progress_total": row["progress_total"],
                "error_message": row["error_message"],
            }
            if payload != last_payload:
                yield f"event: progress\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                last_payload = payload

            if row["status"] in terminal_states:
                yield f"event: done\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                return

            await asyncio.sleep(2)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Background processors
# ============================================================================


async def _update_output_progress(
    output_id: str, current: int, total: int, status: Optional[str] = None
) -> None:
    db = await get_db()
    fields = ["progress_current = ?", "progress_total = ?", "updated_at = ?"]
    params = [current, total, datetime.now().isoformat()]
    if status is not None:
        fields.append("status = ?")
        params.append(status)
    params.append(output_id)
    await db.execute(
        f"UPDATE competition_outputs SET {', '.join(fields)} WHERE id = ?",
        tuple(params),
        commit=True,
    )


async def _is_cancelled(output_id: str) -> bool:
    db = await get_db()
    row = await db.fetch_one(
        "SELECT status FROM competition_outputs WHERE id = ?", (output_id,)
    )
    return row is not None and row["status"] == "cancelled"


async def _process_lesson_plan(
    output_id: str,
    project: CompetitionProject,
    req: CompetitionLessonPlanGenerateRequest,
) -> None:
    """Background task: generate full lesson plan and render document."""
    try:
        await _update_output_progress(output_id, 0, project.total_hours // project.hours_per_lesson + 2, "processing")
        if await _is_cancelled(output_id):
            return

        generator = CompetitionGenerator(
            provider=settings.ai_provider,
            api_key=settings.get_active_api_key(),
            model=settings.get_active_model(),
        )

        async def progress_cb(current: int, total: int, message: str):
            if await _is_cancelled(output_id):
                return
            await _update_output_progress(output_id, current, total)
            logger.info(f"Lesson plan {output_id} progress: {current}/{total} - {message}")

        content = await generator.generate_full_lesson_plan(
            project=project,
            topics_input=req.topics_input,
            additional_requirements=req.additional_requirements,
            progress_callback=progress_cb,
        )

        if await _is_cancelled(output_id):
            return

        # Render document
        renderer = CompetitionRenderer()
        output_path = renderer.render_lesson_plan(project, content)

        # Save final state
        db = await get_db()
        await db.execute(
            """
            UPDATE competition_outputs
            SET status = 'completed',
                generated_data = ?,
                output_file_path = ?,
                completed_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                json.dumps(content.model_dump(), ensure_ascii=False),
                output_path,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                output_id,
            ),
            commit=True,
        )
        logger.info(f"Lesson plan {output_id} completed: {output_path}")

    except Exception as exc:
        logger.error(f"Lesson plan {output_id} failed: {exc}", exc_info=True)
        db = await get_db()
        await db.execute(
            """
            UPDATE competition_outputs
            SET status = 'failed', error_message = ?, updated_at = ?
            WHERE id = ?
            """,
            (str(exc)[:1000], datetime.now().isoformat(), output_id),
            commit=True,
        )


async def _process_report(
    output_id: str,
    project: CompetitionProject,
    req: CompetitionReportGenerateRequest,
) -> None:
    """Background task: generate report and render document."""
    try:
        await _update_output_progress(output_id, 0, 2, "processing")
        if await _is_cancelled(output_id):
            return

        # Optionally load related lesson plan
        related_lesson_plan: Optional[CompetitionLessonContent] = None
        if req.related_output_id:
            db = await get_db()
            row = await db.fetch_one(
                "SELECT generated_data, output_type FROM competition_outputs WHERE id = ?",
                (req.related_output_id,),
            )
            if row and row["output_type"] == "lesson_plan" and row["generated_data"]:
                try:
                    data = json.loads(row["generated_data"])
                    related_lesson_plan = CompetitionLessonContent(**data)
                except Exception as e:
                    logger.warning(f"Failed to load related lesson plan: {e}")

        generator = CompetitionGenerator(
            provider=settings.ai_provider,
            api_key=settings.get_active_api_key(),
            model=settings.get_active_model(),
        )

        async def progress_cb(current: int, total: int, message: str):
            if await _is_cancelled(output_id):
                return
            await _update_output_progress(output_id, current, total)
            logger.info(f"Report {output_id} progress: {current}/{total} - {message}")

        content = await generator.generate_report(
            project=project,
            related_lesson_plan=related_lesson_plan,
            additional_requirements=req.additional_requirements,
            progress_callback=progress_cb,
        )

        if await _is_cancelled(output_id):
            return

        renderer = CompetitionRenderer()
        output_path = renderer.render_report(project, content)

        db = await get_db()
        await db.execute(
            """
            UPDATE competition_outputs
            SET status = 'completed',
                generated_data = ?,
                output_file_path = ?,
                completed_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                json.dumps(content.model_dump(), ensure_ascii=False),
                output_path,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                output_id,
            ),
            commit=True,
        )
        logger.info(f"Report {output_id} completed: {output_path}")

    except Exception as exc:
        logger.error(f"Report {output_id} failed: {exc}", exc_info=True)
        db = await get_db()
        await db.execute(
            """
            UPDATE competition_outputs
            SET status = 'failed', error_message = ?, updated_at = ?
            WHERE id = ?
            """,
            (str(exc)[:1000], datetime.now().isoformat(), output_id),
            commit=True,
        )
