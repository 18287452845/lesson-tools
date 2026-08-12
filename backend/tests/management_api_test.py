"""API coverage for lesson plans, documents, templates, and settings."""

import pathlib
import types

import pytest

from backend.api import documents as documents_api
from backend.api import lesson_plans as lesson_plans_api
from backend.api import settings as settings_api
from backend.api import templates as templates_api
from backend.services.builtin_template import BUILTIN_TEMPLATE_ID


def _lesson_plan(plan_id="plan-api"):
    return {
        "id": plan_id,
        "template_id": BUILTIN_TEMPLATE_ID,
        "title": "API 教案",
        "subject": "Python",
        "grade": "大一",
        "topic": "列表操作",
        "input_data": "{}",
        "generated_content": "{}",
        "status": "draft",
        "created_at": "2026-08-12T00:00:00",
        "updated_at": "2026-08-12T00:00:00",
    }


@pytest.fixture
def fake_lesson_plan_service(tmp_path):
    calls = []

    async def list_lesson_plans(filters, page, limit):
        calls.append(("list", filters, page, limit))
        return [_lesson_plan()], 1

    async def get_lesson_plan(plan_id):
        calls.append(("get", plan_id))
        return None if plan_id == "missing" else _lesson_plan(plan_id)

    async def update_field(lesson_plan_id, field_name, field_value):
        calls.append(("update", lesson_plan_id, field_name, field_value))
        if lesson_plan_id == "explode":
            raise ValueError("update failed")
        return _lesson_plan(lesson_plan_id)

    async def regenerate_field(lesson_plan_id, field_name, additional_instruction=None):
        calls.append(("regenerate", lesson_plan_id, field_name, additional_instruction))
        if lesson_plan_id == "explode":
            raise ValueError("regenerate failed")
        return {"text": "重新生成内容"}

    async def publish_lesson_plan(plan_id):
        calls.append(("publish", plan_id))
        if plan_id == "explode":
            raise ValueError("publish failed")
        return str(tmp_path / f"{plan_id}.docx"), f"/download/{plan_id}.docx"

    async def batch_publish(lesson_plan_ids, group_by_document):
        calls.append(("batch_publish", lesson_plan_ids, group_by_document))
        if lesson_plan_ids == ["missing"]:
            return str(tmp_path / "missing.zip")
        path = tmp_path / "plans.zip"
        path.write_bytes(b"PK test zip")
        return str(path)

    async def delete_lesson_plan(plan_id):
        calls.append(("delete", plan_id))
        if plan_id in {"bad", "explode"}:
            raise ValueError("delete failed")

    return types.SimpleNamespace(
        calls=calls,
        list_lesson_plans=list_lesson_plans,
        get_lesson_plan=get_lesson_plan,
        update_field=update_field,
        regenerate_field=regenerate_field,
        publish_lesson_plan=publish_lesson_plan,
        batch_publish=batch_publish,
        delete_lesson_plan=delete_lesson_plan,
    )


