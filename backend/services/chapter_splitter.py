"""
Course chapter splitting service using AI.

Supports:
- AI-powered automatic chapter generation based on total hours
- Manual chapter input (user provides chapter titles)
"""
import json
import re
from typing import List, Optional

from ..config import settings
from ..models.schemas import ChapterInfo
from .ai_provider import generate_with_ai, AIProviderFactory


class ChapterSplitter:
    """
    AI-powered course chapter splitting service.

    Automatically generates lesson plan chapters based on total hours,
    or parses user-provided chapter titles.
    """

    SYSTEM_PROMPT = """你是一位资深的课程设计专家，拥有20年教学经验和课程规划能力。
你擅长分析课程特点，合理规划教学进度，设计符合教育规律的课程大纲。"""

    CHAPTER_SPLIT_PROMPT = """请根据课程名称和教案数量，智能规划每份教案的教学主题和内容要点。

## 课程信息
- 课程名称：{course_name}
- 学科：{subject}
- 年级：{grade}
- 总课时：{total_hours} 课时
- 每份教案课时：{hours_per_lesson} 课时
- 教案数量：{num_lessons} 份
{additional_info}

## 输出要求
请返回JSON数组格式，每份教案一个对象，严格按照以下格式：

```json
[
  {{
    "lesson_number": 1,
    "topic": "本教案课题（简明扼要，10-20字）",
    "content_summary": "本教案教学内容概述，说明要讲授的主要内容和学习目标（100-200字）",
    "key_concepts": ["核心概念1", "核心概念2", "核心概念3"]
  }},
  {{
    "lesson_number": 2,
    "topic": "第二份教案课题",
    "content_summary": "第二份教案教学内容概述...",
    "key_concepts": ["概念1", "概念2", "概念3"]
  }}
]
```

## 设计要求
1. **课题命名**：
   - 要具体、可操作，适合{hours_per_lesson}课时完成
   - 避免过于抽象或宽泛的表述
   - 体现教案的核心教学内容

2. **内容规划**：
   - 内容要循序渐进，符合认知规律
   - 前后教案应有逻辑关联和递进关系
   - 确保覆盖课程的完整知识体系
   - 每份教案重点突出，避免内容重复

3. **知识点分布**：
   - 基础知识在前，复杂概念在后
   - 理论与实践相结合
   - 考虑学生的接受能力

4. **格式要求**：
   - 必须返回纯JSON格式，不要包含其他说明文字
   - lesson_number字段必须从1开始，到{num_lessons}结束
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
        total_hours: int,
        hours_per_lesson: int = 2,
        chapters_input: Optional[str] = None,
        additional_info: Optional[str] = None,
    ) -> List[ChapterInfo]:
        """
        Generate chapters based on total hours.

        Supports two modes:
        - Manual: User provides chapter titles (one per line)
        - AI: Automatically generate chapters

        Args:
            course_name: Name of the course
            subject: Subject area
            grade: Grade level
            total_hours: Total course hours (e.g., 64, 72)
            hours_per_lesson: Hours per lesson plan (default 2)
            chapters_input: Optional user-provided chapters (one per line)
            additional_info: Optional additional information about the course

        Returns:
            List of ChapterInfo objects

        Raises:
            ValueError: If the response cannot be parsed
        """
        num_lessons = total_hours // hours_per_lesson

        if chapters_input and chapters_input.strip():
            # Mode 1: Parse user-provided chapters
            return self._parse_manual_chapters(chapters_input, num_lessons)
        else:
            # Mode 2: AI-generated chapters
            return await self._generate_ai_chapters(
                course_name, subject, grade,
                total_hours, hours_per_lesson, num_lessons,
                additional_info
            )

    def _parse_manual_chapters(
        self,
        chapters_input: str,
        num_lessons: int
    ) -> List[ChapterInfo]:
        """
        Parse user-provided chapter titles.

        Args:
            chapters_input: User input with one chapter per line
            num_lessons: Expected number of lessons

        Returns:
            List of ChapterInfo objects
        """
        lines = [
            line.strip()
            for line in chapters_input.strip().split('\n')
            if line.strip()
        ]

        chapters = []
        for i in range(num_lessons):
            lesson_number = i + 1
            if i < len(lines):
                topic = lines[i]
            else:
                # Fill with generic title if not enough lines
                topic = f"第{lesson_number}课"

            chapters.append(ChapterInfo(
                lesson_number=lesson_number,
                topic=topic,
                content_summary="",
                key_concepts=[]
            ))

        return chapters

    async def _generate_ai_chapters(
        self,
        course_name: str,
        subject: str,
        grade: str,
        total_hours: int,
        hours_per_lesson: int,
        num_lessons: int,
        additional_info: Optional[str] = None,
    ) -> List[ChapterInfo]:
        """
        Generate chapters using AI.

        Uses batch generation to stay within API token limits.
        DeepSeek has a max output of 8192 tokens, so we generate
        in batches of ~12 lessons at a time.

        Args:
            course_name: Name of the course
            subject: Subject area
            grade: Grade level
            total_hours: Total course hours
            hours_per_lesson: Hours per lesson plan
            num_lessons: Number of lessons to generate
            additional_info: Optional additional information

        Returns:
            List of ChapterInfo objects
        """
        # Build additional info section
        additional_info_section = ""
        if additional_info:
            additional_info_section = f"\n- 补充说明：{additional_info}"

        # Batch size: max 12 lessons per batch to stay within token limits
        BATCH_SIZE = 12
        all_chapters = []

        # Generate in batches
        batch_start = 1
        while batch_start <= num_lessons:
            batch_end = min(batch_start + BATCH_SIZE - 1, num_lessons)
            batch_count = batch_end - batch_start + 1

            # Build batch-specific prompt
            batch_prompt = self.CHAPTER_SPLIT_PROMPT.format(
                course_name=course_name,
                subject=subject,
                grade=grade,
                total_hours=total_hours,
                hours_per_lesson=hours_per_lesson,
                num_lessons=batch_count,
                additional_info=additional_info_section,
            )

            # Add context for continuation
            if batch_start > 1:
                batch_prompt += f"\n\n注意：这是第{batch_start}-{batch_end}课，请延续之前的内容继续生成。"

            # Call AI
            response = await generate_with_ai(
                prompt=batch_prompt,
                system_prompt=self.SYSTEM_PROMPT,
                provider=self.provider,
                api_key=self.api_key,
                model=self.model,
                max_tokens=settings.ai_max_tokens_batch,
            )

            # Parse response
            chapters_data = self._parse_json_response(response)

            # Validate and convert to ChapterInfo objects
            for idx, data in enumerate(chapters_data):
                lesson_num = batch_start + idx
                data["lesson_number"] = lesson_num

                # Ensure required fields exist
                if "content_summary" not in data:
                    data["content_summary"] = ""
                if "key_concepts" not in data:
                    data["key_concepts"] = []

                try:
                    chapter = ChapterInfo(**data)
                    all_chapters.append(chapter)
                except Exception as e:
                    raise ValueError(
                        f"Failed to parse chapter {lesson_num}: {str(e)}\nData: {data}"
                    )

            batch_start = batch_end + 1

        # Final validation - ensure we have the exact number requested
        if len(all_chapters) < num_lessons:
            # Fill missing with generic titles
            while len(all_chapters) < num_lessons:
                lesson_num = len(all_chapters) + 1
                all_chapters.append(ChapterInfo(
                    lesson_number=lesson_num,
                    topic=f"第{lesson_num}课",
                    content_summary="",
                    key_concepts=[]
                ))

        return all_chapters[:num_lessons]  # Trim if too many

    async def _generate_ai_chapters_stream(
        self,
        course_name: str,
        subject: str,
        grade: str,
        total_hours: int,
        hours_per_lesson: int,
        num_lessons: int,
        additional_info: Optional[str] = None,
    ):
        """
        流式生成章节，逐个 yield ChapterInfo。

        Uses batch generation to stay within API token limits.

        Args:
            course_name: Name of the course
            subject: Subject area
            grade: Grade level
            total_hours: Total course hours
            hours_per_lesson: Hours per lesson plan
            num_lessons: Number of lessons to generate
            additional_info: Optional additional information

        Yields:
            ChapterInfo objects as they are generated
        """
        # Build additional info section
        additional_info_section = ""
        if additional_info:
            additional_info_section = f"\n- 补充说明：{additional_info}"

        # Batch size: max 12 lessons per batch to stay within token limits
        BATCH_SIZE = 12
        yielded_chapters = set()  # Track which chapters we've already yielded

        # Generate in batches
        batch_start = 1
        while batch_start <= num_lessons:
            batch_end = min(batch_start + BATCH_SIZE - 1, num_lessons)
            batch_count = batch_end - batch_start + 1

            # Build batch-specific prompt
            batch_prompt = self.CHAPTER_SPLIT_PROMPT.format(
                course_name=course_name,
                subject=subject,
                grade=grade,
                total_hours=total_hours,
                hours_per_lesson=hours_per_lesson,
                num_lessons=batch_count,
                additional_info=additional_info_section,
            )

            # Add context for continuation
            if batch_start > 1:
                batch_prompt += f"\n\n注意：这是第{batch_start}-{batch_end}课，请延续之前的内容继续生成。"

            # Get provider with batch max_tokens
            provider = AIProviderFactory.create_provider(
                self.provider, self.api_key, self.model, settings.ai_max_tokens_batch
            )

            # Accumulate streaming response
            full_response = ""

            # Use streaming if available
            if hasattr(provider, 'generate_stream'):
                async for chunk in provider.generate_stream(batch_prompt, self.SYSTEM_PROMPT):
                    # Parse SSE format (data: {...})
                    if chunk.startswith("data: "):
                        data_str = chunk[6:]  # Remove "data: " prefix
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data_str)

                            # Handle DeepSeek/OpenAI format
                            if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                delta = chunk_data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                full_response += content

                                # Try to parse partial JSON and yield any complete chapters
                                partial_chapters = self._try_parse_partial_chapters(full_response)
                                for chapter in partial_chapters:
                                    # Adjust lesson_number for overall sequence
                                    chapter.lesson_number = batch_start + (chapter.lesson_number - 1)
                                    if chapter.lesson_number not in yielded_chapters:
                                        yielded_chapters.add(chapter.lesson_number)
                                        yield chapter

                            # Handle Anthropic format
                            elif "delta" in chunk_data:
                                if "text" in chunk_data["delta"]:
                                    full_response += chunk_data["delta"]["text"]
                                    partial_chapters = self._try_parse_partial_chapters(full_response)
                                    for chapter in partial_chapters:
                                        chapter.lesson_number = batch_start + (chapter.lesson_number - 1)
                                        if chapter.lesson_number not in yielded_chapters:
                                            yielded_chapters.add(chapter.lesson_number)
                                            yield chapter

                        except json.JSONDecodeError:
                            # Ignore unparseable chunks during streaming
                            continue

            # Parse final response and yield remaining chapters from this batch
            chapters_data = self._parse_json_response(full_response)
            for idx, data in enumerate(chapters_data):
                lesson_num = batch_start + idx
                data["lesson_number"] = lesson_num

                # Ensure required fields exist
                if "content_summary" not in data:
                    data["content_summary"] = ""
                if "key_concepts" not in data:
                    data["key_concepts"] = []

                chapter = ChapterInfo(**data)
                if chapter.lesson_number not in yielded_chapters:
                    yielded_chapters.add(chapter.lesson_number)
                    yield chapter

            batch_start = batch_end + 1

        # Fill missing chapters if AI generated fewer than expected
        for lesson_num in range(1, num_lessons + 1):
            if lesson_num not in yielded_chapters:
                filler_chapter = ChapterInfo(
                    lesson_number=lesson_num,
                    topic=f"第{lesson_num}课",
                    content_summary="",
                    key_concepts=[]
                )
                yield filler_chapter

    def _try_parse_partial_chapters(self, content: str) -> List[ChapterInfo]:
        """
        尝试解析部分完成的 JSON 数组。

        Returns list of complete chapters that can be parsed.
        """
        chapters = []

        # Try to match JSON array pattern
        array_match = re.search(r'\[.*?\]', content, re.DOTALL)
        if not array_match:
            return chapters

        try:
            # Try parsing as-is
            data = json.loads(array_match.group(0))
            if isinstance(data, list):
                chapters = [ChapterInfo(**d) for d in data]
        except json.JSONDecodeError:
            pass

        if not chapters:
            # Try fixing trailing commas
            fixed = re.sub(r',\s*([}\]])', r'\1', array_match.group(0))
            try:
                data = json.loads(fixed)
                if isinstance(data, list):
                    chapters = [ChapterInfo(**d) for d in data]
            except (json.JSONDecodeError, ValueError):
                pass

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
    total_hours: int,
    hours_per_lesson: int = 2,
    chapters_input: Optional[str] = None,
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
        total_hours: Total course hours
        hours_per_lesson: Hours per lesson plan
        chapters_input: Optional user-provided chapters
        additional_info: Optional additional information
        provider: AI provider name
        api_key: Optional API key
        model: Optional model name

    Returns:
        List of ChapterInfo objects
    """
    splitter = ChapterSplitter(provider, api_key, model)
    return await splitter.split_course_chapters(
        course_name, subject, grade,
        total_hours, hours_per_lesson,
        chapters_input, additional_info
    )
