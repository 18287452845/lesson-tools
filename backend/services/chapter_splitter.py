"""
Course chapter splitting service using AI.

Supports:
- AI-powered automatic chapter generation based on total hours
- Manual chapter input (user provides chapter titles)
"""
import asyncio
import json
import logging
import re
from typing import List, Optional

from ..config import settings
from ..models.schemas import ChapterInfo
from .ai_provider import generate_with_ai, AIProviderFactory

logger = logging.getLogger(__name__)


def _flatten_key_concepts(key_concepts):
    """
    Flatten nested lists in key_concepts to ensure all elements are strings.

    Args:
        key_concepts: Can be a list of strings, nested lists, or mixed

    Returns:
        Flattened list of strings
    """
    if not isinstance(key_concepts, list):
        return []

    result = []
    for item in key_concepts:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, list):
            # Recursively flatten nested lists
            result.extend(_flatten_key_concepts(item))
        else:
            # Convert other types to string
            result.append(str(item))
    return result


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

4. **章节层级**：
   - 只输出顶层教案主题，不要把子章节/子话题拆成独立教案
   - 子章节或细分内容请并入对应教案的content_summary

5. **格式要求**：
   - 必须返回纯JSON格式，不要包含其他说明文字
   - lesson_number字段必须从1开始，到{num_lessons}结束
   - 每个key_concepts数组包含3-5个核心概念

请直接输出JSON数组，不要添加任何其他文字。
"""

    SMART_ALLOCATION_PROMPT = """请根据用户提供的章节标题，智能分配到指定周数的周次教学计划中。

## 课程信息
- 课程名称：{course_name}
- 学科：{subject}
- 年级：{grade}
- 总周数：{total_weeks} 周
- 每周课时：{hours_per_week} 课时/周
- 总课时：{total_hours} 课时
{additional_info}

## 用户提供的章节标题
{chapters_list}

## 任务说明
你需要将上述章节智能分配到 **{total_weeks} 周** 的教学计划中。每周为一个教学单元，课题命名需要体现该周的教学内容。

**分配策略**：
1. **重要或复杂的章节** 可以跨越 2 周完成（如"第1章：XXX（上）"和"第1章：XXX（下）"）
2. **简单或关联性强的章节** 可以合并到 1 周内（如"第2章 + 第3章"）
3. **中等难度的章节** 独立占 1 周
4. 可以安排 **复习周** 或 **实践周**（如"阶段复习"、"期中总结"、"期末项目"）

## 输出要求
返回 **{total_weeks}** 个 JSON 对象的数组，每个对象代表一周的教学计划：

```json
[
  {{
    "lesson_number": 1,
    "topic": "第1周：第1章 课程导论（上）",
    "content_summary": "本周教学内容概述...",
    "key_concepts": ["概念1", "概念2", "概念3"]
  }},
  {{
    "lesson_number": 2,
    "topic": "第2周：第1章 课程导论（下）",
    "content_summary": "延续上周内容...",
    "key_concepts": ["概念4", "概念5"]
  }},
  {{
    "lesson_number": 3,
    "topic": "第3周：第2章 基础知识 + 第3章 基本操作",
    "content_summary": "本周合并讲解两个基础章节...",
    "key_concepts": ["概念1", "概念2", "概念3"]
  }}
]
```

## 课题命名规范
- 单章节跨周：`第X周：第N章 XXX（上）` / `第Y周：第N章 XXX（下）`
- 合并章节：`第X周：第N章 XXX + 第M章 YYY`
- 独立章节：`第X周：第N章 XXX`
- 复习周：`第X周：阶段复习` 或 `第X周：期中总结`

## 关键要求
1. **必须输出 {total_weeks} 个对象**（不多不少）
2. lesson_number 从 1 到 {total_weeks}
3. 每个 topic 必须以 `第X周：` 开头
4. content_summary 说明该周的教学内容（100-200字）
5. key_concepts 包含 3-5 个核心概念
6. 合理分配难度，前期基础后期深化
7. 输出纯 JSON 数组，不要任何其他文字

