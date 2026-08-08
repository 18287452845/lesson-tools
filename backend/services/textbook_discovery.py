"""External textbook discovery and table-of-contents normalization."""

from __future__ import annotations

import asyncio
import html
import ipaddress
import json
import logging
import re
import socket
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from html.parser import HTMLParser
from typing import Any, Iterable, Optional
from urllib.parse import urljoin, urlparse

import httpx

from ..config import settings
from .ai_provider import generate_with_ai

logger = logging.getLogger(__name__)


class BookDiscoveryError(Exception):
    """Base error for expected textbook discovery failures."""


class SourceUnavailableError(BookDiscoveryError):
    """An external source could not be reached or returned invalid data."""


class CatalogNotFoundError(BookDiscoveryError):
    """No sourced table of contents was found for a selected edition."""


class DuplicateTextbookError(BookDiscoveryError):
    """The selected ISBN is already present in the local library."""


@dataclass(slots=True)
class DiscoveryQuery:
    isbn: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None


@dataclass(slots=True)
class BookCandidate:
    id: str
    source: str
    source_name: str
    source_id: str
    title: str
    source_url: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    edition: Optional[str] = None
    isbn_10: Optional[str] = None
    isbn_13: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    toc_available: bool = False
    match_score: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CatalogChapter:
    client_id: str
    chapter_number: str
    chapter_title: str
    sort_order: int
    parent_chapter_id: Optional[str] = None
    content_summary: str = ""
    key_concepts: list[str] = field(default_factory=list)
    hours_required: Optional[int] = None
    content_origin: str = "source"
    confidence: float = 0.9

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CatalogPreview:
    chapters: list[CatalogChapter]
    source_type: str
    source_name: str
    source_url: Optional[str]
    confidence: float
    warnings: list[str] = field(default_factory=list)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_isbn(value: Optional[str]) -> Optional[str]:
    """Remove display punctuation while retaining an ISBN-10 check digit."""
    if not value:
        return None
    normalized = re.sub(r"[^0-9Xx]", "", value).upper()
    return normalized or None


def is_valid_isbn(value: Optional[str]) -> bool:
    isbn = normalize_isbn(value)
    if not isbn:
        return False
    if len(isbn) == 10:
        if not re.fullmatch(r"\d{9}[\dX]", isbn):
            return False
        total = sum((10 - index) * (10 if char == "X" else int(char)) for index, char in enumerate(isbn))
        return total % 11 == 0
    if len(isbn) == 13 and isbn.isdigit():
        total = sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(isbn[:12]))
        check_digit = (10 - total % 10) % 10
        return check_digit == int(isbn[-1])
    return False


def _normalize_search_text(value: Optional[str]) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE)


def calculate_match_score(candidate: BookCandidate, query: DiscoveryQuery) -> int:
    query_isbn = normalize_isbn(query.isbn)
    if query_isbn and query_isbn in {candidate.isbn_10, candidate.isbn_13}:
        return 100

    score = 0.0
    normalized_title = _normalize_search_text(candidate.title)
    query_title = _normalize_search_text(query.title)
    if normalized_title and query_title:
        score += SequenceMatcher(None, normalized_title, query_title).ratio() * 75

    normalized_author = _normalize_search_text(" ".join(candidate.authors))
    query_author = _normalize_search_text(query.author)
    if normalized_author and query_author:
        score += SequenceMatcher(None, normalized_author, query_author).ratio() * 20

    if candidate.toc_available:
        score += 5
    return min(100, max(0, round(score)))


