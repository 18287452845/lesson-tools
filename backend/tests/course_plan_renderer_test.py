import zipfile
import pathlib

import pytest
import pydantic
from docx import Document
from docx.oxml.ns import qn

from backend.config import settings
from backend.models import schemas
from backend.services import course_plan_renderer


def _chapters(count: int = 32, *, with_experiment_names: bool = True):
    return [
        schemas.ChapterInfo(
            lesson_number=index,
            topic=f"任务{index} Windows服务器安全配置",
            content_summary=f"掌握第{index}项服务器配置与安全验证方法",
            key_concepts=[f"配置{index}", "安全验证"],
            experiment_name=(
                f"安全配置实验{(index + 1) // 2}"
                if with_experiment_names and index % 2 == 1
                else ""
            ),
        )
        for index in range(1, count + 1)
    ]


def _all_text(path: str | pathlib.Path) -> str:
    document = Document(str(path))
    return "\n".join(
        [paragraph.text for paragraph in document.paragraphs]
        + [
            cell.text
            for table in document.tables
            for row in table.rows
            for cell in row.cells
        ]
    )


def _assert_preserved_parts(reference: pathlib.Path, generated: pathlib.Path):
    with zipfile.ZipFile(reference) as source, zipfile.ZipFile(generated) as output:
        assert set(source.namelist()) == set(output.namelist())
        for name in source.namelist():
            if name != "word/document.xml":
                assert output.read(name) == source.read(name), name


def test_fixed_course_plan_templates_are_valid():
    reports = course_plan_renderer.validate_all_course_plan_templates()

    assert {report["type"] for report in reports} == {
        "teaching_plan",
        "experiment_plan",
    }
    assert all(report["is_valid"] for report in reports)
    assert all(report["sha256"] == report["expected_sha256"] for report in reports)


def test_render_teaching_and_per_class_experiment_plans(tmp_path: pathlib.Path):
    renderer = course_plan_renderer.CoursePlanRenderer(tmp_path)
    chapters = _chapters()

    teaching_path = pathlib.Path(
        renderer.render_teaching_plan(
            batch_task_id="batch-1",
            course_name="Windows服务器安全配置",
            grade="24级",
            class_names=["24级信息安全技术应用1班", "24级信息安全技术应用2班"],
            academic_year="2025-2026",
            semester=2,
            teacher_name="李阳",
            total_hours=64,
            hours_per_lesson=2,
            start_week=1,
            chapters=chapters,
            location="慧心楼3516，实训楼204",
        )
    )
    experiment_paths = [
        pathlib.Path(path)
        for path in renderer.render_experiment_plans(
            batch_task_id="batch-1",
            course_name="Windows服务器安全配置",
            grade="24级",
            class_names=["24级信息安全技术应用1班", "24级信息安全技术应用2班"],
            academic_year="2025-2026",
            semester=2,
            teacher_name="李阳",
            plan_date="2026-02-25",
            first_class_date="2026-03-05",
            class_periods="3-4",
            hours_per_lesson=2,
            start_week=2,
            chapters=chapters,
            location="",
            class_schedules=[
                {
                    "class_name": "24级信息安全技术应用1班",
                    "weekday": 4,
                    "class_periods": "3-4",
                    "first_class_date": "2026-03-05",
                    "classroom": "慧心楼3516",
                },
                {
                    "class_name": "24级信息安全技术应用2班",
                    "weekday": 5,
                    "class_periods": "5-6",
                    "first_class_date": "2026-03-06",
                    "classroom": "实训楼204",
                },
            ],
        )
    ]

    assert teaching_path.is_file()
    assert len(experiment_paths) == 2
    teaching = Document(teaching_path)
    assert len(teaching.tables) == 6
    assert teaching.tables[-1].rows[-1].cells[2].text == "32"
    assert teaching.tables[-1].rows[-1].cells[3].text == "32"
    assert teaching.tables[-1].rows[-1].cells[4].text == "64"
    teaching_text = _all_text(teaching_path)
    assert "24级信息安全技术应用1、2班" in teaching_text
    assert "慧心楼3516，实训楼204" in teaching_text
    assert "任务32 Windows服务器安全配置" in teaching_text

    expectations = (
        ("24级信息安全技术应用1班", "四", "3-4", "05", "12", "慧心楼3516"),
        ("24级信息安全技术应用2班", "五", "5-6", "06", "13", "实训楼204"),
    )
    for output_index, (path, expectation) in enumerate(zip(
        experiment_paths,
        expectations,
    )):
        class_name, weekday, periods, first_day, second_day, classroom = expectation
        metadata_runs = Document(path).paragraphs[1].runs
        text = _all_text(path)
        assert class_name in text
        assert f"第 02 周  星期 {weekday}   第 {periods} 节     3 月  {first_day} 日" in text
        assert f"第 03 周  星期 {weekday}   第 {periods} 节     3 月  {second_day} 日" in text
        assert classroom in text
        assert "32    学时" in text
        assert all(metadata_runs[index].underline is True for index in (1, 3, 5, 7, 14, 16, 19, 21))
        experiment_table = Document(path).tables[0]
        assert len(experiment_table.rows) == 18
        assert experiment_table.rows[1].cells[3].text == classroom
        assert experiment_table.rows[1].cells[1].text == "安全配置实验1"
        assert "\n" not in experiment_table.rows[1].cells[1].text
        assert "…" not in experiment_table.rows[1].cells[1].text
        assert experiment_table.rows[1].cells[1]._tc.tcPr.find(qn("w:noWrap")) is not None
        assert all(
            any(cell.text.strip() for cell in row.cells)
            for row in experiment_table.rows[1:-1]
        )
        if output_index == 0:
            schedule_runs = experiment_table.rows[1].cells[2].paragraphs[0].runs
            assert [(run.text, run.underline) for run in schedule_runs] == [
                ("第", False),
                (" 02 ", True),
                ("周  星期", False),
                (" 四 ", True),
                ("  第", False),
                (" 3-4 ", True),
                ("节    ", False),
                (" 3 ", True),
                ("月 ", False),
                (" 05 ", True),
                ("日", False),
            ]

    _assert_preserved_parts(settings.teaching_plan_template_path, teaching_path)
    _assert_preserved_parts(settings.experiment_plan_template_path, experiment_paths[0])


