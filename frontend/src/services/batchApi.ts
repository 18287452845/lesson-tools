/**
 * Batch generation API service
 */
import axios from 'axios';
import type {
  ChapterSplitRequest,
  ChapterSplitResponse,
  BatchTaskCreateRequest,
  BatchTaskCreateResponse,
  BatchTask,
  BatchTaskListResponse,
  ChapterTemplateListResponse,
} from '@/types';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 60000, // 60 seconds
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle validation errors (422)
    if (error.response?.status === 422) {
      const detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        // Pydantic validation errors
        const errors = detail.map((err: any) => {
          const field = err.loc?.join('.') || 'unknown';
          return `${field}: ${err.msg}`;
        }).join('; ');
        return Promise.reject(new Error(`验证失败: ${errors}`));
      }
      return Promise.reject(new Error(detail || '数据验证失败'));
    }

    const message = error.response?.data?.detail || error.message || '请求失败';
    return Promise.reject(new Error(message));
  }
);

// ============================================================================
// Batch Generation API
// ============================================================================

export const batchApi = {
  /**
   * Split a course into chapters using AI
   */
  async splitChapters(data: ChapterSplitRequest): Promise<ChapterSplitResponse> {
    const response = await api.post<ChapterSplitResponse>('/batch/split-chapters', data);
    return response.data;
  },

  /**
   * Create a batch task and start processing
   */
  async createBatchTask(data: BatchTaskCreateRequest): Promise<BatchTaskCreateResponse> {
    const response = await api.post<BatchTaskCreateResponse>('/batch/create-task', data);
    return response.data;
  },

  /**
   * Get batch task status
   */
  async getBatchTask(taskId: string): Promise<BatchTask> {
    const response = await api.get<BatchTask>(`/batch/tasks/${taskId}`);
    return response.data;
  },

  /**
   * List all batch tasks
   */
  async listBatchTasks(params?: {
    status?: string;
    page?: number;
    limit?: number;
  }): Promise<BatchTaskListResponse> {
    const response = await api.get<BatchTaskListResponse>('/batch/tasks', { params });
    return response.data;
  },

  /**
   * Download the ZIP file for a completed batch task
   */
  async downloadBatchZip(taskId: string, courseName: string): Promise<void> {
    const response = await api.get(`/batch/tasks/${taskId}/download`, {
      responseType: 'blob',
    });

    // Create a download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${courseName}_批量教案.zip`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  /**
   * Delete or cancel a batch task
   */
  async deleteBatchTask(taskId: string): Promise<void> {
    await api.delete(`/batch/tasks/${taskId}`);
  },

  /**
   * List all cached chapter templates
   */
  async listChapterTemplates(params?: {
    page?: number;
    limit?: number;
  }): Promise<ChapterTemplateListResponse> {
    const response = await api.get<ChapterTemplateListResponse>('/batch/chapter-templates', { params });
    return response.data;
  },
};

export default batchApi;
