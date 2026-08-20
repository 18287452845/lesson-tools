"""Service tests for lesson-plan persistence and document publishing."""

import json
import pathlib
import types
import zipfile

import pytest

from backend.services import lesson_plan_service as service_module


VALID_INPUT = {
    "template_id": "yunlin-standard",
    "subject": "Python",
    "grade": "大一",
    "topic": "列表操作",
    "duration": "2课时",
}


async def _insert_plan(
    database,
    plan_id,
    *,
    title="Python 教案",
    subject="Python",
    grade="大一",
    topic="列表操作",
    input_data=None,
    generated_content=None,
    output_file_path=None,
):
    await database.execute(
        """
        INSERT INTO lesson_plans
            (id, template_id, title, subject, grade, topic, input_data,
             generated_content, output_file_path, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft_cached')
        """,
        (
            plan_id,
            "yunlin-standard",
            title,
            subject,
            grade,
            topic,
            json.dumps(VALID_INPUT, ensure_ascii=False) if input_data is None else input_data,
            json.dumps({"key_points": "列表索引"}, ensure_ascii=False)
            if generated_content is None
            else generated_content,
            output_file_path,
        ),
        commit=True,
    )


@pytest.fixture
async def lesson_service(test_db, tmp_path, monkeypatch):
    async def get_test_db():
        return test_db

    async def regenerate_field(**kwargs):
        return f"重新生成：{kwargs['field_name']}"

    rendered = []

    def render(*, template_path, output_path, data):
        path = pathlib.Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"generated document")
        rendered.append(
            {
                "template_path": template_path,
                "output_path": output_path,
                "data": data,
            }
        )
        return output_path

    monkeypatch.setattr(service_module, "get_db", get_test_db)
    monkeypatch.setattr(service_module.settings, "output_dir", tmp_path)
    monkeypatch.setattr(
        service_module,
        "require_valid_builtin_template",
        lambda template_id: {"is_valid": True, "template_id": template_id},
    )
    monkeypatch.setattr(
        service_module,
        "get_builtin_template_path",
        lambda: tmp_path / "builtin.docx",
    )

    await test_db.execute(
        """
        INSERT INTO templates (id, name, file_path, fields_config)
        VALUES (?, ?, ?, ?)
        """,
        ("yunlin-standard", "云林标准模板", str(tmp_path / "builtin.docx"), "[]"),
        commit=True,
    )

    service = object.__new__(service_module.LessonPlanService)
    service.ai_generator = types.SimpleNamespace(regenerate_field=regenerate_field)
    service.document_renderer = types.SimpleNamespace(render=render)
    service.rendered = rendered
    return service


@pytest.mark.service
async def test_lesson_plan_query_update_and_regeneration(
    lesson_service,
    test_db,
):
    await _insert_plan(test_db, "plan-1", title="列表操作基础")
    await _insert_plan(
        test_db,
        "plan-2",
        title="字典操作",
        topic="字典操作",
        subject="数据结构",
        grade="大二",
        generated_content="not-json",
    )

    plan = await lesson_service.get_lesson_plan("plan-1")
    assert plan is not None
    assert plan.title == "列表操作基础"
    assert await lesson_service.get_lesson_plan("missing") is None

    all_plans, total = await lesson_service.list_lesson_plans({}, page=1, limit=10)
    assert total == 2
    assert {item.id for item in all_plans} == {"plan-1", "plan-2"}

    filtered, total = await lesson_service.list_lesson_plans(
        {
            "status": "draft_cached",
            "template_id": "yunlin-standard",
            "subject": "Python",
            "grade": "大一",
            "search": "列表",
        },
        page=1,
        limit=1,
    )
    assert total == 1
    assert [item.id for item in filtered] == ["plan-1"]

    updated = await lesson_service.update_field(
        "plan-1",
        "teaching_methods",
        ["演示", "练习"],
    )
    assert json.loads(updated.generated_content)["teaching_methods"] == ["演示", "练习"]

    recovered = await lesson_service.update_field("plan-2", "key_points", "字典键值")
    assert json.loads(recovered.generated_content) == {"key_points": "字典键值"}

    regenerated = await lesson_service.regenerate_field(
        "plan-1",
        "key_points",
        "突出实践",
    )
    assert regenerated == "重新生成：key_points"
    persisted = await lesson_service.get_lesson_plan("plan-1")
    assert json.loads(persisted.generated_content)["key_points"] == regenerated

    await test_db.execute(
        "UPDATE lesson_plans SET final_content=? WHERE id='plan-1'",
        (json.dumps({"key_points": "最终重点"}, ensure_ascii=False),),
        commit=True,
    )
    await lesson_service.update_field("plan-1", "teaching_methods", "项目教学")
    regenerated_final = await lesson_service.regenerate_field("plan-1", "key_points")
    persisted = await lesson_service.get_lesson_plan("plan-1")
    final_content = json.loads(persisted.final_content)
    assert final_content == {
        "key_points": regenerated_final,
        "teaching_methods": "项目教学",
    }

    await test_db.execute(
        """INSERT INTO batch_tasks
        (id, course_name, subject, grade, template_id, total_hours, chapters,
         status, total_count)
        VALUES ('processing-service', 'Python', 'Python', '大学', 'yunlin-standard',
                2, '[]', 'processing', 1)""",
        commit=True,
    )
    await test_db.execute(
        "UPDATE lesson_plans SET batch_task_id='processing-service' WHERE id='plan-1'",
        commit=True,
    )
    with pytest.raises(ValueError, match="任务完成后"):
        await lesson_service.update_field("plan-1", "key_points", "处理中不可编辑")
    with pytest.raises(ValueError, match="任务完成后"):
        await lesson_service.regenerate_field("plan-1", "key_points")
    await test_db.execute(
        "UPDATE batch_tasks SET status='completed' WHERE id='processing-service'",
        commit=True,
    )

    with pytest.raises(ValueError, match="not found"):
        await lesson_service.update_field("missing", "key_points", "内容")
    with pytest.raises(ValueError, match="not found"):
        await lesson_service.regenerate_field("missing", "key_points")

    await _insert_plan(test_db, "bad-input", input_data="not-json")
    with pytest.raises(ValueError, match="Invalid JSON"):
        await lesson_service.regenerate_field("bad-input", "key_points")


