"""
Template management API endpoints.
"""
import os
import shutil
import json
import tempfile
import logging
from pathlib import Path
from typing import Optional
from urllib.request import urlopen
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Body, Request
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
from ..services.template_versioning import (
    save_version,
    get_versions,
    get_version_content,
    compare_versions,
    restore_version,
    delete_old_versions,
)

router = APIRouter(prefix="/templates", tags=["templates"])
logger = logging.getLogger(__name__)


async def _ensure_fields_config(template_id: str, file_path: str, fields_config_json: Optional[str]) -> list[dict]:
    """Ensure fields_config is populated; parse and persist if missing."""
    if fields_config_json:
        try:
            fields = json.loads(fields_config_json)
            if fields:
                return fields
        except Exception:
            pass

    # Parse template to recover fields_config
    try:
        parser = TemplateParser(file_path)
        fields = parser.parse()
        fields_config = [f.model_dump() for f in fields]
        await db.execute(
            "UPDATE templates SET fields_config = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(fields_config), template_id),
            commit=True,
        )
        return fields_config
    except Exception as exc:
        logger.warning("Failed to rebuild fields_config for template %s: %s", template_id, exc)
        return []


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


@router.get("/standard-fields")
async def get_standard_fields():
    """
    Get standard field mappings for reference.
    Returns predefined field configurations with Chinese display names.
    """
    from ..services.template_parser import TemplateParser

    standard_fields = []
    for name, config in TemplateParser.STANDARD_FIELDS.items():
        standard_fields.append({
            "name": name,
            "display_name": config["display"],
            "field_type": config["type"],
            "required": config["required"],
        })

    return {"fields": standard_fields}


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

    fields_config = await _ensure_fields_config(
        template_id=template_id,
        file_path=row["file_path"],
        fields_config_json=row["fields_config"],
    )

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


