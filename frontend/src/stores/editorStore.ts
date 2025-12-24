/**
 * Editor store for managing document editing state
 */
import { create } from 'zustand';
import type {
  DocumentUploadResponse,
  ParsedSection,
  SectionEditRequest,
  EditHistoryItem,
} from '@/types';
import { editApi } from '@/services/api';

interface EditorState {
  // Current document being edited
  documentId: string | null;
  filename: string | null;
  parsedSections: Record<string, ParsedSection>;
  editHistory: EditHistoryItem[];

  // Loading states
  isUploading: boolean;
  isEditing: boolean;
  isSaving: boolean;

  // Error state
  error: string | null;

  // Actions
  uploadDocument: (file: File) => Promise<DocumentUploadResponse>;
  editSection: (request: SectionEditRequest) => Promise<void>;
  aiEnhanceSection: (sectionName: string, enhancementType: string, instruction?: string) => Promise<void>;
  addSection: (sectionName: string, aiGenerate: boolean, manualContent?: string) => Promise<void>;
  saveDocument: () => Promise<Blob>;
  undoEdit: () => Promise<void>;
  clearCurrentDocument: () => void;
  clearError: () => void;
}

export const useEditorStore = create<EditorState>((set, get) => ({
  documentId: null,
  filename: null,
  parsedSections: {},
  editHistory: [],
  isUploading: false,
  isEditing: false,
  isSaving: false,
  error: null,

  uploadDocument: async (file) => {
    set({ isUploading: true, error: null });
    try {
      const response = await editApi.uploadDocument(file);
      set({
        documentId: response.id,
        filename: response.filename,
        parsedSections: response.parsed_sections,
        editHistory: [],
        isUploading: false,
      });
      return response;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '上传文档失败',
        isUploading: false,
      });
      throw error;
    }
  },

  editSection: async (request) => {
    const documentId = get().documentId;
    if (!documentId) {
      set({ error: '请先上传文档' });
      return;
    }

    set({ isEditing: true, error: null });
    try {
      const result = await editApi.editSection(documentId, request);

      // Update parsed sections
      const parsedSections = { ...get().parsedSections };
      parsedSections[request.section_name] = {
        ...parsedSections[request.section_name],
        content: result.new_content,
        found: true,
      };

      // Add to edit history
      const editHistory = [
        ...get().editHistory,
        {
          section: request.section_name,
          operation: request.operation,
          timestamp: new Date().toISOString(),
        },
      ];

      set({
        parsedSections,
        editHistory,
        isEditing: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '编辑部分失败',
        isEditing: false,
      });
      throw error;
    }
  },

  aiEnhanceSection: async (sectionName, enhancementType, instruction) => {
    const documentId = get().documentId;
    if (!documentId) {
      set({ error: '请先上传文档' });
      return;
    }

    set({ isEditing: true, error: null });
    try {
      const result = await editApi.aiEnhanceSection(documentId, {
        section_name: sectionName,
        enhancement_type: enhancementType as any,
        specific_instruction: instruction,
      });

      // Update parsed sections
      const parsedSections = { ...get().parsedSections };
      parsedSections[sectionName] = {
        ...parsedSections[sectionName],
        content: result.enhanced_content,
        found: true,
      };

      // Add to edit history
      const editHistory = [
        ...get().editHistory,
        {
          section: sectionName,
          operation: `ai_enhance_${enhancementType}`,
          timestamp: new Date().toISOString(),
        },
      ];

      set({
        parsedSections,
        editHistory,
        isEditing: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'AI增强失败',
        isEditing: false,
      });
      throw error;
    }
  },

  addSection: async (sectionName, aiGenerate, manualContent) => {
    const documentId = get().documentId;
    if (!documentId) {
      set({ error: '请先上传文档' });
      return;
    }

    set({ isEditing: true, error: null });
    try {
      const result = await editApi.addSection(documentId, {
        section_name: sectionName,
        position: 'end',
        ai_generate: aiGenerate,
        manual_content: manualContent,
      });

      // Update parsed sections
      const parsedSections = { ...get().parsedSections };
      parsedSections[sectionName] = {
        name: sectionName,
        found: true,
        content: result.content,
      };

      // Add to edit history
      const editHistory = [
        ...get().editHistory,
        {
          section: sectionName,
          operation: 'add',
          timestamp: new Date().toISOString(),
        },
      ];

      set({
        parsedSections,
        editHistory,
        isEditing: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '添加部分失败',
        isEditing: false,
      });
      throw error;
    }
  },

  saveDocument: async () => {
    const documentId = get().documentId;
    if (!documentId) {
      set({ error: '请先上传文档' });
      throw new Error('请先上传文档');
    }

    set({ isSaving: true, error: null });
    try {
      const blob = await editApi.saveDocument(documentId);
      set({ isSaving: false });
      return blob;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '保存文档失败',
        isSaving: false,
      });
      throw error;
    }
  },

  undoEdit: async () => {
    const documentId = get().documentId;
    if (!documentId) {
      set({ error: '请先上传文档' });
      return;
    }

    set({ isEditing: true, error: null });
    try {
      await editApi.undoEdit(documentId);

      // Remove last edit from history
      const editHistory = [...get().editHistory];
      editHistory.pop();

      set({ editHistory, isEditing: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '撤销失败',
        isEditing: false,
      });
      throw error;
    }
  },

  clearCurrentDocument: () => {
    set({
      documentId: null,
      filename: null,
      parsedSections: {},
      editHistory: [],
      error: null,
    });
  },

  clearError: () => set({ error: null }),
}));
