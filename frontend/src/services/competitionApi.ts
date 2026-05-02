/**
 * Competition module API service
 *
 * Endpoints:
 *   - Project CRUD
 *   - Generate lesson plan / report (background tasks)
 *   - Poll output status / SSE stream / download
 */
import axios from 'axios';
import type {
  CompetitionProject,
  CompetitionProjectCreate,
  CompetitionProjectUpdate,
  CompetitionProjectListResponse,
  CompetitionLessonPlanGenerateRequest,
  CompetitionReportGenerateRequest,
  CompetitionGenerateResponse,
  CompetitionOutput,
  CompetitionOutputListResponse,
} from '@/types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 60000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    if (Array.isArray(detail)) {
      const errors = detail
        .map((err: any) => `${(err.loc || []).join('.')}: ${err.msg}`)
        .join('; ');
      return Promise.reject(new Error(`验证失败: ${errors}`));
    }
    const message = detail || error.message || '请求失败';
    return Promise.reject(new Error(message));
  }
);

export const competitionApi = {
  // ----- Project CRUD -----
  async createProject(data: CompetitionProjectCreate): Promise<CompetitionProject> {
    const response = await api.post<CompetitionProject>('/competition/projects', data);
    return response.data;
  },

  async listProjects(params?: {
    page?: number;
    limit?: number;
  }): Promise<CompetitionProjectListResponse> {
    const response = await api.get<CompetitionProjectListResponse>('/competition/projects', {
      params,
    });
    return response.data;
  },

  async getProject(projectId: string): Promise<CompetitionProject> {
    const response = await api.get<CompetitionProject>(`/competition/projects/${projectId}`);
    return response.data;
  },

  async updateProject(
    projectId: string,
    data: CompetitionProjectUpdate
  ): Promise<CompetitionProject> {
    const response = await api.patch<CompetitionProject>(
      `/competition/projects/${projectId}`,
      data
    );
    return response.data;
  },

  async deleteProject(projectId: string): Promise<void> {
    await api.delete(`/competition/projects/${projectId}`);
  },

  // ----- Outputs -----
  async listProjectOutputs(projectId: string): Promise<CompetitionOutputListResponse> {
    const response = await api.get<CompetitionOutputListResponse>(
      `/competition/projects/${projectId}/outputs`
    );
    return response.data;
  },

  async generateLessonPlan(
    projectId: string,
    data: CompetitionLessonPlanGenerateRequest
  ): Promise<CompetitionGenerateResponse> {
    const response = await api.post<CompetitionGenerateResponse>(
      `/competition/projects/${projectId}/generate-lesson-plan`,
      data
    );
    return response.data;
  },

  async generateReport(
    projectId: string,
    data: CompetitionReportGenerateRequest
  ): Promise<CompetitionGenerateResponse> {
    const response = await api.post<CompetitionGenerateResponse>(
      `/competition/projects/${projectId}/generate-report`,
      data
    );
    return response.data;
  },

  async getOutput(outputId: string): Promise<CompetitionOutput> {
    const response = await api.get<CompetitionOutput>(`/competition/outputs/${outputId}`);
    return response.data;
  },

  async deleteOutput(outputId: string): Promise<void> {
    await api.delete(`/competition/outputs/${outputId}`);
  },

  /**
   * Subscribe to SSE progress stream for an output.
   *
   * Usage:
   *   const cleanup = competitionApi.streamOutputProgress(outputId, {
   *     onProgress: (data) => { ... },
   *     onDone: (data) => { ... },
   *     onError: (msg) => { ... },
   *   });
   *   // Call cleanup() to disconnect
   */
  streamOutputProgress(
    outputId: string,
    callbacks: {
      onProgress?: (data: {
        status: string;
        progress_current: number;
        progress_total: number;
        error_message?: string | null;
      }) => void;
      onDone?: (data: any) => void;
      onError?: (message: string) => void;
    }
  ): () => void {
    const url = `${api.defaults.baseURL}/competition/outputs/${outputId}/stream`;
    const eventSource = new EventSource(url);

    eventSource.addEventListener('progress', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        callbacks.onProgress?.(data);
      } catch (err) {
        console.error('SSE progress parse error', err);
      }
    });

    eventSource.addEventListener('done', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        callbacks.onDone?.(data);
      } catch (err) {
        console.error('SSE done parse error', err);
      } finally {
        eventSource.close();
      }
    });

    eventSource.addEventListener('error', (e: MessageEvent) => {
      try {
        const data = e.data ? JSON.parse(e.data) : { message: 'SSE connection error' };
        callbacks.onError?.(data.message || 'SSE error');
      } catch {
        callbacks.onError?.('SSE connection error');
      }
      eventSource.close();
    });

    return () => eventSource.close();
  },

  /**
   * Get download URL for a completed output.
   */
  getDownloadUrl(outputId: string): string {
    return `${api.defaults.baseURL}/competition/outputs/${outputId}/download`;
  },

  /**
   * Trigger browser download.
   */
  async downloadOutput(outputId: string): Promise<void> {
    const url = this.getDownloadUrl(outputId);
    window.open(url, '_blank');
  },
};