@router.api_route("/{template_id}/download", methods=["GET", "HEAD"])
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
        "SELECT fields_config, file_path FROM templates WHERE id = ?",
        (template_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    fields_config = await _ensure_fields_config(
        template_id=template_id,
        file_path=row["file_path"],
        fields_config_json=row["fields_config"],
    )
    return {"fields": fields_config}


class UpdateFieldsRequest(BaseModel):
    fields: list[dict]


@router.put("/{template_id}/fields")
async def update_template_fields(template_id: str, request: UpdateFieldsRequest = Body(...)):
    """
    Update fields configuration for a template.
    """
    # Check if template exists
    row = await db.fetch_one(
        "SELECT id FROM templates WHERE id = ?",
        (template_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    # Convert fields to JSON
    fields_config_json = json.dumps(request.fields)

    # Update fields_config
    await db.execute(
        "UPDATE templates SET fields_config = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (fields_config_json, template_id),
        commit=True,
    )

    return {"success": True, "fields": request.fields}


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
# OnlyOffice Integration
# ============================================================================

ONLYOFFICE_ASSET_VERSION = "20260121-fix6"

class OnlyOfficeCallbackRequest(BaseModel):
    status: int
    url: Optional[str] = None
    changesurl: Optional[str] = None
    key: Optional[str] = None
    forcesavetype: Optional[int] = None


def _build_base_url(request: Request) -> str:
    """Return public base URL for callbacks and file access."""
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


@router.get("/{template_id}/onlyoffice/config")
async def get_onlyoffice_config(template_id: str, request: Request):
    """
    Return OnlyOffice editor configuration for the given template.
    """
    if not settings.onlyoffice_docs_url:
        raise HTTPException(
            status_code=503,
            detail="OnlyOffice Document Server URL not configured"
        )

    row = await db.fetch_one(
        "SELECT file_path, name FROM templates WHERE id = ?",
        (template_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    file_path = row["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Template file not found")

    base_url = _build_base_url(request)
    file_stat = Path(file_path).stat()

    download_url = f"{base_url}{settings.api_prefix}/templates/{template_id}/download"
    callback_url = f"{base_url}{settings.api_prefix}/templates/{template_id}/onlyoffice/callback"
    document_server = settings.onlyoffice_docs_url.rstrip("/")

    config = {
        "documentType": "word",
        "document": {
            "fileType": "docx",
            "key": f"{template_id}-{int(file_stat.st_mtime)}",
            "title": f"{row['name']}.docx",
            "url": download_url,
            "permissions": {
                "edit": True,
                "download": True,
                "print": True,
            },
        },
        "editorConfig": {
            "lang": "zh-CN",
            "callbackUrl": callback_url,
            "mode": "edit",
            "user": {
                "id": "template-editor",
                "name": "模板编辑器",
            },
        },
    }

    # Optional JWT protection
    token = None
    if settings.onlyoffice_jwt_secret:
        try:
            import jwt

            # JWT payload must mirror the editor config for Document Server validation
            payload = json.loads(json.dumps(config))
            token = jwt.encode(payload, settings.onlyoffice_jwt_secret, algorithm="HS256")
            if isinstance(token, bytes):
                token = token.decode("utf-8")

            # Attach token in all expected locations (DS 7.1+ enforces document.key in JWT)
            config["token"] = token
            config["jwt"] = token
            config["document"]["token"] = token
            config["document"]["jwt"] = token
            config["editorConfig"]["token"] = token
            config["editorConfig"]["jwt"] = token
        except ImportError:
            # JWT library not installed; skip token generation
            token = None

    return {
        "config": config,
        "token": token,
        "documentServerUrl": document_server,
        "apiJsUrl": f"{document_server}/web-apps/apps/api/documents/api.js?v={ONLYOFFICE_ASSET_VERSION}",
    }


@router.post("/{template_id}/onlyoffice/callback")
async def onlyoffice_callback(template_id: str, payload: OnlyOfficeCallbackRequest):
    """
    Handle OnlyOffice Document Server save callbacks.
    """
    row = await db.fetch_one(
        "SELECT file_path FROM templates WHERE id = ?",
        (template_id,),
    )

    if not row:
        return {"error": 1}

    file_path = row["file_path"]
    status = payload.status

    # Status codes 2, 3, 6, 7 mean the document must be saved
    if status in (2, 3, 6, 7):
        if not payload.url:
            return {"error": 1}

        temp_fd, temp_path = tempfile.mkstemp(suffix=".docx")
        backup_path = file_path + ".backup"

        try:
            with urlopen(payload.url) as remote, os.fdopen(temp_fd, "wb") as tmp_file:
                shutil.copyfileobj(remote, tmp_file)

            # Backup current file
            if os.path.exists(file_path):
                shutil.copy2(file_path, backup_path)

            # Replace with updated file
            shutil.copy2(temp_path, file_path)

            # Remove backup after successful save
            if os.path.exists(backup_path):
                os.remove(backup_path)

            # Persist version history as HTML snapshot (best effort)
            try:
                from ..services.docx_converter import convert_docx_to_html

                result = convert_docx_to_html(file_path)
                await save_version(
                    template_id=template_id,
                    content=result.get("html", ""),
                    user="OnlyOffice",
                    comment="OnlyOffice 保存",
                )
            except Exception:
                # Conversion is optional; continue even if it fails
                pass

            await db.execute(
                "UPDATE templates SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (template_id,),
                commit=True,
            )

            return {"error": 0}
        except Exception:
            # Restore from backup if something goes wrong
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
                os.remove(backup_path)
            return {"error": 1}
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    # Other statuses: acknowledge without changes
    return {"error": 0}


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
        from ..services.docx_converter import convert_docx_to_html

        result = convert_docx_to_html(file_path)
        html = result["html"]
        messages = result.get("messages", [])
        metadata = result.get("metadata", {})
        if "title" not in metadata or not metadata["title"]:
            metadata["title"] = row["name"]

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
        from ..services.docx_converter import convert_html_to_docx

        # 保存版本记录（在修改DOCX之前）
        version_comment = "保存更新"
        version_user = "用户"
        if request.metadata:
            version_comment = request.metadata.get("version_comment", version_comment)
            version_user = request.metadata.get("user", version_user)

        await save_version(
            template_id=template_id,
            content=request.html,
            user=version_user,
            comment=version_comment
        )

        # Save to the same file (backup original first)
        backup_path = file_path + ".backup"
        shutil.copy2(file_path, backup_path)

        try:
            convert_html_to_docx(
                html=request.html,
                output_path=file_path,
                original_docx_path=file_path,
            )
            if request.metadata:
                from docx import Document
                doc = Document(file_path)
                if "title" in request.metadata:
                    doc.core_properties.title = request.metadata["title"]
                if "author" in request.metadata:
                    doc.core_properties.author = request.metadata["author"]
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
    Uses sandboxed environment to prevent SSTI attacks.
    """
    from jinja2 import Environment, TemplateSyntaxError, select_autoescape
    from jinja2.sandbox import SandboxedEnvironment

    try:
        # Use sandboxed environment to prevent SSTI attacks
        env = SandboxedEnvironment(
            autoescape=select_autoescape(['html', 'xml']),
        )

        # Sanitize sample_data - only allow basic types
        def sanitize_data(data, max_depth=5):
            if max_depth <= 0:
                return str(data)
            if data is None:
                return None
            if isinstance(data, (str, int, float, bool)):
                return data
            if isinstance(data, list):
                return [sanitize_data(item, max_depth - 1) for item in data[:100]]
            if isinstance(data, dict):
                return {
                    str(k): sanitize_data(v, max_depth - 1)
                    for k, v in list(data.items())[:50]
                }
            return str(data)

        safe_data = sanitize_data(request.sample_data)

        # Render template with sanitized sample data
        try:
            template = env.from_string(request.html)
            preview_html = template.render(**safe_data)
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


# ============================================================================
# Template Version History API Endpoints
# ============================================================================

class VersionCompareRequest(BaseModel):
    version_id_1: str
    version_id_2: str


class ExportHtmlRequest(BaseModel):
    html: str


@router.get("/{template_id}/versions")
async def list_template_versions(
    template_id: str,
    limit: int = Query(50, le=100),
    offset: int = Query(0),
):
    """
    获取模板的版本历史列表
    """
    # 验证模板存在
    row = await db.fetch_one(
        "SELECT id FROM templates WHERE id = ?",
        (template_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    versions = await get_versions(template_id, limit, offset)
    return {"versions": versions}


@router.get("/{template_id}/versions/{version_id}")
async def get_template_version(template_id: str, version_id: str):
    """
    获取指定版本的内容
    """
    content = await get_version_content(version_id)
    if not content:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"content": content}


@router.post("/{template_id}/versions/{version_id}/restore")
async def restore_template_version(template_id: str, version_id: str):
    """
    恢复到指定版本
    """
    try:
        # 恢复版本（创建新版本记录）
        new_version_id = await restore_version(template_id, version_id)

        # 同时需要将HTML内容同步回DOCX文件
        content = await get_version_content(version_id)
        if content:
            row = await db.fetch_one(
                "SELECT file_path FROM templates WHERE id = ?",
                (template_id,),
            )
            if row and os.path.exists(row["file_path"]):
                try:
                    from ..services.docx_converter import convert_html_to_docx

                    # 备份原文件
                    backup_path = row["file_path"] + ".backup"
                    shutil.copy2(row["file_path"], backup_path)

                    try:
                        # 转换HTML为DOCX
                        convert_html_to_docx(
                            html=content,
                            output_path=row["file_path"],
                            original_docx_path=row["file_path"],
                        )
                        os.remove(backup_path)
                    except Exception:
                        # 恢复备份
                        shutil.copy2(backup_path, row["file_path"])
                        os.remove(backup_path)
                        raise
                except ImportError:
                    pass  # 如果htmldocx不可用，仅恢复版本记录

        return {
            "success": True,
            "new_version_id": new_version_id,
            "message": "版本恢复成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复版本失败: {str(e)}")


@router.post("/{template_id}/versions/compare")
async def compare_template_versions(
    template_id: str,
    request: VersionCompareRequest = Body(...),
):
    """
    对比两个版本的差异
    """
    try:
        result = await compare_versions(
            request.version_id_1,
            request.version_id_2
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对比版本失败: {str(e)}")


@router.delete("/{template_id}/versions/cleanup")
async def cleanup_template_versions(
    template_id: str,
    keep_count: int = Query(20, ge=1, le=100),
):
    """
    清理旧版本，只保留最新的N个版本
    """
    deleted_count = await delete_old_versions(template_id, keep_count)
    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"已删除 {deleted_count} 个旧版本"
    }


# ============================================================================
# HTML Export API
# ============================================================================

@router.post("/{template_id}/export/html")
async def export_template_html(template_id: str, request: ExportHtmlRequest = Body(...)):
    """
    导出模板的HTML内容为文件下载
    """
    row = await db.fetch_one(
        "SELECT name FROM templates WHERE id = ?",
        (template_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        from datetime import datetime

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = row["name"].replace(" ", "_").replace("/", "_")
        filename = f"{safe_name}_{timestamp}.html"

        # 保存到输出目录
        output_path = str(settings.output_dir / filename)

        # 添加HTML包装
        full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{row["name"]}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', SimSun, sans-serif; margin: 40px; line-height: 1.6; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
        .jinja-placeholder {{ background-color: #e6f7ff; border: 1px solid #1890ff;
                             border-radius: 3px; padding: 2px 6px; font-family: monospace; }}
        h1, h2, h3, h4, h5, h6 {{ color: #333; }}
    </style>
</head>
<body>
{request.html}
</body>
</html>"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_html)

        return {
            "success": True,
            "filename": filename,
            "download_url": f"/static/{filename}"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"导出HTML失败: {str(e)}"
        )
