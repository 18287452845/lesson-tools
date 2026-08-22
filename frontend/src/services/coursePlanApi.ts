/**
 * Standalone Course Plan API Client
 *
 * Builds editable Yunlin teaching/experiment plan drafts from generated
 * lesson plans and exports them as fixed-template Word documents.
 */
import api from './api';
import { downloadBlob } from './lessonPlanApi';
import type {
  CoursePlanCreateRequest,
  CoursePlanDetail,
  CoursePlanListResponse,
  CoursePlanUpdateRequest,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

/**
 * Create a semester-plan draft from selected generated lesson plans
 */
export async function createCoursePlan(
  request: CoursePlanCreateRequest
): Promise<CoursePlanDetail> {
  const response = await api.post(`${API_BASE_URL}/course-plans`, request);
  return response.data;
}

/**
 * List semester-plan drafts
 */
export async function listCoursePlans(params: {
  status?: string;
  page?: number;
  limit?: number;
} = {}): Promise<CoursePlanListResponse> {
  const queryParams = new URLSearchParams();
  if (params.status) queryParams.append('status', params.status);
  if (params.page) queryParams.append('page', params.page.toString());
  if (params.limit) queryParams.append('limit', params.limit.toString());
  const response = await api.get(
    `${API_BASE_URL}/course-plans?${queryParams.toString()}`
  );
  return response.data;
}

/**
 * Get the full editable state of a semester plan
 */
export async function getCoursePlan(coursePlanId: string): Promise<CoursePlanDetail> {
  const response = await api.get(`${API_BASE_URL}/course-plans/${coursePlanId}`);
  return response.data;
}

/**
 * Save edited metadata and lesson rows
 */
export async function updateCoursePlan(
  coursePlanId: string,
  request: CoursePlanUpdateRequest
): Promise<CoursePlanDetail> {
  const response = await api.put(
    `${API_BASE_URL}/course-plans/${coursePlanId}`,
    request
  );
  return response.data;
}

/**
 * Delete a semester-plan draft
 */
export async function deleteCoursePlan(coursePlanId: string): Promise<void> {
  await api.delete(`${API_BASE_URL}/course-plans/${coursePlanId}`);
}

/**
 * Export the semester plan as docx (or zip when multiple files) and download it
 */
export async function exportCoursePlan(coursePlanId: string): Promise<string> {
  const response = await api.post(
    `${API_BASE_URL}/course-plans/${coursePlanId}/export`,
    null,
    { responseType: 'blob' }
  );
  const disposition = String(response.headers?.['content-disposition'] || '');
  const match = disposition.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i);
  const filename = match
    ? decodeURIComponent(match[1].replace(/"/g, ''))
    : '学期计划.docx';
  downloadBlob(response.data, filename);
  return filename;
}

export default {
  createCoursePlan,
  listCoursePlans,
  getCoursePlan,
  updateCoursePlan,
  deleteCoursePlan,
  exportCoursePlan,
};
