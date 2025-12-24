"""
Lesson plan generation API endpoints.
"""
import json
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from ..models.database import db
from ..models.schemas import (
    LessonPlanGenerateRequest,
    LessonPlanResponse,
    FieldRegenerateRequest,
    FieldEditRequest,
    GeneratedContent,
    generate_id,
)
from ..services.ai_generator import AIGenerator
from ..services.document_renderer import DocumentRenderer
from ..utils.ai_config import get_ai_generator

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("", response_model=LessonPlanResponse)
async def generate_lesson_plan(request: LessonPlanGenerateRequest):
    """
    Generate a complete lesson plan based on input data.
    """
    # Verify template exists
    template = await db.fetch_one(
        "SELECT * FROM templates WHERE id = ?",
        (request.template_id,),
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Generate content using AI
    try:
        generator = await get_ai_generator()
        content = await generator.generate_lesson_plan(request)
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

    # Parse current content
    input_data = json.loads(row["input_data"])
    current_content = json.loads(row["generated_content"])

    # Regenerate field
    try:
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
        import re
        json_match = re.search(r"\[.*\]", new_content, re.DOTALL)
        if json_match:
            current_content[field_name] = json.loads(json_match.group(0))
        else:
            current_content[field_name] = json.loads(new_content)
    elif field_name == "teaching_goals":
        # Parse JSON object
        import re
        json_match = re.search(r"\{.*\}", new_content, re.DOTALL)
        if json_match:
            current_content[field_name] = json.loads(json_match.group(0))
        else:
            current_content[field_name] = json.loads(new_content)
    elif field_name == "homework":
        # Parse JSON object
        import re
        json_match = re.search(r"\{.*\}", new_content, re.DOTALL)
        if json_match:
            current_content[field_name] = json.loads(json_match.group(0))
        else:
            current_content[field_name] = json.loads(new_content)
    else:
        current_content[field_name] = new_content

    # Update database
    await db.execute(
        "UPDATE lesson_plans SET generated_content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (json.dumps(current_content), lesson_plan_id),
        commit=True,
    )

    return {
        "field_name": field_name,
        "new_content": current_content[field_name],
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

    # Parse current content
    current_content = json.loads(row["generated_content"])

    # Update field
    current_content[request.field_name] = request.content

    # Update final content if exists, otherwise update generated
    final_content = row["final_content"]
    if final_content:
        final = json.loads(final_content)
        final[request.field_name] = request.content
        await db.execute(
            "UPDATE lesson_plans SET final_content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(final), lesson_plan_id),
            commit=True,
        )
    else:
        await db.execute(
            "UPDATE lesson_plans SET generated_content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(current_content), lesson_plan_id),
            commit=True,
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

    # Get template
    template = await db.fetch_one(
        "SELECT * FROM templates WHERE id = ?",
        (row["template_id"],),
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Use final content if available, otherwise use generated
    content_data = row["final_content"] or row["generated_content"]
    content = json.loads(content_data)
    input_data = json.loads(row["input_data"])

    # Prepare data for rendering
    render_data = {
        "subject": input_data.get("subject", ""),
        "grade": input_data.get("grade", ""),
        "topic": input_data.get("topic", ""),
        "teaching_topic": input_data.get("topic", ""),  # For template compatibility
        "duration": input_data.get("duration", ""),
        "class_name": input_data.get("grade", ""),  # For template compatibility
        "week_number": "",  # For template compatibility
        "location": "",  # For template compatibility
        "references": "",  # For template compatibility
        "ideological_political": "",  # For template compatibility
        **content,
    }

    # Render document
    try:
        renderer = DocumentRenderer()
        output_path = renderer.render_lesson_plan(template["file_path"], render_data)
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
    generated_content = json.loads(row["generated_content"])
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
