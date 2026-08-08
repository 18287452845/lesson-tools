"""
Pydantic models for request/response validation.
"""
import json
from datetime import datetime
from typing import Optional, Dict, List, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from uuid import uuid4


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid4())


# ============================================================================
# Template Models
# ============================================================================


class TemplateUpload(BaseModel):
    """Template upload request."""
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    subject: Optional[str] = Field(None, description="Subject")
    grade: Optional[str] = Field(None, description="Grade")


class FieldConfig(BaseModel):
    """Field configuration."""
    name: str
    display_name: str
    description: Optional[str] = None
    required: bool = True
    field_type: Literal["text", "textarea", "json", "array"] = "text"
    default_value: Optional[str] = None


class TemplateInfo(BaseModel):
    """Template information."""
    id: str
    name: str
    description: Optional[str]
    subject: Optional[str]
    grade: Optional[str]
    file_path: str
    fields_config: List[FieldConfig]
    preview_image: Optional[str]
    use_count: int
    created_at: str
    updated_at: str


class TemplateUploadResponse(BaseModel):
    """Template upload response."""
    id: str
    name: str
    fields: List[FieldConfig]
    preview_url: Optional[str]


# ============================================================================
# Class Management Models
# ============================================================================


class ClassInfo(BaseModel):
    """Class information for lesson plan assignment."""
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str


class ClassCreateRequest(BaseModel):
    """Request to create a new class."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class ClassUpdateRequest(BaseModel):
    """Request to update a class."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class ClassListResponse(BaseModel):
    """Response for listing classes."""
    classes: List[ClassInfo]
    total: int


# ============================================================================
# Subject Management Models
# ============================================================================


class SubjectInfo(BaseModel):
    """Subject information."""
    id: str
    name: str
    category: str  # 'university_course' or 'basic_subject'
    is_preset: bool
    sort_order: int
    description: Optional[str] = None
    created_at: str
    updated_at: str


class SubjectCreateRequest(BaseModel):
    """Request to create a new subject."""
    name: str = Field(..., min_length=1, max_length=50, description="学科名称")
    category: str = Field(..., description="学科分类: university_course 或 basic_subject")
    description: Optional[str] = Field(None, description="学科描述")


class SubjectUpdateRequest(BaseModel):
    """Request to update a subject."""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="学科名称")
    description: Optional[str] = Field(None, description="学科描述")


class SubjectListResponse(BaseModel):
    """Response for listing subjects."""
    subjects: List[SubjectInfo]
    total: int


class SubjectWithUsageStats(SubjectInfo):
    """Subject information with usage statistics."""
    usage_stats: dict


# ============================================================================
# Grade Management Models
# ============================================================================


class GradeInfo(BaseModel):
    """Grade information."""
    id: str
    name: str
    category: str  # 'university', 'high_school', 'middle_school', or 'elementary'
    is_preset: bool
    sort_order: int
    description: Optional[str] = None
    created_at: str
    updated_at: str


class GradeCreateRequest(BaseModel):
    """Request to create a new grade."""
    name: str = Field(..., min_length=1, max_length=20, description="年级名称")
    category: str = Field(..., description="年级分类: university, high_school, middle_school, 或 elementary")
    description: Optional[str] = Field(None, description="年级描述")


class GradeUpdateRequest(BaseModel):
    """Request to update a grade."""
    name: Optional[str] = Field(None, min_length=1, max_length=20, description="年级名称")
    description: Optional[str] = Field(None, description="年级描述")


class GradeListResponse(BaseModel):
    """Response for listing grades."""
    grades: List[GradeInfo]
    total: int


class GradeWithUsageStats(GradeInfo):
    """Grade information with usage statistics."""
    usage_stats: dict


# ============================================================================
# Textbook Management Models
# ============================================================================


class TextbookCreateRequest(BaseModel):
    """Request to create a new textbook."""
    name: str = Field(..., min_length=1, max_length=200, description="教材名称")
    isbn: Optional[str] = Field(None, max_length=20, description="ISBN号")
    author: Optional[str] = Field(None, max_length=200, description="作者")
    publisher: Optional[str] = Field(None, max_length=200, description="出版社")
    edition: Optional[str] = Field(None, max_length=50, description="版本/版次")
    subject: Optional[str] = Field(None, max_length=50, description="学科")
    grade: Optional[str] = Field(None, max_length=50, description="适用年级")
    cover_image: Optional[str] = Field(None, description="封面图片路径")
    description: Optional[str] = Field(None, description="教材简介")


