"""
Lesson plan generation API endpoints.
"""
import json
import re
import asyncio
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from datetime import datetime

from ..models.database import db
from ..models.schemas import (
    LessonPlanGenerateRequest,
    LessonPlanInput,
    LessonPlanResponse,
    FieldRegenerateRequest,
    FieldEditRequest,
    GeneratedContent,
    FieldConfig,
    generate_id,
)
from ..services.ai_generator import AIGenerator
from ..services.document_renderer import DocumentRenderer
from ..services.builtin_template import (
    BUILTIN_TEMPLATE_ID,
    get_builtin_template_path,
    require_valid_builtin_template,
)
from ..services.lesson_content import merge_lesson_content, parse_content_layer
from ..utils.ai_config import get_ai_generator

router = APIRouter(prefix="/generate", tags=["generate"])


async def _ensure_batch_editable(row) -> None:
    """Keep batch artifacts on one immutable content snapshot while rendering."""
    batch_task_id = dict(row).get("batch_task_id")
    if not batch_task_id:
        return
    task = await db.fetch_one(
        "SELECT status FROM batch_tasks WHERE id = ?",
        (batch_task_id,),
    )
    if task and task["status"] in {"pending", "processing"}:
        raise HTTPException(
            status_code=409,
            detail="批处理任务正在生成文档，请在任务完成后编辑教案",
        )


async def _save_content_layer_if_editable(
    *,
    lesson_plan_id: str,
    column: str,
    content: dict,
) -> None:
    """Atomically reject writes that race with batch document generation."""
    cursor = await db.execute(
        f"""
        UPDATE lesson_plans
        SET {column} = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND NOT EXISTS (
              SELECT 1 FROM batch_tasks
              WHERE batch_tasks.id = lesson_plans.batch_task_id
                AND batch_tasks.status IN ('pending', 'processing')
          )
        """,
        (json.dumps(content, ensure_ascii=False), lesson_plan_id),
        commit=True,
    )
    if cursor.rowcount != 1:
        raise HTTPException(
            status_code=409,
            detail="批处理任务正在生成文档，请在任务完成后编辑教案",
        )


def extract_json_from_content(content: str, is_array: bool = False) -> any:
    """
    Extract JSON data from AI-generated content.

    Args:
        content: The raw content string that may contain JSON
        is_array: If True, looks for array [...], otherwise looks for object {...}

    Returns:
        Parsed JSON data

    Raises:
        json.JSONDecodeError: If JSON parsing fails
    """
    pattern = r"\[.*\]" if is_array else r"\{.*\}"
    json_match = re.search(pattern, content, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(0))
    return json.loads(content)


