/**
 * Settings API service
 */
import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

export interface AIProviderConfig {
  provider: 'deepseek' | 'anthropic';
  api_key: string;
  model?: string;
}

export interface AIProviderResponse {
  provider: string;
  model: string;
  configured: boolean;
  has_api_key: boolean;
}

export interface AIProviderInfo {
  id: string;
  name: string;
  description: string;
  models: Array<{ id: string; name: string }>;
  default_model: string;
  website: string;
}

export interface AIProvidersResponse {
  providers: AIProviderInfo[];
}

export const settingsApi = {
  /**
   * Get current AI provider configuration
   */
  getAIProviderConfig: async (): Promise<AIProviderResponse> => {
    const response = await api.get('/settings/ai-provider');
    return response.data;
  },

  /**
   * Set AI provider configuration
   */
  setAIProviderConfig: async (config: AIProviderConfig): Promise<{
    message: string;
    provider: string;
    model: string;
  }> => {
    const response = await api.post('/settings/ai-provider', config);
    return response.data;
  },

  /**
   * List available AI providers
   */
  listAIProviders: async (): Promise<AIProvidersResponse> => {
    const response = await api.get('/settings/ai-providers');
    return response.data;
  },

  /**
   * Get app info
   */
  getAppInfo: async (): Promise<{
    name: string;
    version: string;
    default_provider: string;
    default_model: string;
  }> => {
    const response = await api.get('/settings/app-info');
    return response.data;
  },
};
