"""
Document export and general document API endpoints.
"""
import os
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/download/{filename}")
async def download_document(filename: str):
    """
    Download a generated or edited document.
    """
    file_path = str(settings.output_dir / filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@router.get("/preview/{filename}")
async def preview_document(filename: str):
    """
    Get a preview of a document.
    """
    file_path = str(settings.output_dir / filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # For now, just return the file
    # Could implement PDF preview or HTML conversion later
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )
