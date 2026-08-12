import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.api import batch as api
from backend.models.schemas import (
    BatchTaskCreateRequest,
    ChapterInfo,
    ChapterSplitRequest,
    DraftTaskCreateRequest,
    ExportSelectedRequest,
    SmartAllocationRequest,
)


def _chapters(count=2):
    return [
        ChapterInfo(
            lesson_number=index,
            topic=f"主题{index}",
            content_summary=f"内容{index}",
            key_concepts=[f"概念{index}"],
            experiment_name=f"实验{index}",
        )
        for index in range(1, count + 1)
    ]


async def _events(response):
    return [chunk async for chunk in response.body_iterator]


@pytest.fixture
async def batch_db(test_db, monkeypatch):
    async def get_test_db():
        return test_db

    monkeypatch.setattr(api, "get_db", get_test_db)
    await test_db.execute(
        """INSERT INTO templates
        (id, name, file_path, created_at, updated_at)
        VALUES ('yunlin-standard', '云林模板', 'builtin.docx', 'x', 'x')""",
        commit=True,
    )
    return test_db


@pytest.mark.asyncio
async def test_split_chapters_reference_cache_regeneration_and_errors(batch_db, monkeypatch):
    class FakeSplitter:
        calls = 0

        def __init__(self, **kwargs):
            pass

        async def split_course_chapters(self, **kwargs):
            FakeSplitter.calls += 1
            return _chapters(2)

    async def normalize(chapters, **kwargs):
        return [c.model_dump() if hasattr(c, "model_dump") else c for c in chapters], True

    monkeypatch.setattr(api, "ChapterSplitter", FakeSplitter)
    monkeypatch.setattr(api, "ensure_experiment_names", normalize)
    request = ChapterSplitRequest(
        course_name="Python", subject="计算机", grade="大学", total_hours=4
    )

    generated = await api.split_chapters(request)
    assert generated.total_lessons == 2 and FakeSplitter.calls == 1
    cached = await api.split_chapters(request)
    assert cached.total_lessons == 2 and FakeSplitter.calls == 1
    use_count = await batch_db.fetch_one("SELECT use_count FROM course_chapter_templates")
    assert use_count["use_count"] == 1

    await batch_db.execute(
        "UPDATE course_chapter_templates SET chapters = ?",
        (json.dumps([_chapters(1)[0].model_dump()], ensure_ascii=False),),
        commit=True,
    )
    regenerated = await api.split_chapters(request)
    assert regenerated.total_lessons == 2 and FakeSplitter.calls == 2

    reference = request.model_copy(update={"chapters_input": "第一章\n第二章"})
    assert (await api.split_chapters(reference)).total_lessons == 2

    class ValueErrorSplitter(FakeSplitter):
        async def split_course_chapters(self, **kwargs):
            raise ValueError("bad outline")

    monkeypatch.setattr(api, "ChapterSplitter", ValueErrorSplitter)
    with pytest.raises(HTTPException) as exc:
        await api.split_chapters(reference)
    assert exc.value.status_code == 400

    class RuntimeErrorSplitter(FakeSplitter):
        async def split_course_chapters(self, **kwargs):
            raise RuntimeError("provider down")

    monkeypatch.setattr(api, "ChapterSplitter", RuntimeErrorSplitter)
    with pytest.raises(HTTPException) as exc:
        await api.split_chapters(reference)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_chapter_split_stream_cache_ai_mismatch_and_error(batch_db, monkeypatch):
    request = ChapterSplitRequest(
        course_name="流式课程", subject="计算机", grade="大学", total_hours=4
    )
    now = "2026-01-01T00:00:00"
    await batch_db.execute(
        """INSERT INTO course_chapter_templates
        (id, course_name, subject, grade, total_hours, hours_per_lesson, chapters,
         use_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
        (
            "stream-cache", "流式课程", "计算机", "大学", 4, 2,
            json.dumps([c.model_dump() for c in _chapters()], ensure_ascii=False), now, now,
        ),
        commit=True,
    )

    async def normalize(chapters, **kwargs):
        return [c.model_dump() if hasattr(c, "model_dump") else c for c in chapters], True

    async def no_sleep(_):
        return None

    monkeypatch.setattr(api, "ensure_experiment_names", normalize)
    monkeypatch.setattr(api.asyncio, "sleep", no_sleep)
    cached_events = await _events(await api.split_chapters_stream(request))
    assert any("event: complete" in event for event in cached_events)
    assert sum("event: chapter" in event for event in cached_events) == 2

    class FakeStreamSplitter:
        mode = "ok"

        def __init__(self, **kwargs):
            pass

        async def _generate_ai_chapters_stream(self, **kwargs):
            if self.mode == "error":
                raise RuntimeError("stream failed")
            count = 1 if self.mode == "short" else 2
            for chapter in _chapters(count):
                yield chapter

    monkeypatch.setattr(api, "ChapterSplitter", FakeStreamSplitter)
    await batch_db.execute(
        "UPDATE course_chapter_templates SET chapters=? WHERE id='stream-cache'",
        (json.dumps([_chapters(1)[0].model_dump()], ensure_ascii=False),),
        commit=True,
    )
    generated_events = await _events(await api.split_chapters_stream(request))
    assert any("event: complete" in event for event in generated_events)

    FakeStreamSplitter.mode = "short"
    no_cache_request = request.model_copy(update={"chapters_input": "参考目录"})
    mismatch = await _events(await api.split_chapters_stream(no_cache_request))
    assert any("数量不匹配" in event for event in mismatch)

    FakeStreamSplitter.mode = "error"
    errors = await _events(await api.split_chapters_stream(no_cache_request))
    assert any("stream failed" in event for event in errors)


@pytest.mark.asyncio
async def test_smart_allocation_stream_inserts_updates_and_maps_errors(batch_db, monkeypatch):
    request = SmartAllocationRequest(
        course_name="智能课程",
        subject="计算机",
        grade="大学",
        chapters_input="第一章\n第二章",
        total_weeks=2,
        hours_per_week=2,
        total_hours=4,
    )

    class FakeSmartSplitter:
        fail = False

        def __init__(self, **kwargs):
            pass

        async def _generate_smart_allocation_stream(self, **kwargs):
            if self.fail:
                raise RuntimeError("allocation failed")
            for chapter in _chapters(2):
                yield chapter

    async def normalize(chapters, **kwargs):
        return [c.model_dump() for c in chapters], False

    monkeypatch.setattr(api, "ChapterSplitter", FakeSmartSplitter)
    monkeypatch.setattr(api, "ensure_experiment_names", normalize)
    first = await _events(await api.split_chapters_smart_allocation_stream(request))
    assert any("event: complete" in event for event in first)
    second = await _events(await api.split_chapters_smart_allocation_stream(request))
    assert any("event: complete" in event for event in second)
    count = await batch_db.fetch_one(
        "SELECT COUNT(*) AS count FROM course_chapter_templates WHERE course_name='智能课程'"
    )
    assert count["count"] == 1
    FakeSmartSplitter.fail = True
    errors = await _events(await api.split_chapters_smart_allocation_stream(request))
    assert any("allocation failed" in event for event in errors)


@pytest.fixture
def fake_batch_background(monkeypatch):
    calls = []

    class FakeProcessor:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        async def process_batch_task(self, task_id, is_draft_mode=False):
            return None

    def close_background(coro, name=None):
        calls.append((name, coro.cr_frame.f_locals.get("is_draft_mode", False)))
        coro.close()

    monkeypatch.setattr(api, "BatchTaskProcessor", FakeProcessor)
    monkeypatch.setattr(api, "run_in_background", close_background)
    monkeypatch.setattr(api, "require_valid_builtin_template", lambda template_id: None)
    monkeypatch.setattr(api, "require_valid_course_plan_template", lambda artifact: None)
    return calls


@pytest.mark.asyncio
async def test_batch_task_crud_templates_drafts_and_selected_export(
    batch_db, tmp_path, monkeypatch, fake_batch_background
):
    normal_request = BatchTaskCreateRequest(
        course_name="批量课程",
        subject="计算机",
        grade="大学",
        template_id="yunlin-standard",
        total_hours=4,
        chapters=_chapters(),
    )
    created = await api.create_batch_task(normal_request)
    task_id = created.task_id
    task = await api.get_batch_task(task_id)
    assert task.id == task_id and task.chapters[0].topic == "主题1"
    listing = await api.list_batch_tasks(status="pending", page=1, limit=10)
    assert listing.total == 1 and listing.tasks[0].id == task_id
    assert (await api.list_batch_tasks(status=None, page=1, limit=10)).total == 1
    with pytest.raises(HTTPException) as exc:
        await api.get_batch_task("missing")
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        await api.download_batch_zip(task_id)
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException):
        await api.download_batch_zip("missing")
    await batch_db.execute(
        "UPDATE batch_tasks SET status='completed' WHERE id=?", (task_id,), commit=True
    )
    with pytest.raises(HTTPException, match="ZIP file path"):
        await api.download_batch_zip(task_id)
    absent = tmp_path / "absent.zip"
    await batch_db.execute(
        "UPDATE batch_tasks SET zip_file_path=? WHERE id=?", (str(absent), task_id), commit=True
    )
    with pytest.raises(HTTPException, match="not found on disk"):
        await api.download_batch_zip(task_id)
    archive = tmp_path / "batch.zip"
    archive.write_bytes(b"zip")
    await batch_db.execute(
        "UPDATE batch_tasks SET zip_file_path=? WHERE id=?", (str(archive), task_id), commit=True
    )
    response = await api.download_batch_zip(task_id)
    assert response.filename == "batch.zip"

    # A pending task is cancelled; a completed task and its archive are deleted.
    pending = await api.create_batch_task(normal_request.model_copy(update={"course_name": "待取消"}))
    assert (await api.delete_batch_task(pending.task_id))["message"] == "Task cancelled"
    assert (await api.delete_batch_task(task_id))["message"] == "Task deleted"
    assert not archive.exists()
    with pytest.raises(HTTPException):
        await api.delete_batch_task("missing")

    # Cached chapter templates are listed and deserialized.
    now = "2026-01-01T00:00:00"
    await batch_db.execute(
        """INSERT INTO course_chapter_templates
        (id, course_name, subject, grade, total_hours, hours_per_lesson, chapters,
         use_count, created_at, updated_at) VALUES ('list-template','课程','科目','年级',4,2,?,2,?,?)""",
        (json.dumps([c.model_dump() for c in _chapters()], ensure_ascii=False), now, now),
        commit=True,
    )
    templates = await api.list_chapter_templates(page=1, limit=10)
    assert templates.total >= 1 and templates.templates[0].chapters

    draft_request = DraftTaskCreateRequest(
        course_name="草稿课程",
        subject="计算机",
        grade="大学",
        template_id="yunlin-standard",
        total_hours=4,
        chapters=_chapters(),
        textbook_name="教材",
    )
    draft = await api.create_draft_task(draft_request)
    assert draft.status == "pending"

    # Attach one lesson plan and verify the task-detail endpoint parses new JSON fields.
    plan_id = "draft-plan"
    await batch_db.execute(
        """INSERT INTO lesson_plans
        (id, template_id, title, subject, grade, topic, input_data,
         generated_content, status, batch_task_id, lesson_number, created_at)
        VALUES (?, 'yunlin-standard', '教案', '计算机', '大学', '主题1', '{}', '{}',
                'draft_cached', ?, 1, ?)""",
        (plan_id, draft.task_id, now),
        commit=True,
    )
    await batch_db.execute(
        """INSERT INTO batch_lesson_plans
        (id, batch_task_id, lesson_plan_id, lesson_number, topic, status, created_at)
        VALUES ('link', ?, ?, 1, '主题1', 'completed', ?)""",
        (draft.task_id, plan_id, now),
        commit=True,
    )
    details = await api.get_task_lesson_plans(draft.task_id, page=1, limit=10)
    assert details.total == 1 and details.lesson_plans[0].id == plan_id
    with pytest.raises(HTTPException):
        await api.get_task_lesson_plans("missing")

    export_file = tmp_path / "selected.zip"
    export_file.write_bytes(b"selected")
    import backend.services.lesson_plan_service as service_module

    class FakeLessonPlanService:
        async def batch_publish(self, **kwargs):
            return str(export_file)

    monkeypatch.setattr(service_module, "LessonPlanService", FakeLessonPlanService)
    exported = await api.export_selected_lesson_plans(
        draft.task_id, ExportSelectedRequest(lesson_plan_ids=[plan_id])
    )
    assert exported.filename == "selected.zip"
    export_file.unlink()
    with pytest.raises(HTTPException) as exc:
        await api.export_selected_lesson_plans(
            draft.task_id, ExportSelectedRequest(lesson_plan_ids=[plan_id])
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_batch_creation_validation_and_database_failures(batch_db, monkeypatch, fake_batch_background):
    base = {
        "course_name": "验证课程",
        "subject": "计算机",
        "grade": "大学",
        "template_id": "yunlin-standard",
        "total_hours": 4,
        "chapters": _chapters(),
    }
    with pytest.raises(HTTPException) as exc:
        await api.create_batch_task(BatchTaskCreateRequest(**{**base, "chapters": []}))
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        await api.create_batch_task(BatchTaskCreateRequest(**{**base, "chapters": _chapters(1)}))
    assert exc.value.status_code == 400

    await batch_db.execute(
        "INSERT INTO classes (id, name, created_at, updated_at) VALUES ('class-1','一班','x','x')",
        commit=True,
    )
    created = await api.create_batch_task(
        BatchTaskCreateRequest(**{**base, "class_ids": ["class-1"]})
    )
    row = await batch_db.fetch_one("SELECT class_names FROM batch_tasks WHERE id=?", (created.task_id,))
    assert row["class_names"] == "一班"
    with pytest.raises(HTTPException) as exc:
        await api.create_batch_task(BatchTaskCreateRequest(**{**base, "class_ids": ["missing"]}))
    assert exc.value.status_code == 400

    def invalid_template(_):
        raise ValueError("invalid template")

    monkeypatch.setattr(api, "require_valid_builtin_template", invalid_template)
    with pytest.raises(HTTPException) as exc:
        await api.create_draft_task(
            DraftTaskCreateRequest(**base)
        )
    assert exc.value.status_code == 400
