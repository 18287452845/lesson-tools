/**
 * API service for communicating with the backend
 */
import axios from 'axios';
import type {
  TemplateInfo,
  LessonPlanInput,
  LessonPlanResponse,
  GeneratedContent,
  DocumentUploadResponse,
  ParsedSection,
  SectionEditRequest,
  AIEnhanceRequest,
} from '@/types';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 120000, // 120 seconds for AI generation
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败';
    return Promise.reject(new Error(message));
  }
);

// ============================================================================
// Template API
// ============================================================================

export const templateApi = {
  /**
   * Upload a new template
   */
  uploadTemplate: async (file: File, metadata: {
    name: string;
    description?: string;
    subject?: string;
    grade?: string;
  }) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', metadata.name);
    if (metadata.description) formData.append('description', metadata.description);
    if (metadata.subject) formData.append('subject', metadata.subject);
    if (metadata.grade) formData.append('grade', metadata.grade);

    const response = await api.post('/templates/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  /**
   * List all templates
   */
  listTemplates: async (params?: {
    subject?: string;
    grade?: string;
    limit?: number;
    offset?: number;
  }): Promise<TemplateInfo[]> => {
    const response = await api.get('/templates', { params });
    return response.data;
  },

  /**
   * Get a specific template
   */
  getTemplate: async (id: string): Promise<TemplateInfo> => {
    const response = await api.get(`/templates/${id}`);
    return response.data;
  },

  /**
   * Delete a template
   */
  deleteTemplate: async (id: string): Promise<void> => {
    await api.delete(`/templates/${id}`);
  },

  /**
   * Download a template file
   */
  downloadTemplate: async (id: string): Promise<Blob> => {
    const response = await api.get(`/templates/${id}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

// ============================================================================
// Lesson Plan Generation API
// ============================================================================

export const generateApi = {
  /**
   * Generate a complete lesson plan
   */
  generateLessonPlan: async (input: LessonPlanInput): Promise<LessonPlanResponse> => {
    const response = await api.post('/generate', input);
    return response.data;
  },

  /**
   * Regenerate a single field
   */
  regenerateField: async (
    lessonPlanId: string,
    fieldName: string,
    additionalInstruction?: string
  ): Promise<{ field_name: string; new_content: any }> => {
    const response = await api.post(`/${lessonPlanId}/regenerate-field`, null, {
      params: {
        field_name: fieldName,
        additional_instruction: additionalInstruction,
      },
    });
    return response.data;
  },

  /**
   * Update a field manually
   */
  updateField: async (
    lessonPlanId: string,
    fieldName: string,
    content: string
  ): Promise<void> => {
    await api.put(`/${lessonPlanId}/content`, {
      field_name: fieldName,
      content,
    });
  },

  /**
   * Export lesson plan as Word document
   */
  exportLessonPlan: async (lessonPlanId: string): Promise<Blob> => {
    const response = await api.post(`/generate/${lessonPlanId}/export`, null, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Get a lesson plan
   */
  getLessonPlan: async (id: string): Promise<any> => {
    const response = await api.get(`/generate/${id}`);
    return response.data;
  },

  /**
   * List all lesson plans
   */
  listLessonPlans: async (params?: {
    limit?: number;
    offset?: number;
    subject?: string;
    grade?: string;
    status?: string;
  }): Promise<any[]> => {
    const response = await api.get('/generate', { params });
    return response.data;
  },

  /**
   * Delete a lesson plan
   */
  deleteLessonPlan: async (id: string): Promise<void> => {
    await api.delete(`/generate/${id}`);
  },
};

// ============================================================================
// Document Editing API
// ============================================================================

export const editApi = {
  /**
   * Upload an existing document for editing
   */
  uploadDocument: async (file: File): Promise<DocumentUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/edit/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  /**
   * Get document details
   */
  getDocument: async (documentId: string): Promise<any> => {
    const response = await api.get(`/edit/${documentId}`);
    return response.data;
  },

  /**
   * Edit a section
   */
  editSection: async (
    documentId: string,
    request: SectionEditRequest
  ): Promise<{ section_name: string; new_content: string }> => {
    const response = await api.post(`/edit/${documentId}/section`, request);
    return response.data;
  },

  /**
   * AI enhance a section
   */
  aiEnhanceSection: async (
    documentId: string,
    request: AIEnhanceRequest
  ): Promise<{ section_name: string; enhanced_content: string }> => {
    const response = await api.post(`/edit/${documentId}/ai-enhance`, request);
    return response.data;
  },

  /**
   * Add a missing section
   */
  addSection: async (
    documentId: string,
    request: {
      section_name: string;
      position: 'auto' | 'end';
      after_section?: string;
      ai_generate: boolean;
      manual_content?: string;
    }
  ): Promise<{ success: boolean; section_name: string; content: string }> => {
    const response = await api.post(`/edit/${documentId}/add-section`, request);
    return response.data;
  },

  /**
   * Save/download the edited document
   */
  saveDocument: async (documentId: string): Promise<Blob> => {
    const response = await api.post(`/edit/${documentId}/save`, null, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Undo the last edit
   */
  undoEdit: async (documentId: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post(`/edit/${documentId}/undo`);
    return response.data;
  },

  /**
   * Get edit history
   */
  getEditHistory: async (documentId: string): Promise<{ document_id: string; edits: any[] }> => {
    const response = await api.get(`/edit/${documentId}/history`);
    return response.data;
  },
};

export default api;
