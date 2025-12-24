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
# Lesson Plan Generation Models
# ============================================================================


class LessonPlanInput(BaseModel):
    """Lesson plan input data."""
    template_id: str
    subject: str
    grade: str
    topic: str
    duration: str
    textbook_version: Optional[str] = None
    unit_name: Optional[str] = None
    prior_knowledge: Optional[str] = None
    focus_areas: Optional[str] = None
    teaching_style: Optional[str] = None
    additional_requirements: Optional[str] = None


class LessonPlanGenerateRequest(LessonPlanInput):
    """Request to generate a lesson plan."""
    pass


class TeachingGoal(BaseModel):
    """Teaching goal."""
    knowledge: List[str]
    ability: List[str]
    emotion: List[str]


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
    """Generated lesson plan content."""
    teaching_goals: TeachingGoal
    key_points: str
    difficult_points: str
    teaching_tools: str
    teaching_methods: str
    student_analysis: str
    textbook_analysis: str
    teaching_steps: List[TeachingStep]
    homework: Homework
    blackboard_design: Optional[str] = None
    reflection: Optional[str] = None


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