class TextbookUpdateRequest(BaseModel):
    """Request to update a textbook."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    isbn: Optional[str] = Field(None, max_length=20)
    author: Optional[str] = Field(None, max_length=200)
    publisher: Optional[str] = Field(None, max_length=200)
    edition: Optional[str] = Field(None, max_length=50)
    subject: Optional[str] = Field(None, max_length=50)
    grade: Optional[str] = Field(None, max_length=50)
    cover_image: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["active", "inactive"]] = None


class TextbookChapterInfo(BaseModel):
    """Textbook chapter information."""
    id: str
    textbook_id: str
    chapter_number: str
    chapter_title: str
    content_summary: Optional[str] = None
    key_concepts: List[str] = Field(default_factory=list)
    sort_order: int = 0
    hours_required: Optional[int] = None
    parent_chapter_id: Optional[str] = None
    source_id: Optional[str] = None
    content_origin: Literal["manual", "source", "ai_enriched", "ai_inferred"] = "manual"
    confidence: Optional[float] = Field(None, ge=0, le=1)
    created_at: str
    updated_at: str


class TextbookSourceInfo(BaseModel):
    """External evidence used to import textbook metadata or its catalog."""
    id: str
    textbook_id: str
    source_type: str
    source_name: str
    source_url: Optional[str] = None
    external_id: Optional[str] = None
    confidence: float = Field(0, ge=0, le=1)
    retrieved_at: str
    created_at: str


class TextbookInfo(BaseModel):
    """Textbook information with chapters."""
    id: str
    name: str
    isbn: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    edition: Optional[str] = None
    subject: Optional[str] = None
    grade: Optional[str] = None
    cover_image: Optional[str] = None
    description: Optional[str] = None
    status: str
    use_count: int
    created_at: str
    updated_at: str
    chapters: List[TextbookChapterInfo] = Field(default_factory=list)
    sources: List[TextbookSourceInfo] = Field(default_factory=list)


class TextbookListResponse(BaseModel):
    """Response for listing textbooks."""
    textbooks: List[TextbookInfo]
    total: int


class TextbookChapterGenerateRequest(BaseModel):
    """Request to generate textbook chapters using AI."""
    textbook_name: str = Field(..., description="教材名称")
    isbn: Optional[str] = Field(None, description="ISBN号")
    subject: Optional[str] = Field(None, description="学科")
    grade: Optional[str] = Field(None, description="年级")
    additional_info: Optional[str] = Field(None, description="补充说明")


class TextbookChapterCreateRequest(BaseModel):
    """Request to create a single chapter."""
    id: Optional[str] = Field(None, description="章节ID（可选，用于保持层级关系）")
    client_id: Optional[str] = Field(
        None, description="客户端生成的临时ID，用于父子映射（可选）"
    )
    chapter_number: str = Field(..., description="章节号，如'第1章'")
    chapter_title: str = Field(..., min_length=1, max_length=200, description="章节标题")
    content_summary: Optional[str] = Field(None, description="内容概述")
    key_concepts: List[str] = Field(default_factory=list, description="核心概念列表")
    sort_order: int = Field(0, description="排序顺序")
    hours_required: Optional[int] = Field(None, description="建议课时数")
    parent_chapter_id: Optional[str] = Field(None, description="父章节ID")
    source_id: Optional[str] = Field(None, description="章节来源ID")
    content_origin: Literal["manual", "source", "ai_enriched", "ai_inferred"] = "manual"
    confidence: Optional[float] = Field(None, ge=0, le=1)


class TextbookChapterBatchCreateRequest(BaseModel):
    """Request to batch create or update chapters."""
    chapters: List[TextbookChapterCreateRequest]


class TextbookChapterGenerateResponse(BaseModel):
    """Response from AI chapter generation."""
    chapters: List[TextbookChapterCreateRequest]
    message: str = "章节生成成功"


class TextbookChapterEnrichRequest(BaseModel):
    """Request to AI补充章节概述和核心概念。"""
    chapters: List[TextbookChapterCreateRequest]


class TextbookChapterEnrichResponse(BaseModel):
    """Response for AI enriched chapters."""
    chapters: List[TextbookChapterCreateRequest]
    message: str = "章节内容概述和核心概念已生成"


class TextbookSearchRequest(BaseModel):
    """Search external catalogs by ISBN or by title and author."""
    isbn: Optional[str] = Field(None, max_length=32)
    title: Optional[str] = Field(None, max_length=200)
    author: Optional[str] = Field(None, max_length=200)
    max_results: int = Field(8, ge=1, le=20)

    @model_validator(mode="after")
    def validate_search_terms(self):
        self.isbn = self.isbn.strip() if self.isbn else None
        self.title = self.title.strip() if self.title else None
        self.author = self.author.strip() if self.author else None
        if not self.isbn and not self.title:
            raise ValueError("请提供 ISBN，或至少提供书名")
        return self


class TextbookSearchCandidate(BaseModel):
    """A single edition candidate returned by an external source."""
    id: str
    source: str
    source_name: str
    source_id: str
    source_url: Optional[str] = None
    title: str
    authors: List[str] = Field(default_factory=list)
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    edition: Optional[str] = None
    isbn_10: Optional[str] = None
    isbn_13: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    toc_available: bool = False
    match_score: int = Field(0, ge=0, le=100)


class TextbookSearchResponse(BaseModel):
    candidates: List[TextbookSearchCandidate]
    source_errors: Dict[str, str] = Field(default_factory=dict)
    message: str


class TextbookCatalogRequest(BaseModel):
    candidate: TextbookSearchCandidate
    source_url: Optional[str] = Field(None, max_length=2000)
    ai_enrich: bool = True


class TextbookCatalogPreviewResponse(BaseModel):
    candidate: TextbookSearchCandidate
    chapters: List[TextbookChapterCreateRequest]
    source_type: str
    source_name: str
    source_url: Optional[str] = None
    confidence: float = Field(0, ge=0, le=1)
    warnings: List[str] = Field(default_factory=list)
    message: str


class TextbookImportRequest(BaseModel):
    candidate: TextbookSearchCandidate
    chapters: List[TextbookChapterCreateRequest] = Field(..., min_length=1)
    source_type: str
    source_name: str
    source_url: Optional[str] = Field(None, max_length=2000)
    confidence: float = Field(0, ge=0, le=1)
    subject: Optional[str] = Field(None, max_length=50)
    grade: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    allow_duplicate: bool = False

    @field_validator("subject", "grade")
    @classmethod
    def reject_corrupted_metadata(cls, value: Optional[str]) -> Optional[str]:
        """Reject metadata that has clearly been replaced by encoding placeholders."""
        if value and all(character in "?？�" or character.isspace() for character in value):
            raise ValueError("字段疑似乱码，请重新选择或输入")
        return value


# ============================================================================
# Lesson Plan Generation Models
# ============================================================================


class LessonPlanInput(BaseModel):
    """Lesson plan input data."""
    template_id: str
    subject: str
    grade: str
    topic: str
    duration: str
    textbook_name: Optional[str] = None
    location: Optional[str] = None
    online_resources: Optional[str] = None
    unit_name: Optional[str] = None
    prior_knowledge: Optional[str] = None
    focus_areas: Optional[str] = None
    teaching_style: Optional[str] = None
    additional_requirements: Optional[str] = None
    class_ids: List[str] = Field(default_factory=list, description="授课班级ID列表")
    class_name: Optional[str] = None


class LessonPlanGenerateRequest(LessonPlanInput):
    """Request to generate a lesson plan."""
    generate_reflection: bool = False  # Whether to generate teaching reflection


class TeachingGoal(BaseModel):
    """Teaching goal.

    Different templates may require different fields:
    - Standard templates: knowledge, ability, emotion
    - Vocational templates: knowledge, ability, quality

    All fields are optional to support various template requirements.
    """
    knowledge: Optional[List[str]] = None
    ability: Optional[List[str]] = None
    emotion: Optional[List[str]] = None  # 情感态度价值观目标（标准模板）
    quality: Optional[List[str]] = None  # 素质目标（职业院校模板）

    class Config:
        extra = "allow"  # Allow additional custom goal types

    def model_dump(self, **kwargs):
        """Override to exclude None values."""
        # Get the base dict
        data = super().model_dump(**kwargs)
        # Remove None values to prevent 'NoneType is not iterable' errors in templates
        return {k: v for k, v in data.items() if v is not None}


class TeachingStep(BaseModel):
    """Teaching step."""
    stage: str
    duration: str
    teacher_activity: str
    student_activity: str
    design_intent: str


class Homework(BaseModel):
    """Homework."""
    required: str
    optional: Optional[str] = None


class GeneratedContent(BaseModel):
    """Generated lesson plan content.

    All fields are optional to support dynamic templates with different field requirements.
    """
    # Core fields (commonly used)
    teaching_goals: Optional[TeachingGoal] = None
    key_points: Optional[str] = None
    difficult_points: Optional[str] = None
    teaching_tools: Optional[str] = None
    teaching_methods: Optional[str] = None
    student_analysis: Optional[str] = None
    textbook_analysis: Optional[str] = None
    teaching_steps: Optional[List[TeachingStep]] = None
    homework: Optional[Homework] = None
    blackboard_design: Optional[str] = None
    reflection: Optional[str] = None
    online_resources: Optional[str] = None

    @field_validator(
        "key_points",
        "difficult_points",
        "teaching_tools",
        "teaching_methods",
        "student_analysis",
        "textbook_analysis",
        "blackboard_design",
        "reflection",
        "online_resources",
        mode="before",
    )
    @classmethod
    def normalize_ai_text_fields(cls, value: Any) -> Optional[str]:
        """Normalize common AI list/object responses into displayable text."""
        if value is None or isinstance(value, str):
            return value
        if isinstance(value, list):
            return "\n".join(
                json.dumps(item, ensure_ascii=False)
                if isinstance(item, (dict, list))
                else str(item)
                for item in value
                if item is not None
            )
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    # Allow extra fields for custom template fields
    class Config:
        extra = "allow"


class LessonPlanResponse(BaseModel):
    """Lesson plan generation response."""
    id: str
    template_id: str
    input: LessonPlanInput
    content: GeneratedContent
    status: str
    created_at: str


PreparationArtifactType = Literal["lesson_plan", "handout", "presentation"]


class PreparationGenerateRequest(BaseModel):
    """Create one or more teaching-preparation artifacts from shared inputs."""

    subject: str = Field(..., min_length=1, max_length=100)
    grade: str = Field(..., min_length=1, max_length=100)
    topic: str = Field(..., min_length=1, max_length=200)
    duration: str = Field(..., min_length=1, max_length=50)
    artifact_types: List[PreparationArtifactType] = Field(min_length=1)
    textbook_name: Optional[str] = None
    location: Optional[str] = None
    online_resources: Optional[str] = None
    unit_name: Optional[str] = None
    prior_knowledge: Optional[str] = None
    focus_areas: Optional[str] = None
    teaching_style: Optional[str] = None
    additional_requirements: Optional[str] = None
    class_ids: List[str] = Field(default_factory=list)
    generate_reflection: bool = False

    @field_validator("artifact_types")
    @classmethod
    def unique_artifact_types(
        cls, value: List[PreparationArtifactType]
    ) -> List[PreparationArtifactType]:
        return list(dict.fromkeys(value))


class PreparationArtifact(BaseModel):
    type: PreparationArtifactType
    label: str
    filename: str
    download_url: str
    media_type: str


class PreparationResponse(BaseModel):
    id: str
    title: str
    template_id: str
    template_name: str
    content: GeneratedContent
    artifacts: List[PreparationArtifact]
    created_at: str


class FieldRegenerateRequest(BaseModel):
    """Request to regenerate a single field."""
    lesson_plan_id: str
    field_name: str
    additional_instruction: Optional[str] = None


class FieldEditRequest(BaseModel):
    """Request to edit a field."""
    lesson_plan_id: str
    field_name: str
    content: str


# ============================================================================
# Document Editing Models
# ============================================================================


class SectionLocation(BaseModel):
    """Location of a section in the document."""
    in_table: bool = False
    table_idx: Optional[int] = None
    cell_location: Optional[tuple] = None
    start_para_idx: Optional[int] = None
    end_para_idx: Optional[int] = None


class ParsedSection(BaseModel):
    """Parsed section from a document."""
    name: str
    found: bool
    content: Optional[str]
    location: Optional[SectionLocation] = None


class DocumentUploadResponse(BaseModel):
    """Document upload response."""
    id: str
    filename: str
    parsed_sections: Dict[str, ParsedSection]


class SectionEditRequest(BaseModel):
    """Request to edit a section."""
    section_name: str
    operation: Literal["replace", "append", "insert", "generate", "ai_modify"] = "replace"
    content: Optional[str] = None
    ai_instruction: Optional[str] = None


class DocumentEditRequest(BaseModel):
    """Request to edit a document."""
    document_id: str
    edits: List[SectionEditRequest]


class DocumentEditResponse(BaseModel):
    """Document edit response."""
    section_name: str
    new_content: str
    preview_url: Optional[str]


class AddSectionRequest(BaseModel):
    """Request to add a new section."""
    section_name: str
    position: Literal["auto", "end"] = "end"
    after_section: Optional[str] = None
    ai_generate: bool = True
    manual_content: Optional[str] = None


class AIEnhanceRequest(BaseModel):
    """Request to AI enhance content."""
    section_name: str
    enhancement_type: Literal["detailed", "professional", "simplified", "rewrite"] = "detailed"
    specific_instruction: Optional[str] = None


# ============================================================================
# Common Models
# ============================================================================


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None


class ExportRequest(BaseModel):
    """Document export request."""
    format: Literal["docx"] = "docx"


class ExportResponse(BaseModel):
    """Document export response."""
    download_url: str
    file_path: str


# ============================================================================
# Batch Generation Models
# ============================================================================


class ChapterInfo(BaseModel):
    """Chapter information for batch generation."""
    lesson_number: int = Field(..., ge=1, description="教案序号（1, 2, 3...）")
    topic: str = Field(..., description="课题/章节标题")
    content_summary: str = Field(default="", description="内容概述")
    key_concepts: List[str] = Field(default_factory=list, description="核心概念")
    experiment_name: Optional[str] = Field(
        None,
        max_length=100,
        description="实验项目名称；最终限制18字，不合规时在实验计划合并前重新生成",
    )


class ChapterSplitRequest(BaseModel):
    """Request to split course into chapters."""
    course_name: str
    subject: str
    grade: str
    total_hours: int = Field(..., ge=2, description="总课时数（如64、72）")
    hours_per_lesson: int = Field(default=2, ge=1, description="每份教案课时")
    chapters_input: Optional[str] = Field(None, description="用户手动输入的章节（每行一个，可选）")
    additional_info: Optional[str] = None


class SmartAllocationRequest(BaseModel):
    """智能周次分配请求 - 用户提供章节标题，AI智能分配到周次"""
    course_name: str
    subject: str
    grade: str
    chapters_input: str = Field(..., description="用户提供的章节标题（每行一个）")
    total_weeks: int = Field(..., ge=1, le=20, description="总周数（如16周）")
    hours_per_week: int = Field(..., ge=1, le=8, description="每周课时数（如4课时/周）")
    total_hours: int = Field(..., description="总课时数 = total_weeks × hours_per_week")
    additional_info: Optional[str] = Field(None, description="补充说明")


class ChapterSplitResponse(BaseModel):
    """Response from chapter splitting."""
    chapters: List[ChapterInfo]
    total_lessons: int = Field(..., description="教案总数")


class MajorClassSelection(BaseModel):
    """Class numbers selected for one major."""
    major: str = Field(..., min_length=1, max_length=100, description="专业名称")
    class_numbers: List[int] = Field(..., min_length=1, description="该专业的班号（1-5班）")

    @field_validator("major")
    @classmethod
    def clean_major(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("专业名称不能为空")
        return cleaned

    @field_validator("class_numbers")
    @classmethod
    def validate_class_numbers(cls, value: List[int]) -> List[int]:
        numbers = list(dict.fromkeys(value))
        if any(number < 1 or number > 5 for number in numbers):
            raise ValueError("班级只能选择 1-5 班")
        return numbers


class ExperimentClassSchedule(BaseModel):
    """Recurring weekly experiment schedule for one concrete class."""
    class_name: str = Field(..., min_length=1, max_length=150, description="完整班级名称")
    weekday: Literal[1, 2, 3, 4, 5, 6, 7] = Field(..., description="星期一至星期日")
    class_periods: str = Field(
        ...,
        min_length=1,
        max_length=30,
        pattern=r"^\d{1,2}(?:-\d{1,2})?$",
        description="上课节次，如 3-4",
    )
    first_class_date: str = Field(..., description="第一周实验日期，YYYY-MM-DD")
    classroom: str = Field(..., min_length=1, max_length=100, description="该班实验教室")

    @field_validator(
        "class_name", "class_periods", "first_class_date", "classroom", mode="before"
    )
    @classmethod
    def clean_schedule_text(cls, value: Any) -> str:
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("实验课安排字段不能为空")
        return cleaned

    @model_validator(mode="after")
    def validate_first_date_weekday(self):
        try:
            first_date = datetime.strptime(self.first_class_date, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("第一周日期必须是 YYYY-MM-DD 格式") from exc
        if first_date.isoweekday() != self.weekday:
            weekday_name = "一二三四五六日"[self.weekday - 1]
            raise ValueError(f"{self.class_name}第一周日期必须是星期{weekday_name}")
        return self


class BatchTaskCreateRequest(BaseModel):
    """Request to create a batch task."""
    course_name: str
    subject: str
    grade: str
    template_id: str
    total_hours: int = Field(..., ge=2, description="总课时数")
    hours_per_lesson: int = Field(default=2, ge=1, description="每份教案课时")
    chapters: List[ChapterInfo]
    start_week: int = Field(default=1, ge=1, description="起始周次")
    class_ids: List[str] = Field(default_factory=list, description="授课班级ID列表")
    major_classes: List[MajorClassSelection] = Field(
        default_factory=list,
        description="各专业独立选择的班号",
    )
    majors: List[str] = Field(default_factory=list, description="专业列表")
    class_numbers: List[int] = Field(default_factory=list, description="班号列表（1-5班）")
    location: Optional[str] = Field(None, description="授课地点")
    locations: List[str] = Field(default_factory=list, description="授课地点列表")
    textbook_name: Optional[str] = Field(None, description="教材名称")
    online_resources: Optional[str] = Field(None, description="网络资源")
    additional_requirements: Optional[str] = None
    generate_reflection: bool = Field(default=False, description="是否生成教学反思")
    supplemental_artifacts: List[Literal["teaching_plan", "experiment_plan"]] = Field(
        default_factory=list,
        description="与批量教案同步生成的学期计划",
    )
    academic_year: Optional[str] = Field(
        None,
        pattern=r"^\d{4}-\d{4}$",
        description="学年，如 2025-2026",
    )
    semester: Optional[Literal[1, 2]] = None
    teacher_name: Optional[str] = Field(None, min_length=1, max_length=50)
    plan_date: Optional[str] = Field(None, description="制表日期，YYYY-MM-DD")
    first_class_date: Optional[str] = Field(None, description="首课日期，YYYY-MM-DD")
    class_periods: Optional[str] = Field(None, max_length=30, description="上课节次，如 3-4")
    experiment_schedules: List[ExperimentClassSchedule] = Field(
        default_factory=list,
        description="各班独立的每周实验课安排",
    )

    @field_validator("supplemental_artifacts")
    @classmethod
    def unique_supplemental_artifacts(
        cls, value: List[Literal["teaching_plan", "experiment_plan"]]
    ) -> List[Literal["teaching_plan", "experiment_plan"]]:
        return list(dict.fromkeys(value))

    @field_validator("majors", "locations")
    @classmethod
    def clean_multi_value_text(cls, value: List[str]) -> List[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))

    @field_validator("class_numbers")
    @classmethod
    def validate_class_numbers(cls, value: List[int]) -> List[int]:
        numbers = list(dict.fromkeys(value))
        if any(number < 1 or number > 5 for number in numbers):
            raise ValueError("班级只能选择 1-5 班")
        return numbers

    @model_validator(mode="after")
    def validate_supplemental_plan_inputs(self):
        uses_professional_classes = bool(
            self.major_classes or self.majors or self.class_numbers
        )
        if uses_professional_classes:
            if not self.major_classes:
                if not self.majors:
                    raise ValueError("请选择至少一个专业")
                if not self.class_numbers:
                    raise ValueError("请选择至少一个班级")
            if not self.grade.endswith("级"):
                raise ValueError("年级必须为 2022级 至 2035级")
            try:
                grade_year = int(self.grade[:-1])
            except ValueError as exc:
                raise ValueError("年级必须为 2022级 至 2035级") from exc
            if grade_year < 2022 or grade_year > 2035:
                raise ValueError("年级必须为 2022级 至 2035级")

        if not self.supplemental_artifacts:
            return self

        missing = [
            label
            for field_name, label in (
                ("academic_year", "学年"),
                ("semester", "学期"),
                ("teacher_name", "教师姓名"),
            )
            if not getattr(self, field_name)
        ]
        if not self.class_ids and not self.major_classes and not (
            self.majors and self.class_numbers
        ):
            missing.append("授课班级")
        if "experiment_plan" in self.supplemental_artifacts:
            if not self.experiment_schedules:
                if not self.first_class_date:
                    missing.append("首课日期")
                if not self.class_periods:
                    missing.append("上课节次")
                if not self.location and not self.locations:
                    missing.append("实验室/授课地点")
            if not self.plan_date:
                missing.append("制表日期")
        if missing:
            raise ValueError("同步生成学期计划还需填写：" + "、".join(missing))

        for field_name, label in (("plan_date", "制表日期"), ("first_class_date", "首课日期")):
            value = getattr(self, field_name)
            if not value:
                continue
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError(f"{label}必须是 YYYY-MM-DD 格式") from exc

        week_count = (len(self.chapters) + 1) // 2
        if "teaching_plan" in self.supplemental_artifacts and week_count > 16:
            raise ValueError(f"授课计划固定模板最多 16 周，当前为 {week_count} 周")

        if "experiment_plan" in self.supplemental_artifacts:
            has_explicit = any(chapter.experiment_name for chapter in self.chapters)
            if has_explicit:
                experiment_count = sum(
                    1
                    for index in range(0, len(self.chapters), 2)
                    if any(chapter.experiment_name for chapter in self.chapters[index:index + 2])
                )
            else:
                experiment_count = week_count
            if experiment_count > 18:
                raise ValueError(
                    f"实验计划固定模板最多 18 条，当前为 {experiment_count} 条"
                )
        return self


class BatchTaskCreateResponse(BaseModel):
    """Response from batch task creation."""
    task_id: str
    status: str


class BatchTask(BaseModel):
    """Batch task information."""
    id: str
    course_name: str
    subject: str
    grade: str
    template_id: str
    total_hours: int
    hours_per_lesson: int = 2
    chapters: List[ChapterInfo]
    start_week: int = 1
    class_ids: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    textbook_name: Optional[str] = None
    online_resources: Optional[str] = None
    generate_reflection: bool = False
    class_names: Optional[str] = None
    supplemental_artifacts: List[Literal["teaching_plan", "experiment_plan"]] = Field(
        default_factory=list
    )
    academic_year: Optional[str] = None
    semester: Optional[int] = None
    teacher_name: Optional[str] = None
    plan_date: Optional[str] = None
    first_class_date: Optional[str] = None
    class_periods: Optional[str] = None
    experiment_schedules: List[ExperimentClassSchedule] = Field(default_factory=list)
    status: Literal["pending", "processing", "completed", "failed", "cancelled"]
    total_count: int
    completed_count: int
    failed_count: int
    zip_file_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None


class BatchLessonPlan(BaseModel):
    """Individual lesson plan in a batch."""
    id: str
    batch_task_id: str
    lesson_plan_id: str
    lesson_number: int
    topic: str
    status: Literal["pending", "processing", "completed", "failed"]
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str


class BatchTaskListResponse(BaseModel):
    """Response for listing batch tasks."""
    tasks: List[BatchTask]
    total: int


class CourseChapterTemplate(BaseModel):
    """Saved course chapter template."""
    id: str
    course_name: str
    subject: str
    grade: str
    total_hours: int
    hours_per_lesson: int = 2
    chapters: List[ChapterInfo]
    use_count: int
    created_at: str
    updated_at: str


class ChapterTemplateListResponse(BaseModel):
    """Response for listing chapter templates."""
    templates: List[CourseChapterTemplate]
    total: int


# ============================================================================
# Lesson Plan Management Models (for Draft System)
# ============================================================================


class LessonPlan(BaseModel):
    """Lesson plan full information."""
    id: str
    template_id: str
    title: str
    subject: Optional[str] = None
    grade: Optional[str] = None
    topic: Optional[str] = None
    input_data: Optional[str] = None  # JSON string
    generated_content: Optional[str] = None  # JSON string
    final_content: Optional[str] = None
    output_file_path: Optional[str] = None
    status: str = "draft"  # draft, draft_cached, generated, published
    batch_task_id: Optional[str] = None
    lesson_number: Optional[int] = None
    class_ids: Optional[str] = None  # JSON string
    created_at: str
    updated_at: str


class LessonPlanListResponse(BaseModel):
    """Response for listing lesson plans."""
    lesson_plans: List[LessonPlan]
    total: int


class UpdateFieldRequest(BaseModel):
    """Request to update a field in lesson plan."""
    field_name: str = Field(..., description="字段名（如 teaching_goals）")
    field_value: Any = Field(..., description="字段新值")


class RegenerateFieldRequest(BaseModel):
    """Request to regenerate a field."""
    field_name: str = Field(..., description="字段名")
    additional_instruction: Optional[str] = Field(None, description="额外指令")


class RegenerateFieldResponse(BaseModel):
    """Response from field regeneration."""
    field_name: str
    field_value: Any


class PublishResponse(BaseModel):
    """Response from publishing a lesson plan."""
    lesson_plan_id: str
    output_file_path: str
    download_url: str


class BatchPublishRequest(BaseModel):
    """Request to batch publish lesson plans."""
    lesson_plan_ids: List[str] = Field(..., description="教案ID列表")
    group_by_document: bool = Field(default=True, description="是否按文档分组（2个/文档）")


class BatchDeleteRequest(BaseModel):
    """Request to batch delete lesson plans."""
    lesson_plan_ids: List[str] = Field(..., description="教案ID列表")


class ExportSelectedRequest(BaseModel):
    """Request to export selected lesson plans from batch task."""
    lesson_plan_ids: List[str] = Field(..., description="选中的教案ID列表")
    group_by_document: bool = Field(default=True, description="是否按文档分组（2个/文档）")


class BatchLessonPlanListResponse(BaseModel):
    """Response for listing lesson plans in a batch task."""
    lesson_plans: List[LessonPlan]
    total: int
    task: BatchTask


class DraftTaskCreateRequest(BaseModel):
    """Request to create a draft task (pre-generate lesson plans)."""
    course_name: str
    subject: str
    grade: str
    template_id: str
    total_hours: int = Field(..., ge=2, description="总课时数")
    hours_per_lesson: int = Field(default=2, ge=1, description="每份教案课时")
    chapters: List[ChapterInfo]
    major_classes: List[MajorClassSelection] = Field(
        default_factory=list,
        description="各专业独立选择的班号",
    )
    majors: List[str] = Field(default_factory=list, description="专业列表")
    class_numbers: List[int] = Field(default_factory=list, description="班号列表（1-5班）")
    textbook_name: Optional[str] = Field(None, description="教材名称")
    location: Optional[str] = Field(None, description="授课地点")
    locations: List[str] = Field(default_factory=list, description="授课地点列表")
    online_resources: Optional[str] = Field(None, description="网络资源")
    generate_reflection: bool = Field(default=False, description="是否生成教学反思")

    @field_validator("majors", "locations")
    @classmethod
    def clean_multi_value_text(cls, value: List[str]) -> List[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))

    @field_validator("class_numbers")
    @classmethod
    def validate_class_numbers(cls, value: List[int]) -> List[int]:
        numbers = list(dict.fromkeys(value))
        if any(number < 1 or number > 5 for number in numbers):
            raise ValueError("班级只能选择 1-5 班")
        return numbers

    @model_validator(mode="after")
    def validate_professional_classes(self):
        if not self.major_classes and not self.majors and not self.class_numbers:
            return self
        if not self.major_classes:
            if not self.majors:
                raise ValueError("请选择至少一个专业")
            if not self.class_numbers:
                raise ValueError("请选择至少一个班级")
        if not self.grade.endswith("级"):
            raise ValueError("年级必须为 2022级 至 2035级")
        try:
            grade_year = int(self.grade[:-1])
        except ValueError as exc:
            raise ValueError("年级必须为 2022级 至 2035级") from exc
        if grade_year < 2022 or grade_year > 2035:
            raise ValueError("年级必须为 2022级 至 2035级")
        return self


class DraftTaskCreateResponse(BaseModel):
    """Response from draft task creation."""
    task_id: str
    status: str


# ============================================================================
# Competition Module Schemas (教学能力比赛模块)
# ============================================================================


class CompetitionProjectCreate(BaseModel):
    """Request to create a competition project."""
    name: str = Field(..., min_length=1, max_length=200, description="项目名称")
    competition_year: Optional[str] = Field(None, description="参赛年份,如 '2024年'")
    competition_region: Optional[str] = Field(None, description="参赛地区/级别,如 '云南省' '全国'")
    competition_level: Optional[str] = Field(None, description="赛事级别,如 '省赛' '国赛'")
    work_name: Optional[str] = Field(None, description="作品名称")
    course_name: Optional[str] = Field(None, description="课程名称,如 《JavaScript编程技术》")
    major_category: Optional[str] = Field(None, description="专业大类,如 电子与信息大类-计算机类")
    major_name: Optional[str] = Field(None, description="专业名称")
    group_name: Optional[str] = Field(None, description="参赛组别,如 专业二组")
    total_hours: int = Field(default=16, ge=2, le=128, description="总学时")
    hours_per_lesson: int = Field(default=2, ge=1, le=8, description="单个教案学时")
    class_name: Optional[str] = Field(None, description="授课班级")
    location: Optional[str] = Field(None, description="授课地点")
    textbook_info: Optional[Dict[str, Any]] = Field(None, description="教材信息")
    context_data: Optional[Dict[str, Any]] = Field(None, description="附加上下文(学情/资源等)")


class CompetitionProjectUpdate(BaseModel):
    """Request to update a competition project."""
    name: Optional[str] = None
    competition_year: Optional[str] = None
    competition_region: Optional[str] = None
    competition_level: Optional[str] = None
    work_name: Optional[str] = None
    course_name: Optional[str] = None
    major_category: Optional[str] = None
    major_name: Optional[str] = None
    group_name: Optional[str] = None
    total_hours: Optional[int] = Field(None, ge=2, le=128)
    hours_per_lesson: Optional[int] = Field(None, ge=1, le=8)
    class_name: Optional[str] = None
    location: Optional[str] = None
    textbook_info: Optional[Dict[str, Any]] = None
    context_data: Optional[Dict[str, Any]] = None


class CompetitionProject(BaseModel):
    """Full competition project info."""
    id: str
    name: str
    competition_year: Optional[str] = None
    competition_region: Optional[str] = None
    competition_level: Optional[str] = None
    work_name: Optional[str] = None
    course_name: Optional[str] = None
    major_category: Optional[str] = None
    major_name: Optional[str] = None
    group_name: Optional[str] = None
    total_hours: int = 16
    hours_per_lesson: int = 2
    class_name: Optional[str] = None
    location: Optional[str] = None
    textbook_info: Optional[Dict[str, Any]] = None
    context_data: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str


class CompetitionProjectListResponse(BaseModel):
    """Response for listing competition projects."""
    projects: List[CompetitionProject]
    total: int


# ----- Generation Request Models -----


class CompetitionLessonPlanGenerateRequest(BaseModel):
    """Request to generate a competition lesson plan."""
    topics_input: Optional[str] = Field(
        None,
        description="可选的任务清单(每行一个,如 '识读施工图\\n深化施工图');不提供则由 AI 自动拆分"
    )
    additional_requirements: Optional[str] = Field(None, description="特殊要求")


class CompetitionReportGenerateRequest(BaseModel):
    """Request to generate a teaching implementation report."""
    related_output_id: Optional[str] = Field(
        None,
        description="可选关联的参赛教案 output_id,作为生成上下文(实现弱关联)"
    )
    additional_requirements: Optional[str] = Field(None, description="特殊要求")


class CompetitionGenerateResponse(BaseModel):
    """Response from triggering generation."""
    output_id: str
    status: str


# ----- Output / Status Models -----


class CompetitionOutput(BaseModel):
    """Competition generation output (lesson plan or report)."""
    id: str
    project_id: str
    output_type: str  # 'lesson_plan' | 'report'
    status: str
    generated_data: Optional[Dict[str, Any]] = None
    output_file_path: Optional[str] = None
    progress_current: int = 0
    progress_total: int = 0
    error_message: Optional[str] = None
    related_lesson_plan_id: Optional[str] = None
    topics_input: Optional[str] = None
    additional_requirements: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None


class CompetitionOutputListResponse(BaseModel):
    """Response for listing outputs of a project."""
    outputs: List[CompetitionOutput]
    total: int


# ----- Generated Content Structure -----


class CompetitionTeachingStep(BaseModel):
    """Single teaching step in a competition lesson plan (课前/课中/课后 内的环节)."""
    stage: str = Field(..., description="环节名称,如 '明确任务' '创设情境'")
    duration: Optional[str] = Field(None, description="时长,如 '5min'")
    content: Optional[str] = Field(None, description="教学内容")
    teacher_activity: Optional[str] = Field(None, description="教师活动")
    student_activity: Optional[str] = Field(None, description="学生活动")
    design_intent: Optional[str] = Field(None, description="设计意图")
    ideological_political: Optional[str] = Field(None, description="思政点")


class CompetitionLessonObjectives(BaseModel):
    """Three-dimensional teaching objectives."""
    knowledge: List[str] = Field(default_factory=list, description="知识目标")
    ability: List[str] = Field(default_factory=list, description="能力目标")
    quality: List[str] = Field(default_factory=list, description="素质目标")


class CompetitionLessonStudentAnalysis(BaseModel):
    """Student situation analysis for a single lesson."""
    knowledge_basis: Optional[str] = Field(None, description="知识与技能基础")
    cognition_practice: Optional[str] = Field(None, description="认知和实践能力")
    learning_features: Optional[str] = Field(None, description="学习特点")
    assessment: Optional[str] = Field(None, description="评估结果")


class CompetitionSingleLesson(BaseModel):
    """Single 【教案 X】 within a competition lesson plan."""
    lesson_number: int = Field(..., description="教案序号 1,2,3...")
    title: str = Field(..., description="任务名称,如 '识读施工图'")
    module_name: Optional[str] = Field(None, description="模块名称")
    project_name: Optional[str] = Field(None, description="项目名称")
    hours: Optional[str] = Field(None, description="授课学时,如 '2 学时'")
    location: Optional[str] = Field(None, description="授课地点")
    class_name: Optional[str] = Field(None, description="授课班级")

    # 教学设计
    position_competition_certificate: Optional[str] = Field(None, description="岗课赛证融合设计")
    student_analysis: Optional[CompetitionLessonStudentAnalysis] = None
    objectives: CompetitionLessonObjectives = Field(default_factory=CompetitionLessonObjectives)
    key_points: Optional[str] = Field(None, description="教学重点")
    difficult_points: Optional[str] = Field(None, description="教学难点")
    key_difficult_solutions: Optional[str] = Field(None, description="重难点解决措施")
    teaching_methods: Optional[str] = Field(None, description="教学方法")
    information_resources: Optional[str] = Field(None, description="信息化平台及资源")

    # 教学实施过程
    pre_class_steps: List[CompetitionTeachingStep] = Field(default_factory=list, description="课前环节")
    in_class_steps: List[CompetitionTeachingStep] = Field(default_factory=list, description="课中环节")
    after_class_steps: List[CompetitionTeachingStep] = Field(default_factory=list, description="课后环节")

    # 反思
    reflection: Optional[str] = Field(None, description="教学反思与改进")


class CompetitionOverallDesign(BaseModel):
    """Overall design section for a competition lesson plan."""
    content_analysis: Optional[str] = Field(None, description="内容分析")
    student_analysis: Optional[str] = Field(None, description="学情分析")
    goal_analysis: Optional[str] = Field(None, description="目标分析")
    process_design: Optional[str] = Field(None, description="过程设计")
    teaching_method: Optional[str] = Field(None, description="教学方法")
    survey_questions: List[str] = Field(default_factory=list, description="学情调查问卷")


class CompetitionLessonContent(BaseModel):
    """Complete competition lesson plan content."""
    overall_design: CompetitionOverallDesign = Field(default_factory=CompetitionOverallDesign)
    lessons: List[CompetitionSingleLesson] = Field(default_factory=list, description="多个教案")


# ----- Report Content Structure -----


class CompetitionReportEvaluation(BaseModel):
    """Multi-source evaluation in implementation report."""
    student_evaluation: Optional[str] = Field(None, description="学生评价")
    teacher_evaluation: Optional[str] = Field(None, description="教师评价")
    enterprise_evaluation: Optional[str] = Field(None, description="企业评价")


class CompetitionReportEffect(BaseModel):
    """Student learning effect section."""
    pre_class_improvement: Optional[str] = Field(None, description="课前学习提升")
    in_class_improvement: Optional[str] = Field(None, description="课中教学质量提升")
    certification_competition: Optional[str] = Field(None, description="取证及竞赛成绩")


class CompetitionReportReflection(BaseModel):
    """Teaching reflection section."""
    feature_innovations: List[str] = Field(default_factory=list, description="特色创新点")
    shortcomings: List[str] = Field(default_factory=list, description="不足之处")
    improvement_measures: List[str] = Field(default_factory=list, description="改进措施")


class CompetitionImplementationStage(BaseModel):
    """Single implementation stage row in the report."""
    stage: str = Field(..., description="阶段,如 '课前' '课中(线上)'")
    task: str = Field(..., description="任务描述")
    effect: str = Field(..., description="效果/图说")


class CompetitionReportContent(BaseModel):
    """Complete teaching implementation report content."""
    intro_summary: Optional[str] = Field(None, description="开篇总述")

    # 一、整体教学设计
    content_analysis: Optional[str] = Field(None, description="教学内容分析")
    student_analysis: Optional[str] = Field(None, description="学情分析")
    teaching_objectives: Optional[str] = Field(None, description="教学目标与重难点")
    teaching_strategy: Optional[str] = Field(None, description="教学策略")

    # 二、教学实施过程
    implementation_stages: List[CompetitionImplementationStage] = Field(default_factory=list)
    blended_teaching_improvement: Optional[str] = Field(None, description="混合式教学实施改进")
    evaluation: CompetitionReportEvaluation = Field(default_factory=CompetitionReportEvaluation)

    # 三、学生学习效果
    learning_effect: CompetitionReportEffect = Field(default_factory=CompetitionReportEffect)

    # 四、教学反思与改进
    reflection: CompetitionReportReflection = Field(default_factory=CompetitionReportReflection)
