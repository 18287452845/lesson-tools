import pytest

from backend.models.schemas import GeneratedContent


@pytest.mark.unit
def test_generated_content_normalizes_ai_text_lists():
    content = GeneratedContent(
        reflection=["First observation", "Second observation"],
        online_resources=["Resource A", "Resource B"],
        key_points=["Point A", "Point B"],
    )

    assert content.reflection == "First observation\nSecond observation"
    assert content.online_resources == "Resource A\nResource B"
    assert content.key_points == "Point A\nPoint B"


@pytest.mark.unit
def test_generated_content_has_optional_online_resources():
    content = GeneratedContent(key_points="A key point")

    assert content.online_resources is None
