import importlib

import httpx
import pytest

from backend.services import textbook_discovery as discovery
from backend.services.textbook_importer import import_discovered_textbook


@pytest.mark.unit
def test_isbn_normalization_and_checksum_validation():
    assert discovery.normalize_isbn("ISBN 978-7-302-72012-6") == "9787302720126"
    assert discovery.is_valid_isbn("978-7-302-72012-6")
    assert discovery.is_valid_isbn("0-385-47257-9")
    assert not discovery.is_valid_isbn("978-7-302-72012-7")
    assert not discovery.is_valid_isbn("123")


@pytest.mark.unit
def test_tsinghua_search_fragment_is_parsed_and_ranked():
    fragment = """
    <li><a class="item fs16 lh24" href="book_11414101.html">
      <img src="/upload/smallbookimg/114141-01.jpg"></img>
      <div class="title" title="面向对象与Java程序设计（第4版）">面向对象与Java程序设计（第4版）</div>
      <div class="vicetitle" title="朱福喜 徐冬">朱福喜 徐冬</div>
      <div class="tip">9787302720126</div>
    </a></li>
    """
    candidates = discovery.parse_tsinghua_search_html(
        fragment,
        discovery.DiscoveryQuery(isbn="9787302720126"),
    )

    assert len(candidates) == 1
    assert candidates[0].source_id == "11414101"
    assert candidates[0].isbn_13 == "9787302720126"
    assert candidates[0].match_score == 100
    assert candidates[0].toc_available is True


@pytest.mark.unit
def test_aijiaocai_search_and_project_catalog_are_parsed():
    content = """
    <ul class="bookList"><li class="clearfix">
      <label><a href="/textbook/details?textbook_id=12871864">
        <img src="https://img.aijiaocai.com/cover/9787516541456.png">
      </a></label>
      <div class="bookList-info">
        <a href="/textbook/details?textbook_id=12871864"
           title="Python程序设计案例教程（双色）（含微课）">教材</a>
        <p>远俊红，杨旭，向魏 著；</p>
        <p>ISBN：9787516541456</p>
        <p>出版年月：2026-02</p>
        <p>出版社：航空工业出版社</p>
      </div>
    </li></ul>
    """
    candidates = discovery.parse_aijiaocai_search_html(
        content,
        discovery.DiscoveryQuery(isbn="978-7-5165-4145-6"),
    )

    assert len(candidates) == 1
    assert candidates[0].source_id == "12871864"
    assert candidates[0].authors == ["远俊红", "杨旭", "向魏"]
    assert candidates[0].publisher == "航空工业出版社"
    assert candidates[0].match_score == 100

    chapters = discovery.parse_catalog_lines(
        [
            "基础篇",
            "项目1 开启Python学习之旅",
            "任务1 搭建Python开发环境",
            "一、Python简介",
            "二、Python开发工具",
            "项目2 Python编程基础",
            "任务1 计算订单总价",
            "附录A 常用字符与ASCII代码对照表",
        ],
        confidence=0.94,
    )
    assert [chapter.chapter_number for chapter in chapters] == [
        "项目1",
        "任务1",
        "一、",
        "二、",
        "项目2",
        "任务1",
        "附录A",
    ]
    assert chapters[1].parent_chapter_id == chapters[0].client_id
    assert chapters[2].parent_chapter_id == chapters[1].client_id
    assert chapters[5].parent_chapter_id == chapters[4].client_id
    assert chapters[6].parent_chapter_id is None


