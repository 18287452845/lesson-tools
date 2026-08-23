"""Service tests for standalone semester plans built from generated lesson plans."""

import json
import zipfile
from datetime import date

import pytest

from backend.models.schemas import (
    CoursePlanCreateRequest,
    CoursePlanUpdateRequest,
)
from backend.services import course_plan_service as service_module
from backend.services.course_plan_service import CoursePlanService


MONDAY = date(2026, 3, 2).isoformat()  # 2026-03-02 是星期一


async def _insert_lesson(
    database,
    plan_id,
    *,
    topic,
    generated_content,
    final_content=None,
):
    await database.execute(
        """
        INSERT INTO lesson_plans
            (id, template_id, title, subject, grade, topic, input_data,
             generated_content, final_content, status)
        VALUES (?, ?, ?, 'Python', '2024级', ?, ?, ?, ?, 'draft_cached')
        """,
        (
            plan_id,
            "yunlin-standard",
            f"{topic}教案",
            topic,
            json.dumps({"topic": topic, "subject": "Python"}, ensure_ascii=False),
            json.dumps(generated_content, ensure_ascii=False),
            json.dumps(final_content, ensure_ascii=False) if final_content else None,
        ),
        commit=True,
    )


def _content(key_points, difficult_points="综合运用", homework=None):
    return {
        "key_points": key_points,
        "difficult_points": difficult_points,
        "homework": homework or {"required": "课后练习", "optional": "拓展阅读"},
        "teaching_steps": [{"stage": "课堂实践", "content": "完成上机练习"}],
    }


def _create_request(lesson_plan_ids, **overrides):
    payload = {
        "lesson_plan_ids": lesson_plan_ids,
        "plan_types": ["teaching_plan"],
        "course_name": "Python 程序设计",
        "grade": "2024级",
        "class_names": ["2024级大数据1班"],
        "academic_year": "2025-2026",
        "semester": 1,
        "teacher_name": "李老师",
        "hours_per_lesson": 2,
    }
    payload.update(overrides)
    return CoursePlanCreateRequest(**payload)


@pytest.fixture
async def service(test_db, tmp_path, monkeypatch):
    async def get_test_db():
        return test_db

    async def fake_ai_config():
        return (None, None, None)

    monkeypatch.setattr(service_module, "get_db", get_test_db)
    monkeypatch.setattr(service_module, "get_user_ai_config", fake_ai_config)
    monkeypatch.setattr(service_module.settings, "output_dir", tmp_path)
    # 测试中不让精简进入后台线程，由用例显式 await _finalize_draft
    monkeypatch.setattr(
        service_module, "run_in_background", lambda coro, name=None: coro.close()
    )

    await test_db.execute(
        """
        INSERT INTO templates (id, name, file_path, fields_config)
        VALUES (?, ?, ?, ?)
        """,
        ("yunlin-standard", "云林标准模板", str(tmp_path / "builtin.docx"), "[]"),
        commit=True,
    )
    return CoursePlanService()


@pytest.mark.service
async def test_create_draft_derives_rows_from_lesson_plans(service, test_db):
    await _insert_lesson(
        test_db,
        "lp-1",
        topic="列表操作",
        generated_content=_content("列表索引"),
        final_content={"key_points": "列表索引与切片"},  # 编辑层应覆盖生成层
    )
    await _insert_lesson(
        test_db,
        "lp-2",
        topic="字典操作",
        generated_content=_content("键值访问"),
    )

    plan = await service.create_draft(_create_request(["lp-1", "lp-2"]))

    assert plan.status == "condensing"
    assert plan.total_hours == 4  # 2 份教案 × 每份 2 课时
    assert [chapter.lesson_number for chapter in plan.chapters] == [1, 2]
    assert plan.chapters[0].topic == "列表操作"
    assert plan.chapters[0].key_points == "列表索引与切片"
    assert plan.chapters[1].key_points == "键值访问"
    assert plan.source_lesson_plan_ids == ["lp-1", "lp-2"]
    assert plan.class_names == ["2024级大数据1班"]