@pytest.mark.service
async def test_publish_lesson_plan_persists_document_metadata(
    lesson_service,
    test_db,
):
    await _insert_plan(
        test_db,
        "publish-12345678",
        topic="网络/安全:基础",
        input_data=json.dumps({**VALID_INPUT, "location": "实训楼"}, ensure_ascii=False),
        generated_content=json.dumps({"key_points": "安全配置"}, ensure_ascii=False),
    )
    await test_db.execute(
        "UPDATE lesson_plans SET final_content=? WHERE id='publish-12345678'",
        (json.dumps({"key_points": "最终安全配置"}, ensure_ascii=False),),
        commit=True,
    )

    output_path, download_url = await lesson_service.publish_lesson_plan(
        "publish-12345678"
    )

    assert pathlib.Path(output_path).is_file()
    assert pathlib.Path(output_path).name == "网络_安全_基础_publish-.docx"
    assert download_url == "/api/documents/download/网络_安全_基础_publish-.docx"
    assert lesson_service.rendered[-1]["data"]["location"] == "实训楼"
    assert lesson_service.rendered[-1]["data"]["key_points"] == "最终安全配置"

    stored = await lesson_service.get_lesson_plan("publish-12345678")
    assert stored.status == "published"
    assert stored.output_file_path == output_path

    with pytest.raises(ValueError, match="not found"):
        await lesson_service.publish_lesson_plan("missing")

    await _insert_plan(test_db, "publish-invalid", generated_content="not-json")
    with pytest.raises(ValueError, match="Invalid JSON"):
        await lesson_service.publish_lesson_plan("publish-invalid")


@pytest.mark.service
async def test_batch_publish_groups_documents_and_skips_missing_plans(
    lesson_service,
    test_db,
):
    for index in range(1, 4):
        await _insert_plan(
            test_db,
            f"batch-{index}",
            title=f"批量教案 {index}",
            topic=f"主题 {index}",
        )
    await test_db.execute(
        "UPDATE lesson_plans SET final_content=? WHERE id='batch-1'",
        (json.dumps({"key_points": "选中导出最终重点"}, ensure_ascii=False),),
        commit=True,
    )

    zip_path = await lesson_service.batch_publish(
        ["batch-1", "missing", "batch-2", "batch-3"],
        group_by_document=True,
    )

    assert pathlib.Path(zip_path).is_file()
    assert lesson_service.rendered[0]["data"]["key_points"] == "选中导出最终重点"
    with zipfile.ZipFile(zip_path) as archive:
        assert sorted(archive.namelist()) == ["主题 1_01.docx", "主题 3_02.docx"]

    for plan_id in ("batch-1", "batch-2", "batch-3"):
        stored = await lesson_service.get_lesson_plan(plan_id)
        assert stored.status == "published"
        assert stored.output_file_path

    separate_zip = await lesson_service.batch_publish(
        ["batch-1", "batch-2"],
        group_by_document=False,
    )
    assert pathlib.Path(separate_zip).is_file()

    with pytest.raises(ValueError, match="No valid"):
        await lesson_service.batch_publish(["missing"], group_by_document=True)
    with pytest.raises(ValueError, match="No lesson plans"):
        await lesson_service._render_combined_document([], 1)

    await _insert_plan(test_db, "bad-render", input_data="not-json")
    bad_plan = await lesson_service.get_lesson_plan("bad-render")
    with pytest.raises(ValueError, match="No valid lesson plan data"):
        await lesson_service._render_combined_document([bad_plan], 1)


@pytest.mark.service
async def test_delete_lesson_plan_removes_links_and_output_file(
    lesson_service,
    test_db,
    tmp_path,
):
    output_path = tmp_path / "obsolete.docx"
    output_path.write_bytes(b"obsolete")
    await _insert_plan(
        test_db,
        "delete-me",
        output_file_path=str(output_path),
    )
    await test_db.execute(
        """
        INSERT INTO batch_tasks
            (id, course_name, subject, grade, template_id, total_hours,
             chapters, total_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "unused-task",
            "Python",
            "Python",
            "大一",
            "yunlin-standard",
            2,
            "[]",
            1,
        ),
        commit=True,
    )
    await test_db.execute(
        """
        INSERT INTO batch_lesson_plans
            (id, batch_task_id, lesson_plan_id, lesson_number, topic)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("link-1", "unused-task", "delete-me", 1, "列表操作"),
        commit=True,
    )

    await lesson_service.delete_lesson_plan("delete-me")

    assert not output_path.exists()
    assert await lesson_service.get_lesson_plan("delete-me") is None
    assert (
        await test_db.fetch_one(
            "SELECT id FROM batch_lesson_plans WHERE lesson_plan_id = ?",
            ("delete-me",),
        )
        is None
    )

    with pytest.raises(ValueError, match="not found"):
        await lesson_service.delete_lesson_plan("delete-me")
