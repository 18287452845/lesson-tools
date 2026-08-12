import json

from backend.services import textbook_generator


def test_ai_catalog_parser_flattens_nested_chapter_tree():
    generator = textbook_generator.TextbookChapterGenerator()
    content = json.dumps(
        [
            {
                "client_id": "chapter-1",
                "chapter_number": "第1章",
                "chapter_title": "Python基础",
                "children": [
                    {
                        "client_id": "section-1",
                        "chapter_number": "1.1",
                        "chapter_title": "开发环境",
                        "children": [
                            {
                                "client_id": "topic-1",
                                "chapter_number": "1.1.1",
                                "chapter_title": "安装解释器",
                            }
                        ],
                    }
                ],
            }
        ],
        ensure_ascii=False,
    )

    chapters = generator._parse_json_response(content)

    assert [chapter["client_id"] for chapter in chapters] == [
        "chapter-1",
        "section-1",
        "topic-1",
    ]
    assert chapters[1]["parent_chapter_id"] == "chapter-1"
    assert chapters[2]["parent_chapter_id"] == "section-1"


def test_ai_catalog_parser_infers_five_level_parent_relationships():
    generator = textbook_generator.TextbookChapterGenerator()
    items = generator._parse_json_response(
        json.dumps(
            [
                {"chapter_number": "1", "chapter_title": "大章节"},
                {"chapter_number": "1.1", "chapter_title": "二级"},
                {"chapter_number": "1.1.1", "chapter_title": "三级"},
                {"chapter_number": "1.1.1.1", "chapter_title": "四级"},
                {"chapter_number": "1.1.1.1.1", "chapter_title": "五级"},
            ],
            ensure_ascii=False,
        )
    )

    chapters = generator._infer_missing_hierarchy(items)

    assert chapters[0]["parent_chapter_id"] is None
    for index in range(1, len(chapters)):
        assert chapters[index]["parent_chapter_id"] == chapters[index - 1]["client_id"]
