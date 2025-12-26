"""
Template management API endpoints.
"""
import os
import shutil
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..config import settings
from ..models.database import db
from ..models.schemas import (
    TemplateInfo,
    TemplateUploadResponse,
    generate_id,
)
from ..services.template_parser import TemplateParser

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("/upload", response_model=TemplateUploadResponse)
async def upload_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    grade: Optional[str] = Form(None),
):
    """
    Upload a new lesson plan template.

    The template should be a .docx file with Jinja2-style placeholders.
    """
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    # Generate unique ID and filename
    template_id = generate_id()
    filename = f"{template_id}_{file.filename}"
    file_path = str(settings.template_dir / filename)

    # Save uploaded file
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Parse template to extract fields
    try:
        parser = TemplateParser(file_path)
        fields = parser.parse()

        # Validate template
        is_valid, errors = parser.validate_template()
        if not is_valid:
            # Clean up file if validation fails
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail=f"Template validation failed: {'; '.join(errors)}",
            )

    except Exception as e:
        # Clean up file if parsing fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Failed to parse template: {e}")

    # Save to database
    fields_config_json = json.dumps([f.model_dump() for f in fields])

    await db.execute(
        """
        INSERT INTO templates (id, name, description, subject, grade, file_path, fields_config)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (template_id, name, description, subject, grade, file_path, fields_config_json),
        commit=True,
    )

    return TemplateUploadResponse(
        id=template_id,
        name=name,
        fields=fields,
        preview_url=None,  # Could add preview image generation later
    )


@router.get("", response_model=list[TemplateInfo])
async def list_templates(
    subject: Optional[str] = Query(None),
    grade: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
):
    """
    List all templates with optional filtering.
    """
    # Build query
    sql = "SELECT * FROM templates"
    params = []

    conditions = []
    if subject:
        conditions.append("subject = ?")
        params.append(subject)
    if grade:
        conditions.append("grade = ?")
        params.append(grade)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY use_count DESC, created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = await db.fetch_all(sql, tuple(params))

    templates = []
    for row in rows:
        fields_config = json.loads(row["fields_config"]) if row["fields_config"] else []
        templates.append(
            TemplateInfo(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                subject=row["subject"],
                grade=row["grade"],
                file_path=row["file_path"],
                fields_config=fields_config,
                preview_image=row["preview_image"],
                use_count=row["use_count"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )

    return templates


@router.get("/{template_id}", response_model=TemplateInfo)
async def get_template(template_id: str):
    """
    Get details of a specific template.
    """
    row = await db.fetch_one(
        "SELECT * FROM templates WHERE id = ?",
        (template_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    fields_config = json.loads(row["fields_config"]) if row["fields_config"] else []

    return TemplateInfo(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        subject=row["subject"],
        grade=row["grade"],
        file_path=row["file_path"],
        fields_config=fields_config,
        preview_image=row["preview_image"],
        use_count=row["use_count"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/{template_id}/download")
async def download_template(template_id: str):
    """
    Download a template file.
    """
    row = await db.fetch_one(
        "SELECT file_path, name FROM templates WHERE id = ?",
        (template_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    file_path = row["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Template file not found")

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=row["name"] + ".docx",
    )


@router.get("/{template_id}/preview")
async def get_template_preview(template_id: str):
    """
    Get a preview image of the template.
    """
    row = await db.fetch_one(
        "SELECT preview_image, file_path FROM templates WHERE id = ?",
        (template_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    # For now, we don't generate preview images
    # Could add docx to image conversion later
    raise HTTPException(status_code=501, detail="Preview not implemented")


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    """
    Delete a template.
    """
    row = await db.fetch_one(
        "SELECT file_path FROM templates WHERE id = ?",
        (template_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    # Delete file
    file_path = row["file_path"]
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass  # Continue even if file deletion fails

    # Delete from database
    await db.execute(
        "DELETE FROM templates WHERE id = ?",
        (template_id,),
        commit=True,
    )

    return {"message": "Template deleted successfully"}


@router.get("/{template_id}/fields")
async def get_template_fields(template_id: str):
    """
    Get fields configuration for a template.
    """
    row = await db.fetch_one(
        "SELECT fields_config FROM templates WHERE id = ?",
        (template_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    fields_config = json.loads(row["fields_config"]) if row["fields_config"] else []
    return {"fields": fields_config}


@router.patch("/{template_id}")
async def update_template(
    template_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    subject: Optional[str] = None,
    grade: Optional[str] = None,
):
    """
    Update template metadata.
    """
    # Check if template exists
    row = await db.fetch_one(
        "SELECT id FROM templates WHERE id = ?",
        (template_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    # Build update query
    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if subject is not None:
        updates.append("subject = ?")
        params.append(subject)
    if grade is not None:
        updates.append("grade = ?")
        params.append(grade)

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(template_id)

        await db.execute(
            f"UPDATE templates SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
            commit=True,
        )

    return {"message": "Template updated successfully"}


# ============================================================================
# Template Editor API Endpoints
# ============================================================================

class JinjaValidateRequest(BaseModel):
    html: str


class SaveHtmlRequest(BaseModel):
    html: str
    metadata: Optional[dict] = None


class PreviewHtmlRequest(BaseModel):
    html: str
    sample_data: dict


@router.get("/{template_id}/html")
async def get_template_html(template_id: str):
    """
    Get template content as HTML for editing.
    Converts DOCX to HTML using mammoth.
    """
    row = await db.fetch_one(
        "SELECT file_path, name FROM templates WHERE id = ?",
        (template_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    file_path = row["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Template file not found")

    try:
        import mammoth

        with open(file_path, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file)
            html = result.value
            messages = [str(msg) for msg in result.messages]

        # Extract basic metadata from docx
        from docx import Document
        doc = Document(file_path)
        metadata = {
            "title": doc.core_properties.title or row["name"],
            "author": doc.core_properties.author or "",
            "created": str(doc.core_properties.created) if doc.core_properties.created else "",
            "modified": str(doc.core_properties.modified) if doc.core_properties.modified else "",
            "paragraphs_count": len(doc.paragraphs),
            "tables_count": len(doc.tables),
        }

        return {
            "html": html,
            "metadata": metadata,
            "messages": messages,
            "name": row["name"],
        }

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="mammoth library not installed. Run: pip install mammoth",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to convert template to HTML: {str(e)}",
        )


@router.post("/{template_id}/validate-jinja")
async def validate_jinja(template_id: str, request: JinjaValidateRequest = Body(...)):
    """
    Validate Jinja2 syntax in HTML content and extract variables.
    """
    from jinja2 import Environment, meta, TemplateSyntaxError

    try:
        env = Environment()

        # Parse template to check for syntax errors
        try:
            ast = env.parse(request.html)
        except TemplateSyntaxError as e:
            return {
                "valid": False,
                "errors": [f"Jinja2 syntax error at line {e.lineno}: {e.message}"],
                "variables": [],
            }

        # Extract variables
        variables = list(meta.find_undeclared_variables(ast))

        return {
            "valid": True,
            "errors": [],
            "variables": variables,
        }

    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Validation error: {str(e)}"],
            "variables": [],
        }


@router.post("/{template_id}/save-html")
async def save_template_html(template_id: str, request: SaveHtmlRequest = Body(...)):
    """
    Save HTML content back to DOCX template.
    Uses htmldocx to convert HTML back to DOCX.
    """
    row = await db.fetch_one(
        "SELECT file_path, name FROM templates WHERE id = ?",
        (template_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    file_path = row["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Template file not found")

    try:
        from htmldocx import HtmlToDocx
        from docx import Document

        # Create a new document
        doc = Document()

        # Convert HTML to DOCX
        parser = HtmlToDocx()
        parser.add_html_to_document(request.html, doc)

        # Update metadata if provided
        if request.metadata:
            if "title" in request.metadata:
                doc.core_properties.title = request.metadata["title"]
            if "author" in request.metadata:
                doc.core_properties.author = request.metadata["author"]

        # Save to the same file (backup original first)
        backup_path = file_path + ".backup"
        shutil.copy2(file_path, backup_path)

        try:
            doc.save(file_path)
            # If successful, remove backup
            os.remove(backup_path)
        except Exception as e:
            # Restore from backup if save fails
            shutil.copy2(backup_path, file_path)
            os.remove(backup_path)
            raise e

        # Update template in database
        await db.execute(
            "UPDATE templates SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (template_id,),
            commit=True,
        )

        return {
            "success": True,
            "message": "Template saved successfully",
        }

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="htmldocx library not installed. Run: pip install htmldocx",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save HTML to DOCX: {str(e)}",
        )


@router.post("/{template_id}/preview-html")
async def preview_template_html(template_id: str, request: PreviewHtmlRequest = Body(...)):
    """
    Preview HTML with sample data rendered using Jinja2.
    """
    from jinja2 import Environment, TemplateSyntaxError

    try:
        env = Environment()

        # Render template with sample data
        try:
            template = env.from_string(request.html)
            preview_html = template.render(**request.sample_data)
        except TemplateSyntaxError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Jinja2 syntax error at line {e.lineno}: {e.message}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Template rendering error: {str(e)}",
            )

        return {
            "preview_html": preview_html,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Preview generation failed: {str(e)}",
        )
