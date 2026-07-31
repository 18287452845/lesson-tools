"""Render fixed-format Yunlin teaching and experiment plans.

The two resources are immutable application assets. Generation copies the DOCX
package and changes only ``word/document.xml`` so styles, relationships, page
geometry, and all other package parts remain byte-for-byte identical.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import zipfile
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Sequence

from docx import Document
from docx.enum.section import WD_ORIENT
from lxml import etree

from ..config import settings


CoursePlanType = Literal["teaching_plan", "experiment_plan"]

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
W = f"{{{W_NS}}}"


@dataclass(frozen=True)
class CoursePlanTemplateSpec:
    type: CoursePlanType
    template_id: str
    name: str
    path: Path
    sha256: str
    title: str
    table_shapes: tuple[tuple[int, int], ...]
    capacity: int


TEMPLATE_SPECS: dict[CoursePlanType, CoursePlanTemplateSpec] = {
    "teaching_plan": CoursePlanTemplateSpec(
        type="teaching_plan",
        template_id="yunlin-teaching-plan",
        name="云林教师授课计划表",
        path=settings.teaching_plan_template_path,
        sha256="1e08531f22f93dc7cfa6a15d53a4f43829f1cb1feb8ce96aa1203920756607b8",
        title="云南林业职业技术学院教师授课计划表",
        table_shapes=((4, 9), (4, 9), (5, 9), (5, 9), (5, 9), (6, 9)),
        capacity=16,
    ),
    "experiment_plan": CoursePlanTemplateSpec(
        type="experiment_plan",
        template_id="yunlin-experiment-plan",
        name="云林课程实验计划表",
        path=settings.experiment_plan_template_path,
        sha256="76217eb3db84a0f1ca931381341665108d2c0135f36de692a543f1fbb812c5f1",
        title="云南林业职业技术学院课程实验计划表",
        table_shapes=((20, 5),),
        capacity=18,
    ),
}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_course_plan_template(plan_type: CoursePlanType) -> dict[str, Any]:
    """Validate the fixed asset checksum and the structural rendering contract."""
    spec = TEMPLATE_SPECS[plan_type]
    errors: list[str] = []
    warnings: list[str] = []
    actual_sha256 = ""

    if not spec.path.is_file():
        errors.append(f"固定模板不存在：{spec.path}")
    elif spec.path.suffix.lower() != ".docx":
        errors.append("固定模板必须是 .docx 文件")
    else:
        actual_sha256 = _file_sha256(spec.path)
        if actual_sha256 != spec.sha256:
            errors.append("固定模板指纹不匹配，资源可能已被替换或修改")

        try:
            document = Document(str(spec.path))
            if len(document.sections) != 1:
                errors.append(f"模板应为 1 节，实际为 {len(document.sections)} 节")
            elif document.sections[0].orientation != WD_ORIENT.LANDSCAPE:
                errors.append("模板页面方向必须为横向")

            table_shapes = tuple(
                (len(table.rows), len(table.columns)) for table in document.tables
            )
            if table_shapes != spec.table_shapes:
                errors.append(
                    f"模板表格结构不匹配：期望 {spec.table_shapes}，实际 {table_shapes}"
                )

            titles = [p.text.strip() for p in document.paragraphs]
            expected_title_count = 6 if plan_type == "teaching_plan" else 1
            if titles.count(spec.title) != expected_title_count:
                errors.append(
                    f"模板标题数量不匹配：期望 {expected_title_count}，"
                    f"实际 {titles.count(spec.title)}"
                )

            if plan_type == "teaching_plan":
                header = [cell.text.replace("\n", "") for cell in document.tables[0].rows[0].cells]
                for required in ("课序周次", "内容摘要", "教学时数", "教学重点", "教学难点"):
                    if not any(required.replace(" ", "") in value.replace(" ", "") for value in header):
                        errors.append(f"授课计划模板缺少表头：{required}")
            else:
                header = [cell.text.replace("\n", "") for cell in document.tables[0].rows[0].cells]
                for required in ("实验序号", "实验项目名称", "授课时间", "实验室", "备注"):
                    if required not in header:
                        errors.append(f"实验计划模板缺少表头：{required}")
        except Exception as exc:
            errors.append(f"固定模板无法解析：{exc}")

    if spec.path.is_file() and spec.path.stat().st_size < 10_000:
        warnings.append("模板文件体积异常偏小")

    return {
        "template_id": spec.template_id,
        "type": spec.type,
        "name": spec.name,
        "is_valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "file_size": spec.path.stat().st_size if spec.path.is_file() else 0,
        "sha256": actual_sha256,
        "expected_sha256": spec.sha256,
        "capacity": spec.capacity,
        "checked_at": datetime.now().astimezone().isoformat(),
    }


def validate_all_course_plan_templates() -> list[dict[str, Any]]:
    return [
        validate_course_plan_template("teaching_plan"),
        validate_course_plan_template("experiment_plan"),
    ]


def require_valid_course_plan_template(plan_type: CoursePlanType) -> dict[str, Any]:
    report = validate_course_plan_template(plan_type)
    if not report["is_valid"]:
        raise ValueError(
            f"{report['name']}校验失败：" + "；".join(report["errors"])
        )
    return report


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return cleaned or "课程计划"


def _display_width(value: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in {"W", "F"} else 1 for ch in value)


def _fit_text(value: str, max_width: int) -> str:
    value = " ".join(str(value or "").split())
    if _display_width(value) <= max_width:
        return value
    result: list[str] = []
    width = 0
    for char in value:
        char_width = 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
        if width + char_width + 2 > max_width:
            break
        result.append(char)
        width += char_width
    return "".join(result).rstrip() + "…"


def _normalize_chapters(chapters: Iterable[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for chapter in chapters:
        if hasattr(chapter, "model_dump"):
            item = chapter.model_dump()
        else:
            item = dict(chapter)
        item["topic"] = str(item.get("topic") or "").strip()
        item["content_summary"] = str(item.get("content_summary") or "").strip()
        concepts = item.get("key_concepts") or []
        item["key_concepts"] = [str(value).strip() for value in concepts if str(value).strip()]
        item["experiment_name"] = str(item.get("experiment_name") or "").strip()
        normalized.append(item)
    return normalized


def _group_chapters(chapters: Iterable[Any], size: int = 2) -> list[list[dict[str, Any]]]:
    values = _normalize_chapters(chapters)
    return [values[index:index + size] for index in range(0, len(values), size)]


def _direct_paragraphs(root: etree._Element) -> list[etree._Element]:
    return root.xpath("/w:document/w:body/w:p", namespaces=NS)


def _direct_tables(root: etree._Element) -> list[etree._Element]:
    return root.xpath("/w:document/w:body/w:tbl", namespaces=NS)


def _direct_runs(paragraph: etree._Element) -> list[etree._Element]:
    return paragraph.xpath("./w:r", namespaces=NS)


def _set_page_break_before(paragraph: etree._Element) -> None:
    paragraph_properties = paragraph.find(W + "pPr")
    if paragraph_properties is None:
        paragraph_properties = etree.Element(W + "pPr")
        paragraph.insert(0, paragraph_properties)
    if paragraph_properties.find(W + "pageBreakBefore") is None:
        etree.SubElement(paragraph_properties, W + "pageBreakBefore")


def _set_run_text(
    run: etree._Element,
    value: str,
    *,
    underline: bool | None = None,
) -> None:
    for child in list(run):
        if child.tag != W + "rPr":
            run.remove(child)
    if underline is not None:
        run_properties = run.find(W + "rPr")
        if run_properties is None:
            run_properties = etree.Element(W + "rPr")
            run.insert(0, run_properties)
        underline_element = run_properties.find(W + "u")
        if underline_element is None:
            underline_element = etree.SubElement(run_properties, W + "u")
        underline_element.set(W + "val", "single" if underline else "none")
    text = etree.SubElement(run, W + "t")
    if value.startswith(" ") or value.endswith(" "):
        text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text.text = value


def _set_cell_text(cell: etree._Element, value: str) -> None:
    paragraphs = cell.xpath("./w:p", namespaces=NS)
    if not paragraphs:
        paragraph = etree.SubElement(cell, W + "p")
    else:
        paragraph = paragraphs[0]
        for extra in paragraphs[1:]:
            cell.remove(extra)

    runs = paragraph.xpath("./w:r", namespaces=NS)
    if runs:
        run = runs[0]
    else:
        run = etree.SubElement(paragraph, W + "r")

    for child in list(paragraph):
        if child.tag not in {W + "pPr", W + "r"} or (
            child.tag == W + "r" and child is not run
        ):
            paragraph.remove(child)

    for child in list(run):
        if child.tag != W + "rPr":
            run.remove(child)

    lines = str(value or "").splitlines() or [""]
    for index, line in enumerate(lines):
        if index:
            etree.SubElement(run, W + "br")
        text = etree.SubElement(run, W + "t")
        if line.startswith(" ") or line.endswith(" "):
            text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        text.text = line


def _set_cell_runs(
    cell: etree._Element,
    segments: Sequence[tuple[str, bool]],
) -> None:
    """Replace cell text with explicitly styled runs while preserving layout."""
    paragraphs = cell.xpath("./w:p", namespaces=NS)
    if not paragraphs:
        paragraph = etree.SubElement(cell, W + "p")
    else:
        paragraph = paragraphs[0]
        for extra in paragraphs[1:]:
            cell.remove(extra)

    existing_runs = paragraph.xpath("./w:r", namespaces=NS)
    base_run = existing_runs[0] if existing_runs else etree.Element(W + "r")
    for child in list(paragraph):
        if child.tag != W + "pPr":
            paragraph.remove(child)

    for text, underline in segments:
        run = deepcopy(base_run)
        _set_run_text(run, text, underline=underline)
        paragraph.append(run)


def _set_experiment_schedule_cell(
    cell: etree._Element,
    *,
    week: int,
    weekday: str,
    periods: str,
    lesson_date: date,
) -> None:
    """Match Yunlin's schedule style with underlines on every variable value."""
    _set_cell_runs(
        cell,
        (
            ("第", False),
            (f" {week:02d} ", True),
            ("周  星期", False),
            (f" {weekday} ", True),
            ("  第", False),
            (f" {periods} ", True),
            ("节    ", False),
            (f" {lesson_date.month} ", True),
            ("月 ", False),
            (f" {lesson_date.day:02d} ", True),
            ("日", False),
        ),
    )


