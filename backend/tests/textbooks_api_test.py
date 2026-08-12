"""Integration coverage for textbook and chapter management endpoints."""

import json
import types

import pytest

from backend.api import textbooks as textbooks_api


@pytest.fixture
def textbook_payload():
    return {
        "name": "Python 程序设计",
        "isbn": "9787300000000",
        "author": "张老师",
        "publisher": "教育出版社",
        "edition": "第2版",
        "subject": "Python",
        "grade": "大一",
        "cover_image": "/covers/python.png",
        "description": "程序设计基础教材",
    }


@pytest.mark.api
async def test_textbook_crud_and_hierarchical_chapter_workflow(
    test_client,
    test_db,
    monkeypatch,
    textbook_payload,
):
    monkeypatch.setattr(textbooks_api, "db", test_db)

    created = await test_client.post("/api/textbooks", json=textbook_payload)
    assert created.status_code == 200
    textbook_id = created.json()["id"]
    assert created.json()["total_hours"] == 0

    second = await test_client.post(
        "/api/textbooks",
        json={"name": "空教材", "subject": "Python", "grade": "大一"},
    )
    assert second.status_code == 200

    listed = await test_client.get(
        "/api/textbooks",
        params={
            "subject": "Python",
            "grade": "大一",
            "status": "active",
            "page": 1,
            "limit": 10,
        },
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 2

    update = {
        "name": "Python 核心编程",
        "isbn": "9787300000001",
        "author": "李老师",
        "publisher": "科技出版社",
        "edition": "第3版",
        "subject": "软件技术",
        "grade": "大二",
        "cover_image": "/covers/updated.png",
        "description": "更新说明",
        "status": "active",
    }
    updated = await test_client.patch(f"/api/textbooks/{textbook_id}", json=update)
    assert updated.status_code == 200
    assert updated.json()["name"] == "Python 核心编程"
    assert updated.json()["publisher"] == "科技出版社"

    unchanged = await test_client.patch(f"/api/textbooks/{textbook_id}", json={})
    assert unchanged.status_code == 200

    chapters = {
        "chapters": [
            {
                "client_id": "part",
                "chapter_number": "第一篇",
                "chapter_title": "基础篇",
                "content_summary": "课程基础",
                "key_concepts": ["基础"],
                "sort_order": 1,
                "hours_required": 2,
            },
            {
                "client_id": "root",
                "chapter_number": "第1章",
                "chapter_title": "Python 入门",
                "content_summary": "语言基础",
                "key_concepts": ["变量", "类型"],
                "sort_order": 2,
                "hours_required": 4,
            },
            {
                "id": "child-fixed",
                "chapter_number": "1.1",
                "chapter_title": "变量与类型",
                "key_concepts": [],
                "sort_order": 3,
                "hours_required": 2,
                "parent_chapter_id": "root",
            },
            {
                "chapter_number": "附录A",
                "chapter_title": "环境安装",
                "sort_order": 4,
                "hours_required": 3,
            },
        ]
    }
    saved = await test_client.post(
        f"/api/textbooks/{textbook_id}/chapters",
        json=chapters,
    )
    assert saved.status_code == 200
    saved_body = saved.json()
    assert saved_body["main_chapter_count"] == 1
    assert saved_body["total_hours"] == 7
    root = next(item for item in saved_body["chapters"] if item["chapter_number"] == "第1章")
    child = next(item for item in saved_body["chapters"] if item["id"] == "child-fixed")
    assert child["parent_chapter_id"] == root["id"]

    fetched = await test_client.get(f"/api/textbooks/{textbook_id}")
    assert fetched.status_code == 200
    assert len(fetched.json()["chapters"]) == 4

    await test_db.execute(
        "UPDATE textbook_chapters SET key_concepts = ? WHERE id = ?",
        ("not-json", "child-fixed"),
        commit=True,
    )
    malformed = await test_client.get(
        f"/api/textbooks/{textbook_id}/chapters/child-fixed"
    )
    assert malformed.status_code == 200
    assert malformed.json()["key_concepts"] == []

    chapter_update = {
        "chapter_number": "1.2",
        "chapter_title": "数据类型",
        "content_summary": "更新后的概述",
        "key_concepts": ["字符串", "列表"],
        "sort_order": 5,
        "hours_required": 3,
        "parent_chapter_id": root["id"],
    }
    chapter_updated = await test_client.patch(
        f"/api/textbooks/{textbook_id}/chapters/child-fixed",
        json=chapter_update,
    )
    assert chapter_updated.status_code == 200
    assert chapter_updated.json()["key_concepts"] == ["字符串", "列表"]

    assert (
        await test_client.get(f"/api/textbooks/{textbook_id}/chapters/missing")
    ).status_code == 404
    assert (
        await test_client.patch(
            f"/api/textbooks/{textbook_id}/chapters/missing",
            json=chapter_update,
        )
    ).status_code == 404
    assert (
        await test_client.delete(f"/api/textbooks/{textbook_id}/chapters/missing")
    ).status_code == 404

    deleted_chapter = await test_client.delete(
        f"/api/textbooks/{textbook_id}/chapters/child-fixed"
    )
    assert deleted_chapter.status_code == 200

    assert (await test_client.delete(f"/api/textbooks/{textbook_id}")).status_code == 200
    inactive = await test_client.get(f"/api/textbooks/{textbook_id}")
    assert inactive.json()["status"] == "inactive"

    assert (await test_client.get("/api/textbooks/missing")).status_code == 404
    assert (await test_client.patch("/api/textbooks/missing", json={})).status_code == 404
    assert (await test_client.delete("/api/textbooks/missing")).status_code == 404
    assert (
        await test_client.post("/api/textbooks/missing/chapters", json={"chapters": []})
    ).status_code == 404


@pytest.mark.api
async def test_textbook_ai_generation_enrichment_and_keyword_paths(
    test_client,
    test_db,
    monkeypatch,
    textbook_payload,
):
    monkeypatch.setattr(textbooks_api, "db", test_db)
    created = await test_client.post("/api/textbooks", json=textbook_payload)
    textbook_id = created.json()["id"]

    generated_chapters = [
        textbooks_api.TextbookChapterCreateRequest(
            chapter_number="第1章",
            chapter_title="基础",
            content_summary="概述",
            key_concepts=["变量"],
        ),
        textbooks_api.TextbookChapterCreateRequest(
            chapter_number="附录A",
            chapter_title="附录",
        ),
    ]

    async def generate_chapters(request):
        return generated_chapters

    monkeypatch.setattr(
        textbooks_api,
        "TextbookChapterGenerator",
        lambda: types.SimpleNamespace(generate_chapters=generate_chapters),
    )
    generated = await test_client.post(
        f"/api/textbooks/{textbook_id}/generate-chapters",
        json={"textbook_name": "Python 程序设计", "subject": "Python"},
    )
    assert generated.status_code == 200
    assert "1 个大章节" in generated.json()["message"]
    assert (
        await test_client.post(
            "/api/textbooks/missing/generate-chapters",
            json={"textbook_name": "缺失"},
        )
    ).status_code == 404

    chapters = [
        {
            "chapter_number": "第1章",
            "chapter_title": "基础",
            "content_summary": "已有概述",
            "key_concepts": [],
        },
        {
            "chapter_number": "第2章",
            "chapter_title": "进阶",
            "key_concepts": [],
        },
    ]
    responses = [
        json.dumps(
            [
                {
                    "chapter_number": "第一章",
                    "chapter_title": "编程基础",
                    "summary": "AI 概述",
                    "keywords": "变量, 类型；表达式",
                },
                {
                    "content_summary": "进阶概述",
                    "key_concepts": ["函数", "模块", "", 123],
                },
            ],
            ensure_ascii=False,
        ),
        "没有 JSON 的响应",
        '["变量", "类型", "表达式", "函数", "模块", "第六项"]',
        "1. 变量\n2、类型\n要求：忽略",
    ]

    async def provider_generate(*args, **kwargs):
        return responses.pop(0)

    provider = types.SimpleNamespace(generate=provider_generate)
    monkeypatch.setattr(
        textbooks_api.AIProviderFactory,
        "create_provider",
        lambda **kwargs: provider,
    )

    enriched = await test_client.post(
        f"/api/textbooks/{textbook_id}/chapters/ai-enrich",
        json={"chapters": chapters},
    )
    assert enriched.status_code == 200
    assert enriched.json()["chapters"][0]["content_summary"] == "AI 概述"
    assert enriched.json()["chapters"][0]["key_concepts"] == ["变量", "类型", "表达式"]
    assert enriched.json()["chapters"][1]["key_concepts"] == ["函数", "模块"]

    fallback_enrich = await test_client.post(
        f"/api/textbooks/{textbook_id}/chapters/ai-enrich",
        json={"chapters": chapters[:1]},
    )
    assert fallback_enrich.status_code == 200
    assert fallback_enrich.json()["chapters"][0]["content_summary"] == "已有概述"

    assert (
        await test_client.post(
            f"/api/textbooks/{textbook_id}/chapters/ai-enrich",
            json={"chapters": []},
        )
    ).status_code == 400
    assert (
        await test_client.post(
            "/api/textbooks/missing/chapters/ai-enrich",
            json={"chapters": chapters},
        )
    ).status_code == 404

    await test_client.post(
        f"/api/textbooks/{textbook_id}/chapters",
        json={"chapters": chapters[:1]},
    )
    textbook = (await test_client.get(f"/api/textbooks/{textbook_id}")).json()
    chapter_id = textbook["chapters"][0]["id"]

    keywords = await test_client.post(
        f"/api/textbooks/{textbook_id}/chapters/{chapter_id}/extract-keywords",
        params={"chapter_title": "基础", "content_summary": "变量和类型"},
    )
    assert keywords.status_code == 200
    assert keywords.json()["keywords"] == ["变量", "类型", "表达式", "函数", "模块"]

    keyword_fallback = await test_client.post(
        f"/api/textbooks/{textbook_id}/chapters/{chapter_id}/extract-keywords",
        params={"chapter_title": "基础"},
    )
    assert keyword_fallback.status_code == 200
    assert keyword_fallback.json()["keywords"] == ["变量", "类型"]
    assert (
        await test_client.post(
            f"/api/textbooks/{textbook_id}/chapters/missing/extract-keywords",
            params={"chapter_title": "缺失"},
        )
    ).status_code == 404


@pytest.mark.api
async def test_textbook_ai_errors_are_mapped_to_http_500(
    test_client,
    test_db,
    monkeypatch,
    textbook_payload,
):
    monkeypatch.setattr(textbooks_api, "db", test_db)
    textbook_id = (await test_client.post("/api/textbooks", json=textbook_payload)).json()["id"]

    async def fail(*args, **kwargs):
        raise RuntimeError("AI unavailable")

    monkeypatch.setattr(
        textbooks_api,
        "TextbookChapterGenerator",
        lambda: types.SimpleNamespace(generate_chapters=fail),
    )
    generation = await test_client.post(
        f"/api/textbooks/{textbook_id}/generate-chapters",
        json={"textbook_name": "Python"},
    )
    assert generation.status_code == 500

    monkeypatch.setattr(
        textbooks_api.AIProviderFactory,
        "create_provider",
        lambda **kwargs: types.SimpleNamespace(generate=fail),
    )
    enrich = await test_client.post(
        f"/api/textbooks/{textbook_id}/chapters/ai-enrich",
        json={
            "chapters": [
                {"chapter_number": "1", "chapter_title": "基础", "key_concepts": []}
            ]
        },
    )
    assert enrich.status_code == 500

    await test_client.post(
        f"/api/textbooks/{textbook_id}/chapters",
        json={
            "chapters": [
                {"chapter_number": "1", "chapter_title": "基础", "key_concepts": []}
            ]
        },
    )
    chapter_id = (await test_client.get(f"/api/textbooks/{textbook_id}")).json()["chapters"][0]["id"]
    keywords = await test_client.post(
        f"/api/textbooks/{textbook_id}/chapters/{chapter_id}/extract-keywords",
        params={"chapter_title": "基础"},
    )
    assert keywords.status_code == 500
