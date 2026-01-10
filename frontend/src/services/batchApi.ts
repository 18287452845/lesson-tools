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
  ChapterInfo,
  SmartAllocationRequest,
} from '@/types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
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
   * Split chapters with Server-Sent Events streaming
   *
   * @param data - Chapter split request
   * @param onProgress - Callback for progress updates: (current, total, message) => void
   * @param onChapter - Callback for each chapter: (chapter) => void
   * @param onComplete - Callback when complete: (response) => void
   * @param onError - Callback on error: (errorMessage) => void
   */
  async splitChaptersStream(
    data: ChapterSplitRequest,
    onProgress: (current: number, total: number, message: string) => void,
    onChapter: (chapter: ChapterInfo) => void,
    onComplete: (response: ChapterSplitResponse) => void,
    onError: (errorMessage: string) => void
  ): Promise<void> {
    const response = await fetch(`${api.defaults.baseURL}/batch/split-chapters-stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('Response body is null');
    }

    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages (separated by \n\n)
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || ''; // Keep incomplete message in buffer

        for (const line of lines) {
          if (!line.trim()) continue;

          // Parse SSE format: "event: xxx\ndata: {...}"
          const eventMatch = line.match(/^event: (.+)$/m);
          const dataMatch = line.match(/^data: (.+)$/m);

          if (eventMatch && dataMatch) {
            const eventType = eventMatch[1];
            const data = JSON.parse(dataMatch[1]);

            switch (eventType) {
              case 'progress':
                onProgress(data.current, data.total, data.message);
                break;
              case 'chapter':
                onChapter(data);
                break;
              case 'complete':
                onComplete(data);
                return;
              case 'error':
                onError(data.message);
                return;
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  /**
   * Smart allocation: AI intelligently allocates chapters to weekly teaching plans
   */
  async splitChaptersSmartStream(
    data: SmartAllocationRequest,
    onProgress: (current: number, total: number, message: string) => void,
    onChapter: (chapter: ChapterInfo) => void,
    onComplete: (response: ChapterSplitResponse) => void,
    onError: (errorMessage: string) => void
  ): Promise<void> {
    const response = await fetch(`${api.defaults.baseURL}/batch/split-chapters-smart-stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('Response body is null');
    }

    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;

          // Parse SSE format
          const eventMatch = line.match(/^event: (.+)$/m);
          const dataMatch = line.match(/^data: (.+)$/m);

          if (eventMatch && dataMatch) {
            const eventType = eventMatch[1];
            const data = JSON.parse(dataMatch[1]);

            switch (eventType) {
              case 'progress':
                onProgress(data.current, data.total, data.message);
                break;
              case 'chapter':
                onChapter(data);
                break;
              case 'complete':
                onComplete(data);
                return;
              case 'error':
                onError(data.message);
                return;
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
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
   * Create a draft task (pre-generate lesson plans without creating documents)
   */
  async createDraftTask(data: import('@/types').DraftTaskCreateRequest): Promise<import('@/types').DraftTaskCreateResponse> {
    const response = await api.post<import('@/types').DraftTaskCreateResponse>('/batch/create-draft-task', data);
    return response.data;
  },

  /**
   * Get all lesson plans for a batch task
   */
  async getTaskLessonPlans(
    taskId: string,
    params?: {
      page?: number;
      limit?: number;
    }
  ): Promise<import('@/types').BatchLessonPlanListResponse> {
    const response = await api.get<import('@/types').BatchLessonPlanListResponse>(
      `/batch/tasks/${taskId}/lesson-plans`,
      { params }
    );
    return response.data;
  },

  /**
   * Export selected lesson plans from a batch task as a ZIP file
   */
  async exportSelectedLessonPlans(
    taskId: string,
    request: import('@/types').ExportSelectedRequest
  ): Promise<Blob> {
    const response = await api.post(`/batch/tasks/${taskId}/export-selected`, request, {
      responseType: 'blob',
    });
    return response.data;
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
