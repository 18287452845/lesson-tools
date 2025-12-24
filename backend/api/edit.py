"""
Old lesson plan editing API endpoints.
This is the core API for the "edit existing lesson plans" feature.
"""
import json
import os
import shutil
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse

from ..config import settings
from ..models.database import db
from ..models.schemas import (
    DocumentUploadResponse,
    SectionEditRequest,
    DocumentEditResponse,
    AddSectionRequest,
    AIEnhanceRequest,
    generate_id,
)
from ..services.lesson_plan_parser import LessonPlanParser
from ..services.document_modifier import DocumentModifier
from ..services.ai_editor import AIEditor
from ..utils.ai_config import get_ai_editor

router = APIRouter(prefix="/edit", tags=["edit"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload an existing lesson plan document for editing.

    The API will parse the document and identify all sections.
    """
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    # Generate unique ID and save file
    doc_id = generate_id()
    filename = f"{doc_id}_{file.filename}"
    file_path = str(settings.upload_dir / filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse the document
    try:
        parser = LessonPlanParser(file_path)
        parser.parse()
        parsed_sections = parser.get_parsed_sections()
    except Exception as e:
        # Clean up file if parsing fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Failed to parse document: {e}")

    # Save to database
    await db.execute(
        """
        INSERT INTO document_edits (id, original_file_path, original_file_name, parsed_content, current_file_path)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            doc_id,
            file_path,
            file.filename,
            json.dumps({k: v.model_dump() for k, v in parsed_sections.items()}),
            file_path,
        ),
        commit=True,
    )

    return DocumentUploadResponse(
        id=doc_id,
        filename=file.filename,
        parsed_sections=parsed_sections,
    )


