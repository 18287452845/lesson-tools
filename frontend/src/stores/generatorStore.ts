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

  // Real-time progress
  generationProgress: number;
  generationMessage: string;

  // Error state
  error: string | null;

  // Actions
  generateLessonPlan: (input: LessonPlanInput) => Promise<void>;
  generateLessonPlanStream: (input: LessonPlanInput) => Promise<void>;
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
  generationProgress: 0,
  generationMessage: '',
  error: null,

  generateLessonPlanStream: async (input) => {
    set({
      isGenerating: true,
      error: null,
      generationProgress: 0,
      generationMessage: '准备生成教案...'
    });

    try {
      const response = await fetch('http://localhost:8000/api/generate/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(input),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('无法读取响应流');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'status') {
                set({
                  generationProgress: data.progress || 0,
                  generationMessage: data.message,
                });
              } else if (data.type === 'complete') {
                set({
                  currentLessonPlan: {
                    id: data.data.id,
                    template_id: data.data.template_id,
                    input,
                    content: data.data.content,
                    status: data.data.status,
                    created_at: data.data.created_at,
                  },
                  generatedContent: data.data.content,
                  isGenerating: false,
                  generationProgress: 100,
                  generationMessage: data.message,
                });
                return;
              } else if (data.type === 'error') {
                set({
                  error: data.message,
                  isGenerating: false,
                });
                return;
              }
            } catch (err) {
              console.error('Error parsing SSE data:', err);
            }
          }
        }
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '生成教案失败',
        isGenerating: false,
      });
      throw error;
    }
  },

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
