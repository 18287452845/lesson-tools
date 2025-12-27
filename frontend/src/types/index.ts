/**
 * TypeScript type definitions for the Lesson Plan Tool
 */

// ============================================================================
// Template Types
// ============================================================================

export interface FieldConfig {
  name: string;
  display_name: string;
  description?: string;
  required: boolean;
  field_type: 'text' | 'textarea' | 'json' | 'array';
  default_value?: string;
}

export interface TemplateInfo {
  id: string;
  name: string;
  description?: string;
  subject?: string;
  grade?: string;
  file_path: string;
  fields_config: FieldConfig[];
  preview_image?: string;
  use_count: number;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Lesson Plan Generation Types
// ============================================================================

export interface LessonPlanInput {
  template_id: string;
  subject: string;
  grade: string;
  topic: string;
  duration: string;
  textbook_version?: string;
  unit_name?: string;
  prior_knowledge?: string;
  focus_areas?: string;
  teaching_style?: string;
  additional_requirements?: string;
}

export interface TeachingGoal {
  knowledge: string[];
  ability: string[];
  emotion: string[];
}

export interface TeachingStep {
  stage: string;
  duration: string;
  teacher_activity: string;
  student_activity: string;
  design_intent: string;
}

export interface Homework {
  required: string;
  optional?: string;
}

export interface GeneratedContent {
  teaching_goals: TeachingGoal;
  key_points: string;
  difficult_points: string;
  teaching_tools: string;
  teaching_methods: string;
  student_analysis: string;
  textbook_analysis: string;
  teaching_steps: TeachingStep[];
  homework: Homework;
  blackboard_design?: string;
  reflection?: string;
}

export interface LessonPlanResponse {
  id: string;
  template_id: string;
  input: LessonPlanInput;
  content: GeneratedContent;
  status: string;
  created_at: string;
}

// ============================================================================
// Document Editing Types
// ============================================================================

export interface SectionLocation {
  in_table: boolean;
  table_idx?: number;
  cell_location?: [number, number];
  start_para_idx?: number;
  end_para_idx?: number;
}

export interface ParsedSection {
  name: string;
  found: boolean;
  content?: string;
  location?: SectionLocation;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  parsed_sections: Record<string, ParsedSection>;
}

export type EditOperation = 'replace' | 'append' | 'insert' | 'generate' | 'ai_modify';

export interface SectionEditRequest {
  section_name: string;
  operation: EditOperation;
  content?: string;
  ai_instruction?: string;
}

export type EnhancementType = 'detailed' | 'professional' | 'simplified' | 'rewrite';

export interface AIEnhanceRequest {
  section_name: string;
  enhancement_type: EnhancementType;
  specific_instruction?: string;
}

export interface EditHistoryItem {
  section: string;
  operation: string;
  timestamp: string;
}

// ============================================================================
// Common Types
// ============================================================================

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

export type GradeLevel =
  | '一年级' | '二年级' | '三年级' | '四年级' | '五年级' | '六年级'
  | '七年级' | '八年级' | '九年级'
  | '高一' | '高二' | '高三'
  | '大一' | '大二' | '大三' | '大四'
  | '2023级' | '2024级' | '2025级';

export type Subject =
  | '语文' | '数学' | '英语' | '物理' | '化学' | '生物'
  | '历史' | '地理' | '政治' | '科学' | '音乐' | '美术' | '体育'
  | '大数据技术' | '信息安全技术' | '云计算技术' | '人工智能' | 'Java程序设计'
  | 'Python程序设计' | '数据结构' | '计算机网络' | '操作系统' | '数据库原理'
  | '软件工程' | 'Web开发' | '移动应用开发' | 'Linux系统管理';

export const SUBJECT_OPTIONS: Subject[] = [
  // 大学专业课程
  '大数据技术', '信息安全技术', '云计算技术', '人工智能',
  'Java程序设计', 'Python程序设计', '数据结构', '计算机网络',
  '操作系统', '数据库原理', '软件工程', 'Web开发',
  '移动应用开发', 'Linux系统管理',
  // 基础学科
  '语文', '数学', '英语', '物理', '化学', '生物',
  '历史', '地理', '政治', '科学', '音乐', '美术', '体育',
];

export const GRADE_OPTIONS: GradeLevel[] = [
  // 大学年级
  '大一', '大二', '大三', '大四',
  '2023级', '2024级', '2025级',
  // 高中年级
  '高一', '高二', '高三',
  // 初中年级
  '七年级', '八年级', '九年级',
  // 小学年级
  '一年级', '二年级', '三年级', '四年级', '五年级', '六年级',
];

export const DURATION_OPTIONS = [
  '1课时', '2课时', '3课时', '0.5课时', '45分钟', '40分钟',
];

// ============================================================================
// Batch Generation Types
// ============================================================================

export interface ChapterInfo {
  lesson_number: number;
  topic: string;
  content_summary: string;
  key_concepts: string[];
}

export interface ChapterSplitRequest {
  course_name: string;
  subject: string;
  grade: string;
  total_hours: number;
  hours_per_lesson?: number;
  chapters_input?: string;
  additional_info?: string;
}

export interface ChapterSplitResponse {
  chapters: ChapterInfo[];
  total_lessons: number;
}

export interface BatchTaskCreateRequest {
  course_name: string;
  subject: string;
  grade: string;
  template_id: string;
  total_hours: number;
  hours_per_lesson?: number;
  chapters: ChapterInfo[];
  additional_requirements?: string;
}

export interface BatchTaskCreateResponse {
  task_id: string;
  status: string;
}

export type BatchTaskStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface BatchTask {
  id: string;
  course_name: string;
  subject: string;
  grade: string;
  template_id: string;
  total_hours: number;
  hours_per_lesson: number;
  chapters: ChapterInfo[];
  status: BatchTaskStatus;
  total_count: number;
  completed_count: number;
  failed_count: number;
  zip_file_path?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface BatchLessonPlan {
  id: string;
  batch_task_id: string;
  lesson_plan_id: string;
  lesson_number: number;
  topic: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  file_path?: string;
  error_message?: string;
  created_at: string;
}

export interface BatchTaskListResponse {
  tasks: BatchTask[];
  total: number;
}

export interface CourseChapterTemplate {
  id: string;
  course_name: string;
  subject: string;
  grade: string;
  total_hours: number;
  hours_per_lesson: number;
  chapters: ChapterInfo[];
  use_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChapterTemplateListResponse {
  templates: CourseChapterTemplate[];
  total: number;
}

// ============================================================================
// Template Editor Types
// ============================================================================

export interface TemplateVersion {
  id: string;
  version_number: number;
  user: string;
  comment: string;
  created_at: string;
  content_size: number;
}

export interface VersionListResponse {
  versions: TemplateVersion[];
}

export interface VersionCompareResult {
  version_1: string;
  version_2: string;
  diff: string;
  added_lines: number;
  removed_lines: number;
  total_changes: number;
}

export interface TemplateHtmlResponse {
  html: string;
  metadata: TemplateMetadata;
  messages: string[];
  name: string;
}

export interface TemplateMetadata {
  title?: string;
  subject?: string;
  author?: string;
  created?: string;
  modified?: string;
  file_size?: number;
  file_name?: string;
  paragraphs_count?: number;
  tables_count?: number;
}

export interface JinjaValidationResult {
  valid: boolean;
  errors: string[];
  variables: string[];
}

export interface JinjaVariable {
  name: string;
  type: string;
}

export interface HtmlExportResponse {
  success: boolean;
  filename: string;
  download_url: string;
}