@pytest.mark.unit
def test_html_catalog_extraction_and_three_level_hierarchy():
    content = """
    <html><body><h3>图书目录</h3><div class="article">
      <p>目录<p><p>第1章 Java概述<p><p>1.1 开发环境<p>
      <p>1．1．1 安装JDK<p><p>第2章 面向对象<p><p>2.1 类与对象<p>
    </div><div>作者简介</div></body></html>
    """
    lines = discovery.extract_catalog_lines_from_html(content)
    chapters = discovery.parse_catalog_lines(lines, confidence=0.97)

    assert [chapter.chapter_number for chapter in chapters] == [
        "第1章",
        "1.1",
        "1.1.1",
        "第2章",
        "2.1",
    ]
    assert chapters[1].parent_chapter_id == chapters[0].client_id
    assert chapters[2].parent_chapter_id == chapters[1].client_id
    assert chapters[4].parent_chapter_id == chapters[3].client_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_source_failure_does_not_hide_successful_results():
    candidate = discovery.BookCandidate(
        id="working:1",
        source="working",
        source_name="Working Source",
        source_id="1",
        title="Java程序设计",
        match_score=88,
    )

    class WorkingSource:
        key = "working"

        async def search(self, query, max_results):
            return [candidate]

    class FailingSource:
        key = "failing"

        async def search(self, query, max_results):
            raise discovery.SourceUnavailableError("暂时不可用")

    service = discovery.TextbookDiscoveryService([WorkingSource(), FailingSource()])
    results, errors = await service.search(discovery.DiscoveryQuery(title="Java程序设计"), 8)

    assert results == [candidate]
    assert errors == {"failing": "暂时不可用"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_discovered_textbook_import_is_atomic_and_preserves_provenance(test_db):
    candidate = discovery.BookCandidate(
        id="tsinghua_press:11414101",
        source="tsinghua_press",
        source_name="清华大学出版社",
        source_id="11414101",
        source_url="https://www.tup.tsinghua.edu.cn/booksCenter/book_11414101.html",
        title="面向对象与Java程序设计（第4版）",
        authors=["朱福喜", "徐冬"],
        publisher="清华大学出版社",
        isbn_13="9787302720126",
        toc_available=True,
        match_score=100,
    )
    chapters = [
        {
            "client_id": "source-1",
            "chapter_number": "第1章",
            "chapter_title": "Java概述",
            "sort_order": 1,
            "content_origin": "source",
            "confidence": 0.97,
        },
        {
            "client_id": "source-2",
            "chapter_number": "1.1",
            "chapter_title": "开发环境",
            "sort_order": 2,
            "parent_chapter_id": "source-1",
            "content_origin": "ai_enriched",
            "content_summary": "介绍开发环境。",
            "key_concepts": ["JDK"],
            "confidence": 0.97,
        },
    ]

    textbook_id = await import_discovered_textbook(
        test_db,
        candidate,
        chapters,
        source_type="tsinghua_press",
        source_name="清华大学出版社",
        source_url=candidate.source_url,
        confidence=0.97,
        subject="计算机",
        grade="大学",
    )

    textbook = await test_db.fetch_one("SELECT * FROM textbooks WHERE id = ?", (textbook_id,))
    sources = await test_db.fetch_all(
        "SELECT * FROM textbook_sources WHERE textbook_id = ?", (textbook_id,)
    )
    saved_chapters = await test_db.fetch_all(
        "SELECT * FROM textbook_chapters WHERE textbook_id = ? ORDER BY sort_order",
        (textbook_id,),
    )

    assert textbook["isbn"] == "9787302720126"
    assert len(sources) == 1
    assert len(saved_chapters) == 2
    assert saved_chapters[1]["parent_chapter_id"] == saved_chapters[0]["id"]
    assert saved_chapters[1]["source_id"] == sources[0]["id"]
    assert saved_chapters[1]["content_origin"] == "ai_enriched"

    with pytest.raises(discovery.DuplicateTextbookError):
        await import_discovered_textbook(
            test_db,
            candidate,
            chapters,
            source_type="tsinghua_press",
            source_name="清华大学出版社",
            source_url=candidate.source_url,
            confidence=0.97,
        )

    count = await test_db.fetch_one("SELECT COUNT(*) AS count FROM textbooks")
    assert count["count"] == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_discovery_api_search_preview_and_import(test_db, monkeypatch):
    from backend.main import app

    discovery_api = importlib.import_module("backend.api.textbook_discovery")
    textbooks_api = importlib.import_module("backend.api.textbooks")
    candidate = discovery.BookCandidate(
        id="official:book-1",
        source="official",
        source_name="出版社官网",
        source_id="book-1",
        source_url="https://publisher.example/books/book-1",
        title="Java程序设计",
        authors=["张三"],
        publisher="示例出版社",
        isbn_13="9787302720126",
        toc_available=True,
        match_score=100,
    )

    class FakeDiscoveryService:
        sources = [object()]

        async def search(self, query, max_results):
            return [candidate], {}

        async def fetch_catalog(self, selected, source_url=None):
            return discovery.CatalogPreview(
                chapters=[
                    discovery.CatalogChapter(
                        client_id="source-1",
                        chapter_number="第1章",
                        chapter_title="Java概述",
                        sort_order=1,
                        confidence=0.98,
                    )
                ],
                source_type="official",
                source_name="出版社官网",
                source_url=selected.source_url,
                confidence=0.98,
            )

    monkeypatch.setattr(discovery_api, "db", test_db)
    monkeypatch.setattr(textbooks_api, "db", test_db)
    monkeypatch.setattr(discovery_api, "TextbookDiscoveryService", FakeDiscoveryService)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        search_response = await client.post(
            "/api/textbook-searches",
            json={"isbn": "9787302720126"},
        )
        assert search_response.status_code == 200
        selected = search_response.json()["candidates"][0]

        preview_response = await client.post(
            "/api/textbook-catalog-previews",
            json={"candidate": selected, "ai_enrich": False},
        )
        assert preview_response.status_code == 200
        preview = preview_response.json()

        import_response = await client.post(
            "/api/textbook-imports",
            json={
                "candidate": selected,
                "chapters": preview["chapters"],
                "source_type": preview["source_type"],
                "source_name": preview["source_name"],
                "source_url": preview["source_url"],
                "confidence": preview["confidence"],
            },
        )

    assert import_response.status_code == 201
    imported = import_response.json()
    assert imported["name"] == "Java程序设计"
    assert imported["chapters"][0]["chapter_title"] == "Java概述"
    assert imported["sources"][0]["source_name"] == "出版社官网"
