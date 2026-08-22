/**
 * Lesson Plan Management API Client
 *
 * Provides API methods for managing cached/draft lesson plans:
 * - List and filter lesson plans
 * - Get lesson plan details
 * - Update and regenerate fields
 * - Publish drafts to Word documents
 * - Batch operations (publish, delete)
 */
import api from './api';
import type {
  LessonPlan,
  LessonPlanListResponse,
  UpdateFieldRequest,
  RegenerateFieldRequest,
  RegenerateFieldResponse,
  PublishResponse,
  BatchPublishRequest,
  BatchDeleteRequest,
} from '@/types';



/**
 * List lesson plans with optional filters
 */
export async function listLessonPlans(params: {
  status?: string;
  template_id?: string;
  subject?: string;
  grade?: string;
  search?: string;
  page?: number;
  limit?: number;
}): Promise<LessonPlanListResponse> {
  const queryParams = new URLSearchParams();

  if (params.status) queryParams.append('status', params.status);
  if (params.template_id) queryParams.append('template_id', params.template_id);
  if (params.subject) queryParams.append('subject', params.subject);
  if (params.grade) queryParams.append('grade', params.grade);
  if (params.search) queryParams.append('search', params.search);
  if (params.page) queryParams.append('page', params.page.toString());
  if (params.limit) queryParams.append('limit', params.limit.toString());

  const response = await api.get(
    `/lesson-plans?${queryParams.toString()}`
  );
  return response.data;
}

/**
 * Get a single lesson plan by ID
 */
export async function getLessonPlan(lessonPlanId: string): Promise<LessonPlan> {
  const response = await api.get(`/lesson-plans/${lessonPlanId}`);
  return response.data;
}

/**
 * Update a single field in a lesson plan
 */
export async function updateField(
  lessonPlanId: string,
  request: UpdateFieldRequest
): Promise<LessonPlan> {
  const response = await api.put(
    `/lesson-plans/${lessonPlanId}/field`,
    request
  );
  return response.data;
}

/**
 * Regenerate a single field using AI
 */
export async function regenerateField(
  lessonPlanId: string,
  request: RegenerateFieldRequest
): Promise<RegenerateFieldResponse> {
  const response = await api.post(
    `/lesson-plans/${lessonPlanId}/regenerate-field`,
    request
  );
  return response.data;
}

/**
 * Publish a draft lesson plan (generate Word document)
 */
export async function publishLessonPlan(lessonPlanId: string): Promise<PublishResponse> {
  const response = await api.post(
    `/lesson-plans/${lessonPlanId}/publish`
  );
  return response.data;
}

/**
 * Batch publish multiple lesson plans
 * Returns a ZIP file blob
 */
export async function batchPublish(request: BatchPublishRequest): Promise<Blob> {
  const response = await api.post(
    `/lesson-plans/batch-publish`,
    request,
    { responseType: 'blob' }
  );
  return response.data;
}

/**
 * Delete a single lesson plan
 */
export async function deleteLessonPlan(lessonPlanId: string): Promise<void> {
  await api.delete(`/lesson-plans/${lessonPlanId}`);
}

/**
 * Batch delete multiple lesson plans
 */
export async function batchDelete(request: BatchDeleteRequest): Promise<{
  message: string;
  deleted_count: number;
  failed_ids: string[];
}> {
  const response = await api.post(
    `/lesson-plans/batch-delete`,
    request
  );
  return response.data;
}

/**
 * Helper: Download blob as file
 */
export function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * Helper: Parse canonical content (partial final fields override generated fields)
 */
export function parseGeneratedContent(lessonPlan: LessonPlan): any {
  let generated: Record<string, unknown> = {};
  try {
    generated = lessonPlan.generated_content
      ? JSON.parse(lessonPlan.generated_content)
      : {};
  } catch (e) {
    console.error('Failed to parse generated_content:', e);
  }
  if (!lessonPlan.final_content) return generated;
  try {
    return { ...generated, ...JSON.parse(lessonPlan.final_content) };
  } catch (e) {
    console.error('Failed to parse final_content:', e);
    return generated;
  }
}

/**
 * Helper: Parse input_data JSON from lesson plan
 */
export function parseInputData(lessonPlan: LessonPlan): any {
  if (!lessonPlan.input_data) return {};
  try {
    return JSON.parse(lessonPlan.input_data);
  } catch (e) {
    console.error('Failed to parse input_data:', e);
    return {};
  }
}

export default {
  listLessonPlans,
  getLessonPlan,
  updateField,
  regenerateField,
  publishLessonPlan,
  batchPublish,
  deleteLessonPlan,
  batchDelete,
  downloadBlob,
  parseGeneratedContent,
  parseInputData,
};
