/**
 * Generator store using Zustand
 */
import { create } from 'zustand';
import type { LessonPlanInput, LessonPlanResponse, GeneratedContent } from '@/types';
import { generateApi } from '@/services/api';

interface GeneratorState {
  // Current lesson plan being generated
  currentLessonPlan: LessonPlanResponse | null;
  generatedContent: GeneratedContent | null;

  // Loading states
  isGenerating: boolean;
  isRegenerating: boolean;
  regeneratingField: string | null;

  // Error state
  error: string | null;

  // Actions
  generateLessonPlan: (input: LessonPlanInput) => Promise<void>;
  regenerateField: (fieldName: string, additionalInstruction?: string) => Promise<void>;
  updateField: (fieldName: string, content: any) => Promise<void>;
  exportLessonPlan: () => Promise<Blob>;
  clearCurrentLessonPlan: () => void;
  clearError: () => void;
}

export const useGeneratorStore = create<GeneratorState>((set, get) => ({
  currentLessonPlan: null,
  generatedContent: null,
  isGenerating: false,
  isRegenerating: false,
  regeneratingField: null,
  error: null,

  generateLessonPlan: async (input) => {
    set({ isGenerating: true, error: null });
    try {
      const response = await generateApi.generateLessonPlan(input);
      set({
        currentLessonPlan: response,
        generatedContent: response.content,
        isGenerating: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '生成教案失败',
        isGenerating: false,
      });
      throw error;
    }
  },

  regenerateField: async (fieldName, additionalInstruction) => {
    if (!get().currentLessonPlan) {
      set({ error: '请先生成教案' });
      return;
    }

    set({
      isRegenerating: true,
      regeneratingField: fieldName,
      error: null,
    });

    try {
      const lessonPlanId = get().currentLessonPlan!.id;
      const result = await generateApi.regenerateField(
        lessonPlanId,
        fieldName,
        additionalInstruction
      );

      // Update the generated content
      const currentContent = get().generatedContent!;
      const updatedContent = {
        ...currentContent,
        [fieldName]: result.new_content,
      };

      set({
        generatedContent: updatedContent,
        isRegenerating: false,
        regeneratingField: null,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '重新生成字段失败',
        isRegenerating: false,
        regeneratingField: null,
      });
      throw error;
    }
  },

  updateField: async (fieldName, content) => {
    if (!get().currentLessonPlan) {
      set({ error: '请先生成教案' });
      return;
    }

    try {
      const lessonPlanId = get().currentLessonPlan!.id;
      await generateApi.updateField(lessonPlanId, fieldName, JSON.stringify(content));

      // Update local state
      const currentContent = get().generatedContent!;
      const updatedContent = {
        ...currentContent,
        [fieldName]: content,
      };

      set({ generatedContent: updatedContent });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '更新字段失败',
      });
      throw error;
    }
  },

  exportLessonPlan: async () => {
    if (!get().currentLessonPlan) {
      set({ error: '请先生成教案' });
      throw new Error('请先生成教案');
    }

    const lessonPlanId = get().currentLessonPlan!.id;
    return await generateApi.exportLessonPlan(lessonPlanId);
  },

  clearCurrentLessonPlan: () => {
    set({
      currentLessonPlan: null,
      generatedContent: null,
      error: null,
    });
  },

  clearError: () => set({ error: null }),
}));
