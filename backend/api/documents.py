"""
Document export and general document API endpoints.
"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from ..config import settings
from ..services.document_preview import render_document_preview

router = APIRouter(prefix="/documents", tags=["documents"])


def _resolve_output_file(filename: str) -> Path:
    output_dir = Path(settings.output_dir).resolve()
    candidate = (output_dir / Path(filename).name).resolve()
    if candidate.parent != output_dir or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return candidate


@router.get("/download/{filename}")
async def download_document(filename: str):
    """
    Download a generated or edited document.
    """
    file_path = _resolve_output_file(filename)

    return FileResponse(
        str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@router.get("/preview/{filename}")
async def preview_document(filename: str):
    """
    Get a preview of a document.
    """
    file_path = _resolve_output_file(filename)
    try:
        html = render_document_preview(file_path)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except Exception:
        # Preserve the legacy behavior for damaged/third-party office files
        # that python-docx/python-pptx cannot parse.
        return FileResponse(str(file_path), filename=filename)
    return HTMLResponse(html)
