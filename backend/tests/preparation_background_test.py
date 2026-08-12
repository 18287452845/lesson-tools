from pathlib import Path

import pytest

from backend.api import preparation as api
from backend.models.schemas import GeneratedContent, PreparationGenerateRequest
from backend.services.background_runner import BackgroundTaskManager, BackgroundTaskRunner


def _request():
    return PreparationGenerateRequest(
        subject="Python",
        grade="大学",
        topic="变量",
        duration="2课时",
        artifact_types=["lesson_plan", "handout", "presentation", "handout"],
        textbook_name="Python教材",
        online_resources="网络课程",
        class_ids=["class-1"],
        generate_reflection=True,
    )


@pytest.mark.asyncio
async def test_preparation_capabilities_generation_and_helpers(test_db, tmp_path, monkeypatch):
    monkeypatch.setattr(api, "db", test_db)
    await test_db.execute(
        "INSERT INTO templates (id,name,file_path) VALUES ('yunlin-standard','云林模板','builtin.docx')",
        commit=True,
    )
    await test_db.execute(
        "INSERT INTO classes (id,name) VALUES ('class-1','一班')", commit=True
    )
    monkeypatch.setattr(
        api, "require_valid_builtin_template", lambda *args: {"is_valid": True, "sha256": "hash"}
    )
    monkeypatch.setattr(api, "get_builtin_template_path", lambda: tmp_path / "template.docx")

    content = GeneratedContent(key_points="重点", online_resources="AI资源")

    class FakeGenerator:
        async def generate_lesson_plan(self, request, configs, reflection):
            assert reflection is True
            return content

    async def get_generator():
        return FakeGenerator()

    monkeypatch.setattr(api, "get_ai_generator", get_generator)

    class FakeDocumentRenderer:
        def render_lesson_plan(self, template, render_data):
            assert render_data["class_name"] == "一班"
            assert render_data["references"] == "《Python教材》\n网络课程"
            path = tmp_path / "lesson.docx"
            path.write_bytes(b"lesson")
            return str(path)

    class FakePreparationRenderer:
        def render_handout(self, *args):
            path = tmp_path / "handout.docx"
            path.write_bytes(b"handout")
            return str(path)

        def render_presentation(self, *args):
            path = tmp_path / "presentation.pptx"
            path.write_bytes(b"ppt")
            return str(path)

    monkeypatch.setattr(api, "DocumentRenderer", FakeDocumentRenderer)
    monkeypatch.setattr(api, "PreparationRenderer", FakePreparationRenderer)

    capabilities = await api.get_preparation_capabilities()
    assert capabilities["template"]["is_valid"] is True
    assert len(capabilities["artifacts"]) == 3
    assert await api._resolve_class_names([]) == []
    assert await api._resolve_class_names(["class-1"]) == ["一班"]
    render = api._build_lesson_render_data(
        {"topic": "变量", "textbook_name": "教材"}, {"online_resources": "资源"}, []
    )
    assert render["references"] == "《教材》\n资源"

    result = await api.generate_preparation(_request())
    assert [item.type for item in result.artifacts] == ["lesson_plan", "handout", "presentation"]
    row = await test_db.fetch_one("SELECT * FROM lesson_plans WHERE id=?", (result.id,))
    assert row["status"] == "completed"


@pytest.mark.asyncio
async def test_preparation_error_mapping_and_cleanup(test_db, tmp_path, monkeypatch):
    monkeypatch.setattr(api, "db", test_db)
    request = _request().model_copy(update={"artifact_types": ["lesson_plan", "handout"]})

    def invalid_template(*args):
        raise ValueError("template broken")

    monkeypatch.setattr(api, "require_valid_builtin_template", invalid_template)
    with pytest.raises(Exception) as exc:
        await api.generate_preparation(request)
    assert exc.value.status_code == 503

    monkeypatch.setattr(api, "require_valid_builtin_template", lambda: {"sha256": "hash"})

    class BrokenGenerator:
        error = ValueError("invalid input")

        async def generate_lesson_plan(self, *args, **kwargs):
            raise self.error

    broken = BrokenGenerator()

    async def get_broken():
        return broken

    monkeypatch.setattr(api, "get_ai_generator", get_broken)
    with pytest.raises(Exception) as exc:
        await api.generate_preparation(request)
    assert exc.value.status_code == 400
    broken.error = RuntimeError("offline")
    with pytest.raises(Exception) as exc:
        await api.generate_preparation(request)
    assert exc.value.status_code == 500

    content = GeneratedContent(key_points="重点")

    class GoodGenerator:
        async def generate_lesson_plan(self, *args, **kwargs):
            return content

    async def get_good():
        return GoodGenerator()

    first = tmp_path / "first.docx"

    class PartlyBrokenRenderer:
        def render_lesson_plan(self, *args):
            first.write_bytes(b"created")
            return str(first)

    class BrokenExtra:
        def render_handout(self, *args):
            raise RuntimeError("render failed")

    monkeypatch.setattr(api, "get_ai_generator", get_good)
    monkeypatch.setattr(api, "DocumentRenderer", PartlyBrokenRenderer)
    monkeypatch.setattr(api, "PreparationRenderer", BrokenExtra)
    with pytest.raises(Exception) as exc:
        await api.generate_preparation(request)
    assert exc.value.status_code == 500 and not first.exists()


def test_background_task_manager_runner_decorator_and_errors():
    manager = BackgroundTaskManager()
    manager._shutdown_requested = False
    assert manager is BackgroundTaskManager()
    assert manager.is_shutdown_requested() is False

    errors = []

    async def success():
        return 1

    thread = BackgroundTaskRunner.run_async_task(success(), name="success-test")
    thread.join(timeout=5)
    assert not thread.is_alive()

    async def failure():
        raise RuntimeError("task failed")

    thread = BackgroundTaskRunner.run_async_task(
        failure(), name="failure-test", on_error=lambda exc: errors.append(str(exc))
    )
    thread.join(timeout=5)
    assert errors == ["task failed"]

    def broken_handler(_):
        raise RuntimeError("handler failed")

    thread = BackgroundTaskRunner.run_async_task(failure(), on_error=broken_handler)
    thread.join(timeout=5)

    @BackgroundTaskRunner.run_async_function(name="decorated-test")
    async def decorated(value):
        return value

    thread = decorated(2)
    thread.join(timeout=5)
    assert BackgroundTaskRunner.is_shutdown_requested() is False
    manager.shutdown(timeout=0.1)
    assert manager.is_shutdown_requested() is True
