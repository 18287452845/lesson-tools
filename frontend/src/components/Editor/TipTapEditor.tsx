/**
 * TipTap 富文本编辑器组件
 *
 * 配置了表格、颜色、字体等扩展，以及 Jinja2 占位符支持
 */
import React, { useEffect } from 'react'
import { useEditor, EditorContent, Editor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
import Color from '@tiptap/extension-color'
import TextStyle from '@tiptap/extension-text-style'
import FontFamily from '@tiptap/extension-font-family'
import TextAlign from '@tiptap/extension-text-align'
import Highlight from '@tiptap/extension-highlight'
import Underline from '@tiptap/extension-underline'
import { JinjaPlaceholder } from './JinjaPlaceholderExtension'
import { FontSize } from './FontSizeExtension'
import EditorToolbar from './EditorToolbar'
import TableToolbar from './TableToolbar'
import { Card, Button, Space, Tooltip } from 'antd'
import {
  UndoOutlined,
  RedoOutlined,
  PlusOutlined,
} from '@ant-design/icons'

import './TipTapEditor.css'

interface TipTapEditorProps {
  content: string
  onChange: (html: string) => void
  editable?: boolean
  onInsertJinjaClick?: () => void
  onEditorReady?: (editor: Editor) => void
}

const TipTapEditor: React.FC<TipTapEditorProps> = ({
  content,
  onChange,
  editable = true,
  onInsertJinjaClick,
  onEditorReady,
}) => {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // 禁用默认的表格支持，使用自定义的
        table: false,
      }),
      Table.configure({
        resizable: true,
        HTMLAttributes: {
          class: 'tiptap-table',
        },
      }),
      TableRow,
      TableCell,
      TableHeader,
      TextAlign.configure({
        types: ['heading', 'paragraph'],
      }),
      Highlight.configure({
        multicolor: true,
      }),
      Underline,
      Color,
      TextStyle,
      FontFamily,
      FontSize,
      JinjaPlaceholder,
    ],
    content,
    editable,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    },
  })

  // 当外部内容变化时更新编辑器
  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content, false)
    }
  }, [content, editor])

  // 通知父组件 editor 已准备好
  useEffect(() => {
    if (editor && onEditorReady) {
      onEditorReady(editor)
    }
  }, [editor, onEditorReady])

  if (!editor) {
    return null
  }

  return (
    <div className="tiptap-editor-wrapper">
      {/* 主工具栏 */}
      <Card size="small" style={{ marginBottom: 8 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          {/* 基础操作 */}
          <Space wrap>
            <Space.Compact>
              <Tooltip title="撤销 (Ctrl+Z)">
                <Button
                  size="small"
                  icon={<UndoOutlined />}
                  onClick={() => editor.chain().focus().undo().run()}
                  disabled={!editor.can().undo()}
                />
              </Tooltip>
              <Tooltip title="重做 (Ctrl+Y)">
                <Button
                  size="small"
                  icon={<RedoOutlined />}
                  onClick={() => editor.chain().focus().redo().run()}
                  disabled={!editor.can().redo()}
                />
              </Tooltip>
            </Space.Compact>

            {onInsertJinjaClick && (
              <Tooltip title="插入 Jinja2 变量/循环/条件">
                <Button
                  size="small"
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={onInsertJinjaClick}
                >
                  插入 Jinja2
                </Button>
              </Tooltip>
            )}
          </Space>

          {/* 格式工具栏 */}
          <EditorToolbar editor={editor} />
        </Space>
      </Card>

      {/* 表格工具栏 */}
      <TableToolbar editor={editor} visible={editor.isActive('table')} />

      {/* 编辑器内容 */}
      <Card
        className="tiptap-editor-content"
        styles={{
          body: {
            minHeight: '500px',
            maxHeight: '700px',
            overflow: 'auto',
            padding: '20px',
          }
        }}
      >
        <EditorContent editor={editor} />
      </Card>
    </div>
  )
}

export default TipTapEditor
