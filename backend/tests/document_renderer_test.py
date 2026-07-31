from docx import Document
from docx.oxml.ns import qn

from backend.services import document_renderer


def test_clean_text_removes_blank_lines_without_inventing_line_breaks():
    renderer = document_renderer.DocumentRenderer()

    text = "第一项完成。  2. 第二项继续\r\n\r\n  【教师】讲解  \n   \n【学生】练习"

    assert renderer._clean_text_for_output(text) == (
        "第一项完成。 2. 第二项继续\n【教师】讲解\n【学生】练习"
    )


def test_process_data_adds_role_markers_and_numeric_template_duration():
    renderer = document_renderer.DocumentRenderer()

    processed = renderer._process_data(
        {
            "duration": "2课时",
            "teaching_steps": [
                {
                    "stage": "传授新知",
                    "duration": "30分钟",
                    "teacher_activity": "讲解配置原理",
                    "student_activity": "完成同步操作",
                    "design_intent": "建立知识与操作的联系",
                }
            ],
        }
    )

    assert processed["duration"] == "2"
    assert processed["teaching_steps"][0]["teacher_activity"].startswith("【教师】")
    assert processed["teaching_steps"][0]["student_activity"].startswith("【学生】")


def test_combine_documents_adds_page_break_and_keeps_sectpr_last(
    temp_dir,
    monkeypatch,
):
    first_path = temp_dir / "first.docx"
    second_path = temp_dir / "second.docx"

    first_doc = Document()
    first_doc.add_paragraph("教案一")
    first_doc.save(first_path)

    second_doc = Document()
    second_doc.add_paragraph("教案二")
    second_doc.save(second_path)

    renderer = document_renderer.DocumentRenderer()
    monkeypatch.setattr(renderer, "output_dir", temp_dir)

    output_path = renderer._combine_documents_with_page_breaks(
        [str(first_path), str(second_path)],
        course_name="测试课程",
        document_number=1,
        week_number=1,
    )

    combined = Document(output_path)
    page_breaks = [
        element
        for element in combined.element.body.iter()
        if element.tag == qn("w:br") and element.get(qn("w:type")) == "page"
    ]

    assert len(page_breaks) == 1
    assert [paragraph.text for paragraph in combined.paragraphs if paragraph.text] == [
        "教案一",
        "教案二",
    ]
    assert combined.element.body[-1].tag == qn("w:sectPr")
