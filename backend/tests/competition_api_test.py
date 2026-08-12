import json
from pathlib import Path

import httpx
import pytest

from backend.api import competition as api
from backend.main import app
from backend.models.schemas import (
    CompetitionLessonContent,
    CompetitionLessonPlanGenerateRequest,
    CompetitionOverallDesign,
    CompetitionProjectCreate,
    CompetitionProjectUpdate,
    CompetitionReportContent,
    CompetitionReportGenerateRequest,
    CompetitionSingleLesson,
)


async def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def competition_db(test_db, monkeypatch):
    async def get_test_db():
        return test_db

    monkeypatch.setattr(api, "get_db", get_test_db)
    return test_db


@pytest.mark.asyncio
async def test_competition_project_crud_generation_output_and_download(competition_db, tmp_path, monkeypatch):
    captured = []

    def capture_background(coro, name=None):
        captured.append(name)
        coro.close()

    monkeypatch.setattr(api, "run_in_background", capture_background)
    async with await _client() as client:
        create = await client.post(
            "/api/competition/projects",
            json={
                "name": "参赛项目",
                "work_name": "Python作品",
                "course_name": "Python",
                "total_hours": 4,
                "hours_per_lesson": 2,
                "textbook_info": {"name": "教材"},
                "context_data": {"class": "一班"},
            },
        )
        assert create.status_code == 200
        project_id = create.json()["id"]

        listing = await client.get("/api/competition/projects?page=1&limit=5")
        assert listing.json()["total"] == 1
        assert (await client.get(f"/api/competition/projects/{project_id}")).status_code == 200
        assert (await client.get("/api/competition/projects/missing")).status_code == 404
        updated = await client.patch(
            f"/api/competition/projects/{project_id}",
            json={"name": "更新项目", "textbook_info": {"edition": "2"}, "context_data": None},
        )
        assert updated.json()["name"] == "更新项目"
        assert updated.json()["textbook_info"] == {"edition": "2"}
        assert (await client.patch("/api/competition/projects/missing", json={"name": "x"})).status_code == 404

        lesson = await client.post(
            f"/api/competition/projects/{project_id}/generate-lesson-plan",
            json={"topics_input": "任务1\n任务2", "additional_requirements": "要求"},
        )
        report = await client.post(
            f"/api/competition/projects/{project_id}/generate-report",
            json={"related_output_id": lesson.json()["output_id"]},
        )
        lesson_id = lesson.json()["output_id"]
        report_id = report.json()["output_id"]
        assert lesson.status_code == report.status_code == 200
        assert len(captured) == 2
        assert (await client.post("/api/competition/projects/missing/generate-lesson-plan", json={})).status_code == 404
        assert (await client.post("/api/competition/projects/missing/generate-report", json={})).status_code == 404

        outputs = await client.get(f"/api/competition/projects/{project_id}/outputs")
        assert outputs.json()["total"] == 2
        assert (await client.get(f"/api/competition/outputs/{lesson_id}")).json()["status"] == "pending"
        assert (await client.get("/api/competition/outputs/missing")).status_code == 404
        assert (await client.get(f"/api/competition/outputs/{lesson_id}/download")).status_code == 400
        assert (await client.get("/api/competition/outputs/missing/download")).status_code == 404

        cancel = await client.delete(f"/api/competition/outputs/{report_id}")
        assert cancel.json()["message"] == "Output cancelled"
        assert (await client.delete("/api/competition/outputs/missing")).status_code == 404

        completed_file = tmp_path / "competition.docx"
        completed_file.write_bytes(b"docx-content")
        await competition_db.execute(
            "UPDATE competition_outputs SET status='completed', output_file_path=? WHERE id=?",
            (str(completed_file), lesson_id),
            commit=True,
        )
        download = await client.get(f"/api/competition/outputs/{lesson_id}/download")
        assert download.status_code == 200 and download.content == b"docx-content"
        deleted = await client.delete(f"/api/competition/outputs/{lesson_id}")
        assert deleted.json()["message"] == "Output deleted"
        assert not completed_file.exists()

        await competition_db.execute(
            "UPDATE competition_outputs SET status='completed', output_file_path=? WHERE id=?",
            (str(tmp_path / "absent.docx"), report_id),
            commit=True,
        )
        assert (await client.get(f"/api/competition/outputs/{report_id}/download")).status_code == 404

        empty_update = await api.update_project(project_id, CompetitionProjectUpdate())
        assert empty_update.id == project_id
        deleted_project = await client.delete(f"/api/competition/projects/{project_id}")
        assert deleted_project.status_code == 200
        assert (await client.delete(f"/api/competition/projects/{project_id}")).status_code == 404