def test_explicit_experiment_names_filter_non_experiment_weeks(tmp_path: pathlib.Path):
    chapters = _chapters(8, with_experiment_names=False)
    chapters[0].experiment_name = "认识Windows服务"
    chapters[4].experiment_name = "配置IIS安全功能"
    renderer = course_plan_renderer.CoursePlanRenderer(tmp_path)

    output = pathlib.Path(
        renderer.render_experiment_plans(
            batch_task_id="batch-2",
            course_name="Windows服务器安全配置",
            grade="24级",
            class_names=["24级信息安全技术应用1班"],
            academic_year="2025-2026",
            semester=2,
            teacher_name="李阳",
            plan_date="2026-02-25",
            first_class_date="2026-03-05",
            class_periods="3-4",
            hours_per_lesson=2,
            start_week=2,
            chapters=chapters,
            location="慧心楼3516",
        )[0]
    )
    document = Document(output)

    assert len(document.tables[0].rows) == 4
    assert document.tables[0].rows[1].cells[1].text == "认识Windows服务"
    assert document.tables[0].rows[2].cells[1].text == "配置IIS安全功能"
    assert "第 04 周" in document.tables[0].rows[2].cells[2].text
    assert "4    学时" in document.tables[0].rows[-1].cells[2].text


def test_experiment_plan_rejects_names_that_would_wrap(tmp_path: pathlib.Path):
    chapters = _chapters(2, with_experiment_names=False)
    chapters[0].experiment_name = "这是一个明显超过固定模板单行容量的实验项目名称"
    renderer = course_plan_renderer.CoursePlanRenderer(tmp_path)

    with pytest.raises(ValueError, match="不能超过 18 个字符"):
        renderer.render_experiment_plans(
            batch_task_id="batch-invalid-name",
            course_name="Windows服务器安全配置",
            grade="24级",
            class_names=["24级信息安全技术应用1班"],
            academic_year="2025-2026",
            semester=2,
            teacher_name="李阳",
            plan_date="2026-02-25",
            first_class_date="2026-03-05",
            class_periods="3-4",
            hours_per_lesson=2,
            start_week=2,
            chapters=chapters,
            location="慧心楼3516",
        )


def test_batch_plan_request_requires_fixed_schedule_fields():
    with pytest.raises(pydantic.ValidationError, match="学年"):
        schemas.BatchTaskCreateRequest(
            course_name="网络安全",
            subject="信息安全技术",
            grade="2024级",
            template_id="yunlin-standard",
            total_hours=4,
            chapters=_chapters(2),
            class_ids=["class-1"],
            supplemental_artifacts=["teaching_plan"],
        )

    request = schemas.BatchTaskCreateRequest(
        course_name="网络安全",
        subject="信息安全技术",
        grade="2024级",
        template_id="yunlin-standard",
        total_hours=4,
        chapters=_chapters(2),
        class_ids=["class-1"],
        supplemental_artifacts=["teaching_plan"],
        academic_year="2025-2026",
        semester=2,
        teacher_name="李阳",
    )
    assert request.plan_date is None
