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
  TextbookSearchRequest,
  TextbookSearchResponse,
  TextbookCatalogRequest,
  TextbookCatalogPreviewResponse,
  TextbookImportRequest,
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
   * List every textbook matching the filters, across all API pages.
   * Selection controls use this so newly added books cannot fall off page one.
   */
  listAllTextbooks: async (params?: {
    subject?: string;
    grade?: string;
    status?: 'active' | 'inactive';
  }): Promise<TextbookInfo[]> => {
    const limit = 100;
    const firstResponse = await api.get<TextbookListResponse>('/textbooks', {
      params: { ...params, page: 1, limit },
    });
    const firstPage = firstResponse.data;
    const pageCount = Math.ceil(firstPage.total / limit);
    const remainingPages = pageCount > 1
      ? await Promise.all(
        Array.from({ length: pageCount - 1 }, (_, index) => (
          api.get<TextbookListResponse>('/textbooks', {
            params: { ...params, page: index + 2, limit },
          })
        ))
      )
      : [];

    const byId = new Map<string, TextbookInfo>();
    [firstPage, ...remainingPages.map((response) => response.data)]
      .flatMap((page) => page.textbooks)
      .forEach((textbook) => byId.set(textbook.id, textbook));

    return Array.from(byId.values()).sort((left, right) => {
      const createdDifference = Date.parse(right.created_at) - Date.parse(left.created_at);
      return createdDifference || left.name.localeCompare(right.name, 'zh-CN');
    });
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

  /** Search public book catalogs and publisher sites. */
  searchTextbooks: async (data: TextbookSearchRequest): Promise<TextbookSearchResponse> => {
    const response = await api.post('/textbook-searches', data, { timeout: 45000 });
    return response.data;
  },

  /** Resolve and optionally AI-enrich a selected edition's real catalog. */
  previewCatalog: async (
    data: TextbookCatalogRequest
  ): Promise<TextbookCatalogPreviewResponse> => {
    const response = await api.post('/textbook-catalog-previews', data, {
      timeout: 180000,
    });
    return response.data;
  },

  /** Persist a confirmed edition and its catalog atomically. */
  importTextbook: async (data: TextbookImportRequest): Promise<TextbookInfo> => {
    const response = await api.post('/textbook-imports', data);
    return response.data;
  },
};

export default textbookApi;