@pytest.mark.service
async def test_create_draft_rejects_unknown_lesson(service, test_db):
    await _insert_lesson(test_db, "lp-1", topic="列表操作", generated_content=_content("x"))
    with pytest.raises(ValueError, match="不存在"):
        await service.create_draft(_create_request(["lp-1", "lp-missing"]))


@pytest.mark.service
async def test_create_draft_rejects_lesson_without_content(service, test_db):
    await database_insert_empty_plan(test_db)
    with pytest.raises(ValueError, match="还没有生成内容"):
        await service.create_draft(_create_request(["lp-empty"]))


async def database_insert_empty_plan(test_db):
    await test_db.execute(
        """
        INSERT INTO lesson_plans
            (id, template_id, title, subject, grade, topic, status)
        VALUES ('lp-empty', 'yunlin-standard', '空教案', 'Python', '2024级', '空课题', 'draft')
        """,
        commit=True,
    )


@pytest.mark.service
async def test_create_draft_generates_experiment_names(service, test_db, monkeypatch):
    await _insert_lesson(test_db, "lp-1", topic="列表操作", generated_content=_content("a"))
    await _insert_lesson(test_db, "lp-2", topic="字典操作", generated_content=_content("b"))

    async def fake_ensure_names(chapters, **kwargs):
        assert kwargs["require_every_group"] is True
        prepared = [dict(chapter) for chapter in chapters]
        prepared[0]["experiment_name"] = "列表与字典上机"
        prepared[1]["experiment_name"] = ""
        return prepared, True

    monkeypatch.setattr(service_module, "ensure_experiment_names", fake_ensure_names)

    plan = await service.create_draft(
        _create_request(
            ["lp-1", "lp-2"],
            plan_types=["teaching_plan", "experiment_plan"],
            plan_date="2026-03-01",
            first_class_date=MONDAY,
            class_periods="3-4",
        )
    )
    await service._finalize_draft(plan.id)
    finalized = await service.get_course_plan(plan.id)

    assert finalized.chapters[0].experiment_name == "列表与字典上机"
    assert finalized.chapters[1].experiment_name == ""


@pytest.mark.service
async def test_create_draft_requires_experiment_metadata(service, test_db):
    await _insert_lesson(test_db, "lp-1", topic="列表操作", generated_content=_content("a"))
    with pytest.raises(ValueError, match="制表日期"):
        await service.create_draft(
            _create_request(["lp-1"], plan_types=["experiment_plan"])
        )


@pytest.mark.service
async def test_update_validates_experiment_names(service, test_db, monkeypatch):
    await _insert_lesson(test_db, "lp-1", topic="列表操作", generated_content=_content("a"))
    await _insert_lesson(test_db, "lp-2", topic="字典操作", generated_content=_content("b"))

    async def fake_ensure_names(chapters, **kwargs):
        prepared = [dict(chapter) for chapter in chapters]
        prepared[0]["experiment_name"] = "列表与字典上机"
        prepared[1]["experiment_name"] = ""
        return prepared, True

    monkeypatch.setattr(service_module, "ensure_experiment_names", fake_ensure_names)
    plan = await service.create_draft(
        _create_request(
            ["lp-1", "lp-2"],
            plan_types=["experiment_plan"],
            plan_date="2026-03-01",
            first_class_date=MONDAY,
            class_periods="3-4",
        )
    )
    await service._finalize_draft(plan.id)
    plan = await service.get_course_plan(plan.id)

    # 实验名称超过固定模板单行限制时应拒绝保存
    invalid_chapters = [
        chapter.model_copy(update={"experiment_name": "这是一个特别长的实验项目名称用来验证校验逻辑"})
        if index == 0
        else chapter
        for index, chapter in enumerate(plan.chapters)
    ]
    update = CoursePlanUpdateRequest(
        course_name=plan.course_name,
        grade=plan.grade,
        class_names=plan.class_names,
        academic_year=plan.academic_year,
        semester=plan.semester,
        teacher_name=plan.teacher_name,
        hours_per_lesson=plan.hours_per_lesson,
        start_week=plan.start_week,
        total_hours=plan.total_hours,
        plan_date=plan.plan_date,
        first_class_date=plan.first_class_date,
        class_periods=plan.class_periods,
        chapters=invalid_chapters,
    )
    with pytest.raises(ValueError, match="第 1 个实验名称"):
        await service.update_course_plan(plan.id, update)

    # 缺少实验名称的组同样拒绝
    empty_chapters = [
        chapter.model_copy(update={"experiment_name": ""})
        for chapter in plan.chapters
    ]
    with pytest.raises(ValueError, match="必须且只能有一个实验名称"):
        await service.update_course_plan(
            plan.id,
            CoursePlanUpdateRequest(
                course_name=plan.course_name,
                grade=plan.grade,
                class_names=plan.class_names,
                academic_year=plan.academic_year,
                semester=plan.semester,
                teacher_name=plan.teacher_name,
                hours_per_lesson=plan.hours_per_lesson,
                start_week=plan.start_week,
                total_hours=plan.total_hours,
                plan_date=plan.plan_date,
                first_class_date=plan.first_class_date,
                class_periods=plan.class_periods,
                chapters=empty_chapters,
            ),
        )


