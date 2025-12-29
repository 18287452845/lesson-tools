"""
Pydantic models for request/response validation.
"""
import json
from datetime import datetime
from typing import Optional, Dict, List, Any, Literal
from pydantic import BaseModel, Field
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


class ChapterSplitRequest(BaseModel):
    """Request to split course into chapters."""
    course_name: str
    subject: str
    grade: str
    total_hours: int = Field(..., ge=2, description="总课时数（如64、72）")
    hours_per_lesson: int = Field(default=2, ge=1, description="每份教案课时")
    chapters_input: Optional[str] = Field(None, description="用户手动输入的章节（每行一个，可选）")
    additional_info: Optional[str] = None


class ChapterSplitResponse(BaseModel):
    """Response from chapter splitting."""
    chapters: List[ChapterInfo]
    total_lessons: int = Field(..., description="教案总数")


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
    location: Optional[str] = Field(None, description="授课地点")
    textbook_name: Optional[str] = Field(None, description="教材名称")
    online_resources: Optional[str] = Field(None, description="网络资源")
    additional_requirements: Optional[str] = None
    generate_reflection: bool = Field(default=False, description="是否生成教学反思")


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
    class_ids: List[str] = []
    location: Optional[str] = None
    textbook_name: Optional[str] = None
    online_resources: Optional[str] = None
    generate_reflection: bool = False
    class_names: Optional[str] = None
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
