from backend.api.textbooks import (
    _calculate_textbook_total_hours,
    _count_main_chapters,
    _normalize_chapter_hierarchy,
)
from backend.models import schemas


def _chapter(
    chapter_id: str,
    hours: int | None,
    parent_id: str | None = None,
    chapter_number: str | None = None,
    chapter_title: str | None = None,
) -> schemas.TextbookChapterInfo:
    return schemas.TextbookChapterInfo(
        id=chapter_id,
        textbook_id="textbook-1",
        chapter_number=chapter_number or chapter_id,
        chapter_title=chapter_title or chapter_id,
        hours_required=hours,
        parent_chapter_id=parent_id,
        created_at="2026-08-10T00:00:00",
        updated_at="2026-08-10T00:00:00",
    )


def test_calculate_textbook_total_hours_sums_flat_chapters():
    chapters = [
        _chapter("chapter-1", 32),
        _chapter("chapter-2", 40),
    ]

    assert _calculate_textbook_total_hours(chapters) == 72


def test_calculate_textbook_total_hours_avoids_parent_child_double_counting():
    chapters = [
        _chapter("chapter-1", 8),
        _chapter("section-1", 2, "chapter-1"),
        _chapter("section-2", 2, "chapter-1"),
        _chapter("chapter-2", 4),
    ]

    assert _calculate_textbook_total_hours(chapters) == 12


def test_calculate_textbook_total_hours_uses_more_detailed_child_total():
    chapters = [
        _chapter("chapter-1", 8),
        _chapter("section-1", 4, "chapter-1"),
        _chapter("section-2", 6, "chapter-1"),
    ]

    assert _calculate_textbook_total_hours(chapters) == 10


def test_count_main_chapters_excludes_children():
    chapters = [
        _chapter("chapter-1", 8),
        _chapter("section-1", 2, "chapter-1"),
        _chapter("section-2", 2, "chapter-1"),
        _chapter("chapter-2", 4),
    ]

    assert _count_main_chapters(chapters) == 2


def test_legacy_flat_project_catalog_counts_only_nine_main_chapters():
    chapters = []
    for project_number in range(1, 10):
        chapters.append(
            _chapter(
                f"project-{project_number}",
                None,
                chapter_number=f"项目{project_number}",
            )
        )
        if project_number >= 7:
            chapters.append(
                _chapter(
                    f"project-{project_number}-item-1",
                    None,
                    chapter_number="一、",
                )
            )
    chapters.extend(
        [
            _chapter("appendix-a", None, chapter_number="附录A"),
            _chapter("appendix-b", None, chapter_number="附录B"),
        ]
    )

    normalized = _normalize_chapter_hierarchy(chapters)
    by_id = {chapter.id: chapter for chapter in normalized}

    for project_number in range(7, 10):
        assert (
            by_id[f"project-{project_number}-item-1"].parent_chapter_id
            == f"project-{project_number}"
        )
    assert _count_main_chapters(normalized) == 9


def test_part_headings_group_eighteen_numbered_chapters_without_being_counted():
    chapters = []
    chapter_ranges = ((1, 10), (11, 16), (17, 18))
    for part_number, (start, end) in enumerate(chapter_ranges, 1):
        chapters.append(
            _chapter(
                f"part-{part_number}",
                None,
                chapter_number=f"第{part_number}篇",
            )
        )
        for chapter_number in range(start, end + 1):
            chapter_id = f"chapter-{chapter_number}"
            chapters.append(
                _chapter(
                    chapter_id,
                    None,
                    chapter_number=f"第{chapter_number}章",
                )
            )
            chapters.append(
                _chapter(
                    f"section-{chapter_number}-1",
                    None,
                    parent_id=chapter_id,
                    chapter_number=f"{chapter_number}.1",
                )
            )

    normalized = _normalize_chapter_hierarchy(chapters)
    by_id = {chapter.id: chapter for chapter in normalized}

    assert by_id["chapter-1"].parent_chapter_id == "part-1"
    assert by_id["chapter-11"].parent_chapter_id == "part-2"
    assert by_id["chapter-17"].parent_chapter_id == "part-3"
    assert _count_main_chapters(normalized) == 18
