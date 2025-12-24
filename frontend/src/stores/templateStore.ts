/**
 * Template store using Zustand
 */
import { create } from 'zustand';
import type { TemplateInfo } from '@/types';
import { templateApi } from '@/services/api';

interface TemplateState {
  templates: TemplateInfo[];
  selectedTemplate: TemplateInfo | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchTemplates: (params?: {
    subject?: string;
    grade?: string;
  }) => Promise<void>;
  selectTemplate: (template: TemplateInfo | null) => void;
  uploadTemplate: (file: File, metadata: {
    name: string;
    description?: string;
    subject?: string;
    grade?: string;
  }) => Promise<TemplateInfo>;
  deleteTemplate: (id: string) => Promise<void>;
  clearError: () => void;
}

export const useTemplateStore = create<TemplateState>((set, get) => ({
  templates: [],
  selectedTemplate: null,
  loading: false,
  error: null,

  fetchTemplates: async (params) => {
    set({ loading: true, error: null });
    try {
      const templates = await templateApi.listTemplates(params);
      set({ templates, loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '获取模板列表失败',
        loading: false,
      });
    }
  },

  selectTemplate: (template) => {
    set({ selectedTemplate: template });
  },

  uploadTemplate: async (file, metadata) => {
    set({ loading: true, error: null });
    try {
      const result = await templateApi.uploadTemplate(file, metadata);
      // Refresh templates
      await get().fetchTemplates();
      set({ loading: false });
      return result;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '上传模板失败',
        loading: false,
      });
      throw error;
    }
  },

  deleteTemplate: async (id) => {
    set({ loading: true, error: null });
    try {
      await templateApi.deleteTemplate(id);
      // Refresh templates
      await get().fetchTemplates();
      set({ loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '删除模板失败',
        loading: false,
      });
      throw error;
    }
  },

  clearError: () => set({ error: null }),
}));