def _table_cells(row: etree._Element) -> list[etree._Element]:
    return row.xpath("./w:tc", namespaces=NS)


def _patch_docx(
    template_path: Path,
    output_path: Path,
    patcher: Callable[[etree._Element], None],
) -> Path:
    with zipfile.ZipFile(template_path, "r") as source:
        document_xml = source.read("word/document.xml")
        root = etree.fromstring(document_xml)
        patcher(root)
        patched_xml = etree.tostring(
            root,
            encoding="UTF-8",
            xml_declaration=True,
            standalone=True,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w") as target:
            for item in source.infolist():
                payload = patched_xml if item.filename == "word/document.xml" else source.read(item.filename)
                copied = deepcopy(item)
                target.writestr(copied, payload)
    return output_path


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("首课日期必须是 YYYY-MM-DD 格式") from exc


def _format_classes(class_names: Sequence[str]) -> str:
    names = [str(name).strip() for name in class_names if str(name).strip()]
    if len(names) <= 1:
        return "".join(names)

    prefix = names[0]
    for name in names[1:]:
        while prefix and not name.startswith(prefix):
            prefix = prefix[:-1]

    reversed_names = [name[::-1] for name in names]
    reversed_suffix = reversed_names[0]
    for name in reversed_names[1:]:
        while reversed_suffix and not name.startswith(reversed_suffix):
            reversed_suffix = reversed_suffix[:-1]
    suffix = reversed_suffix[::-1]

    if prefix and suffix and len(prefix) + len(suffix) < min(map(len, names)):
        middle = [name[len(prefix):len(name) - len(suffix)] for name in names]
        if all(middle):
            return f"{prefix}{'、'.join(middle)}{suffix}"
    return "、".join(names)


def _compact_topic_lines(topics: Sequence[str]) -> list[str]:
    if len(topics) == 2:
        for separator in ("：", ":"):
            if separator in topics[0] and separator in topics[1]:
                first_prefix, first_suffix = topics[0].rsplit(separator, 1)
                second_prefix, second_suffix = topics[1].rsplit(separator, 1)
                if first_prefix.strip() == second_prefix.strip():
                    first_suffix = first_suffix.strip()
                    second_suffix = second_suffix.strip()
                    if second_suffix == f"{first_suffix}实训":
                        second_suffix = f"{first_suffix}（含实训）"
                        summary = second_suffix
                    else:
                        summary = f"{first_suffix}、{second_suffix}"
                    return [
                        _fit_text(first_prefix.strip(), 55),
                        _fit_text(summary, 55),
                    ]
    return [_fit_text(topic, 55) for topic in topics[:2]]


class CoursePlanRenderer:
    """Create fixed teaching/experiment plan documents from a batch schedule."""

    teaching_slots = ((0, 2), (0, 3), (1, 2), (1, 3), (2, 2), (2, 3), (2, 4),
                      (3, 2), (3, 3), (3, 4), (4, 2), (4, 3), (4, 4),
                      (5, 2), (5, 3), (5, 4))

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = Path(output_dir or settings.output_dir)

    def render_teaching_plan(
        self,
        *,
        batch_task_id: str,
        course_name: str,
        grade: str,
        class_names: Sequence[str],
        academic_year: str,
        semester: int,
        teacher_name: str,
        total_hours: int,
        hours_per_lesson: int,
        start_week: int,
        chapters: Iterable[Any],
        location: str | None = None,
    ) -> str:
        require_valid_course_plan_template("teaching_plan")
        groups = _group_chapters(chapters)
        spec = TEMPLATE_SPECS["teaching_plan"]
        if len(groups) > spec.capacity:
            raise ValueError(f"授课计划最多容纳 {spec.capacity} 周，当前为 {len(groups)} 周")

        class_display = _format_classes(class_names)
        if not class_display:
            raise ValueError("同步生成授课计划时必须选择至少一个班级")

        output_name = _safe_filename(
            f"{teacher_name}-{grade}《{course_name}》授课计划表.docx"
        )
        output_path = self.output_dir / f"{batch_task_id}_{output_name}"

        def patch(root: etree._Element) -> None:
            paragraphs = _direct_paragraphs(root)
            for title_index in (4, 8, 10, 13, 16):
                _set_page_break_before(paragraphs[title_index])
            for paragraph_index in (1, 5, 9, 11, 14, 17):
                runs = _direct_runs(paragraphs[paragraph_index])
                if len(runs) < 14:
                    raise ValueError("授课计划元数据段结构已改变")
                _set_run_text(runs[1], f" {course_name}")
                _set_run_text(runs[4], academic_year)
                _set_run_text(runs[6], str(semester))
                _set_run_text(runs[8], "")
                _set_run_text(runs[9], "")
                _set_run_text(runs[10], class_display)
                _set_run_text(runs[11], "")
                _set_run_text(runs[13], teacher_name)

            tables = _direct_tables(root)
            for slot_index, (table_index, row_index) in enumerate(self.teaching_slots):
                row = tables[table_index].xpath("./w:tr", namespaces=NS)[row_index]
                cells = _table_cells(row)
                if len(cells) != 9:
                    raise ValueError("授课计划数据行结构已改变")
                if slot_index >= len(groups):
                    for cell in cells:
                        _set_cell_text(cell, "")
                    continue

                group = groups[slot_index]
                weekly_hours = len(group) * hours_per_lesson
                theory_hours = weekly_hours // 2
                practice_hours = weekly_hours - theory_hours
                topics = [item["topic"] for item in group if item["topic"]]
                concepts = [
                    concept for item in group for concept in item.get("key_concepts", [])
                ]
                summaries = [
                    item["content_summary"] for item in group if item.get("content_summary")
                ]

                focus = "、".join(dict.fromkeys(concepts))
                if not focus:
                    focus = summaries[0] if summaries else f"掌握{'、'.join(topics)}"
                difficulty = "、".join(dict.fromkeys(concepts[-2:]))
                if difficulty:
                    difficulty = f"{difficulty}的综合运用"
                else:
                    difficulty = summaries[-1] if summaries else f"综合运用{'、'.join(topics)}"
                assignment_lines = [
                    "1. 课后练习",
                    "2. 实验评估",
                ]

                values = (
                    str(start_week + slot_index),
                    "\n".join(_compact_topic_lines(topics)),
                    str(theory_hours),
                    str(practice_hours),
                    str(weekly_hours),
                    _fit_text(focus, 44),
                    _fit_text(difficulty, 40),
                    (location or "机房") if _display_width(location or "") <= 8 else "机房",
                    "\n".join(assignment_lines),
                )
                for cell, value in zip(cells, values):
                    _set_cell_text(cell, value)

            total_row = tables[5].xpath("./w:tr", namespaces=NS)[5]
            total_cells = _table_cells(total_row)
            theory_total = total_hours // 2
            practice_total = total_hours - theory_total
            for index, value in ((1, "总课时"), (2, str(theory_total)),
                                 (3, str(practice_total)), (4, str(total_hours))):
                _set_cell_text(total_cells[index], value)

        return str(_patch_docx(spec.path, output_path, patch))

    def render_experiment_plans(
        self,
        *,
        batch_task_id: str,
        course_name: str,
        grade: str,
        class_names: Sequence[str],
        academic_year: str,
        semester: int,
        teacher_name: str,
        plan_date: str | date,
        first_class_date: str | date,
        class_periods: str,
        hours_per_lesson: int,
        start_week: int,
        chapters: Iterable[Any],
        location: str,
    ) -> list[str]:
        require_valid_course_plan_template("experiment_plan")
        names = [str(name).strip() for name in class_names if str(name).strip()]
        if not names:
            raise ValueError("同步生成实验计划时必须选择至少一个班级")

        groups = _group_chapters(chapters)
        explicit_experiments = any(
            item.get("experiment_name") for group in groups for item in group
        )
        schedule: list[tuple[int, list[dict[str, Any]]]] = []
        for group_index, group in enumerate(groups):
            if explicit_experiments and not any(item.get("experiment_name") for item in group):
                continue
            schedule.append((group_index, group))

        spec = TEMPLATE_SPECS["experiment_plan"]
        if len(schedule) > spec.capacity:
            raise ValueError(f"实验计划最多容纳 {spec.capacity} 条，当前为 {len(schedule)} 条")

        first_date = _parse_date(first_class_date)
        signed_date = _parse_date(plan_date)
        periods = str(class_periods).strip().replace("第", "").replace("节", "")
        weekday_names = "一二三四五六日"
        outputs: list[str] = []

        for class_name in names:
            output_name = _safe_filename(
                f"{teacher_name}-{class_name}《{course_name}》课程实验计划表.docx"
            )
            output_path = self.output_dir / f"{batch_task_id}_{output_name}"

            def patch(root: etree._Element) -> None:
                paragraphs = _direct_paragraphs(root)
                runs = _direct_runs(paragraphs[1])
                if len(runs) < 23:
                    raise ValueError("实验计划元数据段结构已改变")
                _set_run_text(runs[1], f" {course_name}", underline=True)
                _set_run_text(runs[3], f"{academic_year} ", underline=True)
                _set_run_text(runs[5], str(semester), underline=True)
                _set_run_text(runs[7], f"{class_name} ", underline=True)
                for run_index in (8, 9, 10, 11, 12):
                    _set_run_text(runs[run_index], "")
                _set_run_text(runs[14], teacher_name, underline=True)
                _set_run_text(runs[16], str(signed_date.year), underline=True)
                _set_run_text(runs[17], "")
                _set_run_text(runs[19], str(signed_date.month), underline=True)
                _set_run_text(runs[21], f"{signed_date.day:02d}", underline=True)

                table = _direct_tables(root)[0]
                rows = table.xpath("./w:tr", namespaces=NS)
                for row_index in range(1, 19):
                    if row_index > len(schedule):
                        table.remove(rows[row_index])
                        continue

                    cells = _table_cells(rows[row_index])
                    group_index, group = schedule[row_index - 1]
                    explicit = [
                        item["experiment_name"] for item in group if item.get("experiment_name")
                    ]
                    topics = [item["topic"] for item in group if item.get("topic")]
                    project = "、".join(explicit)
                    if not project:
                        project = "上机实验：" + "、".join(topics)
                    lesson_date = first_date + timedelta(days=7 * group_index)
                    week = start_week + group_index
                    values = (
                        f"实验{row_index}",
                        _fit_text(project, 58),
                        _fit_text(location, 18),
                        "",
                    )
                    for cell, value in zip((cells[0], cells[1], cells[3], cells[4]), values):
                        _set_cell_text(cell, value)
                    _set_experiment_schedule_cell(
                        cells[2],
                        week=week,
                        weekday=weekday_names[lesson_date.weekday()],
                        periods=periods,
                        lesson_date=lesson_date,
                    )

                total_cells = _table_cells(rows[19])
                total_hours = len(schedule) * hours_per_lesson
                _set_cell_text(total_cells[1], f"   {total_hours}    学时")

            outputs.append(str(_patch_docx(spec.path, output_path, patch)))

        return outputs
