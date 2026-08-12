"""Course and semester archive persistence."""
import json
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from ..models.database import db


JSON_FIELDS = {"class_ids"}


def _decode_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


async def _resource_ids(archive_id: str) -> list[str]:
    rows = await db.fetch_all(
        "SELECT resource_id FROM course_archive_resources WHERE archive_id = ? ORDER BY created_at",
        (archive_id,),
    )
    return [row["resource_id"] for row in rows]


async def _serialize_row(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["class_ids"] = _decode_list(item.get("class_ids"))
    item["resource_ids"] = await _resource_ids(item["id"])
    item["batch_task_count"] = int(item.pop("batch_task_count", 0) or 0)
    item["lesson_plan_count"] = int(item.pop("lesson_plan_count", 0) or 0)
    return item


async def _replace_resources(archive_id: str, resource_ids: list[str]) -> None:
    ids = list(dict.fromkeys(resource_ids))
    async with db.transaction() as connection:
        await connection.execute(
            "DELETE FROM course_archive_resources WHERE archive_id = ?", (archive_id,)
        )
        if ids:
            placeholders = ",".join("?" for _ in ids)
            cursor = await connection.execute(
                f"SELECT id FROM teaching_resources WHERE status = 'active' AND id IN ({placeholders})",
                tuple(ids),
            )
            existing = {row[0] for row in await cursor.fetchall()}
            await connection.executemany(
                "INSERT INTO course_archive_resources (archive_id, resource_id) VALUES (?, ?)",
                [(archive_id, resource_id) for resource_id in ids if resource_id in existing],
            )


async def create_archive(data: dict[str, Any]) -> dict[str, Any]:
    archive_id = str(uuid4())
    timestamp = datetime.now().isoformat()
    await db.execute(
        """
        INSERT INTO course_archives (
            id, course_name, subject, grade, academic_year, semester,
            teacher_name, textbook_id, total_hours, hours_per_lesson, start_week,
            class_ids, location, notes, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
        """,
        (
            archive_id, data["course_name"], data["subject"], data["grade"],
            data["academic_year"], data["semester"], data.get("teacher_name"),
            data.get("textbook_id"), data.get("total_hours", 32),
            data.get("hours_per_lesson", 2), data.get("start_week", 1),
            json.dumps(data.get("class_ids", []), ensure_ascii=False),
            data.get("location"), data.get("notes"), timestamp, timestamp,
        ),
        commit=True,
    )
    await _replace_resources(archive_id, data.get("resource_ids", []))
    return await get_archive(archive_id)


async def get_archive(archive_id: str) -> Optional[dict[str, Any]]:
    row = await db.fetch_one(
        """
        SELECT a.*,
            (SELECT COUNT(*) FROM batch_tasks b WHERE b.course_archive_id = a.id) AS batch_task_count,
            (SELECT COUNT(*) FROM lesson_plans l WHERE l.course_archive_id = a.id) AS lesson_plan_count
        FROM course_archives a WHERE a.id = ?
        """,
        (archive_id,),
    )
    return await _serialize_row(row) if row else None


async def list_archives(
    *, search: Optional[str] = None, academic_year: Optional[str] = None,
    semester: Optional[int] = None, status: str = "active", page: int = 1,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    conditions = ["a.status = ?"]
    params: list[Any] = [status]
    if search:
        conditions.append("(a.course_name LIKE ? OR a.subject LIKE ? OR a.grade LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term, term])
    if academic_year:
        conditions.append("a.academic_year = ?")
        params.append(academic_year)
    if semester:
        conditions.append("a.semester = ?")
        params.append(semester)
    where = " AND ".join(conditions)
    count = await db.fetch_one(
        f"SELECT COUNT(*) AS count FROM course_archives a WHERE {where}", tuple(params)
    )
    rows = await db.fetch_all(
        f"""
        SELECT a.*,
          (SELECT COUNT(*) FROM batch_tasks b WHERE b.course_archive_id = a.id) AS batch_task_count,
          (SELECT COUNT(*) FROM lesson_plans l WHERE l.course_archive_id = a.id) AS lesson_plan_count
        FROM course_archives a WHERE {where}
        ORDER BY a.academic_year DESC, a.semester DESC, a.updated_at DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params + [limit, (page - 1) * limit]),
    )
    return [await _serialize_row(row) for row in rows], int(count["count"] if count else 0)


async def update_archive(archive_id: str, changes: dict[str, Any]) -> Optional[dict[str, Any]]:
    if not await get_archive(archive_id):
        return None
    resource_ids = changes.pop("resource_ids", None)
    allowed = {
        "course_name", "subject", "grade", "academic_year", "semester", "teacher_name",
        "textbook_id", "total_hours", "hours_per_lesson", "start_week", "class_ids",
        "location", "notes", "status",
    }
    assignments: list[str] = []
    params: list[Any] = []
    for field, value in changes.items():
        if field not in allowed:
            continue
        assignments.append(f"{field} = ?")
        params.append(json.dumps(value, ensure_ascii=False) if field in JSON_FIELDS else value)
    if assignments:
        assignments.append("updated_at = ?")
        params.extend([datetime.now().isoformat(), archive_id])
        await db.execute(
            f"UPDATE course_archives SET {', '.join(assignments)} WHERE id = ?",
            tuple(params), commit=True,
        )
    if resource_ids is not None:
        await _replace_resources(archive_id, resource_ids)
    return await get_archive(archive_id)


async def archive_course(archive_id: str) -> bool:
    if not await get_archive(archive_id):
        return False
    await db.execute(
        "UPDATE course_archives SET status = 'archived', updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), archive_id), commit=True,
    )
    return True


async def clone_archive(archive_id: str, academic_year: str, semester: int) -> Optional[dict[str, Any]]:
    source = await get_archive(archive_id)
    if not source:
        return None
    data = {key: source[key] for key in (
        "course_name", "subject", "grade", "teacher_name", "textbook_id", "total_hours",
        "hours_per_lesson", "start_week", "class_ids", "resource_ids", "location", "notes",
    )}
    data.update({"academic_year": academic_year, "semester": semester})
    return await create_archive(data)
