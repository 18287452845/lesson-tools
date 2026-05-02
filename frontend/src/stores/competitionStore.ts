/**
 * Competition module Zustand store
 *
 * Manages projects, generation outputs, progress tracking.
 */
import { create } from 'zustand';
import type {
  CompetitionProject,
  CompetitionProjectCreate,
  CompetitionProjectUpdate,
  CompetitionOutput,
  CompetitionLessonPlanGenerateRequest,
  CompetitionReportGenerateRequest,
} from '@/types';
import { competitionApi } from '@/services/competitionApi';

interface CompetitionState {
  // Projects
  projects: CompetitionProject[];
  currentProject: CompetitionProject | null;
  totalProjects: number;
  loadingProjects: boolean;

  // Outputs of the currently viewed project
  outputs: CompetitionOutput[];
  loadingOutputs: boolean;

  // Generation state (one project at a time)
  isGenerating: boolean;
  currentOutputId: string | null;
  currentOutput: CompetitionOutput | null;
  progress: { current: number; total: number };

  // Errors
  error: string | null;

  // Actions: projects
  fetchProjects: (page?: number, limit?: number) => Promise<void>;
  fetchProject: (projectId: string) => Promise<CompetitionProject>;
  createProject: (data: CompetitionProjectCreate) => Promise<CompetitionProject>;
  updateProject: (projectId: string, data: CompetitionProjectUpdate) => Promise<CompetitionProject>;
  deleteProject: (projectId: string) => Promise<void>;

  // Actions: outputs
  fetchProjectOutputs: (projectId: string) => Promise<void>;
  generateLessonPlan: (
    projectId: string,
    data: CompetitionLessonPlanGenerateRequest
  ) => Promise<string>;
  generateReport: (
    projectId: string,
    data: CompetitionReportGenerateRequest
  ) => Promise<string>;
  fetchOutput: (outputId: string) => Promise<CompetitionOutput>;
  pollOutputUntilDone: (outputId: string, intervalMs?: number) => Promise<CompetitionOutput>;
  subscribeOutputProgress: (outputId: string) => () => void;
  deleteOutput: (outputId: string) => Promise<void>;
  downloadOutput: (outputId: string) => Promise<void>;

  // Misc
  clearError: () => void;
  reset: () => void;
}

export const useCompetitionStore = create<CompetitionState>((set, get) => ({
  projects: [],
  currentProject: null,
  totalProjects: 0,
  loadingProjects: false,

  outputs: [],
  loadingOutputs: false,

  isGenerating: false,
  currentOutputId: null,
  currentOutput: null,
  progress: { current: 0, total: 0 },
  error: null,

  fetchProjects: async (page = 1, limit = 20) => {
    set({ loadingProjects: true, error: null });
    try {
      const response = await competitionApi.listProjects({ page, limit });
      set({
        projects: response.projects,
        totalProjects: response.total,
        loadingProjects: false,
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '加载项目列表失败',
        loadingProjects: false,
      });
      throw err;
    }
  },

  fetchProject: async (projectId) => {
    try {
      const project = await competitionApi.getProject(projectId);
      set({ currentProject: project });
      return project;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '加载项目失败' });
      throw err;
    }
  },

  createProject: async (data) => {
    try {
      const project = await competitionApi.createProject(data);
      set((state) => ({
        projects: [project, ...state.projects],
        totalProjects: state.totalProjects + 1,
        currentProject: project,
      }));
      return project;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '创建项目失败' });
      throw err;
    }
  },

  updateProject: async (projectId, data) => {
    try {
      const updated = await competitionApi.updateProject(projectId, data);
      set((state) => ({
        projects: state.projects.map((p) => (p.id === projectId ? updated : p)),
        currentProject: state.currentProject?.id === projectId ? updated : state.currentProject,
      }));
      return updated;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '更新项目失败' });
      throw err;
    }
  },

  deleteProject: async (projectId) => {
    try {
      await competitionApi.deleteProject(projectId);
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== projectId),
        totalProjects: Math.max(0, state.totalProjects - 1),
        currentProject:
          state.currentProject?.id === projectId ? null : state.currentProject,
      }));
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '删除项目失败' });
      throw err;
    }
  },

  fetchProjectOutputs: async (projectId) => {
    set({ loadingOutputs: true, error: null });
    try {
      const response = await competitionApi.listProjectOutputs(projectId);
      set({ outputs: response.outputs, loadingOutputs: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '加载输出列表失败',
        loadingOutputs: false,
      });
      throw err;
    }
  },

  generateLessonPlan: async (projectId, data) => {
    set({ isGenerating: true, error: null, progress: { current: 0, total: 0 } });
    try {
      const response = await competitionApi.generateLessonPlan(projectId, data);
      set({ currentOutputId: response.output_id });
      return response.output_id;
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '启动教案生成失败',
        isGenerating: false,
      });
      throw err;
    }
  },

  generateReport: async (projectId, data) => {
    set({ isGenerating: true, error: null, progress: { current: 0, total: 0 } });
    try {
      const response = await competitionApi.generateReport(projectId, data);
      set({ currentOutputId: response.output_id });
      return response.output_id;
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '启动报告生成失败',
        isGenerating: false,
      });
      throw err;
    }
  },

  fetchOutput: async (outputId) => {
    try {
      const output = await competitionApi.getOutput(outputId);
      set({
        currentOutput: output,
        progress: { current: output.progress_current, total: output.progress_total },
      });
      return output;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '加载生成输出失败' });
      throw err;
    }
  },

  pollOutputUntilDone: async (outputId, intervalMs = 3000) => {
    while (true) {
      const output = await get().fetchOutput(outputId);
      if (
        output.status === 'completed' ||
        output.status === 'failed' ||
        output.status === 'cancelled'
      ) {
        set({ isGenerating: false });
        return output;
      }
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
  },

  subscribeOutputProgress: (outputId) => {
    set({ currentOutputId: outputId, isGenerating: true });
    const cleanup = competitionApi.streamOutputProgress(outputId, {
      onProgress: (data) => {
        set({
          progress: {
            current: data.progress_current,
            total: data.progress_total,
          },
        });
      },
      onDone: async (data) => {
        // Re-fetch full output info to get file path & generated_data
        try {
          const finalOutput = await competitionApi.getOutput(outputId);
          set({
            currentOutput: finalOutput,
            isGenerating: false,
            progress: {
              current: finalOutput.progress_current,
              total: finalOutput.progress_total,
            },
            error: data.error_message || null,
          });
        } catch (err) {
          set({
            isGenerating: false,
            error: err instanceof Error ? err.message : '加载完成结果失败',
          });
        }
      },
      onError: (message) => {
        set({ error: message, isGenerating: false });
      },
    });
    return cleanup;
  },

  deleteOutput: async (outputId) => {
    try {
      await competitionApi.deleteOutput(outputId);
      set((state) => ({
        outputs: state.outputs.filter((o) => o.id !== outputId),
      }));
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '删除输出失败' });
      throw err;
    }
  },

  downloadOutput: async (outputId) => {
    try {
      await competitionApi.downloadOutput(outputId);
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '下载失败' });
      throw err;
    }
  },

  clearError: () => set({ error: null }),

  reset: () =>
    set({
      currentProject: null,
      outputs: [],
      isGenerating: false,
      currentOutputId: null,
      currentOutput: null,
      progress: { current: 0, total: 0 },
      error: null,
    }),
}));
