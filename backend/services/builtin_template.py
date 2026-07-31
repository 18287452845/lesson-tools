"""Read-only access and validation for the built-in Yunlin lesson template."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from docx import Document
from docxtpl import DocxTemplate

from ..config import settings
from ..models.database import db
from .template_parser import TemplateParser


BUILTIN_TEMPLATE_ID = "yunlin-standard"
BUILTIN_TEMPLATE_NAME = "云林标准教案模板"
BUILTIN_TEMPLATE_DESCRIPTION = "云南林业职业技术学院固定教案模板（系统内置，只读）"

# These variables define the minimum contract expected by the renderer.
REQUIRED_TEMPLATE_FIELDS = {
    "teaching_topic",
    "duration",
    "teaching_goals",
    "key_points",
    "difficult_points",
    "teaching_steps",
    "homework",
}


def get_builtin_template_path() -> Path:
    """Return the immutable template resource bundled with the application."""
    return settings.builtin_template_path


def validate_builtin_template() -> dict[str, Any]:
    """Validate resource integrity and the Jinja field contract."""
    path = get_builtin_template_path()
    errors: list[str] = []
    warnings: list[str] = []
    variables: list[str] = []
    fields: list[dict[str, Any]] = []

    if not path.is_file():
        errors.append(f"内置云林模板不存在：{path}")
    elif path.suffix.lower() != ".docx":
        errors.append("内置云林模板必须是 .docx 文件")
    else:
        try:
            # Opening with python-docx catches invalid/corrupt Office packages.
            Document(str(path))
            variables = sorted(DocxTemplate(str(path)).get_undeclared_template_variables())
            fields = [field.model_dump() for field in TemplateParser(path).parse()]
        except Exception as exc:
            errors.append(f"模板结构无法解析：{exc}")

    missing_fields = sorted(REQUIRED_TEMPLATE_FIELDS - set(variables))
    if missing_fields:
        errors.append("模板缺少必需字段：" + "、".join(missing_fields))

    if path.is_file() and path.stat().st_size < 10_000:
        warnings.append("模板文件体积异常偏小，请确认资源完整")

    checksum = ""
    if path.is_file():
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()

    return {
        "template_id": BUILTIN_TEMPLATE_ID,
        "type": "lesson_plan",
        "name": BUILTIN_TEMPLATE_NAME,
        "is_valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "required_fields": sorted(REQUIRED_TEMPLATE_FIELDS),
        "variables": variables,
        "field_count": len(variables),
        "fields": fields,
        "file_size": path.stat().st_size if path.is_file() else 0,
        "sha256": checksum,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_all_builtin_templates() -> list[dict[str, Any]]:
    """Validate every immutable Yunlin document resource."""
    from .course_plan_renderer import validate_all_course_plan_templates

    return [validate_builtin_template(), *validate_all_course_plan_templates()]


def require_valid_builtin_template(template_id: str | None = None) -> dict[str, Any]:
    """Enforce the fixed template id and return its validation report."""
    if template_id is not None and template_id != BUILTIN_TEMPLATE_ID:
        raise ValueError("系统仅支持内置云林标准模板")

    report = validate_builtin_template()
    if not report["is_valid"]:
        raise ValueError("内置云林模板校验失败：" + "；".join(report["errors"]))
    return report


async def ensure_builtin_template_registered() -> dict[str, Any]:
    """Upsert the read-only template record used by legacy generation tables."""
    report = require_valid_builtin_template()
    fields_config = json.dumps(report["fields"], ensure_ascii=False)
    path = str(get_builtin_template_path())

    await db.execute(
        """
        INSERT INTO templates
            (id, name, description, subject, grade, file_path, fields_config)
        VALUES (?, ?, ?, NULL, NULL, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            subject = NULL,
            grade = NULL,
            file_path = excluded.file_path,
            fields_config = excluded.fields_config,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            BUILTIN_TEMPLATE_ID,
            BUILTIN_TEMPLATE_NAME,
            BUILTIN_TEMPLATE_DESCRIPTION,
            path,
            fields_config,
        ),
        commit=True,
    )
    return report
