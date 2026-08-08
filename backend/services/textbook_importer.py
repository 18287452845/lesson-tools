"""Atomic import of a discovered textbook and its sourced chapter tree."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from ..models.database import Database
from .textbook_discovery import BookCandidate, DuplicateTextbookError, normalize_isbn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def import_discovered_textbook(
    database: Database,
    candidate: BookCandidate,
    chapters: list[dict[str, Any]],
    *,
    source_type: str,
    source_name: str,
    source_url: Optional[str],
    confidence: float,
    subject: Optional[str] = None,
    grade: Optional[str] = None,
    description: Optional[str] = None,
    allow_duplicate: bool = False,
) -> str:
    """Create the textbook, provenance and chapters in one transaction."""
    textbook_id = str(uuid4())
    source_id = str(uuid4())
    timestamp = _now()
    isbn = normalize_isbn(candidate.isbn_13 or candidate.isbn_10)

    async with database.transaction() as connection:
        connection.row_factory = sqlite3.Row
        if isbn and not allow_duplicate:
            cursor = await connection.execute(
                "SELECT id, isbn FROM textbooks WHERE isbn IS NOT NULL AND status = 'active'"
            )
            existing_rows = await cursor.fetchall()
            duplicate = next(
                (row for row in existing_rows if normalize_isbn(row["isbn"]) == isbn),
                None,
            )
            if duplicate:
                raise DuplicateTextbookError(
                    f"该 ISBN 已存在于教材库中（教材 ID：{duplicate['id']}）"
                )

        await connection.execute(
            """
            INSERT INTO textbooks (
                id, name, isbn, author, publisher, edition,
                subject, grade, cover_image, description, status,
                use_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 0, ?, ?)
            """,
            (
                textbook_id,
                candidate.title,
                isbn,
                "、".join(candidate.authors) or None,
                candidate.publisher,
                candidate.edition,
                subject,
                grade,
                candidate.cover_image,
                description or candidate.description,
                timestamp,
                timestamp,
            ),
        )

        await connection.execute(
            """
            INSERT INTO textbook_sources (
                id, textbook_id, source_type, source_name, source_url,
                external_id, confidence, raw_metadata, retrieved_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                textbook_id,
                source_type,
                source_name,
                source_url,
                candidate.source_id,
                confidence,
                json.dumps(candidate.to_dict(), ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )

        chapter_ids: dict[str, str] = {}
        resolved: list[tuple[dict[str, Any], str, str]] = []
        for chapter in chapters:
            chapter_id = str(uuid4())
            client_id = str(chapter.get("client_id") or chapter.get("id") or chapter_id)
            chapter_ids[client_id] = chapter_id
            resolved.append((chapter, chapter_id, client_id))

        for index, (chapter, chapter_id, _) in enumerate(resolved, 1):
            parent_key = chapter.get("parent_chapter_id")
            parent_id = chapter_ids.get(str(parent_key)) if parent_key else None
            await connection.execute(
                """
                INSERT INTO textbook_chapters (
                    id, textbook_id, chapter_number, chapter_title,
                    content_summary, key_concepts, sort_order,
                    hours_required, parent_chapter_id, source_id,
                    content_origin, confidence, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chapter_id,
                    textbook_id,
                    str(chapter.get("chapter_number") or f"章节{index}"),
                    str(chapter.get("chapter_title") or chapter.get("chapter_number") or f"章节{index}"),
                    chapter.get("content_summary") or "",
                    json.dumps(chapter.get("key_concepts") or [], ensure_ascii=False),
                    int(chapter.get("sort_order") or index),
                    chapter.get("hours_required"),
                    parent_id,
                    source_id,
                    chapter.get("content_origin") or "source",
                    chapter.get("confidence") if chapter.get("confidence") is not None else confidence,
                    timestamp,
                    timestamp,
                ),
            )

    return textbook_id
