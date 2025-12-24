/**
 * 自动保存 Hook
 *
 * 使用防抖技术自动保存编辑器内容，避免频繁的保存操作
 */
import { useEffect, useRef, useCallback } from 'react'
import { message } from 'antd'

interface UseAutoSaveOptions {
  /** 是否启用自动保存 */
  enabled?: boolean
  /** 防抖延迟时间（毫秒），默认 3000ms (3秒) */
  delay?: number
  /** 保存函数 */
  onSave: () => Promise<void>
  /** 内容是否有修改 */
  isDirty: boolean
  /** 内容（用于检测变化） */
  content: string
}

/**
 * 自动保存 Hook
 *
 * @example
 * useAutoSave({
 *   enabled: true,
 *   delay: 3000,
 *   onSave: async () => {
 *     await saveTemplate()
 *   },
 *   isDirty: isDirty,
 *   content: htmlContent,
 * })
 */
export const useAutoSave = ({
  enabled = true,
  delay = 3000,
  onSave,
  isDirty,
  content,
}: UseAutoSaveOptions) => {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)
  const lastSavedContentRef = useRef<string>(content)
  const isSavingRef = useRef<boolean>(false)

  // 清理定时器
  const clearTimer = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
  }, [])

  // 执行保存
  const executeSave = useCallback(async () => {
    if (isSavingRef.current) {
      return
    }

    try {
      isSavingRef.current = true
      await onSave()
      lastSavedContentRef.current = content
      message.success('已自动保存', 1)
    } catch (error: any) {
      console.error('自动保存失败:', error)
      message.error('自动保存失败: ' + error.message, 2)
    } finally {
      isSavingRef.current = false
    }
  }, [onSave, content])

  // 监听内容变化
  useEffect(() => {
    if (!enabled || !isDirty) {
      return
    }

    // 内容未变化，无需保存
    if (content === lastSavedContentRef.current) {
      return
    }

    // 清除之前的定时器
    clearTimer()

    // 设置新的定时器
    timeoutRef.current = setTimeout(() => {
      executeSave()
    }, delay)

    // 清理函数
    return () => {
      clearTimer()
    }
  }, [enabled, isDirty, content, delay, executeSave, clearTimer])

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      clearTimer()
    }
  }, [clearTimer])

  // 返回手动触发保存的函数
  return {
    /**
     * 手动触发保存（取消防抖，立即保存）
     */
    saveNow: useCallback(async () => {
      clearTimer()
      await executeSave()
    }, [clearTimer, executeSave]),

    /**
     * 取消待执行的自动保存
     */
    cancelAutoSave: clearTimer,
  }
}
