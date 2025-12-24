/**
 * 增强的编辑器工具栏
 *
 * 提供格式刷、字体大小、颜色选择等高级格式功能
 */
import React, { useState } from 'react'
import { Button, Space, Divider, Select, Tooltip, ColorPicker } from 'antd'
import type { Editor } from '@tiptap/react'
import type { Color } from 'antd/es/color-picker'
import {
  BoldOutlined,
  ItalicOutlined,
  UnderlineOutlined,
  StrikethroughOutlined,
  OrderedListOutlined,
  UnorderedListOutlined,
  AlignLeftOutlined,
  AlignCenterOutlined,
  AlignRightOutlined,
  FormatPainterOutlined,
  BgColorsOutlined,
  FontColorsOutlined,
  ClearOutlined,
} from '@ant-design/icons'

interface EditorToolbarProps {
  editor: Editor | null
}

const EditorToolbar: React.FC<EditorToolbarProps> = ({ editor }) => {
  const [formatPainterActive, setFormatPainterActive] = useState(false)
  const [copiedFormat, setCopiedFormat] = useState<any>(null)

  if (!editor) {
    return null
  }

  // 字体大小选项
  const fontSizeOptions = [
    { label: '小', value: '12px' },
    { label: '正常', value: '14px' },
    { label: '中', value: '16px' },
    { label: '大', value: '18px' },
    { label: '特大', value: '24px' },
    { label: '超大', value: '32px' },
  ]

  // 字体族选项
  const fontFamilyOptions = [
    { label: '默认', value: '' },
    { label: '宋体', value: 'SimSun, serif' },
    { label: '黑体', value: 'SimHei, sans-serif' },
    { label: '楷体', value: 'KaiTi, serif' },
    { label: '微软雅黑', value: 'Microsoft YaHei, sans-serif' },
    { label: '等线', value: 'DengXian, sans-serif' },
    { label: 'Arial', value: 'Arial, sans-serif' },
    { label: 'Times New Roman', value: 'Times New Roman, serif' },
    { label: 'Courier New', value: 'Courier New, monospace' },
  ]

  // 格式刷功能
  const handleFormatPainter = () => {
    if (!formatPainterActive) {
      // 复制当前格式
      const attributes = editor.getAttributes('textStyle')
      const marks = {
        bold: editor.isActive('bold'),
        italic: editor.isActive('italic'),
        strike: editor.isActive('strike'),
        underline: editor.isActive('underline'),
        color: attributes.color,
        fontFamily: attributes.fontFamily,
        fontSize: attributes.fontSize,
      }
      setCopiedFormat(marks)
      setFormatPainterActive(true)
    } else {
      // 应用格式
      if (copiedFormat) {
        const { selection } = editor.state
        const { from, to } = selection

        // 清除现有格式
        editor.chain().focus().unsetAllMarks().run()

        // 应用复制的格式
        if (copiedFormat.bold) editor.chain().focus().setBold().run()
        if (copiedFormat.italic) editor.chain().focus().setItalic().run()
        if (copiedFormat.strike) editor.chain().focus().setStrike().run()
        if (copiedFormat.underline) editor.chain().focus().setUnderline().run()
        if (copiedFormat.color) {
          editor.chain().focus().setColor(copiedFormat.color).run()
        }
        if (copiedFormat.fontFamily) {
          editor.chain().focus().setFontFamily(copiedFormat.fontFamily).run()
        }
        if (copiedFormat.fontSize) {
          editor.chain().focus().setFontSize(copiedFormat.fontSize).run()
        }
      }

      setFormatPainterActive(false)
      setCopiedFormat(null)
    }
  }

  // 清除格式
  const handleClearFormat = () => {
    editor.chain().focus().unsetAllMarks().clearNodes().run()
  }

  // 设置文字颜色
  const handleTextColor = (color: Color) => {
    const hex = typeof color === 'string' ? color : color.toHexString()
    editor.chain().focus().setColor(hex).run()
  }

  // 设置背景色
  const handleBackgroundColor = (color: Color) => {
    const hex = typeof color === 'string' ? color : color.toHexString()
    editor.chain().focus().setHighlight({ color: hex }).run()
  }

  // 设置字体大小
  const handleFontSize = (size: string) => {
    if (size) {
      editor.chain().focus().setMark('textStyle', { fontSize: size }).run()
    } else {
      editor.chain().focus().unsetMark('textStyle').run()
    }
  }

  // 设置字体族
  const handleFontFamily = (family: string) => {
    if (family) {
      editor.chain().focus().setFontFamily(family).run()
    } else {
      editor.chain().focus().unsetFontFamily().run()
    }
  }

  return (
    <Space split={<Divider type="vertical" />} wrap>
      {/* 格式刷 */}
      <Tooltip title={formatPainterActive ? '点击选中文字应用格式' : '复制当前格式'}>
        <Button
          size="small"
          type={formatPainterActive ? 'primary' : 'default'}
          icon={<FormatPainterOutlined />}
          onClick={handleFormatPainter}
        >
          格式刷
        </Button>
      </Tooltip>

      {/* 清除格式 */}
      <Tooltip title="清除所有格式">
        <Button
          size="small"
          icon={<ClearOutlined />}
          onClick={handleClearFormat}
          danger
        >
          清除格式
        </Button>
      </Tooltip>

      {/* 基本格式 */}
      <Space.Compact>
        <Tooltip title="加粗 (Ctrl+B)">
          <Button
            size="small"
            type={editor.isActive('bold') ? 'primary' : 'default'}
            icon={<BoldOutlined />}
            onClick={() => editor.chain().focus().toggleBold().run()}
          />
        </Tooltip>
        <Tooltip title="斜体 (Ctrl+I)">
          <Button
            size="small"
            type={editor.isActive('italic') ? 'primary' : 'default'}
            icon={<ItalicOutlined />}
            onClick={() => editor.chain().focus().toggleItalic().run()}
          />
        </Tooltip>
        <Tooltip title="下划线 (Ctrl+U)">
          <Button
            size="small"
            type={editor.isActive('underline') ? 'primary' : 'default'}
            icon={<UnderlineOutlined />}
            onClick={() => editor.chain().focus().toggleUnderline().run()}
          />
        </Tooltip>
        <Tooltip title="删除线">
          <Button
            size="small"
            type={editor.isActive('strike') ? 'primary' : 'default'}
            icon={<StrikethroughOutlined />}
            onClick={() => editor.chain().focus().toggleStrike().run()}
          />
        </Tooltip>
      </Space.Compact>

      {/* 字体大小 */}
      <Tooltip title="字体大小">
        <Select
          size="small"
          style={{ width: 90 }}
          placeholder="大小"
          options={fontSizeOptions}
          onChange={handleFontSize}
          value={editor.getAttributes('textStyle').fontSize || '14px'}
        />
      </Tooltip>

      {/* 字体族 */}
      <Tooltip title="字体">
        <Select
          size="small"
          style={{ width: 120 }}
          placeholder="字体"
          options={fontFamilyOptions}
          onChange={handleFontFamily}
          value={editor.getAttributes('textStyle').fontFamily || ''}
        />
      </Tooltip>

      {/* 文字颜色 */}
      <Tooltip title="文字颜色">
        <ColorPicker
          size="small"
          value={editor.getAttributes('textStyle').color || '#000000'}
          onChange={handleTextColor}
          showText
          presets={[
            {
              label: '常用颜色',
              colors: [
                '#000000',
                '#FFFFFF',
                '#FF0000',
                '#00FF00',
                '#0000FF',
                '#FFFF00',
                '#FF00FF',
                '#00FFFF',
              ],
            },
          ]}
        >
          <Button size="small" icon={<FontColorsOutlined />}>
            颜色
          </Button>
        </ColorPicker>
      </Tooltip>

      {/* 背景色 */}
      <Tooltip title="背景色">
        <ColorPicker
          size="small"
          value={editor.getAttributes('highlight').color || '#FFFFFF'}
          onChange={handleBackgroundColor}
          showText
          presets={[
            {
              label: '常用背景色',
              colors: [
                '#FFFFFF',
                '#FFFF00',
                '#00FF00',
                '#00FFFF',
                '#FF00FF',
                '#FFE4B5',
                '#E6E6FA',
              ],
            },
          ]}
        >
          <Button size="small" icon={<BgColorsOutlined />}>
            背景
          </Button>
        </ColorPicker>
      </Tooltip>

      {/* 对齐 */}
      <Space.Compact>
        <Tooltip title="左对齐">
          <Button
            size="small"
            type={editor.isActive({ textAlign: 'left' }) ? 'primary' : 'default'}
            icon={<AlignLeftOutlined />}
            onClick={() => editor.chain().focus().setTextAlign('left').run()}
          />
        </Tooltip>
        <Tooltip title="居中对齐">
          <Button
            size="small"
            type={editor.isActive({ textAlign: 'center' }) ? 'primary' : 'default'}
            icon={<AlignCenterOutlined />}
            onClick={() => editor.chain().focus().setTextAlign('center').run()}
          />
        </Tooltip>
        <Tooltip title="右对齐">
          <Button
            size="small"
            type={editor.isActive({ textAlign: 'right' }) ? 'primary' : 'default'}
            icon={<AlignRightOutlined />}
            onClick={() => editor.chain().focus().setTextAlign('right').run()}
          />
        </Tooltip>
      </Space.Compact>

      {/* 列表 */}
      <Space.Compact>
        <Tooltip title="无序列表">
          <Button
            size="small"
            type={editor.isActive('bulletList') ? 'primary' : 'default'}
            icon={<UnorderedListOutlined />}
            onClick={() => editor.chain().focus().toggleBulletList().run()}
          />
        </Tooltip>
        <Tooltip title="有序列表">
          <Button
            size="small"
            type={editor.isActive('orderedList') ? 'primary' : 'default'}
            icon={<OrderedListOutlined />}
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
          />
        </Tooltip>
      </Space.Compact>
    </Space>
  )
}

export default EditorToolbar