请直接输出JSON数组。
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
        if chapters_input and chapters_input.strip():
            # Mode 1: Parse user-provided chapters
            return self._parse_manual_chapters(chapters_input)
        else:
            # Mode 2: AI-generated chapters
            num_lessons = total_hours // hours_per_lesson
            return await self._generate_ai_chapters(
                course_name, subject, grade,
                total_hours, hours_per_lesson, num_lessons,
                additional_info
            )

    def _parse_manual_chapters(
        self,
        chapters_input: str
    ) -> List[ChapterInfo]:
        """
        Parse user-provided chapter titles.

        Args:
            chapters_input: User input with one chapter per line

        Returns:
            List of ChapterInfo objects
        """
        lines = [
            line.strip()
            for line in chapters_input.strip().split('\n')
            if line.strip()
        ]

        chapters = []
        for i, topic in enumerate(lines):
            lesson_number = i + 1
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
                else:
                    # Flatten key_concepts to handle nested lists from AI
                    data["key_concepts"] = _flatten_key_concepts(data["key_concepts"])

                try:
                    chapter = ChapterInfo(**data)
                    all_chapters.append(chapter)
                except Exception as e:
                    raise ValueError(
                        f"Failed to parse chapter {lesson_num}: {str(e)}\nData: {data}"
                    )

            batch_start = batch_end + 1

        return all_chapters

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

            def normalize_lesson_number(raw_num: int) -> Optional[int]:
                if batch_start <= raw_num <= batch_end:
                    return raw_num
                if 1 <= raw_num <= batch_count:
                    return batch_start + raw_num - 1
                return None

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
                                    lesson_num = normalize_lesson_number(chapter.lesson_number)
                                    if lesson_num is None:
                                        continue
                                    chapter.lesson_number = lesson_num
                                    if lesson_num not in yielded_chapters:
                                        yielded_chapters.add(lesson_num)
                                        yield chapter

                            # Handle Anthropic format
                            elif "delta" in chunk_data:
                                if "text" in chunk_data["delta"]:
                                    full_response += chunk_data["delta"]["text"]
                                    partial_chapters = self._try_parse_partial_chapters(full_response)
                                    for chapter in partial_chapters:
                                        lesson_num = normalize_lesson_number(chapter.lesson_number)
                                        if lesson_num is None:
                                            continue
                                        chapter.lesson_number = lesson_num
                                        if lesson_num not in yielded_chapters:
                                            yielded_chapters.add(lesson_num)
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
                else:
                    # Flatten key_concepts to handle nested lists from AI
                    data["key_concepts"] = _flatten_key_concepts(data["key_concepts"])

                chapter = ChapterInfo(**data)
                if chapter.lesson_number not in yielded_chapters:
                    yielded_chapters.add(chapter.lesson_number)
                    yield chapter

            batch_start = batch_end + 1

    def _try_parse_partial_chapters(self, content: str) -> List[ChapterInfo]:
        """
        尝试解析部分完成的 JSON 数组。

        Returns list of complete chapters that can be parsed.
        """
        chapters = []

        # Try to match JSON array pattern (use greedy matching to capture full array)
        array_match = re.search(r'\[(.*)\]', content, re.DOTALL)
        if not array_match:
            return chapters

        try:
            # Try parsing as-is with greedy match
            data = json.loads('[' + array_match.group(1) + ']')
            if isinstance(data, list):
                for d in data:
                    if isinstance(d, dict):
                        # Flatten key_concepts if present
                        if "key_concepts" in d:
                            d["key_concepts"] = _flatten_key_concepts(d["key_concepts"])
                        chapters.append(ChapterInfo(**d))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        if not chapters:
            # Try fixing trailing commas
            json_str = '[' + array_match.group(1) + ']'
            fixed = re.sub(r',\s*([}\]])', r'\1', json_str)
            try:
                data = json.loads(fixed)
                if isinstance(data, list):
                    for d in data:
                        if isinstance(d, dict):
                            # Flatten key_concepts if present
                            if "key_concepts" in d:
                                d["key_concepts"] = _flatten_key_concepts(d["key_concepts"])
                            chapters.append(ChapterInfo(**d))
            except (json.JSONDecodeError, ValueError, TypeError):
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

    def _build_smart_allocation_prompt(
        self,
        course_name: str,
        subject: str,
        grade: str,
        chapters_input: str,
        total_weeks: int,
        hours_per_week: int,
        total_hours: int,
        additional_info: Optional[str] = None,
    ) -> str:
        """
        构建智能周次分配的提示词。

        Args:
            course_name: 课程名称
            subject: 学科
            grade: 年级
            chapters_input: 用户输入的章节标题（每行一个）
            total_weeks: 总周数
            hours_per_week: 每周课时
            total_hours: 总课时
            additional_info: 补充说明

        Returns:
            格式化的提示词
        """
        # 解析章节标题为列表
        chapter_lines = [line.strip() for line in chapters_input.strip().split('\n') if line.strip()]
        chapters_list = "\n".join([f"{i+1}. {title}" for i, title in enumerate(chapter_lines)])

        # 构建补充信息
        additional_info_section = ""
        if additional_info:
            additional_info_section = f"\n- 补充说明：{additional_info}"

        # 格式化提示词
        prompt = self.SMART_ALLOCATION_PROMPT.format(
            course_name=course_name,
            subject=subject,
            grade=grade,
            total_weeks=total_weeks,
            hours_per_week=hours_per_week,
            total_hours=total_hours,
            chapters_list=chapters_list,
            additional_info=additional_info_section,
        )

        return prompt

    async def _generate_smart_allocation(
        self,
        course_name: str,
        subject: str,
        grade: str,
        chapters_input: str,
        total_weeks: int,
        hours_per_week: int,
        total_hours: int,
        additional_info: Optional[str] = None,
    ) -> List[ChapterInfo]:
        """
        使用AI智能分配章节到周次。

        Args:
            course_name: 课程名称
            subject: 学科
            grade: 年级
            chapters_input: 用户输入的章节标题
            total_weeks: 总周数
            hours_per_week: 每周课时
            total_hours: 总课时
            additional_info: 补充说明

        Returns:
            ChapterInfo列表（每周一个）
        """
        # 构建提示词
        prompt = self._build_smart_allocation_prompt(
            course_name, subject, grade, chapters_input,
            total_weeks, hours_per_week, total_hours, additional_info
        )

        # 调用AI生成
        provider = AIProviderFactory.create_provider(
            self.provider, self.api_key, self.model, settings.ai_max_tokens_batch
        )

        # 尝试多次生成（最多3次），确保生成完整
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await provider.generate(prompt, self.SYSTEM_PROMPT)

                # 解析JSON响应
                data = self._parse_json_response(response)

                # 转换为ChapterInfo对象
                chapters = []
                for item in data:
                    chapters.append(ChapterInfo(**item))

                logger.info(f"Smart allocation attempt {attempt + 1}: generated {len(chapters)}/{total_weeks} weeks")

                # 如果生成数量正确或接近，直接返回
                if len(chapters) >= total_weeks:
                    if len(chapters) > total_weeks:
                        logger.warning(f"Generated {len(chapters)} weeks, truncating to {total_weeks}")
                        chapters = chapters[:total_weeks]
                    return chapters
                elif len(chapters) >= total_weeks * 0.8:  # 如果生成了80%以上，接受
                    logger.warning(f"Generated {len(chapters)}/{total_weeks} weeks (>80%), filling remaining")
                    # 只填充少量缺失的周次
                    existing_nums = {ch.lesson_number for ch in chapters}
                    for week_num in range(1, total_weeks + 1):
                        if week_num not in existing_nums:
                            chapters.append(ChapterInfo(
                                lesson_number=week_num,
                                topic=f"第{week_num}周：待补充",
                                content_summary="请手动填写本周教学内容",
                                key_concepts=[]
                            ))
                    # 按lesson_number排序
                    chapters.sort(key=lambda x: x.lesson_number)
                    return chapters

                # 生成不足80%，重试
                if attempt < max_retries - 1:
                    logger.warning(f"Generated only {len(chapters)}/{total_weeks} weeks, retrying...")
                    await asyncio.sleep(1)  # 等待1秒后重试

            except Exception as e:
                logger.error(f"Smart allocation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    raise

        # 所有重试都失败，抛出异常
        raise Exception(f"Failed to generate complete smart allocation after {max_retries} attempts. Only got {len(chapters)}/{total_weeks} weeks.")

    async def _generate_smart_allocation_stream(
        self,
        course_name: str,
        subject: str,
        grade: str,
        chapters_input: str,
        total_weeks: int,
        hours_per_week: int,
        total_hours: int,
        additional_info: Optional[str] = None,
    ):
        """
        使用AI智能分配章节到周次（流式）。

        Yields:
            ChapterInfo对象（每周一个）
        """
        # 构建提示词
        prompt = self._build_smart_allocation_prompt(
            course_name, subject, grade, chapters_input,
            total_weeks, hours_per_week, total_hours, additional_info
        )

        # 获取provider
        provider = AIProviderFactory.create_provider(
            self.provider, self.api_key, self.model, settings.ai_max_tokens_batch
        )

        # 累积流式响应
        full_response = ""
        yielded_weeks = set()  # 已输出的周次

        # 使用流式生成
        if hasattr(provider, 'generate_stream'):
            async for chunk in provider.generate_stream(prompt, self.SYSTEM_PROMPT):
                # 解析SSE格式
                if chunk.startswith("data: "):
                    data_str = chunk[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(data_str)

                        # 处理DeepSeek/OpenAI格式
                        if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                            delta = chunk_data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            full_response += content

                            # 尝试解析部分完成的周次
                            partial_weeks = self._try_parse_partial_chapters(full_response)
                            for week in partial_weeks:
                                week_num = week.lesson_number
                                if week_num not in yielded_weeks and week_num <= total_weeks:
                                    yielded_weeks.add(week_num)
                                    yield week

                    except json.JSONDecodeError:
                        continue

            # 流式生成完成后，检查是否所有周次都已生成
            logger.info(f"Smart allocation stream completed. Generated {len(yielded_weeks)}/{total_weeks} weeks")

            if len(yielded_weeks) < total_weeks:
                # 流式生成不完整，尝试解析完整响应
                logger.warning(f"Stream incomplete, attempting to parse full response")
                try:
                    data = self._parse_json_response(full_response)
                    for item in data:
                        week = ChapterInfo(**item)
                        week_num = week.lesson_number
                        if week_num not in yielded_weeks and week_num <= total_weeks:
                            yielded_weeks.add(week_num)
                            yield week
                            logger.info(f"Recovered week {week_num} from full response")
                except Exception as e:
                    logger.error(f"Failed to parse full response: {e}")

                # 如果仍然不完整，使用同步方法重新生成
                if len(yielded_weeks) < total_weeks:
                    logger.warning(f"Stream and parse failed, falling back to synchronous generation")
                    try:
                        weeks = await self._generate_smart_allocation(
                            course_name, subject, grade, chapters_input,
                            total_weeks, hours_per_week, total_hours, additional_info
                        )
                        for week in weeks:
                            week_num = week.lesson_number
                            if week_num not in yielded_weeks:
                                yielded_weeks.add(week_num)
                                yield week
                                logger.info(f"Recovered week {week_num} from sync generation")
                    except Exception as e:
                        logger.error(f"Synchronous generation also failed: {e}")
        else:
            # 不支持流式，使用同步方式
            weeks = await self._generate_smart_allocation(
                course_name, subject, grade, chapters_input,
                total_weeks, hours_per_week, total_hours, additional_info
            )
            for week in weeks:
                if week.lesson_number <= total_weeks:
                    yield week
                    yielded_weeks.add(week.lesson_number)

        # 最后检查：只有在所有尝试都失败后才填充占位符
        if len(yielded_weeks) < total_weeks:
            error_msg = f"Failed to generate all weeks. Only got {len(yielded_weeks)}/{total_weeks}"
            logger.error(error_msg)

            # 不生成占位符，而是抛出异常让上层处理
            raise Exception(
                f"AI章节生成未完成：成功生成 {len(yielded_weeks)}/{total_weeks} 周的内容。\n\n"
                f"可能原因：\n"
                f"1. AI API密钥配置错误或已过期\n"
                f"2. AI服务繁忙或网络连接问题\n"
                f"3. 请求的周数过多（当前 {total_weeks} 周），建议分批生成\n"
                f"4. 章节标题过于复杂，建议简化\n\n"
                f"建议操作：\n"
                f"- 检查后端日志查看详细错误信息\n"
                f"- 验证 .env 文件中的 AI_PROVIDER 和 API_KEY 配置\n"
                f"- 尝试减少周数（建议不超过 8-12 周）\n"
                f"- 简化章节标题或提供更具体的教学内容"
            )


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
