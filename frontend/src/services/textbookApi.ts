/**
 * Textbook API service for communicating with the backend
 */
import axios from 'axios';
import type {
  TextbookInfo,
  TextbookCreateRequest,
  TextbookUpdateRequest,
  TextbookListResponse,
  TextbookChapterInfo,
  TextbookChapterCreateRequest,
  TextbookChapterBatchCreateRequest,
  TextbookChapterGenerateRequest,
  TextbookChapterGenerateResponse,
  TextbookChapterEnrichRequest,
  TextbookChapterEnrichResponse,
} from '@/types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 120000, // 120 seconds for AI generation
});

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败';
    return Promise.reject(new Error(message));
  }
);

// ============================================================================
// Textbook CRUD API
// ============================================================================

export const textbookApi = {
  /**
   * Create a new textbook
   */
  createTextbook: async (data: TextbookCreateRequest): Promise<TextbookInfo> => {
    const response = await api.post('/textbooks', data);
    return response.data;
  },

  /**
   * List textbooks with optional filtering
   */
  listTextbooks: async (params?: {
    page?: number;
    limit?: number;
    subject?: string;
    grade?: string;
    status?: 'active' | 'inactive';
  }): Promise<TextbookListResponse> => {
    const response = await api.get('/textbooks', { params });
    return response.data;
  },

  /**
   * Get a specific textbook with chapters
   */
  getTextbook: async (id: string): Promise<TextbookInfo> => {
    const response = await api.get(`/textbooks/${id}`);
    return response.data;
  },

  /**
   * Update textbook information
   */
  updateTextbook: async (
    id: string,
    data: TextbookUpdateRequest
  ): Promise<TextbookInfo> => {
    const response = await api.patch(`/textbooks/${id}`, data);
    return response.data;
  },

  /**
   * Delete textbook (soft delete)
   */
  deleteTextbook: async (id: string): Promise<void> => {
    await api.delete(`/textbooks/${id}`);
  },

  // ============================================================================
  // Chapter Management API
  // ============================================================================

  /**
   * Generate textbook chapters using AI (preview only, not saved)
   */
  generateChapters: async (
    textbookId: string,
    data: TextbookChapterGenerateRequest
  ): Promise<TextbookChapterGenerateResponse> => {
    const response = await api.post(
      `/textbooks/${textbookId}/generate-chapters`,
      data
    );
    return response.data;
  },

  /**
   * AI enrich manually entered chapters with summary and key concepts
   */
  enrichChapters: async (
    textbookId: string,
    data: TextbookChapterEnrichRequest
  ): Promise<TextbookChapterEnrichResponse> => {
    const response = await api.post(
      `/textbooks/${textbookId}/chapters/ai-enrich`,
      data
    );
    return response.data;
  },

  /**
   * Save chapters to textbook (after user review)
   */
  saveChapters: async (
    textbookId: string,
    data: TextbookChapterBatchCreateRequest
  ): Promise<TextbookInfo> => {
    const response = await api.post(`/textbooks/${textbookId}/chapters`, data);
    return response.data;
  },

  /**
   * Get a specific chapter
   */
  getChapter: async (
    textbookId: string,
    chapterId: string
  ): Promise<TextbookChapterInfo> => {
    const response = await api.get(
      `/textbooks/${textbookId}/chapters/${chapterId}`
    );
    return response.data;
  },

  /**
   * Update a chapter
   */
  updateChapter: async (
    textbookId: string,
    chapterId: string,
    data: TextbookChapterCreateRequest
  ): Promise<TextbookChapterInfo> => {
    const response = await api.patch(
      `/textbooks/${textbookId}/chapters/${chapterId}`,
      data
    );
    return response.data;
  },

  /**
   * Delete a chapter
   */
  deleteChapter: async (textbookId: string, chapterId: string): Promise<void> => {
    await api.delete(`/textbooks/${textbookId}/chapters/${chapterId}`);
  },
};

export default textbookApi;
