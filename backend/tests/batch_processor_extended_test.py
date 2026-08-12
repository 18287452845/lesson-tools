import json
import zipfile
from pathlib import Path

import pytest

from backend.models.schemas import GeneratedContent
from backend.services import batch_processor as module
from backend.services.batch_processor import BatchTaskProcessor, _flatten_key_concepts


def _chapter(number, topic=None):
    return {
        "lesson_number": number,
        "topic": topic or f"主题{number}",
        "content_summary": f"内容{number}",
        "key_concepts": [f"概念{number}"],
        "experiment_name": f"实验{number}",
    }


def _content(online_resources=None, complete=True):
    return GeneratedContent(
        teaching_goals={"knowledge": ["掌握知识"]} if complete else None,
        key_points="教学重点" if complete else None,
        teaching_steps=[
            {
                "stage": "课堂实践",
                "duration": "30分钟",
                "teacher_activity": "教师指导",
                "student_activity": "学生操作",
                "design_intent": "实践应用",
            }
        ] if complete else [],
        online_resources=online_resources,
    )


@pytest.fixture
async def processor_db(test_db, monkeypatch):
    async def get_test_db():
        return test_db

    monkeypatch.setattr(module, "get_db", get_test_db)
    await test_db.execute(
        """INSERT INTO templates
        (id, name, file_path, created_at, updated_at)
        VALUES ('yunlin-standard', '云林模板', 'builtin.docx', 'x', 'x')""",
        commit=True,
    )
    return test_db


async def _insert_task(db, task_id, chapters, status="pending", supplemental=None):
    now = "2026-01-01T00:00:00"
    await db.execute(
        """INSERT INTO batch_tasks
        (id, course_name, subject, grade, template_id, total_hours,
         hours_per_lesson, chapters, start_week, class_ids, class_names,
         supplemental_artifacts, experiment_schedules, status, total_count,
         created_at, updated_at)
        VALUES (?, 'Python', '计算机', '大学', 'yunlin-standard', ?, 2, ?, 1,
                '[]', '一班,二班', ?, '[]', ?, ?, ?, ?)""",
        (
            task_id,
            len(chapters) * 2,
            json.dumps(chapters, ensure_ascii=False),
            json.dumps(supplemental or [], ensure_ascii=False),
            status,
            len(chapters),
            now,
            now,
        ),
        commit=True,
    )


def test_flatten_and_group_helpers():
    assert _flatten_key_concepts(["A", ["B", ["C"]], 4, None]) == ["A", "B", "C", "4", "None"]
    processor = BatchTaskProcessor(max_concurrent_documents=1, max_concurrent_lessons=1)
    assert processor.default_duration == "2课时"
    assert processor._group_lessons_by_document([_chapter(1), _chapter(2), _chapter(3)]) == [
        [_chapter(1), _chapter(2)],
        [_chapter(3)],
    ]


