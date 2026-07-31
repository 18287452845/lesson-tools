"""Read-only API for immutable Yunlin document templates."""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..models.database import db
from ..models.schemas import TemplateInfo
from ..services.builtin_template import (
    BUILTIN_TEMPLATE_ID,
    BUILTIN_TEMPLATE_NAME,
    ensure_builtin_template_registered,
    get_builtin_template_path,
    validate_all_builtin_templates,
    validate_builtin_template,
)


router = APIRouter(prefix="/templates", tags=["templates"])


async def _get_template_info() -> TemplateInfo:
    row = await db.fetch_one(
        "SELECT * FROM templates WHERE id = ?",
        (BUILTIN_TEMPLATE_ID,),
    )
    if not row:
        await ensure_builtin_template_registered()
        row = await db.fetch_one(
            "SELECT * FROM templates WHERE id = ?",
            (BUILTIN_TEMPLATE_ID,),
        )
    if not row:
        raise HTTPException(status_code=503, detail="内置云林模板尚未初始化")

    return TemplateInfo(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        subject=None,
        grade=None,
        file_path=str(get_builtin_template_path()),
        fields_config=json.loads(row["fields_config"] or "[]"),
        preview_image=None,
        use_count=row["use_count"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("", response_model=list[TemplateInfo])
async def list_templates():
    """Return the only template users are allowed to select."""
    return [await _get_template_info()]


@router.get("/validation")
async def get_template_validation():
    """Return the latest integrity and field-contract validation report."""
    return validate_builtin_template()


@router.post("/validation")
async def run_template_validation():
    """Re-run validation on demand and refresh the registered metadata."""
    report = validate_builtin_template()
    if report["is_valid"]:
        await ensure_builtin_template_registered()
    return report


@router.get("/validation/all")
async def get_all_template_validations():
    """Return validation reports for lesson, teaching, and experiment plans."""
    return validate_all_builtin_templates()


@router.get("/{template_id}", response_model=TemplateInfo)
async def get_template(template_id: str):
    if template_id != BUILTIN_TEMPLATE_ID:
        raise HTTPException(status_code=404, detail="系统仅提供云林标准模板")
    return await _get_template_info()


@router.get("/{template_id}/download")
async def download_template(template_id: str):
    if template_id != BUILTIN_TEMPLATE_ID:
        raise HTTPException(status_code=404, detail="系统仅提供云林标准模板")

    path = get_builtin_template_path()
    if not path.is_file():
        raise HTTPException(status_code=503, detail="内置云林模板资源缺失")

    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{BUILTIN_TEMPLATE_NAME}.docx",
    )