@pytest.mark.asyncio
async def test_competition_row_helpers_stream_and_background_processors(competition_db, tmp_path, monkeypatch):
    project = await api.create_project(
        CompetitionProjectCreate(name="后台项目", work_name="作品", course_name="课程", total_hours=2)
    )
    assert api._project_from_row(
        {
            **project.model_dump(),
            "textbook_info": "bad-json",
            "context_data": "bad-json",
        }
    ).textbook_info is None

    now = project.created_at

    async def insert_output(output_id, output_type="lesson_plan", status="pending", generated=None):
        await competition_db.execute(
            """INSERT INTO competition_outputs
            (id, project_id, output_type, status, generated_data, progress_current,
             progress_total, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 0, 2, ?, ?)""",
            (output_id, project.id, output_type, status, generated, now, now),
            commit=True,
        )

    await insert_output("bad-json", generated="not-json")
    row = await competition_db.fetch_one("SELECT * FROM competition_outputs WHERE id='bad-json'")
    assert api._output_from_row(row).generated_data is None

    response = await api.stream_output_progress("bad-json")
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
        if len(chunks) == 1:
            await competition_db.execute(
                "UPDATE competition_outputs SET status='completed' WHERE id='bad-json'", commit=True
            )
    assert any("event: done" in chunk for chunk in chunks)
    missing = await api.stream_output_progress("missing")
    assert "Output not found" in await anext(missing.body_iterator)

    lesson_content = CompetitionLessonContent(
        overall_design=CompetitionOverallDesign(teaching_method="任务驱动"),
        lessons=[CompetitionSingleLesson(lesson_number=1, title="任务")],
    )
    report_content = CompetitionReportContent(intro_summary="报告")

    class FakeGenerator:
        def __init__(self, **kwargs):
            pass

        async def generate_full_lesson_plan(self, **kwargs):
            await kwargs["progress_callback"](1, 3, "处理中")
            return lesson_content

        async def generate_report(self, **kwargs):
            await kwargs["progress_callback"](1, 2, "处理中")
            assert kwargs["related_lesson_plan"].lessons[0].title == "任务"
            return report_content

    class FakeRenderer:
        def render_lesson_plan(self, project, content):
            path = tmp_path / "lesson.docx"
            path.write_bytes(b"lesson")
            return str(path)

        def render_report(self, project, content):
            path = tmp_path / "report.docx"
            path.write_bytes(b"report")
            return str(path)

    monkeypatch.setattr(api, "CompetitionGenerator", FakeGenerator)
    monkeypatch.setattr(api, "CompetitionRenderer", FakeRenderer)

    await insert_output("lesson-success")
    await api._process_lesson_plan(
        "lesson-success", project, CompetitionLessonPlanGenerateRequest(topics_input="任务")
    )
    saved = await competition_db.fetch_one("SELECT * FROM competition_outputs WHERE id='lesson-success'")
    assert saved["status"] == "completed" and json.loads(saved["generated_data"])["lessons"]

    await insert_output("report-success", "report")
    await api._process_report(
        "report-success",
        project,
        CompetitionReportGenerateRequest(related_output_id="lesson-success"),
    )
    saved = await competition_db.fetch_one("SELECT * FROM competition_outputs WHERE id='report-success'")
    assert saved["status"] == "completed"

    class BrokenGenerator(FakeGenerator):
        async def generate_full_lesson_plan(self, **kwargs):
            raise RuntimeError("AI failed")

        async def generate_report(self, **kwargs):
            raise RuntimeError("report failed")

    monkeypatch.setattr(api, "CompetitionGenerator", BrokenGenerator)
    await insert_output("lesson-failed")
    await api._process_lesson_plan("lesson-failed", project, CompetitionLessonPlanGenerateRequest())
    assert (await competition_db.fetch_one("SELECT status FROM competition_outputs WHERE id='lesson-failed'"))["status"] == "failed"
    await insert_output("report-failed", "report")
    await api._process_report("report-failed", project, CompetitionReportGenerateRequest())
    assert (await competition_db.fetch_one("SELECT status FROM competition_outputs WHERE id='report-failed'"))["status"] == "failed"

    await insert_output("cancelled", status="cancelled")
    assert await api._is_cancelled("cancelled") is True
    assert await api._is_cancelled("missing") is False
    await api._update_output_progress("cancelled", 1, 4, "processing")
    status = await competition_db.fetch_one("SELECT * FROM competition_outputs WHERE id='cancelled'")
    assert status["progress_current"] == 1 and status["status"] == "processing"
