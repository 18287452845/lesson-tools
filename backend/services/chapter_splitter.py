"""
Course chapter splitting service using AI.
"""
import json
import re
from typing import List, Optional

from ..models.schemas import ChapterInfo
from .ai_provider import generate_with_ai


class ChapterSplitter:
    """
    AI-powered course chapter splitting service.

    Automatically splits a course into weekly chapters with topics,
    content summaries, and key concepts.
    """

    SYSTEM_PROMPT = """你是一位资深的课程设计专家，拥有20年教学经验和课程规划能力。
你擅长分析课程特点，合理规划教学进度，设计符合教育规律的课程大纲。"""

    CHAPTER_SPLIT_PROMPT = """请根据课程名称和教学周数，智能规划每周的教学主题和内容要点。

## 课程信息
- 课程名称：{course_name}
- 学科：{subject}
- 年级：{grade}
- 教学周数：第{start_week}周 到 第{end_week}周（共{total_weeks}周）
{additional_info}

## 输出要求
请返回JSON数组格式，每周一个对象，严格按照以下格式：

```json
[
  {{
    "week": 1,
    "topic": "本周课题（简明扼要，10-20字）",
    "content_summary": "本周教学内容概述，说明本周要讲授的主要内容和学习目标（100-200字）",
    "key_concepts": ["核心概念1", "核心概念2", "核心概念3"]
  }},
  {{
    "week": 2,
    "topic": "第二周课题",
    "content_summary": "第二周教学内容概述...",
    "key_concepts": ["概念1", "概念2", "概念3"]
  }}
]
```

## 设计要求
1. **课题命名**：
   - 要具体、可操作，适合2课时（90分钟）完成
   - 避免过于抽象或宽泛的表述
   - 体现本周的核心教学内容

2. **内容规划**：
   - 内容要循序渐进，符合认知规律
   - 前后周次应有逻辑关联和递进关系
   - 确保覆盖课程的完整知识体系
   - 每周重点突出，避免内容重复

3. **知识点分布**：
   - 基础知识在前，复杂概念在后
   - 理论与实践相结合
   - 考虑学生的接受能力

4. **格式要求**：
   - 必须返回纯JSON格式，不要包含其他说明文字
   - week字段必须从{start_week}开始，到{end_week}结束
   - 每个key_concepts数组包含3-5个核心概念

请直接输出JSON数组，不要添加任何其他文字。
"""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the chapter splitter.

        Args:
            provider: AI provider name ('deepseek' or 'anthropic')
            api_key: API key for the provider
            model: Model name to use
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model

    async def split_course_chapters(
        self,
        course_name: str,
        subject: str,
        grade: str,
        start_week: int,
        end_week: int,
        additional_info: Optional[str] = None,
    ) -> List[ChapterInfo]:
        """
        Split a course into weekly chapters using AI.

        Args:
            course_name: Name of the course
            subject: Subject area
            grade: Grade level
            start_week: Starting week number
            end_week: Ending week number
            additional_info: Optional additional information about the course

        Returns:
            List of ChapterInfo objects

        Raises:
            ValueError: If the AI response cannot be parsed
        """
        total_weeks = end_week - start_week + 1

        # Build additional info section
        additional_info_section = ""
        if additional_info:
            additional_info_section = f"\n- 补充说明：{additional_info}"

        # Build prompt
        prompt = self.CHAPTER_SPLIT_PROMPT.format(
            course_name=course_name,
            subject=subject,
            grade=grade,
            start_week=start_week,
            end_week=end_week,
            total_weeks=total_weeks,
            additional_info=additional_info_section,
        )

        # Call AI
        response = await generate_with_ai(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
        )

        # Parse response
        chapters_data = self._parse_json_response(response)

        # Validate and convert to ChapterInfo objects
        chapters = []
        for idx, data in enumerate(chapters_data):
            # Validate week number
            expected_week = start_week + idx
            if data.get("week") != expected_week:
                # Fix week number if incorrect
                data["week"] = expected_week

            try:
                chapter = ChapterInfo(**data)
                chapters.append(chapter)
            except Exception as e:
                raise ValueError(
                    f"Failed to parse chapter {idx + 1}: {str(e)}\nData: {data}"
                )

        # Final validation
        if len(chapters) != total_weeks:
            raise ValueError(
                f"Expected {total_weeks} chapters but got {len(chapters)}"
            )

        return chapters

    def _parse_json_response(self, content: str) -> List[dict]:
        """
        Parse JSON from AI response.

        Handles cases where JSON is wrapped in markdown code blocks.
        """
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        else:
            # Try without language specifier
            json_match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                content = json_match.group(1)

        # Parse JSON
        try:
            data = json.loads(content)
            if not isinstance(data, list):
                raise ValueError("Response must be a JSON array")
            return data
        except json.JSONDecodeError as e:
            # Try to fix common JSON errors
            # Remove trailing commas
            content = re.sub(r",\s*([}\]])", r"\1", content)

            try:
                data = json.loads(content)
                if not isinstance(data, list):
                    raise ValueError("Response must be a JSON array")
                return data
            except json.JSONDecodeError:
                raise ValueError(f"Failed to parse AI response as JSON: {e}\nContent: {content[:500]}")


async def split_course_chapters(
    course_name: str,
    subject: str,
    grade: str,
    start_week: int,
    end_week: int,
    additional_info: Optional[str] = None,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> List[ChapterInfo]:
    """
    Convenience function to split course chapters.

    Args:
        course_name: Name of the course
        subject: Subject area
        grade: Grade level
        start_week: Starting week number
        end_week: Ending week number
        additional_info: Optional additional information
        provider: AI provider name
        api_key: Optional API key
        model: Optional model name

    Returns:
        List of ChapterInfo objects
    """
    splitter = ChapterSplitter(provider, api_key, model)
    return await splitter.split_course_chapters(
        course_name, subject, grade, start_week, end_week, additional_info
    )
