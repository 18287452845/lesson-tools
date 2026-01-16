/**
 * Textbook store using Zustand
 */
import { create } from 'zustand';
import type {
  TextbookInfo,
  TextbookCreateRequest,
  TextbookUpdateRequest,
  TextbookChapterInfo,
  TextbookChapterCreateRequest,
  TextbookChapterBatchCreateRequest,
  TextbookChapterGenerateRequest,
  TextbookChapterGenerateResponse,
} from '@/types';
import { textbookApi } from '@/services/textbookApi';

interface TextbookState {
  // State
  textbooks: TextbookInfo[];
  selectedTextbook: TextbookInfo | null;
  generatedChapters: TextbookChapterCreateRequest[];
  loading: boolean;
  error: string | null;
  total: number;
  currentPage: number;
  pageSize: number;

  // Actions
  fetchTextbooks: (params?: {
    page?: number;
    limit?: number;
    subject?: string;
    grade?: string;
    status?: 'active' | 'inactive';
  }) => Promise<void>;

  getTextbook: (id: string) => Promise<void>;

  selectTextbook: (textbook: TextbookInfo | null) => void;

  createTextbook: (data: TextbookCreateRequest) => Promise<TextbookInfo>;

  updateTextbook: (id: string, data: TextbookUpdateRequest) => Promise<void>;

  deleteTextbook: (id: string) => Promise<void>;

  // Chapter actions
  generateChapters: (
    textbookId: string,
    data: TextbookChapterGenerateRequest
  ) => Promise<TextbookChapterGenerateResponse>;

  setGeneratedChapters: (chapters: TextbookChapterCreateRequest[]) => void;

  saveChapters: (
    textbookId: string,
    chapters: TextbookChapterCreateRequest[]
  ) => Promise<void>;

  updateChapter: (
    textbookId: string,
    chapterId: string,
    data: TextbookChapterCreateRequest
  ) => Promise<void>;

  deleteChapter: (textbookId: string, chapterId: string) => Promise<void>;

  // Utility actions
  clearError: () => void;
  clearGeneratedChapters: () => void;
  setPage: (page: number) => void;
}

export const useTextbookStore = create<TextbookState>((set, get) => ({
  // Initial state
  textbooks: [],
  selectedTextbook: null,
  generatedChapters: [],
  loading: false,
  error: null,
  total: 0,
  currentPage: 1,
  pageSize: 20,

  // Fetch textbooks list
  fetchTextbooks: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await textbookApi.listTextbooks({
        page: params?.page || get().currentPage,
        limit: params?.limit || get().pageSize,
        subject: params?.subject,
        grade: params?.grade,
        status: params?.status,
      });
      set({
        textbooks: response.textbooks,
        total: response.total,
        currentPage: params?.page || get().currentPage,
        loading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '获取教材列表失败',
        loading: false,
      });
      throw error;
    }
  },

  // Get single textbook with chapters
  getTextbook: async (id) => {
    set({ loading: true, error: null });
    try {
      const textbook = await textbookApi.getTextbook(id);
      set({ selectedTextbook: textbook, loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '获取教材详情失败',
        loading: false,
      });
      throw error;
    }
  },

  // Select textbook
  selectTextbook: (textbook) => {
    set({ selectedTextbook: textbook });
  },

  // Create new textbook
  createTextbook: async (data) => {
    set({ loading: true, error: null });
    try {
      const textbook = await textbookApi.createTextbook(data);
      // Refresh textbooks list
      await get().fetchTextbooks();
      set({ loading: false });
      return textbook;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '创建教材失败',
        loading: false,
      });
      throw error;
    }
  },

  // Update textbook
  updateTextbook: async (id, data) => {
    set({ loading: true, error: null });
    try {
      await textbookApi.updateTextbook(id, data);
      // Refresh textbooks list
      await get().fetchTextbooks();
      // If this is the selected textbook, refresh it
      if (get().selectedTextbook?.id === id) {
        await get().getTextbook(id);
      }
      set({ loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '更新教材失败',
        loading: false,
      });
      throw error;
    }
  },

  // Delete textbook
  deleteTextbook: async (id) => {
    set({ loading: true, error: null });
    try {
      await textbookApi.deleteTextbook(id);
      // Clear selected textbook if it was deleted
      if (get().selectedTextbook?.id === id) {
        set({ selectedTextbook: null });
      }
      // Refresh textbooks list
      await get().fetchTextbooks();
      set({ loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '删除教材失败',
        loading: false,
      });
      throw error;
    }
  },

  // Generate chapters using AI
  generateChapters: async (textbookId, data) => {
    set({ loading: true, error: null });
    try {
      const response = await textbookApi.generateChapters(textbookId, data);
      set({
        generatedChapters: response.chapters,
        loading: false,
      });
      return response;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'AI章节生成失败',
        loading: false,
      });
      throw error;
    }
  },

  // Set generated chapters (for manual editing before save)
  setGeneratedChapters: (chapters) => {
    set({ generatedChapters: chapters });
  },

  // Save chapters to textbook
  saveChapters: async (textbookId, chapters) => {
    set({ loading: true, error: null });
    try {
      await textbookApi.saveChapters(textbookId, { chapters });
      // Refresh the textbook to get updated chapters
      await get().getTextbook(textbookId);
      // Clear generated chapters
      set({ generatedChapters: [], loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '保存章节失败',
        loading: false,
      });
      throw error;
    }
  },

  // Update single chapter
  updateChapter: async (textbookId, chapterId, data) => {
    set({ loading: true, error: null });
    try {
      await textbookApi.updateChapter(textbookId, chapterId, data);
      // Refresh the textbook to get updated chapters
      await get().getTextbook(textbookId);
      set({ loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '更新章节失败',
        loading: false,
      });
      throw error;
    }
  },

  // Delete chapter
  deleteChapter: async (textbookId, chapterId) => {
    set({ loading: true, error: null });
    try {
      await textbookApi.deleteChapter(textbookId, chapterId);
      // Refresh the textbook to get updated chapters
      await get().getTextbook(textbookId);
      set({ loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '删除章节失败',
        loading: false,
      });
      throw error;
    }
  },

  // Clear error
  clearError: () => set({ error: null }),

  // Clear generated chapters
  clearGeneratedChapters: () => set({ generatedChapters: [] }),

  // Set page
  setPage: (page) => {
    set({ currentPage: page });
  },
}));