@pytest.mark.service
async def test_create_draft_condenses_points_via_ai(service, test_db, monkeypatch):
    await _insert_lesson(
        test_db,
        "lp-long",
        topic="异常处理",
        generated_content=_content(
            "掌握raise语句主动抛出异常的方法；掌握assert断言的语法与适用场景；掌握自定义异常类的定义及异常类型继承机制",
            difficult_points="依据业务逻辑设计合理的自定义异常类并正确处理异常继承关系，区分raise和assert的使用场景",
        ),
    )

    calls = []

    async def fake_brief_points(chapters, **kwargs):
        calls.append(len(chapters))
        prepared = [dict(chapter) for chapter in chapters]
        for chapter in prepared:
            chapter["key_points"] = "掌握raise与assert用法"
            chapter["difficult_points"] = "自定义异常类的设计"
        return prepared, True

    monkeypatch.setattr(service_module, "ensure_brief_points", fake_brief_points)

    plan = await service.create_draft(_create_request(["lp-long"]))
    assert plan.status == "condensing"
    await service._finalize_draft(plan.id)
    finalized = await service.get_course_plan(plan.id)
    assert calls == [1]
    assert finalized.status == "draft"
    assert finalized.chapters[0].key_points == "掌握raise与assert用法"
    assert finalized.chapters[0].difficult_points == "自定义异常类的设计"


@pytest.mark.service
async def test_create_draft_fails_when_condensation_fails(service, test_db, monkeypatch):
    await _insert_lesson(
        test_db,
        "lp-long",
        topic="异常处理",
        generated_content=_content(
            "掌握raise语句主动抛出异常的方法；掌握assert断言的语法与适用场景；掌握自定义异常类的定义及异常类型继承机制"
        ),
    )

    async def failing_brief_points(chapters, **kwargs):
        raise ValueError("重难点精简连续 3 次仍不符合每行 25 字要求：超时")

    monkeypatch.setattr(service_module, "ensure_brief_points", failing_brief_points)
    plan = await service.create_draft(_create_request(["lp-long"]))
    await service._finalize_draft(plan.id)
    finalized = await service.get_course_plan(plan.id)
    assert finalized.status == "draft"
    assert finalized.error_message and "重难点精简" in finalized.error_message
    # 精简失败时导出应被拦截并提示
    with pytest.raises(ValueError, match="未能自动精简"):
        await service.export_course_plan(plan.id)


