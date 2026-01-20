import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Alert, Spin } from 'antd'
import { templateEditorApi } from '@/services/api'
import type { OnlyOfficeEditorConfig } from '@/types'

declare global {
  interface Window {
    DocsAPI?: any
  }
}

interface OnlyOfficeEditorProps {
  templateId: string
  onRefresh?: () => void
}

const loadScript = (src: string) => {
  const existing = document.querySelector<HTMLScriptElement>(`script[src="${src}"]`)
  if (existing) {
    return Promise.resolve()
  }
  return new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('OnlyOffice 脚本加载失败'))
    document.body.appendChild(script)
  })
}

const OnlyOfficeEditor: React.FC<OnlyOfficeEditorProps> = ({ templateId, onRefresh }) => {
  const containerId = useMemo(() => `onlyoffice-editor-${templateId}`, [templateId])
  const editorRef = useRef<any>(null)
  const [config, setConfig] = useState<OnlyOfficeEditorConfig | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scriptReady, setScriptReady] = useState(false)

  useEffect(() => {
    let cancelled = false
    const init = async () => {
      setLoading(true)
      setError(null)
      setScriptReady(false)
      try {
        const cfg = await templateEditorApi.getOnlyOfficeConfig(templateId)
        if (cancelled) return
        setConfig(cfg)
        await loadScript(cfg.apiJsUrl)
        if (cancelled) return
        setScriptReady(true)
      } catch (err: any) {
        if (cancelled) return
        setError(err.message || '加载 OnlyOffice 编辑器失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    init()
    return () => {
      cancelled = true
      if (editorRef.current?.destroyEditor) {
        editorRef.current.destroyEditor()
      }
    }
  }, [templateId])

  useEffect(() => {
    if (!scriptReady || !config) return
    if (!window.DocsAPI) {
      setError('OnlyOffice 客户端脚本未就绪')
      return
    }

    const editorConfig: Record<string, any> = {
      ...config.config,
      width: '100%',
      height: '100%',
    }

    if (config.token) {
      editorConfig.token = config.token
    }

    editorRef.current = new window.DocsAPI.DocEditor(containerId, editorConfig)

    // Refresh local state after save completes inside OnlyOffice
    if (onRefresh && editorRef.current?.events) {
      editorRef.current.events.on('onDocumentStateChange', (state: any) => {
        // State becomes false when all changes are saved
        const saved = state === false || state?.data === false
        if (saved) {
          onRefresh()
        }
      })
    }

    return () => {
      if (editorRef.current?.destroyEditor) {
        editorRef.current.destroyEditor()
      }
    }
  }, [scriptReady, config, containerId, onRefresh])

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin tip="加载 OnlyOffice 编辑器..." />
      </div>
    )
  }

  if (error) {
    return (
      <Alert
        type="error"
        message="OnlyOffice 编辑器加载失败"
        description={error}
        showIcon
      />
    )
  }

  return (
    <div
      id={containerId}
      style={{
        border: '1px solid #e5e5e5',
        borderRadius: 8,
        overflow: 'hidden',
        minHeight: '70vh',
        background: '#fafafa',
      }}
    />
  )
}

export default OnlyOfficeEditor