@router.get("/{document_id}")
async def get_document(document_id: str):
    """
    Get details of an uploaded document.
    """
    row = await db.fetch_one(
        "SELECT * FROM document_edits WHERE id = ?",
        (document_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    parsed_content = json.loads(row["parsed_content"]) if row["parsed_content"] else {}
    edit_history = json.loads(row["edit_history"]) if row["edit_history"] else []

    return {
        "id": row["id"],
        "filename": row["original_file_name"],
        "parsed_sections": parsed_content,
        "edit_history": edit_history,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.post("/{document_id}/section")
async def edit_section(document_id: str, request: SectionEditRequest):
    """
    Edit a specific section of the document.

    Operations:
    - replace: Replace the section content
    - append: Append content to the section
    - insert: Insert content at the beginning
    - generate: Use AI to generate content for missing sections
    - ai_modify: Use AI to modify existing content
    """
    # Get document info
    row = await db.fetch_one(
        "SELECT * FROM document_edits WHERE id = ?",
        (document_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    parsed_content = json.loads(row["parsed_content"])
    section_info = parsed_content.get(request.section_name)

    if not section_info:
        raise HTTPException(status_code=404, detail=f"Section '{request.section_name}' not found")

    # Parse the current document
    from ..services.lesson_plan_parser import SectionInfo, SectionLocation

    current_file = row["current_file_path"]
    modifier = DocumentModifier(current_file)

    # Re-parse to get current section locations
    parser = LessonPlanParser(current_file)
    parser.parse()

    section_data = parser.sections.get(request.section_name)
    if not section_data:
        raise HTTPException(status_code=404, detail=f"Section '{request.section_name}' not found in current document")

    # Build section info
    location = SectionLocation(
        in_table=section_data.in_table,
        table_idx=section_data.table_idx,
        cell_location=section_data.cell_location,
        start_para_idx=section_data.start_para_idx,
        end_para_idx=section_data.end_para_idx,
    )

    section_info_obj = SectionInfo(
        name=request.section_name,
        found=section_data.found,
        content=section_data.content,
        start_para_idx=section_data.start_para_idx,
        end_para_idx=section_data.end_para_idx,
        in_table=section_data.in_table,
        table_idx=section_data.table_idx,
        cell_location=section_data.cell_location,
    )

    # Execute the edit operation
    new_content = request.content
    context = {
        "subject": "课程",  # Could extract from document
        "topic": "课题",  # Could extract from document
    }

    if request.operation == "replace":
        if not request.content:
            raise HTTPException(status_code=400, detail="Content is required for replace operation")
        # Direct replacement
        pass

    elif request.operation == "append":
        if not request.content:
            raise HTTPException(status_code=400, detail="Content is required for append operation")
        new_content = section_data.content + "\n" + request.content if section_data.content else request.content
        modifier.append_to_section(section_info_obj, request.content)

    elif request.operation == "insert":
        if not request.content:
            raise HTTPException(status_code=400, detail="Content is required for insert operation")
        new_content = request.content + "\n" + section_data.content if section_data.content else request.content
        modifier.insert_in_section(section_info_obj, request.content, at_start=True)

    elif request.operation == "generate":
        # AI generate for missing section
        editor = await get_ai_editor()
        new_content = await editor.generate_missing_section(
            request.section_name,
            context,
            request.ai_instruction,
        )

    elif request.operation == "ai_modify":
        # AI modify existing content
        if not request.ai_instruction:
            raise HTTPException(status_code=400, detail="AI instruction is required for ai_modify operation")

        editor = await get_ai_editor()
        new_content = await editor.modify_content(
            section_data.content or "",
            request.ai_instruction,
            context,
            request.section_name,
        )

    # Apply the modification
    if request.operation in ("replace", "generate", "ai_modify"):
        modifier.modify_section(section_info_obj, new_content)

    # Save the modified document
    output_path = modifier.save_with_suffix()

    # Update parsed content
    section_info["content"] = new_content
    section_info["found"] = True

    # Add to edit history
    edit_history = json.loads(row["edit_history"]) if row["edit_history"] else []
    edit_history.append({
        "section": request.section_name,
        "operation": request.operation,
        "timestamp": modifier._get_timestamp(),
    })

    # Update database
    await db.execute(
        """
        UPDATE document_edits
        SET parsed_content = ?, edit_history = ?, current_file_path = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (json.dumps(parsed_content), json.dumps(edit_history), output_path, document_id),
        commit=True,
    )

    return DocumentEditResponse(
        section_name=request.section_name,
        new_content=new_content,
        preview_url=None,
    )


@router.post("/{document_id}/ai-enhance")
async def ai_enhance_section(document_id: str, request: AIEnhanceRequest):
    """
    AI enhance a section's content.

    Enhancement types:
    - detailed: Make content more detailed
    - professional: Make content more professional
    - simplified: Simplify content
    - rewrite: Rewrite content for better flow
    """
    # Get document info
    row = await db.fetch_one(
        "SELECT * FROM document_edits WHERE id = ?",
        (document_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    parsed_content = json.loads(row["parsed_content"])
    section_info = parsed_content.get(request.section_name)

    if not section_info or not section_info.get("found"):
        raise HTTPException(status_code=404, detail=f"Section '{request.section_name}' not found")

    # Get current content
    content = section_info.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail=f"Section '{request.section_name}' has no content to enhance")

    # Build context
    context = {
        "subject": "课程",
        "grade": "年级",
        "topic": "课题",
    }

    # Enhance with AI
    editor = AIEditor()
    enhanced_content = await editor.enhance_content(
        content,
        request.enhancement_type,
        context,
        request.specific_instruction,
    )

    # Apply modification
    current_file = row["current_file_path"]
    modifier = DocumentModifier(current_file)

    parser = LessonPlanParser(current_file)
    parser.parse()
    section_data = parser.sections.get(request.section_name)

    if section_data:
        modifier.modify_section(section_data, enhanced_content)
        output_path = modifier.save_with_suffix()

        # Update database
        section_info["content"] = enhanced_content
        edit_history = json.loads(row["edit_history"]) if row["edit_history"] else []
        edit_history.append({
            "section": request.section_name,
            "operation": f"ai_enhance_{request.enhancement_type}",
            "timestamp": modifier._get_timestamp(),
        })

        await db.execute(
            """
            UPDATE document_edits
            SET parsed_content = ?, edit_history = ?, current_file_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (json.dumps(parsed_content), json.dumps(edit_history), output_path, document_id),
            commit=True,
        )

    return {
        "section_name": request.section_name,
        "enhanced_content": enhanced_content,
    }


@router.post("/{document_id}/add-section")
async def add_section(document_id: str, request: AddSectionRequest):
    """
    Add a missing section to the document.

    Common additions:
    - reflection (教学反思)
    - blackboard_design (板书设计)
    """
    # Get document info
    row = await db.fetch_one(
        "SELECT * FROM document_edits WHERE id = ?",
        (document_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    parsed_content = json.loads(row["parsed_content"])

    # Check if section already exists
    if request.section_name in parsed_content and parsed_content[request.section_name].get("found"):
        raise HTTPException(status_code=400, detail=f"Section '{request.section_name}' already exists")

    # Generate content
    if request.ai_generate:
        context = {
            "subject": "课程",
            "grade": "年级",
            "topic": "课题",
        }

        # Add context from existing sections
        for section_name, section_data in parsed_content.items():
            if section_data.get("found") and section_data.get("content"):
                context[section_name] = section_data["content"]

        editor = await get_ai_editor()
        content = await editor.generate_missing_section(
            request.section_name,
            context,
        )
    else:
        content = request.manual_content or ""

    # Add to document
    current_file = row["current_file_path"]
    modifier = DocumentModifier(current_file)
    modifier.add_section(request.section_name, content, request.position)
    output_path = modifier.save_with_suffix()

    # Update parsed content
    parsed_content[request.section_name] = {
        "name": request.section_name,
        "found": True,
        "content": content,
        "location": None,
    }

    # Update edit history
    edit_history = json.loads(row["edit_history"]) if row["edit_history"] else []
    edit_history.append({
        "section": request.section_name,
        "operation": "add",
        "timestamp": modifier._get_timestamp(),
    })

    # Update database
    await db.execute(
        """
        UPDATE document_edits
        SET parsed_content = ?, edit_history = ?, current_file_path = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (json.dumps(parsed_content), json.dumps(edit_history), output_path, document_id),
        commit=True,
    )

    return {
        "success": True,
        "section_name": request.section_name,
        "content": content,
    }


@router.post("/{document_id}/save")
async def save_document(document_id: str):
    """
    Save and download the edited document.
    """
    row = await db.fetch_one(
        "SELECT current_file_path, original_file_name FROM document_edits WHERE id = ?",
        (document_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = row["current_file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=row["original_file_name"].replace(".docx", "_edited.docx"),
    )


@router.post("/{document_id}/undo")
async def undo_edit(document_id: str):
    """
    Undo the last edit operation.
    """
    row = await db.fetch_one(
        "SELECT * FROM document_edits WHERE id = ?",
        (document_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    edit_history = json.loads(row["edit_history"]) if row["edit_history"] else []
    if not edit_history:
        raise HTTPException(status_code=400, detail="No edits to undo")

    # Remove last edit
    edit_history.pop()

    # Revert to original file
    original_file = row["original_file_path"]
    output_path = original_file.replace(".docx", "_undo.docx")
    shutil.copy(original_file, output_path)

    # Update database
    await db.execute(
        """
        UPDATE document_edits
        SET edit_history = ?, current_file_path = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (json.dumps(edit_history), output_path, document_id),
        commit=True,
    )

    return {"success": True, "message": "Undo successful"}


@router.get("/{document_id}/history")
async def get_edit_history(document_id: str):
    """
    Get the edit history for a document.
    """
    row = await db.fetch_one(
        "SELECT edit_history FROM document_edits WHERE id = ?",
        (document_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    edit_history = json.loads(row["edit_history"]) if row["edit_history"] else []

    return {
        "document_id": document_id,
        "edits": edit_history,
    }
