/**
 * Settings store using Zustand
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AIProviderResponse, AIProviderInfo } from '@/services/settingsApi';
import { settingsApi } from '@/services/settingsApi';

interface SettingsState {
  // Current AI provider configuration
  currentProvider: AIProviderResponse | null;
  availableProviders: AIProviderInfo[];
  loading: boolean;
  error: string | null;

  // User's saved API keys (local only, not sent to server)
  savedApiKeys: {
    deepseek?: string;
    anthropic?: string;
  };

  // Actions
  fetchCurrentConfig: () => Promise<void>;
  fetchProviders: () => Promise<void>;
  setProviderConfig: (provider: 'deepseek' | 'anthropic', apiKey: string, model?: string) => Promise<void>;
  saveApiKey: (provider: 'deepseek' | 'anthropic', apiKey: string) => void;
  clearError: () => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      currentProvider: null,
      availableProviders: [],
      loading: false,
      error: null,
      savedApiKeys: {},

      fetchCurrentConfig: async () => {
        set({ loading: true, error: null });
        try {
          const config = await settingsApi.getAIProviderConfig();
          set({ currentProvider: config, loading: false });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '获取配置失败',
            loading: false,
          });
        }
      },

      fetchProviders: async () => {
        try {
          const response = await settingsApi.listAIProviders();
          set({ availableProviders: response.providers });
        } catch (error) {
          console.error('Failed to fetch providers:', error);
        }
      },

      setProviderConfig: async (provider, apiKey, model) => {
        set({ loading: true, error: null });
        try {
          // Get default model for provider if not specified
          if (!model) {
            const { availableProviders } = get();
            const providerInfo = availableProviders.find((p) => p.id === provider);
            model = providerInfo?.default_model;
          }

          await settingsApi.setAIProviderConfig({
            provider,
            api_key: apiKey,
            model,
          });

          // Save API key locally
          get().saveApiKey(provider, apiKey);

          // Refresh config
          await get().fetchCurrentConfig();
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '设置配置失败',
            loading: false,
          });
          throw error;
        }
      },

      saveApiKey: (provider, apiKey) => {
        set((state) => ({
          savedApiKeys: {
            ...state.savedApiKeys,
            [provider]: apiKey,
          },
        }));
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'lesson-plan-settings',
      partialize: (state) => ({
        savedApiKeys: state.savedApiKeys,
      }),
    }
  )
);