@pytest.mark.asyncio
async def test_parallel_document_generation_success_failure_draft_and_render(
    processor_db, tmp_path, monkeypatch
):
    task_id = "parallel-task"
    await _insert_task(processor_db, task_id, [_chapter(1), _chapter(2), _chapter(3)])
    monkeypatch.setattr(module, "require_valid_builtin_template", lambda template_id: None)
    monkeypatch.setattr(module, "get_builtin_template_path", lambda: tmp_path / "template.docx")

    processor = BatchTaskProcessor(max_concurrent_lessons=2)

    class FakeAI:
        async def generate_lesson_plan(self, request, generate_reflection=False):
            if request.topic == "主题2":
                raise RuntimeError("AI failed")
            if request.topic == "主题3":
                return _content(complete=False)
            return _content(online_resources=["资源A", "资源B"])

    rendered = tmp_path / "rendered.docx"

    class FakeRenderer:
        def render_lesson_plans_document(self, **kwargs):
            assert kwargs["week_number"] == 2
            assert kwargs["lesson_plans_data"][0]["references"] == "《指定教材》\n资源A\n资源B"
            rendered.write_bytes(b"document")
            return str(rendered)

    processor.ai_generator = FakeAI()
    processor.document_renderer = FakeRenderer()
    result = await processor._generate_document_parallel(
        batch_task_id=task_id,
        document_number=2,
        chapters_data=[_chapter(1), _chapter(2), _chapter(3)],
        template_id="yunlin-standard",
        subject="计算机",
        grade="大学",
        course_name="Python",
        start_week=1,
        generate_reflection=True,
        textbook_name="指定教材",
        class_names="一班",
    )
    assert result == (str(rendered), 1, 2, [1])
    rows = await processor_db.fetch_all(
        "SELECT status, error_message FROM batch_lesson_plans WHERE batch_task_id=? ORDER BY lesson_number",
        (task_id,),
    )
    assert [row["status"] for row in rows] == ["completed", "failed", "failed"]
    assert "Missing required fields" in rows[2]["error_message"]

    draft_id = "draft-processor"
    await _insert_task(processor_db, draft_id, [_chapter(1)])
    processor.ai_generator = FakeAI()
    draft = await processor._generate_document_parallel(
        draft_id, 1, [_chapter(1)], "yunlin-standard", "计算机", "大学", "Python",
        is_draft_mode=True,
    )
    assert draft == ("", 1, 0, [1])
    saved = await processor_db.fetch_one(
        "SELECT status FROM lesson_plans WHERE batch_task_id=?", (draft_id,)
    )
    assert saved["status"] == "draft_cached"

    failed_id = "all-failed"
    await _insert_task(processor_db, failed_id, [_chapter(2)])
    all_failed = await processor._generate_document_parallel(
        failed_id, 1, [_chapter(2)], "yunlin-standard", "计算机", "大学", "Python"
    )
    assert all_failed == ("", 0, 1, [])


