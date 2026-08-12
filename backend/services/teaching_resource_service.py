"""Persistence and prompt-context helpers for the teaching resource library."""
import json
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from ..models.database import db


def _serialize_row(row: Any) -> dict[str, Any]:
    item = dict(row)
    try:
        item["tags"] = json.loads(item.get("tags") or "[]")
    except (TypeError, json.JSONDecodeError):
        item["tags"] = []
    return item


async def create_resource(data: dict[str, Any]) -> dict[str, Any]:
    resource_id = str(uuid4())
    timestamp = datetime.now().isoformat()
    await db.execute(
        """
        INSERT INTO teaching_resources (
            id, title, resource_type, subject, grade, content, source_url,
            tags, status, use_count, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', 0, ?, ?)
        """,
        (
            resource_id,
            data["title"],
            data["resource_type"],
            data.get("subject"),
            data.get("grade"),
            data["content"],
            data.get("source_url"),
            json.dumps(data.get("tags", []), ensure_ascii=False),
            timestamp,
            timestamp,
        ),
        commit=True,
    )
    return await get_resource(resource_id)


async def get_resource(resource_id: str) -> Optional[dict[str, Any]]:
    row = await db.fetch_one(
        "SELECT * FROM teaching_resources WHERE id = ?", (resource_id,)
    )
    return _serialize_row(row) if row else None


async def list_resources(
    *,
    search: Optional[str] = None,
    resource_type: Optional[str] = None,
    subject: Optional[str] = None,
    grade: Optional[str] = None,
    status: str = "active",
    page: int = 1,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    conditions = ["status = ?"]
    params: list[Any] = [status]
    if search:
        conditions.append("(title LIKE ? OR content LIKE ? OR tags LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term, term])
    for column, value in (
        ("resource_type", resource_type),
        ("subject", subject),
        ("grade", grade),
    ):
        if value:
            conditions.append(f"{column} = ?")
            params.append(value)
    where = " AND ".join(conditions)
    count_row = await db.fetch_one(
        f"SELECT COUNT(*) AS count FROM teaching_resources WHERE {where}",
        tuple(params),
    )
    rows = await db.fetch_all(
        f"""
        SELECT * FROM teaching_resources WHERE {where}
        ORDER BY updated_at DESC LIMIT ? OFFSET ?
        """,
        tuple(params + [limit, (page - 1) * limit]),
    )
    return [_serialize_row(row) for row in rows], int(count_row["count"] if count_row else 0)


async def update_resource(resource_id: str, changes: dict[str, Any]) -> Optional[dict[str, Any]]:
    if not await get_resource(resource_id):
        return None
    allowed = {
        "title", "resource_type", "subject", "grade", "content",
        "source_url", "tags", "status",
    }
    assignments: list[str] = []
    params: list[Any] = []
    for field, value in changes.items():
        if field not in allowed:
            continue
        assignments.append(f"{field} = ?")
        params.append(json.dumps(value, ensure_ascii=False) if field == "tags" else value)
    if assignments:
        assignments.append("updated_at = ?")
        params.extend([datetime.now().isoformat(), resource_id])
        await db.execute(
            f"UPDATE teaching_resources SET {', '.join(assignments)} WHERE id = ?",
            tuple(params),
            commit=True,
        )
    return await get_resource(resource_id)


async def delete_resource(resource_id: str) -> bool:
    if not await get_resource(resource_id):
        return False
    await db.execute(
        "UPDATE teaching_resources SET status = 'archived', updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), resource_id),
        commit=True,
    )
    return True


async def get_resource_context(resource_ids: list[str], increment_use: bool = False) -> str:
    """Build bounded, reusable AI context from selected resources."""
    ids = list(dict.fromkeys(resource_ids))
    if not ids:
        return ""
    placeholders = ",".join("?" for _ in ids)
    rows = await db.fetch_all(
        f"""
        SELECT id, title, resource_type, content FROM teaching_resources
        WHERE status = 'active' AND id IN ({placeholders}) ORDER BY title
        """,
        tuple(ids),
    )
    if increment_use and rows:
        found_ids = [row["id"] for row in rows]
        found_placeholders = ",".join("?" for _ in found_ids)
        await db.execute(
            f"UPDATE teaching_resources SET use_count = use_count + 1 WHERE id IN ({found_placeholders})",
            tuple(found_ids),
            commit=True,
        )
    parts = [
        f"[{row['resource_type']}] {row['title']}\n{str(row['content'])[:3000]}"
        for row in rows
    ]
    return "\n\n".join(parts)
