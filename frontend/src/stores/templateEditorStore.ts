/**
 * 模板编辑器状态管理
 *
 * 管理模板编辑器的加载、编辑、保存状态
 */
import { create } from 'zustand'
import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000/api'

export interface TemplateMetadata {
  title?: string
  subject?: string
  author?: string
  created?: string
  modified?: string
  file_size?: number
  file_name?: string
  paragraphs_count?: number
  tables_count?: number
}

export interface JinjaVariable {
  name: string
  type: 'variable' | 'loop' | 'condition'
}

export interface TemplateEditorState {
  // 模板基本信息
  templateId: string | null
  templateName: string

  // 编辑内容
  htmlContent: string
  originalHtml: string  // 用于检测是否有修改

  // 元数据
  metadata: TemplateMetadata | null
  messages: string[]  // 转换消息/警告

  // Jinja2 变量
  variables: JinjaVariable[]

  // 状态标识
  isLoading: boolean
  isSaving: boolean
  isDirty: boolean  // 是否有未保存的修改
  error: string | null

  // 预览相关
  previewHtml: string | null
  isPreviewLoading: boolean

  // Actions
  loadTemplate: (templateId: string) => Promise<void>
  updateHtml: (html: string) => void
  saveTemplate: () => Promise<void>
  validateJinja: () => Promise<{ valid: boolean; errors: string[] }>
  generatePreview: (sampleData: Record<string, any>) => Promise<void>
  resetEditor: () => void
}

export const useTemplateEditorStore = create<TemplateEditorState>((set, get) => ({
  // 初始状态
  templateId: null,
  templateName: '',
  htmlContent: '',
  originalHtml: '',
  metadata: null,
  messages: [],
  variables: [],
  isLoading: false,
  isSaving: false,
  isDirty: false,
  error: null,
  previewHtml: null,
  isPreviewLoading: false,

  // 加载模板
  loadTemplate: async (templateId: string) => {
    set({ isLoading: true, error: null })

    try {
      const response = await axios.get(`${API_BASE}/templates/${templateId}/html`)
      const { html, metadata, messages, name } = response.data

      // 提取 Jinja2 变量
      const variablesResponse = await axios.post(
        `${API_BASE}/templates/${templateId}/validate-jinja`,
        { html },
        { headers: { 'Content-Type': 'application/json' } }
      )

      const { variables: varNames } = variablesResponse.data
      const variables: JinjaVariable[] = varNames.map((name: string) => ({
        name,
        type: 'variable' as const,
      }))

      set({
        templateId,
        templateName: name,
        htmlContent: html,
        originalHtml: html,
        metadata,
        messages: messages || [],
        variables,
        isDirty: false,
        isLoading: false,
      })
    } catch (error: any) {
      console.error('加载模板失败:', error)
      set({
        error: error.response?.data?.detail || '加载模板失败',
        isLoading: false,
      })
      throw error
    }
  },

  // 更新 HTML 内容
  updateHtml: (html: string) => {
    const { originalHtml } = get()
    set({
      htmlContent: html,
      isDirty: html !== originalHtml,
    })
  },

  // 保存模板
  saveTemplate: async () => {
    const { templateId, htmlContent, metadata } = get()

    if (!templateId) {
      throw new Error('未加载模板')
    }

    set({ isSaving: true, error: null })

    try {
      // 先验证 Jinja2 语法
      const validation = await get().validateJinja()
      if (!validation.valid) {
        throw new Error(`Jinja2 语法错误: ${validation.errors.join('; ')}`)
      }

      // 保存
      const response = await axios.post(
        `${API_BASE}/templates/${templateId}/save-html`,
        {
          html: htmlContent,
          metadata,
        },
        {
          headers: { 'Content-Type': 'application/json' },
        }
      )

      set({
        originalHtml: htmlContent,
        isDirty: false,
        isSaving: false,
      })

      return response.data
    } catch (error: any) {
      console.error('保存模板失败:', error)
      set({
        error: error.response?.data?.detail || error.message || '保存模板失败',
        isSaving: false,
      })
      throw error
    }
  },

  // 验证 Jinja2 语法
  validateJinja: async () => {
    const { templateId, htmlContent } = get()

    if (!templateId) {
      return { valid: false, errors: ['未加载模板'] }
    }

    try {
      const response = await axios.post(
        `${API_BASE}/templates/${templateId}/validate-jinja`,
        { html: htmlContent },
        { headers: { 'Content-Type': 'application/json' } }
      )

      const { valid, errors, variables: varNames } = response.data

      // 更新变量列表
      if (valid) {
        const variables: JinjaVariable[] = varNames.map((name: string) => ({
          name,
          type: 'variable' as const,
        }))
        set({ variables })
      }

      return { valid, errors: errors || [] }
    } catch (error: any) {
      console.error('验证 Jinja2 失败:', error)
      return {
        valid: false,
        errors: [error.response?.data?.detail || '验证失败'],
      }
    }
  },

  // 生成预览
  generatePreview: async (sampleData: Record<string, any>) => {
    const { templateId, htmlContent } = get()

    if (!templateId) {
      throw new Error('未加载模板')
    }

    set({ isPreviewLoading: true, error: null })

    try {
      const response = await axios.post(
        `${API_BASE}/templates/${templateId}/preview-html`,
        {
          html: htmlContent,
          sample_data: sampleData,
        },
        {
          headers: { 'Content-Type': 'application/json' },
        }
      )

      set({
        previewHtml: response.data.preview_html,
        isPreviewLoading: false,
      })
    } catch (error: any) {
      console.error('生成预览失败:', error)
      set({
        error: error.response?.data?.detail || '生成预览失败',
        isPreviewLoading: false,
      })
      throw error
    }
  },

  // 重置编辑器
  resetEditor: () => {
    set({
      templateId: null,
      templateName: '',
      htmlContent: '',
      originalHtml: '',
      metadata: null,
      messages: [],
      variables: [],
      isLoading: false,
      isSaving: false,
      isDirty: false,
      error: null,
      previewHtml: null,
      isPreviewLoading: false,
    })
  },
}))