@pytest.mark.service
async def test_update_condenses_overlong_points(service, test_db, monkeypatch):
    await _insert_lesson(test_db, "lp-1", topic="列表操作", generated_content=_content("a"))

    async def brief_ok(chapters, **kwargs):
        return [dict(chapter) for chapter in chapters], False

    async def brief_shorten(chapters, **kwargs):
        prepared = [dict(chapter) for chapter in chapters]
        for chapter in prepared:
            chapter["key_points"] = "掌握VLAN配置要点"
            chapter["difficult_points"] = "理解Trunk转发过程"
        return prepared, True

    monkeypatch.setattr(service_module, "ensure_brief_points", brief_ok)
    plan = await service.create_draft(_create_request(["lp-1"]))
    await service._finalize_draft(plan.id)
    plan = await service.get_course_plan(plan.id)

    # 用户把重点改超长后保存：立即入库并转后台精简
    monkeypatch.setattr(service_module, "ensure_brief_points", brief_shorten)
    updated = await service.update_course_plan(
        plan.id,
        CoursePlanUpdateRequest(
            course_name=plan.course_name,
            grade=plan.grade,
            class_names=plan.class_names,
            academic_year=plan.academic_year,
            semester=plan.semester,
            teacher_name=plan.teacher_name,
            hours_per_lesson=plan.hours_per_lesson,
            start_week=plan.start_week,
            total_hours=plan.total_hours,
            chapters=[
                chapter.model_copy(
                    update={
                        "key_points": "掌握raise语句主动抛出异常的方法；掌握assert断言的语法与适用场景；掌握自定义异常类的定义及异常类型继承机制"
                    }
                )
                for chapter in plan.chapters
            ],
        ),
    )
    assert updated.status == "condensing"
    await service._finalize_draft(plan.id)
    finalized = await service.get_course_plan(plan.id)
    assert finalized.status == "draft"
    assert finalized.chapters[0].key_points == "掌握VLAN配置要点"
    assert finalized.chapters[0].difficult_points == "理解Trunk转发过程"


@pytest.mark.slow
async def test_export_renders_fixed_templates(service, test_db, monkeypatch):
    async def fake_ensure_names(chapters, **kwargs):
        prepared = [dict(chapter) for chapter in chapters]
        prepared[0]["experiment_name"] = "列表与字典上机"
        prepared[1]["experiment_name"] = ""
        return prepared, True

    monkeypatch.setattr(service_module, "ensure_experiment_names", fake_ensure_names)

    await _insert_lesson(test_db, "lp-1", topic="列表操作", generated_content=_content("a"))
    await _insert_lesson(test_db, "lp-2", topic="字典操作", generated_content=_content("b"))
    plan = await service.create_draft(
        _create_request(
            ["lp-1", "lp-2"],
            plan_types=["teaching_plan", "experiment_plan"],
            plan_date="2026-03-01",
            class_schedules=[
                {
                    "class_name": "2024级大数据1班",
                    "weekday": 1,
                    "class_periods": "3-4",
                    "first_class_date": MONDAY,
                    "classroom": "实验楼101",
                }
            ],
        )
    )
    await service._finalize_draft(plan.id)

    file_path, media_type = await service.export_course_plan(plan.id)

    assert media_type == "application/zip"  # 1 份授课计划 + 1 份实验计划
    with zipfile.ZipFile(file_path) as archive:
        names = archive.namelist()
    assert len(names) == 2
    assert any("授课计划表" in name for name in names)
    assert any("实验计划表" in name for name in names)

    refreshed = await service.get_course_plan(plan.id)
    assert refreshed.status == "exported"
    assert len(refreshed.output_files) == 2


@pytest.mark.service
async def test_list_and_delete_course_plans(service, test_db):
    await _insert_lesson(test_db, "lp-1", topic="列表操作", generated_content=_content("a"))
    plan = await service.create_draft(_create_request(["lp-1"]))

    items, total = await service.list_course_plans()
    assert total == 1
    assert items[0].id == plan.id
    assert items[0].plan_types == ["teaching_plan"]

    await service.delete_course_plan(plan.id)
    assert await service.get_course_plan(plan.id) is None
    _, total_after = await service.list_course_plans()
    assert total_after == 0

    with pytest.raises(ValueError, match="不存在"):
        await service.delete_course_plan(plan.id)