@pytest.mark.api
async def test_lesson_plan_management_api_success_paths(
    test_client,
    fake_lesson_plan_service,
    monkeypatch,
):
    monkeypatch.setattr(
        lesson_plans_api,
        "lesson_plan_service",
        fake_lesson_plan_service,
    )

    listed = await test_client.get(
        "/api/lesson-plans",
        params={
            "status": "draft",
            "template_id": BUILTIN_TEMPLATE_ID,
            "subject": "Python",
            "grade": "大一",
            "search": "列表",
            "page": 2,
            "limit": 5,
        },
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert fake_lesson_plan_service.calls[0][1] == {
        "status": "draft",
        "template_id": BUILTIN_TEMPLATE_ID,
        "subject": "Python",
        "grade": "大一",
        "search": "列表",
    }

    assert (await test_client.get("/api/lesson-plans/plan-api")).status_code == 200

    updated = await test_client.put(
        "/api/lesson-plans/plan-api/field",
        json={"field_name": "key_points", "field_value": ["重点"]},
    )
    assert updated.status_code == 200

    regenerated = await test_client.post(
        "/api/lesson-plans/plan-api/regenerate-field",
        json={"field_name": "key_points", "additional_instruction": "更具体"},
    )
    assert regenerated.status_code == 200
    assert regenerated.json()["field_value"] == {"text": "重新生成内容"}

    published = await test_client.post("/api/lesson-plans/plan-api/publish")
    assert published.status_code == 200
    assert published.json()["lesson_plan_id"] == "plan-api"

    archive = await test_client.post(
        "/api/lesson-plans/batch-publish",
        json={"lesson_plan_ids": ["plan-api"], "group_by_document": False},
    )
    assert archive.status_code == 200
    assert archive.headers["content-type"] == "application/zip"

    deleted = await test_client.delete("/api/lesson-plans/plan-api")
    assert deleted.status_code == 200
    assert deleted.json()["id"] == "plan-api"

    batch_deleted = await test_client.post(
        "/api/lesson-plans/batch-delete",
        json={"lesson_plan_ids": ["plan-api", "bad"]},
    )
    assert batch_deleted.status_code == 200
    assert batch_deleted.json()["deleted_count"] == 1
    assert batch_deleted.json()["failed_ids"] == ["bad"]


@pytest.mark.api
async def test_lesson_plan_management_api_error_paths(
    test_client,
    fake_lesson_plan_service,
    monkeypatch,
):
    monkeypatch.setattr(
        lesson_plans_api,
        "lesson_plan_service",
        fake_lesson_plan_service,
    )

    assert (await test_client.get("/api/lesson-plans/missing")).status_code == 404
    assert (
        await test_client.put(
            "/api/lesson-plans/explode/field",
            json={"field_name": "key_points", "field_value": "x"},
        )
    ).status_code == 500
    assert (
        await test_client.post(
            "/api/lesson-plans/explode/regenerate-field",
            json={"field_name": "key_points"},
        )
    ).status_code == 500
    assert (
        await test_client.post("/api/lesson-plans/explode/publish")
    ).status_code == 500
    assert (
        await test_client.post(
            "/api/lesson-plans/batch-publish",
            json={"lesson_plan_ids": ["missing"]},
        )
    ).status_code == 404
    assert (
        await test_client.delete("/api/lesson-plans/explode")
    ).status_code == 500

    async def broken_list(**kwargs):
        raise RuntimeError("list failed")

    fake_lesson_plan_service.list_lesson_plans = broken_list
    response = await test_client.get("/api/lesson-plans")
    assert response.status_code == 500
    assert response.json()["detail"] == "list failed"


@pytest.mark.api
async def test_document_download_preview_and_missing_files(
    test_client,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(documents_api.settings, "output_dir", tmp_path)
    document = tmp_path / "lesson.docx"
    document.write_bytes(b"document")

    download = await test_client.get("/api/documents/download/lesson.docx")
    preview = await test_client.get("/api/documents/preview/lesson.docx")
    assert download.status_code == 200
    assert preview.status_code == 200
    assert download.content == b"document"
    assert (await test_client.get("/api/documents/download/missing.docx")).status_code == 404
    assert (await test_client.get("/api/documents/preview/missing.docx")).status_code == 404


@pytest.mark.api
async def test_template_read_validation_and_download_api(
    test_client,
    test_db,
    tmp_path,
    monkeypatch,
):
    template_path = tmp_path / "builtin.docx"
    template_path.write_bytes(b"template")
    await test_db.execute(
        """
        INSERT INTO templates
            (id, name, description, file_path, fields_config, use_count)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            BUILTIN_TEMPLATE_ID,
            "云林模板",
            "固定模板",
            str(template_path),
            '[{"name":"topic","display_name":"课题"}]',
            3,
        ),
        commit=True,
    )
    monkeypatch.setattr(templates_api, "db", test_db)
    monkeypatch.setattr(templates_api, "get_builtin_template_path", lambda: template_path)
    monkeypatch.setattr(
        templates_api,
        "validate_builtin_template",
        lambda: {"is_valid": True, "errors": []},
    )
    monkeypatch.setattr(
        templates_api,
        "validate_all_builtin_templates",
        lambda: [{"name": "lesson", "is_valid": True}],
    )
    registration_calls = []

    async def ensure_registered():
        registration_calls.append(True)

    monkeypatch.setattr(templates_api, "ensure_builtin_template_registered", ensure_registered)

    listed = await test_client.get("/api/templates")
    assert listed.status_code == 200
    assert listed.json()[0]["fields_config"][0]["name"] == "topic"
    assert (await test_client.get(f"/api/templates/{BUILTIN_TEMPLATE_ID}")).status_code == 200
    assert (await test_client.get("/api/templates/not-allowed")).status_code == 404
    assert (await test_client.get("/api/templates/validation")).json()["is_valid"] is True
    assert len((await test_client.get("/api/templates/validation/all")).json()) == 1
    assert (await test_client.post("/api/templates/validation")).status_code == 200
    assert registration_calls == [True]
    assert (
        await test_client.get(f"/api/templates/{BUILTIN_TEMPLATE_ID}/download")
    ).content == b"template"
    assert (await test_client.get("/api/templates/other/download")).status_code == 404

    template_path.unlink()
    assert (
        await test_client.get(f"/api/templates/{BUILTIN_TEMPLATE_ID}/download")
    ).status_code == 503


@pytest.mark.api
async def test_settings_and_application_info_api(
    test_client,
    test_db,
    monkeypatch,
):
    monkeypatch.setattr(settings_api, "db", test_db)
    monkeypatch.setattr(settings_api.settings, "ai_provider", "deepseek")
    monkeypatch.setattr(settings_api.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(settings_api.settings, "deepseek_model", "deepseek-chat")
    monkeypatch.setattr(settings_api.settings, "ai_model", None)

    current = await test_client.get("/api/settings/ai-provider")
    assert current.status_code == 200
    assert current.json()["configured"] is True

    invalid = await test_client.post(
        "/api/settings/ai-provider",
        json={"provider": "unknown", "api_key": "key"},
    )
    assert invalid.status_code == 400

    deepseek = await test_client.post(
        "/api/settings/ai-provider",
        json={"provider": "deepseek", "api_key": "new-key", "model": "deepseek-chat"},
    )
    assert deepseek.status_code == 200
    assert deepseek.json()["model"] == "deepseek-v4-flash"

    anthropic = await test_client.post(
        "/api/settings/ai-provider",
        json={
            "provider": "anthropic",
            "api_key": "anthropic-key",
            "model": "claude-test",
        },
    )
    assert anthropic.status_code == 200
    assert settings_api.settings.anthropic_api_key == "anthropic-key"

    providers = await test_client.get("/api/settings/ai-providers")
    app_info = await test_client.get("/api/settings/app-info")
    root = await test_client.get("/")
    health = await test_client.get("/health")
    assert len(providers.json()["providers"]) == 2
    assert app_info.json()["name"] == "智能教案助手"
    assert root.json()["version"] == "1.1.0"
    assert health.json() == {"status": "healthy"}
