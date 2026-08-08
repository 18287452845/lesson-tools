"""REST endpoints for external textbook discovery and confirmed imports."""

import logging

from fastapi import APIRouter, HTTPException, status

from ..models.database import db
from ..models.schemas import (
    TextbookCatalogPreviewResponse,
    TextbookCatalogRequest,
    TextbookChapterCreateRequest,
    TextbookImportRequest,
    TextbookInfo,
    TextbookSearchCandidate,
    TextbookSearchRequest,
    TextbookSearchResponse,
)
from ..services.textbook_discovery import (
    BookCandidate,
    BookDiscoveryError,
    CatalogNotFoundError,
    DiscoveryQuery,
    DuplicateTextbookError,
    TextbookDiscoveryService,
    is_valid_isbn,
)
from ..services.textbook_importer import import_discovered_textbook
from ..utils.ai_config import get_user_ai_config
from .textbooks import get_textbook

logger = logging.getLogger(__name__)
router = APIRouter(tags=["textbook-discovery"])


def _to_candidate(model: TextbookSearchCandidate) -> BookCandidate:
    return BookCandidate(**model.model_dump())


@router.post("/textbook-searches", response_model=TextbookSearchResponse)
async def search_textbooks(request: TextbookSearchRequest):
    """Search independent public book sources and return ranked edition candidates."""
    if request.isbn and not is_valid_isbn(request.isbn):
        raise HTTPException(status_code=422, detail="ISBN 校验位不正确")

    service = TextbookDiscoveryService()
    query = DiscoveryQuery(
        isbn=request.isbn,
        title=request.title,
        author=request.author,
    )
    candidates, source_errors = await service.search(query, request.max_results)
    if not candidates and source_errors and len(source_errors) == len(service.sources):
        raise HTTPException(status_code=502, detail="所有外部书目来源暂时不可用")
    return TextbookSearchResponse(
        candidates=[TextbookSearchCandidate(**candidate.to_dict()) for candidate in candidates],
        source_errors=source_errors,
        message=(
            f"找到 {len(candidates)} 个候选版本"
            if candidates
            else "未找到匹配书籍，请检查书名、作者或 ISBN"
        ),
    )


@router.post(
    "/textbook-catalog-previews",
    response_model=TextbookCatalogPreviewResponse,
)
async def preview_textbook_catalog(request: TextbookCatalogRequest):
    """Fetch a real catalog, normalize hierarchy and optionally enrich descriptions."""
    service = TextbookDiscoveryService()
    candidate = _to_candidate(request.candidate)
    try:
        preview = await service.fetch_catalog(candidate, request.source_url)
    except CatalogNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if request.ai_enrich:
        provider, api_key, model = await get_user_ai_config()
        if not provider or not api_key or not model:
            preview.warnings.append("未配置 AI，已保留真实目录但未生成概述和核心概念")
        else:
            try:
                preview.chapters = await service.enrich_catalog(
                    preview.chapters,
                    candidate,
                    provider,
                    api_key,
                    model,
                )
                if any(chapter.parent_chapter_id for chapter in preview.chapters):
                    preview.warnings.append("为控制耗时，AI 仅补充一级章节概述；所有子目录均按来源原文导入")
            except Exception as exc:
                logger.warning("AI catalog enrichment failed: %s", exc, exc_info=True)
                preview.warnings.append("AI 整理失败，已保留来源目录，可直接导入")

    return TextbookCatalogPreviewResponse(
        candidate=request.candidate,
        chapters=[
            TextbookChapterCreateRequest(**chapter.to_dict())
            for chapter in preview.chapters
        ],
        source_type=preview.source_type,
        source_name=preview.source_name,
        source_url=preview.source_url,
        confidence=preview.confidence,
        warnings=preview.warnings,
        message=f"已识别 {len(preview.chapters)} 个目录节点",
    )


@router.post(
    "/textbook-imports",
    response_model=TextbookInfo,
    status_code=status.HTTP_201_CREATED,
)
async def import_textbook(request: TextbookImportRequest):
    """Persist a user-confirmed edition and catalog in one transaction."""
    candidate = _to_candidate(request.candidate)
    try:
        textbook_id = await import_discovered_textbook(
            db,
            candidate,
            [chapter.model_dump() for chapter in request.chapters],
            source_type=request.source_type,
            source_name=request.source_name,
            source_url=request.source_url,
            confidence=request.confidence,
            subject=request.subject,
            grade=request.grade,
            description=request.description,
            allow_duplicate=request.allow_duplicate,
        )
    except DuplicateTextbookError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BookDiscoveryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Textbook import failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="教材导入失败，数据库未发生变更") from exc
    return await get_textbook(textbook_id)