def _find_isbns(identifiers: Iterable[dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
    isbn_10 = None
    isbn_13 = None
    for item in identifiers:
        value = normalize_isbn(str(item.get("identifier", "")))
        if item.get("type") == "ISBN_10" and value:
            isbn_10 = value
        elif item.get("type") == "ISBN_13" and value:
            isbn_13 = value
    return isbn_10, isbn_13


class GoogleBooksSource:
    key = "google_books"
    name = "Google Books"

    async def search(self, query: DiscoveryQuery, max_results: int) -> list[BookCandidate]:
        terms: list[str] = []
        normalized_isbn = normalize_isbn(query.isbn)
        if normalized_isbn:
            terms.append(f"isbn:{normalized_isbn}")
        else:
            if query.title:
                terms.append(f"intitle:{query.title}")
            if query.author:
                terms.append(f"inauthor:{query.author}")

        params: dict[str, Any] = {
            "q": " ".join(terms),
            "maxResults": min(max_results, 40),
            "printType": "books",
            "projection": "full",
        }
        if settings.google_books_api_key:
            params["key"] = settings.google_books_api_key

        try:
            async with httpx.AsyncClient(
                timeout=settings.book_search_timeout,
                headers={"User-Agent": settings.book_search_user_agent},
            ) as client:
                response = await client.get(
                    f"{settings.google_books_base_url.rstrip('/')}/volumes",
                    params=params,
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SourceUnavailableError("Google Books 暂时不可用") from exc

        candidates: list[BookCandidate] = []
        for item in payload.get("items", []):
            info = item.get("volumeInfo") or {}
            title = str(info.get("title") or "").strip()
            if not title:
                continue
            isbn_10, isbn_13 = _find_isbns(info.get("industryIdentifiers") or [])
            candidate = BookCandidate(
                id=f"{self.key}:{item.get('id')}",
                source=self.key,
                source_name=self.name,
                source_id=str(item.get("id") or ""),
                source_url=info.get("infoLink") or item.get("selfLink"),
                title=title,
                authors=[str(author) for author in info.get("authors") or []],
                publisher=info.get("publisher"),
                published_date=info.get("publishedDate"),
                isbn_10=isbn_10,
                isbn_13=isbn_13,
                description=info.get("description"),
                cover_image=(info.get("imageLinks") or {}).get("thumbnail"),
                toc_available=False,
            )
            candidate.match_score = calculate_match_score(candidate, query)
            candidates.append(candidate)
        return candidates


class OpenLibrarySource:
    key = "open_library"
    name = "Open Library"

    async def search(self, query: DiscoveryQuery, max_results: int) -> list[BookCandidate]:
        params: dict[str, Any] = {
            "limit": min(max_results, 20),
            "fields": (
                "key,title,author_name,publisher,first_publish_year,publish_date,"
                "isbn,edition_key,cover_i"
            ),
        }
        normalized_isbn = normalize_isbn(query.isbn)
        if normalized_isbn:
            params["isbn"] = normalized_isbn
        else:
            if query.title:
                params["title"] = query.title
            if query.author:
                params["author"] = query.author

        try:
            async with httpx.AsyncClient(
                timeout=settings.book_search_timeout,
                headers={"User-Agent": settings.book_search_user_agent},
            ) as client:
                response = await client.get(
                    f"{settings.open_library_base_url.rstrip('/')}/search.json",
                    params=params,
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SourceUnavailableError("Open Library 暂时不可用") from exc

        candidates: list[BookCandidate] = []
        for item in payload.get("docs", []):
            title = str(item.get("title") or "").strip()
            edition_keys = item.get("edition_key") or []
            source_id = str(edition_keys[0] if edition_keys else item.get("key") or "").split("/")[-1]
            if not title or not source_id:
                continue

            isbns = [normalize_isbn(str(value)) for value in item.get("isbn") or []]
            isbn_10 = next((value for value in isbns if value and len(value) == 10), None)
            isbn_13 = next((value for value in isbns if value and len(value) == 13), None)
            candidate = BookCandidate(
                id=f"{self.key}:{source_id}",
                source=self.key,
                source_name=self.name,
                source_id=source_id,
                source_url=f"{settings.open_library_base_url.rstrip('/')}/books/{source_id}",
                title=title,
                authors=[str(author) for author in item.get("author_name") or []],
                publisher=next(iter(item.get("publisher") or []), None),
                published_date=str(
                    next(iter(item.get("publish_date") or []), item.get("first_publish_year") or "")
                ) or None,
                isbn_10=isbn_10,
                isbn_13=isbn_13,
                cover_image=(
                    f"https://covers.openlibrary.org/b/id/{item['cover_i']}-M.jpg"
                    if item.get("cover_i")
                    else None
                ),
                toc_available=False,
            )
            candidate.match_score = calculate_match_score(candidate, query)
            candidates.append(candidate)
        return candidates

    async def fetch_catalog(self, candidate: BookCandidate) -> CatalogPreview:
        base_url = settings.open_library_base_url.rstrip("/")
        isbn = candidate.isbn_13 or candidate.isbn_10
        detail_url = f"{base_url}/isbn/{isbn}.json" if isbn else f"{base_url}/books/{candidate.source_id}.json"
        try:
            async with httpx.AsyncClient(
                timeout=settings.book_search_timeout,
                headers={"User-Agent": settings.book_search_user_agent},
                follow_redirects=True,
            ) as client:
                response = await client.get(detail_url)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise CatalogNotFoundError("Open Library 没有可用目录") from exc

        raw_toc = payload.get("table_of_contents") or []
        lines: list[str] = []
        for item in raw_toc:
            if isinstance(item, str):
                lines.append(item)
            elif isinstance(item, dict):
                title = item.get("title") or item.get("label")
                if title:
                    lines.append(str(title))
        chapters = parse_catalog_lines(lines, confidence=0.82)
        if not chapters:
            raise CatalogNotFoundError("Open Library 记录存在，但未收录目录")
        return CatalogPreview(
            chapters=chapters,
            source_type=self.key,
            source_name=self.name,
            source_url=candidate.source_url or detail_url,
            confidence=0.82,
        )


def parse_tsinghua_search_html(fragment: str, query: DiscoveryQuery) -> list[BookCandidate]:
    """Parse the official Tsinghua University Press search result fragment."""
    candidates: list[BookCandidate] = []
    for block in re.findall(r"<a\b[^>]*class=\"item[^\"]*\"[^>]*>.*?</a>", fragment, re.I | re.S):
        href_match = re.search(r"href=\"([^\"]+)\"", block, re.I)
        id_match = re.search(r"book_(\d+)\.html", href_match.group(1) if href_match else "")
        title_match = re.search(r'class=\"title\"\s+title=\"([^\"]+)\"', block, re.I)
        author_match = re.search(r'class=\"vicetitle\"\s+title=\"([^\"]*)\"', block, re.I)
        tip_values = re.findall(r'class=\"tip\"[^>]*>\s*([^<]+)', block, re.I)
        isbn = normalize_isbn(tip_values[0] if tip_values else None)
        image_match = re.search(r'<img[^>]+src=\"([^\"]+)\"', block, re.I)
        if not id_match or not title_match:
            continue
        source_id = id_match.group(1)
        source_url = urljoin(
            f"{settings.tsinghua_press_base_url.rstrip('/')}/booksCenter/",
            href_match.group(1),
        )
        candidate = BookCandidate(
            id=f"tsinghua_press:{source_id}",
            source="tsinghua_press",
            source_name="清华大学出版社",
            source_id=source_id,
            source_url=source_url,
            title=html.unescape(title_match.group(1)).strip(),
            authors=[html.unescape(author_match.group(1)).strip()] if author_match and author_match.group(1).strip() else [],
            publisher="清华大学出版社",
            isbn_10=isbn if isbn and len(isbn) == 10 else None,
            isbn_13=isbn if isbn and len(isbn) == 13 else None,
            cover_image=(
                urljoin(settings.tsinghua_press_base_url, image_match.group(1))
                if image_match
                else None
            ),
            toc_available=True,
        )
        candidate.match_score = calculate_match_score(candidate, query)
        candidates.append(candidate)
    return candidates


class TsinghuaPressSource:
    key = "tsinghua_press"
    name = "清华大学出版社"

    async def search(self, query: DiscoveryQuery, max_results: int) -> list[BookCandidate]:
        keyword = normalize_isbn(query.isbn) or query.title or query.author or ""
        base_url = settings.tsinghua_press_base_url.rstrip("/")
        try:
            async with httpx.AsyncClient(
                timeout=settings.book_search_timeout,
                headers={"User-Agent": settings.book_search_user_agent},
            ) as client:
                page = await client.get(f"{base_url}/booksCenter/booklist")
                page.raise_for_status()
                token_match = re.search(
                    r'name="__RequestVerificationToken"\s+type="hidden"\s+value="([^"]+)"',
                    page.text,
                )
                if not token_match:
                    raise SourceUnavailableError("清华大学出版社搜索令牌获取失败")
                response = await client.post(
                    f"{base_url}/booksCenter/booklist?handler=SearchData",
                    headers={"RequestVerificationToken": token_match.group(1)},
                    data={"keyword": keyword, "pageIndex": 0, "pageSize": min(max_results, 15)},
                )
                response.raise_for_status()
                payload = response.json()
        except SourceUnavailableError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise SourceUnavailableError("清华大学出版社暂时不可用") from exc

        return parse_tsinghua_search_html(payload.get("tbody") or "", query)

    async def fetch_catalog(self, candidate: BookCandidate) -> CatalogPreview:
        base_url = settings.tsinghua_press_base_url.rstrip("/")
        catalog_url = f"{base_url}/booksCenter/bookcatalog?id={candidate.source_id}"
        try:
            async with httpx.AsyncClient(
                timeout=settings.book_search_timeout,
                headers={"User-Agent": settings.book_search_user_agent},
            ) as client:
                response = await client.get(catalog_url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CatalogNotFoundError("清华大学出版社目录页暂时不可用") from exc

        lines = extract_catalog_lines_from_html(response.text)
        chapters = parse_catalog_lines(lines, confidence=0.97)
        if not chapters:
            raise CatalogNotFoundError("出版社页面未识别到有效目录")
        return CatalogPreview(
            chapters=chapters,
            source_type=self.key,
            source_name=self.name,
            source_url=catalog_url,
            confidence=0.97,
        )


class _HTMLTextExtractor(HTMLParser):
    BLOCK_TAGS = {
        "p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "tr", "td", "section"
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.ignored_depth += 1
        elif not self.ignored_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.ignored_depth:
            self.ignored_depth -= 1
        elif not self.ignored_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth:
            self.parts.append(data)

    def lines(self) -> list[str]:
        return [re.sub(r"\s+", " ", line).strip() for line in "".join(self.parts).splitlines() if line.strip()]


def _looks_like_catalog_entry(line: str) -> bool:
    normalized = unicodedata.normalize("NFKC", line)
    return bool(
        re.match(r"^第\s*[一二三四五六七八九十百零〇\d]+\s*(?:篇|章|单元|部分)", normalized)
        or re.match(r"^\d+(?:\.\d+){0,2}\s*\S+", normalized)
        or re.match(r"^(?:Chapter|Unit|Part)\s+[\w一二三四五六七八九十]+", normalized, re.I)
    )


def extract_catalog_lines_from_html(content: str) -> list[str]:
    parser = _HTMLTextExtractor()
    parser.feed(content)
    lines = parser.lines()

    best: list[str] = []
    for index, line in enumerate(lines):
        if line not in {"目录", "图书目录", "Table of Contents", "CONTENTS"} and "图书目录" not in line:
            continue
        section: list[str] = []
        for candidate in lines[index + 1 :]:
            if candidate in {"作者简介", "内容简介", "前言序言", "资源下载", "版权信息", "同系列产品"}:
                break
            if _looks_like_catalog_entry(candidate):
                section.append(candidate)
        if len(section) > len(best):
            best = section
    if best:
        return best
    return [line for line in lines if _looks_like_catalog_entry(line)]


def parse_catalog_lines(lines: Iterable[str], confidence: float = 0.9) -> list[CatalogChapter]:
    """Normalize common Chinese and English catalog numbering into a 3-level tree."""
    chapters: list[CatalogChapter] = []
    last_at_level: dict[int, str] = {}
    chinese_pattern = re.compile(
        r"^(第\s*[一二三四五六七八九十百零〇\d]+\s*(?:篇|章|单元|部分))\s*(.*)$"
    )
    numeric_pattern = re.compile(r"^(\d+(?:\.\d+){0,2})\s*[、.．-]?\s*(.+)$")
    english_pattern = re.compile(r"^((?:Chapter|Unit|Part)\s+[\w一二三四五六七八九十]+)\s*[:：.-]?\s*(.*)$", re.I)

    for raw_line in lines:
        line = unicodedata.normalize("NFKC", html.unescape(str(raw_line)))
        line = re.sub(r"[\u00a0\t]+", " ", line).strip()
        line = re.sub(r"[.·…]{3,}\s*\d*\s*$", "", line).strip()
        if not line or line.casefold() in {"目录", "contents", "table of contents"}:
            continue

        level = 1
        chapter_number = ""
        chapter_title = ""
        chinese_match = chinese_pattern.match(line)
        numeric_match = numeric_pattern.match(line)
        english_match = english_pattern.match(line)
        if chinese_match:
            chapter_number = re.sub(r"\s+", "", chinese_match.group(1))
            chapter_title = chinese_match.group(2).strip() or chapter_number
            level = 1
        elif numeric_match:
            chapter_number = numeric_match.group(1)
            chapter_title = numeric_match.group(2).strip()
            level = min(3, chapter_number.count(".") + 1)
        elif english_match:
            chapter_number = english_match.group(1).strip()
            chapter_title = english_match.group(2).strip() or chapter_number
            level = 1
        else:
            continue

        client_id = f"source-{len(chapters) + 1}"
        parent_id = last_at_level.get(level - 1) if level > 1 else None
        if level > 1 and not parent_id:
            level = 1
        chapter = CatalogChapter(
            client_id=client_id,
            chapter_number=chapter_number,
            chapter_title=chapter_title[:200],
            sort_order=len(chapters) + 1,
            parent_chapter_id=parent_id,
            confidence=confidence,
        )
        chapters.append(chapter)
        last_at_level[level] = client_id
        for stale_level in range(level + 1, 4):
            last_at_level.pop(stale_level, None)
    return chapters


async def _resolve_public_host(hostname: str) -> None:
    try:
        records = await asyncio.to_thread(socket.getaddrinfo, hostname, None)
    except socket.gaierror as exc:
        raise CatalogNotFoundError("目录网址无法解析") from exc
    for record in records:
        address = ipaddress.ip_address(record[4][0])
        if not address.is_global:
            raise CatalogNotFoundError("目录网址不能指向本机或内网地址")


async def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise CatalogNotFoundError("请提供公开的 HTTP/HTTPS 目录网址")
    await _resolve_public_host(parsed.hostname)


class PublicCatalogPageSource:
    key = "publisher_page"
    name = "出版社目录页"
    max_bytes = 2 * 1024 * 1024

    async def fetch_catalog(self, url: str) -> CatalogPreview:
        current_url = url
        try:
            async with httpx.AsyncClient(
                timeout=settings.book_search_timeout,
                headers={"User-Agent": settings.book_search_user_agent},
                follow_redirects=False,
            ) as client:
                for _ in range(4):
                    await _validate_public_url(current_url)
                    response = await client.get(current_url)
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise CatalogNotFoundError("目录网址重定向无效")
                        current_url = urljoin(current_url, location)
                        continue
                    response.raise_for_status()
                    if len(response.content) > self.max_bytes:
                        raise CatalogNotFoundError("目录页面过大，无法安全解析")
                    content_type = response.headers.get("content-type", "")
                    if "html" not in content_type.lower():
                        raise CatalogNotFoundError("当前仅支持 HTML 目录页面")
                    lines = extract_catalog_lines_from_html(response.text)
                    chapters = parse_catalog_lines(lines, confidence=0.85)
                    if not chapters:
                        raise CatalogNotFoundError("页面中未识别到编号目录")
                    return CatalogPreview(
                        chapters=chapters,
                        source_type=self.key,
                        source_name=self.name,
                        source_url=current_url,
                        confidence=0.85,
                    )
        except CatalogNotFoundError:
            raise
        except httpx.HTTPError as exc:
            raise CatalogNotFoundError("目录页面暂时无法访问") from exc
        raise CatalogNotFoundError("目录网址重定向次数过多")


class TextbookDiscoveryService:
    """Orchestrate independent book sources and normalize their results."""

    def __init__(self, sources: Optional[list[Any]] = None):
        self.sources = sources or [
            TsinghuaPressSource(),
            GoogleBooksSource(),
            OpenLibrarySource(),
        ]

    async def search(
        self,
        query: DiscoveryQuery,
        max_results: Optional[int] = None,
    ) -> tuple[list[BookCandidate], dict[str, str]]:
        limit = max_results or settings.book_search_max_results
        outcomes = await asyncio.gather(
            *(source.search(query, limit) for source in self.sources),
            return_exceptions=True,
        )
        candidates: list[BookCandidate] = []
        errors: dict[str, str] = {}
        for source, outcome in zip(self.sources, outcomes):
            if isinstance(outcome, Exception):
                logger.warning("Book source %s failed: %s", source.key, outcome)
                errors[source.key] = str(outcome) or "来源不可用"
                continue
            candidates.extend(outcome)

        unique: dict[str, BookCandidate] = {}
        for candidate in candidates:
            current = unique.get(candidate.id)
            if current is None or candidate.match_score > current.match_score:
                unique[candidate.id] = candidate
        ranked = sorted(
            unique.values(),
            key=lambda item: (item.match_score, item.toc_available),
            reverse=True,
        )
        return ranked[:limit], errors

    async def fetch_catalog(
        self,
        candidate: BookCandidate,
        source_url: Optional[str] = None,
    ) -> CatalogPreview:
        if source_url:
            return await PublicCatalogPageSource().fetch_catalog(source_url)
        if candidate.source == TsinghuaPressSource.key:
            return await TsinghuaPressSource().fetch_catalog(candidate)
        if candidate.source == OpenLibrarySource.key:
            return await OpenLibrarySource().fetch_catalog(candidate)
        if candidate.isbn_13 or candidate.isbn_10:
            try:
                return await OpenLibrarySource().fetch_catalog(candidate)
            except CatalogNotFoundError:
                pass
        raise CatalogNotFoundError(
            "未找到可验证的真实目录；可填写出版社目录页网址后重试"
        )

    async def enrich_catalog(
        self,
        chapters: list[CatalogChapter],
        candidate: BookCandidate,
        provider: str,
        api_key: str,
        model: str,
    ) -> list[CatalogChapter]:
        """Add summaries and keywords while preserving sourced numbering and titles."""
        # A full publisher catalog may contain hundreds of sections. Enriching
        # only top-level chapters keeps latency and cost bounded while preserving
        # every sourced subsection for import.
        targets = [chapter for chapter in chapters if not chapter.parent_chapter_id]
        if not targets:
            targets = chapters[:25]
        for start in range(0, len(targets), 25):
            batch = targets[start : start + 25]
            source_items = [
                {
                    "client_id": chapter.client_id,
                    "chapter_number": chapter.chapter_number,
                    "chapter_title": chapter.chapter_title,
                }
                for chapter in batch
            ]
            prompt = f"""你是教材目录整理助手。教材：{candidate.title}；作者：{'、'.join(candidate.authors)}。
以下目录编号和标题来自外部来源，绝对不能修改、增删或重新排序。请仅为每项补充简短内容概述和2-5个核心概念。
只返回 JSON 对象，格式为 {{"items": [{{"client_id": "...", "content_summary": "...", "key_concepts": ["..."]}}]}}：
{json.dumps(source_items, ensure_ascii=False)}"""
            response = await generate_with_ai(
                prompt=prompt,
                system_prompt="只整理用户提供的真实目录，不推测或新增章节。",
                provider=provider,
                api_key=api_key,
                model=model,
                response_format={"type": "json_object"} if provider == "deepseek" else None,
            )
            items = _parse_ai_enrichment(response)
            by_id = {
                str(item.get("client_id")): item
                for item in items
                if isinstance(item, dict) and item.get("client_id")
            }
            for chapter in batch:
                enrichment = by_id.get(chapter.client_id)
                if not enrichment:
                    continue
                summary = enrichment.get("content_summary")
                concepts = enrichment.get("key_concepts")
                if isinstance(summary, str):
                    chapter.content_summary = summary.strip()[:500]
                if isinstance(concepts, list):
                    chapter.key_concepts = [
                        str(value).strip()[:50]
                        for value in concepts
                        if str(value).strip()
                    ][:5]
                chapter.content_origin = "ai_enriched"
        return chapters


def _parse_ai_enrichment(content: str) -> list[dict[str, Any]]:
    content = content.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", content, re.I)
    if fenced:
        content = fenced.group(1).strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        array_match = re.search(r"\[[\s\S]*\]", content)
        if not array_match:
            raise BookDiscoveryError("AI 目录整理结果格式无效")
        parsed = json.loads(array_match.group(0))
    if isinstance(parsed, dict):
        parsed = parsed.get("chapters") or parsed.get("items") or []
    if not isinstance(parsed, list):
        raise BookDiscoveryError("AI 目录整理结果不是数组")
    return parsed
