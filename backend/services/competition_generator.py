"""
Competition Generator Service
=============================

Generates "教学能力比赛" content using AI:
  1. Full participation lesson plan (multiple 【教案 X】, each 2 hours)
  2. Teaching implementation report (4 chapters)

Key design:
- Reuses ai_provider.generate_with_ai() for AI calls
- Each section is a separate AI request to avoid token-limit blow-ups
- asyncio.gather + Semaphore for concurrent lesson generation
- Robust JSON parsing with retry on parse failure
- All prompts are tuned for "national / provincial competition" quality level
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Optional, Dict, Any, List

from ..config import settings
from ..models.schemas import (
    CompetitionProject,
    CompetitionLessonContent,
    CompetitionReportContent,
    CompetitionOverallDesign,
    CompetitionSingleLesson,
    CompetitionLessonObjectives,
    CompetitionLessonStudentAnalysis,
    CompetitionTeachingStep,
    CompetitionImplementationStage,
    CompetitionReportEvaluation,
    CompetitionReportEffect,
    CompetitionReportReflection,
)
from .ai_provider import generate_with_ai

logger = logging.getLogger(__name__)


# ============================================================================
# Prompts
# ============================================================================

SYSTEM_PROMPT_LESSON = (
    "你是国赛/省赛获奖级别的教学能力比赛教案设计专家,擅长围绕\"岗课赛证\"融通理念,"
    "结合 1+X 职业技能等级证书要求,设计参赛级别的高质量教案。"
    "你输出的内容必须专业、详实、可操作,文字应符合参赛规范,体现新课标理念和课程思政。"
    "你必须严格按照要求输出 JSON 格式。"
)

SYSTEM_PROMPT_REPORT = (
    "你是国赛/省赛教学能力比赛的实施报告撰写专家,擅长以教师视角撰写客观、有数据支撑、"
    "结构完整的教学实施报告。报告要体现教学设计、实施过程、学习效果、反思改进的完整闭环。"
    "你必须严格按照要求输出 JSON 格式。"
)


def _project_context(project: CompetitionProject) -> str:
    """Build a textual context block from project metadata for prompts."""
    parts = [
        f"- 课程名称:{project.course_name or '(未填)'}",
        f"- 作品名称:{project.work_name or '(未填)'}",
        f"- 专业大类:{project.major_category or '(未填)'}",
        f"- 专业名称:{project.major_name or '(未填)'}",
        f"- 参赛组别:{project.group_name or '(未填)'}",
        f"- 总学时:{project.total_hours} 学时",
        f"- 单个教案学时:{project.hours_per_lesson} 学时",
        f"- 授课班级:{project.class_name or '(未填)'}",
        f"- 授课地点:{project.location or '(未填)'}",
    ]
    if project.textbook_info:
        parts.append(f"- 教材信息:{json.dumps(project.textbook_info, ensure_ascii=False)}")
    if project.context_data:
        parts.append(f"- 附加上下文:{json.dumps(project.context_data, ensure_ascii=False)}")
    return "\n".join(parts)


# ============================================================================
# Generator
# ============================================================================


class CompetitionGenerator:
    """Generate competition lesson plans and implementation reports using AI."""

    DEFAULT_MAX_CONCURRENT_LESSONS = 3

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_concurrent_lessons: int = DEFAULT_MAX_CONCURRENT_LESSONS,
    ):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.max_concurrent_lessons = max_concurrent_lessons

    # ------------------------------------------------------------------
    # JSON parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove ```json ... ``` wrappers."""
        text = text.strip()
        if text.startswith("```"):
            # Remove opening fence (```json or ```)
            text = re.sub(r"^```\w*\s*\n?", "", text)
            # Remove closing fence
            text = re.sub(r"\n?```\s*$", "", text)
        return text.strip()

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        """Parse AI response as JSON with tolerant fallback."""
        cleaned = self._strip_code_fences(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract the first JSON object literal
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Failed to parse AI JSON response: {exc}") from exc
            raise ValueError("AI response did not contain a JSON object")

    async def _ai_call_json(
        self,
        prompt: str,
        system_prompt: str,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """Call AI and parse JSON, with retries on parse failure."""
        last_error: Optional[Exception] = None
        for attempt in range(max_attempts):
            try:
                content = await generate_with_ai(
                    prompt=prompt if attempt == 0 else (
                        prompt + "\n\n## 重要:请仅输出严格的 JSON 对象,不要包含 Markdown 代码块或任何说明文字。"
                    ),
                    system_prompt=system_prompt,
                    provider=self.provider,
                    api_key=self.api_key,
                    model=self.model,
                )
                return self._parse_json(content)
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    f"AI JSON parse failed on attempt {attempt + 1}/{max_attempts}: {exc}"
                )
                if attempt < max_attempts - 1:
                    await asyncio.sleep(settings.ai_retry_delay * (2 ** attempt))
        raise last_error or ValueError("AI JSON parsing failed after all retries")

    # ==================================================================
    # Lesson Plan Generation
    # ==================================================================

    async def generate_full_lesson_plan(
        self,
        project: CompetitionProject,
        topics_input: Optional[str] = None,
        additional_requirements: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> CompetitionLessonContent:
        """
        Generate a complete competition lesson plan.

        Args:
            project: Competition project with cover info.
            topics_input: Optional newline-separated task list. If None, AI splits.
            additional_requirements: Optional special requirements.
            progress_callback: Async callable(current: int, total: int, message: str) for progress updates.

        Returns:
            CompetitionLessonContent with overall design and all lessons.
        """
        num_lessons = max(1, project.total_hours // project.hours_per_lesson)

        async def _report(current: int, total: int, message: str):
            if progress_callback:
                try:
                    await progress_callback(current, total, message)
                except Exception:
                    logger.exception("progress_callback failed")

        # Step 1: split topics if not provided
        await _report(0, num_lessons + 2, "拆分教案任务...")
        topics = await self._resolve_topics(project, topics_input, num_lessons)
        logger.info(f"Resolved {len(topics)} lesson topics: {topics}")

        # Step 2: generate overall design (single AI call)
        await _report(1, num_lessons + 2, "生成整体设计...")
        overall_design = await self._generate_overall_design(
            project, topics, additional_requirements
        )

        # Step 3: generate each lesson concurrently with semaphore
        semaphore = asyncio.Semaphore(self.max_concurrent_lessons)
        completed_count = [0]
        completed_lock = asyncio.Lock()

        async def gen_one(lesson_no: int, topic: str) -> CompetitionSingleLesson:
            async with semaphore:
                lesson = await self._generate_single_lesson(
                    project, topic, lesson_no, additional_requirements
                )
                async with completed_lock:
                    completed_count[0] += 1
                    await _report(
                        1 + completed_count[0],
                        num_lessons + 2,
                        f"已完成教案 {completed_count[0]}/{num_lessons}: {topic}",
                    )
                return lesson

        lesson_tasks = [
            gen_one(idx + 1, topic) for idx, topic in enumerate(topics)
        ]
        lessons = await asyncio.gather(*lesson_tasks)

        await _report(num_lessons + 2, num_lessons + 2, "生成完成")

        return CompetitionLessonContent(
            overall_design=overall_design,
            lessons=list(lessons),
        )

    async def _resolve_topics(
        self,
        project: CompetitionProject,
        topics_input: Optional[str],
        num_lessons: int,
    ) -> List[str]:
        """Resolve N topic titles. If user provided, parse; else AI splits."""
        if topics_input:
            topics = [
                line.strip().lstrip("-•").strip()
                for line in topics_input.splitlines()
                if line.strip()
            ]
            if len(topics) >= num_lessons:
                return topics[:num_lessons]
            # User-provided fewer topics; let AI fill the rest
            logger.info(
                f"User provided {len(topics)} topics, AI will fill {num_lessons - len(topics)}"
            )

        # AI splits topics
        prompt = (
            f"请根据以下课程信息,将课程拆分为 {num_lessons} 个教学任务(每个 {project.hours_per_lesson} 学时),"
            "每个任务应当聚焦一个明确的子主题,任务之间循序渐进、层层递进,符合参赛级教学逻辑。\n\n"
            f"## 课程信息\n{_project_context(project)}\n\n"
            "## 输出要求\n"
            f"严格输出 JSON 格式,只包含一个数组字段 topics,数组长度恰好为 {num_lessons}:\n"
            "```json\n"
            f'{{"topics": ["任务1名称", "任务2名称", ...]}}'
            "\n```\n"
            "任务名称应简洁(8-20字),不要带序号前缀。"
        )

        result = await self._ai_call_json(prompt, SYSTEM_PROMPT_LESSON)
        topics = result.get("topics", [])
        if not isinstance(topics, list) or len(topics) == 0:
            raise ValueError(f"AI returned invalid topics structure: {result}")

        # Pad or truncate to exactly num_lessons
        if len(topics) < num_lessons:
            for i in range(len(topics), num_lessons):
                topics.append(f"任务{i + 1}")
        return topics[:num_lessons]

    async def _generate_overall_design(
        self,
        project: CompetitionProject,
        topics: List[str],
        additional_requirements: Optional[str],
    ) -> CompetitionOverallDesign:
        """Generate the overall design section of the lesson plan."""
        topics_str = "\n".join(f"  教案{i + 1}: {t}" for i, t in enumerate(topics))
        extra = f"\n## 特殊要求\n{additional_requirements}" if additional_requirements else ""

        prompt = (
            "请根据以下课程信息和教学任务清单,撰写参赛教案的【整体设计】部分。"
            "这是教案的第一章,统领所有具体教案,需要体现整门课的设计思路。\n\n"
            f"## 课程信息\n{_project_context(project)}\n\n"
            f"## 教学任务清单(共 {len(topics)} 个,每个 {project.hours_per_lesson} 学时)\n{topics_str}\n"
            f"{extra}\n\n"
            "## 输出要求\n严格输出 JSON,字段说明:\n"
            "- content_analysis: 内容分析(200-400字),阐述课程地位、本单元在课程中的位置、内容选择依据、对接岗位\n"
            "- student_analysis: 学情分析(200-400字),包含已有知识/技能基础、能力特点、可能的难点\n"
            "- goal_analysis: 目标分析(150-300字),从知识/能力/素质三维阐述总体目标,体现 1+X 证书对接\n"
            "- process_design: 过程设计(150-300字),阐述教学方法的逻辑、任务驱动方式\n"
            "- teaching_method: 教学方法(100-200字),列出主要采用的教学方法及其应用场景\n"
            "- survey_questions: 学情调查问卷数组,5-9 个问题,每条字符串\n\n"
            "请严格按下面 JSON 结构输出,不要包含其他说明:\n"
            "```json\n"
            "{\n"
            '  "content_analysis": "...",\n'
            '  "student_analysis": "...",\n'
            '  "goal_analysis": "...",\n'
            '  "process_design": "...",\n'
            '  "teaching_method": "...",\n'
            '  "survey_questions": ["问题1?", "问题2?", "..."]\n'
            "}\n"
            "```"
        )

        result = await self._ai_call_json(prompt, SYSTEM_PROMPT_LESSON)
        return CompetitionOverallDesign(**result)

    async def _generate_single_lesson(
        self,
        project: CompetitionProject,
        topic: str,
        lesson_no: int,
        additional_requirements: Optional[str],
    ) -> CompetitionSingleLesson:
        """Generate a single 【教案 X】."""
        extra = f"\n## 特殊要求\n{additional_requirements}" if additional_requirements else ""

        prompt = (
            f"请生成参赛教案中的【教案{lesson_no}】完整内容,任务名称为「{topic}」。\n\n"
            f"## 课程整体信息\n{_project_context(project)}\n\n"
            f"## 本教案聚焦\n任务名称:{topic}\n"
            f"学时:{project.hours_per_lesson} 学时\n"
            f"{extra}\n\n"
            "## 输出要求\n严格输出 JSON,字段说明如下:\n"
            "- module_name: 模块名称(简短)\n"
            "- project_name: 项目名称(可与作品名称呼应)\n"
            "- hours: 学时表述,如 \"2 学时\"\n"
            "- location: 授课地点\n"
            "- class_name: 授课班级\n"
            "- position_competition_certificate: 岗课赛证融合设计(60-150字),阐述本任务对接的岗位、技能竞赛、证书考点\n"
            "- student_analysis: 对象,包含 knowledge_basis(知识与技能基础)、cognition_practice(认知和实践能力)、learning_features(学习特点)、assessment(评估结果),每项 50-150字\n"
            "- objectives: 对象,包含 knowledge(知识目标数组,2-4条)、ability(能力目标数组,2-4条)、quality(素质目标数组,2-3条)\n"
            "- key_points: 教学重点(40-100字)\n"
            "- difficult_points: 教学难点(40-100字)\n"
            "- key_difficult_solutions: 重难点解决措施(80-150字)\n"
            "- teaching_methods: 教学方法(40-100字,列出本任务所用方法)\n"
            "- information_resources: 信息化平台与资源(40-100字)\n"
            "- pre_class_steps: 课前环节数组,每项含 stage(环节名)、duration、content、teacher_activity、student_activity、design_intent、ideological_political,2-4 个环节\n"
            "- in_class_steps: 课中环节数组,每项同上,4-7 个环节,时长加起来约 90 分钟左右(2学时),要包含创设情境/分析任务/掌握要领/巩固训练/课堂总结等\n"
            "- after_class_steps: 课后环节数组,每项同上,1-2 个环节\n"
            "- reflection: 教学反思与改进(100-200字)\n\n"
            "请严格输出 JSON 对象,不要包含说明文字:\n"
            "```json\n"
            "{\n"
            '  "module_name": "...", "project_name": "...", "hours": "2 学时",\n'
            '  "location": "...", "class_name": "...",\n'
            '  "position_competition_certificate": "...",\n'
            '  "student_analysis": {"knowledge_basis": "...", "cognition_practice": "...", "learning_features": "...", "assessment": "..."},\n'
            '  "objectives": {"knowledge": ["..."], "ability": ["..."], "quality": ["..."]},\n'
            '  "key_points": "...", "difficult_points": "...", "key_difficult_solutions": "...",\n'
            '  "teaching_methods": "...", "information_resources": "...",\n'
            '  "pre_class_steps": [{"stage": "...", "duration": "...", "content": "...", "teacher_activity": "...", "student_activity": "...", "design_intent": "...", "ideological_political": "..."}],\n'
            '  "in_class_steps": [...同结构...],\n'
            '  "after_class_steps": [...同结构...],\n'
            '  "reflection": "..."\n'
            "}\n"
            "```"
        )

        result = await self._ai_call_json(prompt, SYSTEM_PROMPT_LESSON)

        # Build objects with required fields filled
        return CompetitionSingleLesson(
            lesson_number=lesson_no,
            title=topic,
            module_name=result.get("module_name") or "",
            project_name=result.get("project_name") or project.work_name,
            hours=result.get("hours") or f"{project.hours_per_lesson} 学时",
            location=result.get("location") or project.location or "",
            class_name=result.get("class_name") or project.class_name or "",
            position_competition_certificate=result.get("position_competition_certificate"),
            student_analysis=CompetitionLessonStudentAnalysis(
                **(result.get("student_analysis") or {})
            ),
            objectives=CompetitionLessonObjectives(
                **(result.get("objectives") or {})
            ),
            key_points=result.get("key_points"),
            difficult_points=result.get("difficult_points"),
            key_difficult_solutions=result.get("key_difficult_solutions"),
            teaching_methods=result.get("teaching_methods"),
            information_resources=result.get("information_resources"),
            pre_class_steps=[
                CompetitionTeachingStep(**s) for s in (result.get("pre_class_steps") or [])
            ],
            in_class_steps=[
                CompetitionTeachingStep(**s) for s in (result.get("in_class_steps") or [])
            ],
            after_class_steps=[
                CompetitionTeachingStep(**s) for s in (result.get("after_class_steps") or [])
            ],
            reflection=result.get("reflection"),
        )

    # ==================================================================
    # Implementation Report Generation
    # ==================================================================

    async def generate_report(
        self,
        project: CompetitionProject,
        related_lesson_plan: Optional[CompetitionLessonContent] = None,
        additional_requirements: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> CompetitionReportContent:
        """
        Generate the teaching implementation report.

        Args:
            project: Competition project.
            related_lesson_plan: Optional related lesson plan content as context.
            additional_requirements: Optional special requirements.
            progress_callback: Async callable for progress updates.

        Returns:
            CompetitionReportContent with all four chapters.
        """

        async def _report(current: int, total: int, message: str):
            if progress_callback:
                try:
                    await progress_callback(current, total, message)
                except Exception:
                    logger.exception("progress_callback failed")

        # We have 4 sections but generate them as 2 AI calls to balance:
        # Call 1: chapters 1+2 (overall design + implementation)
        # Call 2: chapters 3+4 (effects + reflection)
        await _report(0, 2, "生成报告:整体设计与实施过程...")
        section_a = await self._generate_report_part_a(
            project, related_lesson_plan, additional_requirements
        )

        await _report(1, 2, "生成报告:学习效果与反思改进...")
        section_b = await self._generate_report_part_b(
            project, related_lesson_plan, additional_requirements
        )

        await _report(2, 2, "报告生成完成")

        return CompetitionReportContent(
            intro_summary=section_a.get("intro_summary"),
            content_analysis=section_a.get("content_analysis"),
            student_analysis=section_a.get("student_analysis"),
            teaching_objectives=section_a.get("teaching_objectives"),
            teaching_strategy=section_a.get("teaching_strategy"),
            implementation_stages=[
                CompetitionImplementationStage(**s)
                for s in (section_a.get("implementation_stages") or [])
            ],
            blended_teaching_improvement=section_a.get("blended_teaching_improvement"),
            evaluation=CompetitionReportEvaluation(
                **(section_a.get("evaluation") or {})
            ),
            learning_effect=CompetitionReportEffect(
                **(section_b.get("learning_effect") or {})
            ),
            reflection=CompetitionReportReflection(
                **(section_b.get("reflection") or {})
            ),
        )

    async def _generate_report_part_a(
        self,
        project: CompetitionProject,
        related_lesson_plan: Optional[CompetitionLessonContent],
        additional_requirements: Optional[str],
    ) -> Dict[str, Any]:
        """Generate report sections 1+2."""
        related_ctx = self._build_related_context(related_lesson_plan)
        extra = f"\n## 特殊要求\n{additional_requirements}" if additional_requirements else ""

        prompt = (
            "请撰写参赛教学实施报告的【整体教学设计】和【教学实施过程】两章。\n\n"
            f"## 课程信息\n{_project_context(project)}\n"
            f"{related_ctx}{extra}\n\n"
            "## 输出要求\n严格输出 JSON,包含以下字段:\n"
            "- intro_summary: 报告开篇总述(150-300字),概述课程整体策略\n"
            "- content_analysis: 教学内容分析(200-400字),包含图占位的引用\n"
            "- student_analysis: 学情分析(250-450字),包含知识基础/认知能力/学习特点三段\n"
            "- teaching_objectives: 教学目标与重难点(150-300字)\n"
            "- teaching_strategy: 教学策略(200-400字),阐述策略一、策略二、策略三等\n"
            "- implementation_stages: 实施阶段表数组,4-6条,每条 {stage, task, effect}\n"
            "  阶段例如\"课前\"\"课中(线上)\"\"课中(线下)\"\"课后\"\"项目\"\n"
            "  effect 字段写图说,格式如 \"图:智慧云平台预习完成情况\"\n"
            "- blended_teaching_improvement: 混合式教学改进(150-300字)\n"
            "- evaluation: 对象 {student_evaluation, teacher_evaluation, enterprise_evaluation},每项 100-200字\n\n"
            "请严格输出 JSON,不要包含其他说明:\n"
            "```json\n"
            "{\n"
            '  "intro_summary": "...",\n'
            '  "content_analysis": "...",\n'
            '  "student_analysis": "...",\n'
            '  "teaching_objectives": "...",\n'
            '  "teaching_strategy": "...",\n'
            '  "implementation_stages": [{"stage": "...", "task": "...", "effect": "..."}],\n'
            '  "blended_teaching_improvement": "...",\n'
            '  "evaluation": {"student_evaluation": "...", "teacher_evaluation": "...", "enterprise_evaluation": "..."}\n'
            "}\n"
            "```"
        )

        return await self._ai_call_json(prompt, SYSTEM_PROMPT_REPORT)

    async def _generate_report_part_b(
        self,
        project: CompetitionProject,
        related_lesson_plan: Optional[CompetitionLessonContent],
        additional_requirements: Optional[str],
    ) -> Dict[str, Any]:
        """Generate report sections 3+4."""
        related_ctx = self._build_related_context(related_lesson_plan)
        extra = f"\n## 特殊要求\n{additional_requirements}" if additional_requirements else ""

        prompt = (
            "请撰写参赛教学实施报告的【学生学习效果】和【教学反思改进】两章。\n\n"
            f"## 课程信息\n{_project_context(project)}\n"
            f"{related_ctx}{extra}\n\n"
            "## 输出要求\n严格输出 JSON,包含以下字段:\n"
            "- learning_effect: 对象 {pre_class_improvement, in_class_improvement, certification_competition},"
            "每项 150-300字,要包含具体数据(如访问量、通过率、提升百分比等),体现量化效果\n"
            "- reflection: 对象 {feature_innovations, shortcomings, improvement_measures}\n"
            "  - feature_innovations: 特色创新点数组,2-3条,每条 80-150字\n"
            "  - shortcomings: 不足数组,2-3条,每条 60-120字\n"
            "  - improvement_measures: 改进措施数组,2-3条,每条与上对应,80-150字\n\n"
            "请严格输出 JSON,不要包含其他说明:\n"
            "```json\n"
            "{\n"
            '  "learning_effect": {\n'
            '    "pre_class_improvement": "...",\n'
            '    "in_class_improvement": "...",\n'
            '    "certification_competition": "..."\n'
            "  },\n"
            '  "reflection": {\n'
            '    "feature_innovations": ["..."],\n'
            '    "shortcomings": ["..."],\n'
            '    "improvement_measures": ["..."]\n'
            "  }\n"
            "}\n"
            "```"
        )

        return await self._ai_call_json(prompt, SYSTEM_PROMPT_REPORT)

    @staticmethod
    def _build_related_context(
        related_lesson_plan: Optional[CompetitionLessonContent],
    ) -> str:
        """Build a brief context string from a related lesson plan."""
        if not related_lesson_plan:
            return ""
        topics = [
            f"  教案{ls.lesson_number}: {ls.title}"
            for ls in related_lesson_plan.lessons
        ]
        topics_block = "\n".join(topics) if topics else "  (无)"
        overall = related_lesson_plan.overall_design
        return (
            "\n## 关联的参赛教案上下文(请基于此撰写报告,确保两份文档一致)\n"
            f"教学方法:{overall.teaching_method or '(略)'}\n"
            f"任务列表:\n{topics_block}\n"
        )