@router.post("", response_model=LessonPlanResponse)
async def generate_lesson_plan(request: LessonPlanGenerateRequest):
    """
    Generate a complete lesson plan based on input data.
    """
    try:
        require_valid_builtin_template(request.template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Load metadata for the one supported template.
    template = await db.fetch_one(
        "SELECT * FROM templates WHERE id = ?",
        (BUILTIN_TEMPLATE_ID,),
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Parse field configs from template
    field_configs = None
    try:
        # Safely access field_configs column
        fields_config_str = template["fields_config"] if "fields_config" in template.keys() else None

        if fields_config_str:
            configs_data = json.loads(fields_config_str)
            field_configs = [FieldConfig(**config) for config in configs_data]
    except (json.JSONDecodeError, TypeError, KeyError, IndexError) as e:
        # If field_configs parsing fails, continue without it
        print(f"Warning: Failed to parse field_configs: {e}")

    # Generate content using AI
    try:
        generator = await get_ai_generator()
        content = await generator.generate_lesson_plan(request, field_configs, request.generate_reflection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {e}")

    # Create lesson plan record
    lesson_plan_id = generate_id()
    timestamp = datetime.now().isoformat()

    input_data = json.dumps(request.model_dump())
    generated_data = json.dumps(content.model_dump())

    await db.execute(
        """
        INSERT INTO lesson_plans
        (id, template_id, title, subject, grade, topic, input_data, generated_content, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lesson_plan_id,
            request.template_id,
            f"{request.grade} {request.subject} - {request.topic}",
            request.subject,
            request.grade,
            request.topic,
            input_data,
            generated_data,
            "generated",
        ),
        commit=True,
    )

    # Update template use count
    await db.execute(
        "UPDATE templates SET use_count = use_count + 1 WHERE id = ?",
        (request.template_id,),
        commit=True,
    )

    return LessonPlanResponse(
        id=lesson_plan_id,
        template_id=request.template_id,
        input=request,
        content=content,
        status="generated",
        created_at=timestamp,
    )


@router.post("/stream")
async def generate_lesson_plan_stream(request: LessonPlanGenerateRequest):
    """
    Generate a lesson plan with real-time progress updates using Server-Sent Events.
    """
    async def event_generator():
        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': '正在验证模板...'})}\n\n"
            await asyncio.sleep(0.1)

            # Enforce and validate the fixed Yunlin template.
            try:
                require_valid_builtin_template(request.template_id)
            except ValueError as exc:
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
                return

            template = await db.fetch_one(
                "SELECT * FROM templates WHERE id = ?",
                (BUILTIN_TEMPLATE_ID,),
            )

            if not template:
                yield f"data: {json.dumps({'type': 'error', 'message': '模板不存在'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'message': '模板验证成功'})}\n\n"
            await asyncio.sleep(0.1)

            # Parse field configs
            field_configs = None
            try:
                fields_config_str = template["fields_config"] if "fields_config" in template.keys() else None
                if fields_config_str:
                    configs_data = json.loads(fields_config_str)
                    field_configs = [FieldConfig(**config) for config in configs_data]
            except Exception as e:
                print(f"Warning: Failed to parse field_configs: {e}")

            # Generate content with progress updates
            yield f"data: {json.dumps({'type': 'status', 'message': '正在连接AI服务...', 'progress': 10})}\n\n"
            await asyncio.sleep(0.1)

            try:
                generator = await get_ai_generator()
                yield f"data: {json.dumps({'type': 'status', 'message': '开始生成教学目标...', 'progress': 20})}\n\n"
                await asyncio.sleep(0.1)

                content = await generator.generate_lesson_plan(request, field_configs, request.generate_reflection)

                yield f"data: {json.dumps({'type': 'status', 'message': '生成教学重难点...', 'progress': 40})}\n\n"
                await asyncio.sleep(0.1)

                yield f"data: {json.dumps({'type': 'status', 'message': '生成教学步骤...', 'progress': 60})}\n\n"
                await asyncio.sleep(0.1)

                yield f"data: {json.dumps({'type': 'status', 'message': '完善作业布置和板书设计...', 'progress': 80})}\n\n"
                await asyncio.sleep(0.1)

            except ValueError as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                return
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'AI生成失败: {str(e)}'})}\n\n"
                return

            # Save to database
            yield f"data: {json.dumps({'type': 'status', 'message': '正在保存教案...', 'progress': 90})}\n\n"
            await asyncio.sleep(0.1)

            lesson_plan_id = generate_id()
            timestamp = datetime.now().isoformat()

            input_data = json.dumps(request.model_dump())
            generated_data = json.dumps(content.model_dump())

            await db.execute(
                """
                INSERT INTO lesson_plans
                (id, template_id, title, subject, grade, topic, input_data, generated_content, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lesson_plan_id,
                    request.template_id,
                    f"{request.grade} {request.subject} - {request.topic}",
                    request.subject,
                    request.grade,
                    request.topic,
                    input_data,
                    generated_data,
                    "generated",
                ),
                commit=True,
            )

            # Update template use count
            await db.execute(
                "UPDATE templates SET use_count = use_count + 1 WHERE id = ?",
                (request.template_id,),
                commit=True,
            )

            # Send completion event with data
            response_data = {
                'type': 'complete',
                'message': '教案生成完成！',
                'progress': 100,
                'data': {
                    'id': lesson_plan_id,
                    'template_id': request.template_id,
                    'content': content.model_dump(),
                    'status': 'generated',
                    'created_at': timestamp,
                }
            }
            yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'生成过程出错: {str(e)}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{lesson_plan_id}/regenerate-field")
async def regenerate_field(
    lesson_plan_id: str,
    field_name: str = Query(...),
    additional_instruction: Optional[str] = Query(None),
):
    """
    Regenerate a single field of a lesson plan.
    """
    # Get lesson plan
    row = await db.fetch_one(
        "SELECT * FROM lesson_plans WHERE id = ?",
        (lesson_plan_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    await _ensure_batch_editable(row)

    # Regenerate field
    try:
        input_data = LessonPlanInput(**json.loads(row["input_data"]))
        current_content = merge_lesson_content(
            row["generated_content"],
            row["final_content"],
        )
        generator = await get_ai_generator()
        new_content = await generator.regenerate_field(
            input_data,
            field_name,
            current_content,
            additional_instruction,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Field regeneration failed: {e}")

    # Update content
    # Handle different field types
    if field_name == "teaching_steps":
        # Parse JSON array
        field_value = extract_json_from_content(new_content, is_array=True)
    elif field_name in ("teaching_goals", "homework"):
        # Parse JSON object
        field_value = extract_json_from_content(new_content, is_array=False)
    else:
        field_value = new_content

    column = "final_content" if row["final_content"] else "generated_content"
    layer = parse_content_layer(row[column], label="教案内容")
    layer[field_name] = field_value

    # Update database
    await _save_content_layer_if_editable(
        lesson_plan_id=lesson_plan_id,
        column=column,
        content=layer,
    )

    return {
        "field_name": field_name,
        "new_content": field_value,
        "message": f"Field '{field_name}' regenerated successfully",
    }


@router.put("/{lesson_plan_id}/content")
async def update_field(
    lesson_plan_id: str,
    request: FieldEditRequest,
):
    """
    Manually update a field's content.
    """
    # Get lesson plan
    row = await db.fetch_one(
        "SELECT * FROM lesson_plans WHERE id = ?",
        (lesson_plan_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    await _ensure_batch_editable(row)

    # Update final content if exists, otherwise update generated
    column = "final_content" if row["final_content"] else "generated_content"
    layer = parse_content_layer(row[column], label="教案内容")
    layer[request.field_name] = request.content
    await _save_content_layer_if_editable(
        lesson_plan_id=lesson_plan_id,
        column=column,
        content=layer,
    )

    return {"message": "Field updated successfully"}


@router.post("/{lesson_plan_id}/export")
async def export_lesson_plan(lesson_plan_id: str):
    """
    Export lesson plan as Word document.
    """
    # Get lesson plan
    row = await db.fetch_one(
        "SELECT * FROM lesson_plans WHERE id = ?",
        (lesson_plan_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Lesson plan not found")

    try:
        require_valid_builtin_template(row["template_id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content = merge_lesson_content(
        row["generated_content"],
        row["final_content"],
    )
    input_data = json.loads(row["input_data"])

    # Prepare data for rendering
    # Query class names from class_ids
    class_ids = input_data.get("class_ids", [])
    class_names = []
    if class_ids:
        placeholders = ",".join(["?"] * len(class_ids))
        class_rows = await db.fetch_all(
            f"SELECT name FROM classes WHERE id IN ({placeholders})",
            tuple(class_ids)
        )
        class_names = [row["name"] for row in class_rows]

    # Build references from textbook_name and online_resources
    # Use user-provided online_resources, otherwise use AI-generated
    online_resources = input_data.get("online_resources") or content.get("online_resources", "")

    references_parts = []
    if input_data.get("textbook_name"):
        # Add book title marks around textbook name
        textbook_name = input_data['textbook_name']
        references_parts.append(f"《{textbook_name}》")
    if online_resources:
        references_parts.append(online_resources)
    references = "\n".join(references_parts) if references_parts else ""

    render_data = {
        "subject": input_data.get("subject", ""),
        "grade": input_data.get("grade", ""),
        "topic": input_data.get("topic", ""),
        "teaching_topic": input_data.get("topic", ""),  # For template compatibility
        "duration": input_data.get("duration", ""),
        "class_name": ", ".join(class_names) if class_names else "",  # Resolve from class_ids
        "week_number": "",  # For template compatibility
        "location": input_data.get("location", ""),  # Use actual value
        "references": references,  # Use built references
        "ideological_political": "",  # For template compatibility
        # Add textbook_name and online_resources as separate fields for templates
        "textbook_name": input_data.get("textbook_name", ""),
        "online_resources": online_resources,
        **content,
    }

    # Render document
    try:
        renderer = DocumentRenderer()
        output_path = renderer.render_lesson_plan(
            str(get_builtin_template_path()), render_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document rendering failed: {e}")

    # Update database with output path
    from ..config import settings
    relative_path = str(settings.output_dir / Path(output_path).name)

    await db.execute(
        "UPDATE lesson_plans SET output_file_path = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (relative_path, "completed", lesson_plan_id),
        commit=True,
    )

    from fastapi.responses import FileResponse
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=Path(output_path).name,
    )


@router.get("/{lesson_plan_id}")
async def get_lesson_plan(lesson_plan_id: str):
    """
    Get details of a generated lesson plan.
    """
    row = await db.fetch_one(
        "SELECT * FROM lesson_plans WHERE id = ?",
        (lesson_plan_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Lesson plan not found")

    input_data = json.loads(row["input_data"])
    generated_content = merge_lesson_content(
        row["generated_content"],
        row["final_content"],
    )
    final_content = json.loads(row["final_content"]) if row["final_content"] else None

    return {
        "id": row["id"],
        "template_id": row["template_id"],
        "title": row["title"],
        "subject": row["subject"],
        "grade": row["grade"],
        "topic": row["topic"],
        "input": input_data,
        "generated_content": generated_content,
        "final_content": final_content,
        "status": row["status"],
        "output_file_path": row["output_file_path"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.get("")
async def list_lesson_plans(
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    subject: Optional[str] = None,
    grade: Optional[str] = None,
    status: Optional[str] = None,
):
    """
    List all generated lesson plans.
    """
    sql = "SELECT * FROM lesson_plans"
    params = []

    conditions = []
    if subject:
        conditions.append("subject = ?")
        params.append(subject)
    if grade:
        conditions.append("grade = ?")
        params.append(grade)
    if status:
        conditions.append("status = ?")
        params.append(status)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = await db.fetch_all(sql, tuple(params))

    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "template_id": row["template_id"],
            "title": row["title"],
            "subject": row["subject"],
            "grade": row["grade"],
            "topic": row["topic"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })

    return result


@router.delete("/{lesson_plan_id}")
async def delete_lesson_plan(lesson_plan_id: str):
    """
    Delete a lesson plan.
    """
    # Check if exists
    row = await db.fetch_one(
        "SELECT id FROM lesson_plans WHERE id = ?",
        (lesson_plan_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Lesson plan not found")

    # Delete
    await db.execute(
        "DELETE FROM lesson_plans WHERE id = ?",
        (lesson_plan_id,),
        commit=True,
    )

    return {"message": "Lesson plan deleted successfully"}
