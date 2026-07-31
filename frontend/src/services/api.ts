/**
 * API service for communicating with the backend
 */
import axios from 'axios';
import type {
  TemplateInfo,
  LessonPlanInput,
  LessonPlanResponse,
  DocumentUploadResponse,
  SectionEditRequest,
  AIEnhanceRequest,
  ClassInfo,
  ClassCreateRequest,
  ClassUpdateRequest,
  ClassListResponse,
  SubjectInfo,
  SubjectWithUsageStats,
  SubjectCreateRequest,
  SubjectUpdateRequest,
  SubjectListResponse,
  GradeInfo,
  GradeWithUsageStats,
  GradeCreateRequest,
  GradeUpdateRequest,
  GradeListResponse,
  TemplateValidation,
  FixedTemplateValidation,
  PreparationGenerateRequest,
  PreparationResponse,
} from '@/types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
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
   * Download a template file
   */
  downloadTemplate: async (id: string): Promise<Blob> => {
    const response = await api.get(`/templates/${id}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  validateTemplate: async (): Promise<TemplateValidation> => {
    const response = await api.get('/templates/validation');
    return response.data;
  },

  validateAllTemplates: async (): Promise<FixedTemplateValidation[]> => {
    const response = await api.get('/templates/validation/all');
    return response.data;
  },
};

export const preparationApi = {
  generate: async (input: PreparationGenerateRequest): Promise<PreparationResponse> => {
    const response = await api.post('/preparation', input);
    return response.data;
  },

  capabilities: async (): Promise<{
    template: { id: string; name: string; is_valid: boolean; sha256: string };
    artifacts: { type: string; label: string }[];
  }> => {
    const response = await api.get('/preparation/capabilities');
    return response.data;
  },

  resolveDownloadUrl: (downloadUrl: string): string => {
    const configuredBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
    const backendOrigin = new URL(configuredBase, window.location.origin).origin;
    return new URL(downloadUrl, backendOrigin).toString();
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
    const response = await api.post(`/generate/${lessonPlanId}/regenerate-field`, null, {
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
    await api.put(`/generate/${lessonPlanId}/content`, {
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

// ============================================================================
// Class Management API
// ============================================================================

export const classApi = {
  /**
   * List all classes
   */
  listClasses: async (params?: {
    page?: number;
    limit?: number;
  }): Promise<ClassListResponse> => {
    const response = await api.get('/classes', { params });
    return response.data;
  },

  /**
   * Create a new class
   */
  createClass: async (data: ClassCreateRequest): Promise<ClassInfo> => {
    const response = await api.post('/classes', data);
    return response.data;
  },

  /**
   * Get a specific class
   */
  getClass: async (id: string): Promise<ClassInfo> => {
    const response = await api.get(`/classes/${id}`);
    return response.data;
  },

  /**
   * Update a class
   */
  updateClass: async (id: string, data: ClassUpdateRequest): Promise<ClassInfo> => {
    const response = await api.put(`/classes/${id}`, data);
    return response.data;
  },

  /**
   * Delete a class
   */
  deleteClass: async (id: string): Promise<void> => {
    await api.delete(`/classes/${id}`);
  },
};

// ============================================================================
// Subject Management API
// ============================================================================

export const subjectApi = {
  /**
   * List all subjects (with optional category filter)
   */
  listSubjects: async (params?: {
    category?: string;
    page?: number;
    limit?: number;
  }): Promise<SubjectListResponse> => {
    const response = await api.get('/subjects', { params });
    return response.data;
  },

  /**
   * Create a new subject
   */
  createSubject: async (data: SubjectCreateRequest): Promise<SubjectInfo> => {
    const response = await api.post('/subjects', data);
    return response.data;
  },

  /**
   * Get a specific subject with usage statistics
   */
  getSubject: async (id: string): Promise<SubjectWithUsageStats> => {
    const response = await api.get(`/subjects/${id}`);
    return response.data;
  },

  /**
   * Update a subject
   */
  updateSubject: async (id: string, data: SubjectUpdateRequest): Promise<SubjectInfo> => {
    const response = await api.put(`/subjects/${id}`, data);
    return response.data;
  },

  /**
   * Delete a subject
   */
  deleteSubject: async (id: string): Promise<void> => {
    await api.delete(`/subjects/${id}`);
  },
};

// ============================================================================
// Grade Management API
// ============================================================================

export const gradeApi = {
  /**
   * List all grades (with optional category filter)
   */
  listGrades: async (params?: {
    category?: string;
    page?: number;
    limit?: number;
  }): Promise<GradeListResponse> => {
    const response = await api.get('/grades', { params });
    return response.data;
  },

  /**
   * Create a new grade
   */
  createGrade: async (data: GradeCreateRequest): Promise<GradeInfo> => {
    const response = await api.post('/grades', data);
    return response.data;
  },

  /**
   * Get a specific grade with usage statistics
   */
  getGrade: async (id: string): Promise<GradeWithUsageStats> => {
    const response = await api.get(`/grades/${id}`);
    return response.data;
  },

  /**
   * Update a grade
   */
  updateGrade: async (id: string, data: GradeUpdateRequest): Promise<GradeInfo> => {
    const response = await api.put(`/grades/${id}`, data);
    return response.data;
  },

  /**
   * Delete a grade
   */
  deleteGrade: async (id: string): Promise<void> => {
    await api.delete(`/grades/${id}`);
  },
};

export default api;
