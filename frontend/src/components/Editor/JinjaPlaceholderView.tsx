/**
 * Jinja2 占位符视图组件
 *
 * 渲染 Jinja2 语法为可视化的徽章
 */
import React from 'react'
import { NodeViewWrapper } from '@tiptap/react'
import { Tag } from 'antd'

interface JinjaPlaceholderViewProps {
  node: {
    attrs: {
      jinja: string
      type: 'variable' | 'block' | 'comment'
      blockType?: string
      id?: string
    }
  }
}

const JinjaPlaceholderView: React.FC<JinjaPlaceholderViewProps> = ({ node }) => {
  const { jinja, type, blockType } = node.attrs

  // 根据类型选择颜色
  const getColor = () => {
    if (type === 'variable') return 'blue'
    if (type === 'block') {
      if (blockType?.includes('for')) return 'purple'
      if (blockType?.includes('if')) return 'orange'
      return 'cyan'
    }
    if (type === 'comment') return 'default'
    return 'blue'
  }

  // 根据类型选择图标
  const getIcon = () => {
    if (type === 'variable') return '{{ }}'
    if (type === 'block') {
      if (blockType?.includes('for')) return '🔁'
      if (blockType?.includes('if')) return '❓'
      return '{% %}'
    }
    if (type === 'comment') return '💬'
    return ''
  }

  return (
    <NodeViewWrapper as="span" className="jinja-placeholder-wrapper">
      <Tag
        color={getColor()}
        style={{
          margin: '0 2px',
          cursor: 'pointer',
          userSelect: 'none',
          fontFamily: 'monospace',
          fontSize: '13px',
        }}
        title={`Jinja2 ${type}: 点击查看详情`}
      >
        <span style={{ marginRight: 4 }}>{getIcon()}</span>
        {jinja}
      </Tag>
    </NodeViewWrapper>
  )
}

export default JinjaPlaceholderView
