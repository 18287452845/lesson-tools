/**
 * 模板编辑器状态管理
 *
 * 管理模板编辑器的加载、编辑、保存状态
 */
import { create } from 'zustand'
import axios from 'axios'
import type { FieldConfig } from '@/types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

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

export interface TemplateEditorState {
  // 模板基本信息
  templateId: string | null
  templateName: string

  // 元数据
  metadata: TemplateMetadata | null

  // 字段配置
  fieldsConfig: FieldConfig[]
  standardFields: FieldConfig[]
  isFieldsDirty: boolean
  isFieldsSaving: boolean

  // 状态标识
  isLoading: boolean
  error: string | null

  // Actions
  loadTemplate: (templateId: string) => Promise<void>
  resetEditor: () => void

  // 字段管理 Actions
  loadFieldsConfig: () => Promise<void>
  loadStandardFields: () => Promise<void>
  addField: (field: FieldConfig) => void
  updateField: (name: string, updates: Partial<FieldConfig>) => void
  removeField: (name: string) => void
  saveFieldsConfig: () => Promise<void>
}

export const useTemplateEditorStore = create<TemplateEditorState>((set, get) => ({
  // 初始状态
  templateId: null,
  templateName: '',
  metadata: null,
  fieldsConfig: [],
  standardFields: [],
  isFieldsDirty: false,
  isFieldsSaving: false,
  isLoading: false,
  error: null,

  // 加载模板
  loadTemplate: async (templateId: string) => {
    set({ isLoading: true, error: null })

    try {
      const response = await axios.get(`${API_BASE}/templates/${templateId}`)
      const template = response.data

      set({
        templateId,
        templateName: template.name,
        metadata: {
          file_name: `${template.name}.docx`,
          title: template.name,
          subject: template.subject,
          created: template.created_at,
          modified: template.updated_at,
        },
        isLoading: false,
      })

      // 预先加载字段配置，确保字段配置面板能显示已有字段
      await Promise.all([get().loadFieldsConfig(), get().loadStandardFields()])
    } catch (error: any) {
      console.error('加载模板失败:', error)
      set({
        error: error.response?.data?.detail || '加载模板失败',
        isLoading: false,
      })
      throw error
    }
  },

  // 重置编辑器
  resetEditor: () => {
    set({
      templateId: null,
      templateName: '',
      metadata: null,
      fieldsConfig: [],
      standardFields: [],
      isFieldsDirty: false,
      isFieldsSaving: false,
      isLoading: false,
      error: null,
    })
  },

  // 加载字段配置
  loadFieldsConfig: async () => {
    const { templateId } = get()
    if (!templateId) return

    try {
      const response = await axios.get(`${API_BASE}/templates/${templateId}/fields`)
      set({
        fieldsConfig: response.data.fields || [],
        isFieldsDirty: false,
      })
    } catch (error: any) {
      console.error('加载字段配置失败:', error)
    }
  },

  // 加载标准字段
  loadStandardFields: async () => {
    try {
      const response = await axios.get(`${API_BASE}/templates/standard-fields`)
      set({ standardFields: response.data.fields || [] })
    } catch (error: any) {
      console.error('加载标准字段失败:', error)
    }
  },

  // 添加字段
  addField: (field: FieldConfig) => {
    const { fieldsConfig } = get()
    // 检查是否已存在
    if (fieldsConfig.some(f => f.name === field.name)) {
      return
    }
    set({
      fieldsConfig: [...fieldsConfig, field],
      isFieldsDirty: true,
    })
  },

  // 更新字段
  updateField: (name: string, updates: Partial<FieldConfig>) => {
    const { fieldsConfig } = get()
    set({
      fieldsConfig: fieldsConfig.map(f =>
        f.name === name ? { ...f, ...updates } : f
      ),
      isFieldsDirty: true,
    })
  },

  // 删除字段
  removeField: (name: string) => {
    const { fieldsConfig } = get()
    set({
      fieldsConfig: fieldsConfig.filter(f => f.name !== name),
      isFieldsDirty: true,
    })
  },

  // 保存字段配置
  saveFieldsConfig: async () => {
    const { templateId, fieldsConfig } = get()
    if (!templateId) {
      throw new Error('未加载模板')
    }

    set({ isFieldsSaving: true })

    try {
      await axios.put(
        `${API_BASE}/templates/${templateId}/fields`,
        { fields: fieldsConfig },
        { headers: { 'Content-Type': 'application/json' } }
      )
      set({
        isFieldsDirty: false,
        isFieldsSaving: false,
      })
    } catch (error: any) {
      console.error('保存字段配置失败:', error)
      set({ isFieldsSaving: false })
      throw error
    }
  },
}))