@pytest.mark.asyncio
async def test_parallel_generation_reuses_completed_checkpoint_and_replaces_failed(
    processor_db, tmp_path, monkeypatch
):
    task_id = "checkpoint-task"
    chapters = [_chapter(1), _chapter(2)]
    await _insert_task(processor_db, task_id, chapters)
    stored = _content()
    for number, status in ((1, "completed"), (2, "failed")):
        await processor_db.execute(
            """
            INSERT INTO lesson_plans
              (id, template_id, title, subject, grade, topic, input_data,
               generated_content, status, batch_task_id, lesson_number)
            VALUES (?, 'yunlin-standard', ?, '计算机', '大学', ?, '{}', ?, ?, ?, ?)
            """,
            (
                f"plan-{number}", f"教案{number}", f"主题{number}",
                json.dumps(stored.model_dump(), ensure_ascii=False),
                "generated" if status == "completed" else "failed", task_id, number,
            ), commit=True,
        )
        await processor_db.execute(
            """
            INSERT INTO batch_lesson_plans
              (id, batch_task_id, lesson_plan_id, lesson_number, topic, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (f"link-{number}", task_id, f"plan-{number}", number, f"主题{number}", status),
            commit=True,
        )

    monkeypatch.setattr(module, "require_valid_builtin_template", lambda _id: None)
    monkeypatch.setattr(module, "get_builtin_template_path", lambda: tmp_path / "template.docx")
    processor = BatchTaskProcessor(max_concurrent_lessons=2)
    calls = []

    class FakeAI:
        async def generate_lesson_plan(self, request, generate_reflection=False):
            calls.append(request.topic)
            return _content()

    rendered = tmp_path / "checkpoint.docx"
    class Renderer:
        def render_lesson_plans_document(self, **kwargs):
            assert len(kwargs["lesson_plans_data"]) == 2
            rendered.write_bytes(b"checkpoint")
            return str(rendered)

    processor.ai_generator = FakeAI()
    processor.document_renderer = Renderer()
    result = await processor._generate_document_parallel(
        task_id, 1, chapters, "yunlin-standard", "计算机", "大学", "Python",
        resource_ids=["resource-1"], course_archive_id="archive-1",
    )
    assert result == (str(rendered), 2, 0, [1, 2])
    assert calls == ["主题2"]
    links = await processor_db.fetch_all(
        "SELECT lesson_number, lesson_plan_id, status FROM batch_lesson_plans WHERE batch_task_id=? ORDER BY lesson_number",
        (task_id,),
    )
    assert len(links) == 2 and all(row["status"] == "completed" for row in links)
    assert links[0]["lesson_plan_id"] == "plan-1"
    assert links[1]["lesson_plan_id"] != "plan-2"


@pytest.mark.asyncio
async def test_sequential_generation_course_plans_zip_and_database_helpers(
    processor_db, tmp_path, monkeypatch
):
    monkeypatch.setattr(module, "require_valid_builtin_template", lambda template_id: None)
    monkeypatch.setattr(module, "get_builtin_template_path", lambda: tmp_path / "template.docx")
    processor = BatchTaskProcessor()

    class FakeAI:
        async def generate_lesson_plan(self, request, generate_reflection=False):
            return _content()

    sequential_file = tmp_path / "sequential.docx"

    class FakeDocumentRenderer:
        def render_lesson_plans_document(self, **kwargs):
            sequential_file.write_bytes(b"sequential")
            return str(sequential_file)

    processor.ai_generator = FakeAI()
    processor.document_renderer = FakeDocumentRenderer()
    await _insert_task(processor_db, "sequential", [_chapter(1)])
    path = await processor._generate_document_sequential(
        "sequential", 1, [_chapter(1)], "yunlin-standard", "计算机", "大学", "Python"
    )
    assert path == str(sequential_file)
    link = await processor_db.fetch_one(
        "SELECT file_path FROM batch_lesson_plans WHERE batch_task_id='sequential'"
    )
    assert link["file_path"] == str(sequential_file)

    teaching_file = tmp_path / "sequential_teaching.docx"
    experiment_file = tmp_path / "sequential_experiment.docx"
    teaching_file.write_bytes(b"teaching")
    experiment_file.write_bytes(b"experiment")

    class FakeCourseRenderer:
        def render_teaching_plan(self, **kwargs):
            return str(teaching_file)

        def render_experiment_plans(self, **kwargs):
            assert kwargs["class_schedules"] == [{"class_name": "一班"}]
            return [str(experiment_file)]

    async def regenerated(chapters, **kwargs):
        changed = [dict(chapter, experiment_name="合规实验") for chapter in chapters]
        return changed, True

    processor.course_plan_renderer = FakeCourseRenderer()
    monkeypatch.setattr(module, "ensure_experiment_names", regenerated)
    await _insert_task(processor_db, "plans", [_chapter(1)], supplemental=["teaching_plan", "experiment_plan"])
    task = dict(await processor_db.fetch_one("SELECT * FROM batch_tasks WHERE id='plans'"))
    task.update(
        academic_year="2025-2026",
        semester=2,
        teacher_name="教师",
        plan_date="2026-02-01",
        first_class_date="2026-02-02",
        class_periods="1-2",
        location="实训室",
        experiment_schedules=json.dumps([{"class_name": "一班"}], ensure_ascii=False),
    )
    files = await processor._generate_course_plan_files(
        batch_task_id="plans", task=task, chapters=[_chapter(1)]
    )
    assert len(files) == 2
    saved_task = await processor_db.fetch_one("SELECT chapters FROM batch_tasks WHERE id='plans'")
    assert json.loads(saved_task["chapters"])[0]["experiment_name"] == "合规实验"
    assert await processor._generate_course_plan_files(
        batch_task_id="plans", task={**task, "supplemental_artifacts": "[]"}, chapters=[]
    ) == []

    missing = tmp_path / "missing.docx"
    monkeypatch.setattr(module.settings, "output_dir", tmp_path)
    zip_path = await processor._pack_zip(
        "plans",
        "Python",
        [
            {"file_path": str(teaching_file), "archive_name": "授课计划.docx"},
            {"file_path": str(missing)},
        ],
        includes_course_plans=True,
    )
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.namelist() == ["授课计划.docx"]

    assert (await processor._load_batch_task("plans"))["course_name"] == "Python"
    assert await processor._load_batch_task("missing") is None
    await processor._update_task_status("plans", "processing", error_message="temporary")
    await processor._update_task_progress("plans", completed=1, total=1)
    await processor._increment_failed_count("plans")
    row = await processor_db.fetch_one("SELECT * FROM batch_tasks WHERE id='plans'")
    assert row["status"] == "processing" and row["completed_count"] == 1 and row["failed_count"] == 1
    assert await processor._is_task_cancelled("plans") is False
    await processor._update_task_status("plans", "cancelled")
    assert await processor._is_task_cancelled("plans") is True
    assert await processor._is_task_cancelled("missing") is False


@pytest.mark.asyncio
async def test_process_batch_task_success_draft_failure_cancel_and_wrapper(
    processor_db, tmp_path, monkeypatch
):
    processor = BatchTaskProcessor(max_concurrent_documents=2)
    generated = tmp_path / "generated.docx"
    generated.write_bytes(b"generated")
    archive = tmp_path / "generated.zip"

    async def fake_generate(**kwargs):
        return str(generated), len(kwargs["chapters_data"]), 0, [c["lesson_number"] for c in kwargs["chapters_data"]]

    async def no_supplements(**kwargs):
        return []

    async def fake_pack(**kwargs):
        archive.write_bytes(b"zip")
        return str(archive)

    monkeypatch.setattr(processor, "_generate_document_parallel", fake_generate)
    monkeypatch.setattr(processor, "_generate_course_plan_files", no_supplements)
    monkeypatch.setattr(processor, "_pack_zip", fake_pack)
    await _insert_task(processor_db, "workflow", [_chapter(1), _chapter(2), _chapter(3)])
    await processor.process_batch_task("workflow")
    row = await processor_db.fetch_one("SELECT * FROM batch_tasks WHERE id='workflow'")
    assert row["status"] == "completed" and row["completed_count"] == 3

    await _insert_task(processor_db, "workflow-draft", [_chapter(1)])
    await processor.process_batch_task("workflow-draft", is_draft_mode=True)
    assert (await processor_db.fetch_one("SELECT status FROM batch_tasks WHERE id='workflow-draft'"))["status"] == "completed"

    async def fail_generate(**kwargs):
        raise RuntimeError("document failed")

    monkeypatch.setattr(processor, "_generate_document_parallel", fail_generate)
    await _insert_task(processor_db, "workflow-failed", [_chapter(1)])
    await processor.process_batch_task("workflow-failed")
    failed = await processor_db.fetch_one("SELECT status, failed_count FROM batch_tasks WHERE id='workflow-failed'")
    assert failed["status"] == "failed" and failed["failed_count"] == 1

    async def always_cancelled(_):
        return True

    monkeypatch.setattr(processor, "_is_task_cancelled", always_cancelled)
    await _insert_task(processor_db, "workflow-cancel", [_chapter(1)])
    await processor.process_batch_task("workflow-cancel")
    assert (await processor_db.fetch_one("SELECT status FROM batch_tasks WHERE id='workflow-cancel'"))["status"] == "cancelled"

    await processor.process_batch_task("missing")

    class FakeProcessor:
        def __init__(self, *args):
            assert args == ("provider", "key", "model")

        async def process_batch_task(self, task_id):
            assert task_id == "wrapper"

    monkeypatch.setattr(module, "BatchTaskProcessor", FakeProcessor)
    await module.process_batch_task("wrapper", "provider", "key", "model")
