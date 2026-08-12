"""Unified teaching-preparation API for lesson plans, handouts, and PPT files."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException

from ..models.database import db
from ..models.schemas import (
    LessonPlanGenerateRequest,
    PreparationArtifact,
    PreparationGenerateRequest,
    PreparationResponse,
    generate_id,
)
from ..services.builtin_template import (
    BUILTIN_TEMPLATE_ID,
    BUILTIN_TEMPLATE_NAME,
    get_builtin_template_path,
    require_valid_builtin_template,
)
from ..services.document_renderer import DocumentRenderer
from ..services.preparation_renderer import PreparationRenderer
from ..services.teaching_resource_service import get_resource_context
from ..services.ai_metrics import record_quality
from ..utils.ai_config import get_ai_generator


router = APIRouter(prefix="/preparation", tags=["preparation"])

ARTIFACT_LABELS = {
    "lesson_plan": "云林教案",
    "handout": "学生讲义",
    "presentation": "课堂PPT",
}
ARTIFACT_MEDIA_TYPES = {
    "lesson_plan": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "handout": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "presentation": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


async def _resolve_class_names(class_ids: list[str]) -> list[str]:
    if not class_ids:
        return []
    placeholders = ",".join("?" for _ in class_ids)
    rows = await db.fetch_all(
        f"SELECT name FROM classes WHERE id IN ({placeholders})",
        tuple(class_ids),
    )
    return [row["name"] for row in rows]


def _build_lesson_render_data(
    input_data: dict,
    content: dict,
    class_names: list[str],
) -> dict:
    online_resources = input_data.get("online_resources") or content.get(
        "online_resources", ""
    )
    references = []
    if input_data.get("textbook_name"):
        references.append(f"《{input_data['textbook_name']}》")
    if online_resources:
        references.append(str(online_resources))

    return {
        "subject": input_data.get("subject", ""),
        "grade": input_data.get("grade", ""),
        "topic": input_data.get("topic", ""),
        "teaching_topic": input_data.get("topic", ""),
        "duration": input_data.get("duration", ""),
        "class_name": "、".join(class_names),
        "week_number": "",
        "lesson_number": "",
        "location": input_data.get("location", "") or "",
        "references": "\n".join(references),
        "ideological_political": content.get("ideological_political", ""),
        "textbook_name": input_data.get("textbook_name", "") or "",
        "online_resources": online_resources,
        **content,
    }


@router.get("/capabilities")
async def get_preparation_capabilities():
    """Describe the fixed template and supported preparation outputs."""
    validation = require_valid_builtin_template()
    return {
        "template": {
            "id": BUILTIN_TEMPLATE_ID,
            "name": BUILTIN_TEMPLATE_NAME,
            "is_valid": validation["is_valid"],
            "sha256": validation["sha256"],
        },
        "artifacts": [
            {"type": item_type, "label": label}
            for item_type, label in ARTIFACT_LABELS.items()
        ],
    }


@router.post("", response_model=PreparationResponse)
async def generate_preparation(
    request: PreparationGenerateRequest,
) -> PreparationResponse:
    """Generate shared teaching content and export all requested artifacts."""
    try:
        report = require_valid_builtin_template()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    resource_context = await get_resource_context(request.resource_ids, increment_use=True)
    requirements = request.additional_requirements or ""
    if resource_context:
        requirements = (
            f"{requirements}\n\n请优先融合以下已审核教学资源：\n{resource_context}"
        ).strip()

    lesson_request = LessonPlanGenerateRequest(
        template_id=BUILTIN_TEMPLATE_ID,
        **{
            **request.model_dump(
                exclude={"artifact_types", "resource_ids", "course_archive_id"}
            ),
            "additional_requirements": requirements or None,
        },
    )

    try:
        generator = await get_ai_generator()
        content_model = await generator.generate_lesson_plan(
            lesson_request,
            None,
            request.generate_reflection,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"备课内容生成失败：{exc}") from exc

    preparation_id = generate_id()
    created_at = datetime.now().isoformat()
    input_data = lesson_request.model_dump()
    content = content_model.model_dump()
    class_names = await _resolve_class_names(request.class_ids)
    created_paths: list[Path] = []
    artifacts: list[PreparationArtifact] = []
    extra_renderer = PreparationRenderer()

    try:
        for artifact_type in request.artifact_types:
            if artifact_type == "lesson_plan":
                render_data = _build_lesson_render_data(input_data, content, class_names)
                output_path = DocumentRenderer().render_lesson_plan(
                    str(get_builtin_template_path()),
                    render_data,
                )
            elif artifact_type == "handout":
                output_path = extra_renderer.render_handout(
                    preparation_id, input_data, content
                )
            else:
                output_path = extra_renderer.render_presentation(
                    preparation_id, input_data, content
                )

            path = Path(output_path)
            created_paths.append(path)
            artifacts.append(
                PreparationArtifact(
                    type=artifact_type,
                    label=ARTIFACT_LABELS[artifact_type],
                    filename=path.name,
                    download_url=f"/static/{quote(path.name)}",
                    preview_url=f"/api/documents/preview/{quote(path.name)}",
                    media_type=ARTIFACT_MEDIA_TYPES[artifact_type],
                )
            )
    except Exception as exc:
        for path in created_paths:
            if path.is_file():
                path.unlink()
        raise HTTPException(status_code=500, detail=f"备课文件制作失败：{exc}") from exc

    stored_input = {
        **input_data,
        "artifact_types": request.artifact_types,
        "preparation_artifacts": [item.model_dump() for item in artifacts],
        "template_sha256": report["sha256"],
        "resource_ids": request.resource_ids,
        "course_archive_id": request.course_archive_id,
    }
    primary_output = str(created_paths[0]) if created_paths else None
    await db.execute(
        """
        INSERT INTO lesson_plans
            (id, template_id, title, subject, grade, topic, input_data,
             generated_content, output_file_path, status, course_archive_id,
             resource_ids)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            preparation_id,
            BUILTIN_TEMPLATE_ID,
            f"{request.grade} {request.subject} - {request.topic}",
            request.subject,
            request.grade,
            request.topic,
            json.dumps(stored_input, ensure_ascii=False),
            json.dumps(content, ensure_ascii=False),
            primary_output,
            "completed",
            request.course_archive_id,
            json.dumps(request.resource_ids, ensure_ascii=False),
        ),
        commit=True,
    )
    await db.execute(
        "UPDATE templates SET use_count = use_count + 1 WHERE id = ?",
        (BUILTIN_TEMPLATE_ID,),
        commit=True,
    )
    await record_quality("preparation", preparation_id, content_model)

    return PreparationResponse(
        id=preparation_id,
        title=f"{request.topic}备课包",
        template_id=BUILTIN_TEMPLATE_ID,
        template_name=BUILTIN_TEMPLATE_NAME,
        content=content_model,
        artifacts=artifacts,
        created_at=created_at,
    )
