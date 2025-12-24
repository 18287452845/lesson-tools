/**
 * 表格操作工具栏
 *
 * 提供表格的高级编辑功能：插入/删除行列、合并单元格、设置边框样式等
 */
import React from 'react'
import { Button, Space, Divider, Popover, InputNumber, ColorPicker, Tooltip } from 'antd'
import type { Editor } from '@tiptap/react'
import {
  TableOutlined,
  DeleteOutlined,
  MergeCellsOutlined,
  SplitCellsOutlined,
  BorderOutlined,
} from '@ant-design/icons'

interface TableToolbarProps {
  editor: Editor | null
  visible?: boolean
}

const TableToolbar: React.FC<TableToolbarProps> = ({ editor, visible = true }) => {
  if (!editor || !visible) {
    return null
  }

  const isInTable = editor.isActive('table')

  if (!isInTable) {
    return null
  }

  // 插入表格
  const InsertTablePopover = (
    <div style={{ padding: 8 }}>
      <Space direction="vertical">
        <div>
          <label style={{ marginRight: 8 }}>行数:</label>
          <InputNumber
            min={1}
            max={20}
            defaultValue={3}
            id="table-rows"
            style={{ width: 80 }}
          />
        </div>
        <div>
          <label style={{ marginRight: 8 }}>列数:</label>
          <InputNumber
            min={1}
            max={10}
            defaultValue={3}
            id="table-cols"
            style={{ width: 80 }}
          />
        </div>
        <Button
          type="primary"
          block
          onClick={() => {
            const rows =
              (document.getElementById('table-rows') as HTMLInputElement)?.value || '3'
            const cols =
              (document.getElementById('table-cols') as HTMLInputElement)?.value || '3'
            editor
              .chain()
              .focus()
              .insertTable({
                rows: parseInt(rows),
                cols: parseInt(cols),
                withHeaderRow: true,
              })
              .run()
          }}
        >
          插入表格
        </Button>
      </Space>
    </div>
  )

  return (
    <div
      style={{
        padding: '8px 12px',
        background: '#f0f0f0',
        borderRadius: 4,
        marginBottom: 8,
      }}
    >
      <Space split={<Divider type="vertical" />} wrap>
        {/* 插入表格 */}
        {!isInTable && (
          <Popover content={InsertTablePopover} title="插入表格" trigger="click">
            <Tooltip title="插入新表格">
              <Button size="small" icon={<TableOutlined />}>
                插入表格
              </Button>
            </Tooltip>
          </Popover>
        )}

        {/* 表格操作（仅当在表格内时显示） */}
        {isInTable && (
          <>
            {/* 行操作 */}
            <Space.Compact>
              <Tooltip title="在上方插入行">
                <Button
                  size="small"
                  onClick={() => editor.chain().focus().addRowBefore().run()}
                >
                  ↑ 插入行
                </Button>
              </Tooltip>
              <Tooltip title="在下方插入行">
                <Button
                  size="small"
                  onClick={() => editor.chain().focus().addRowAfter().run()}
                >
                  ↓ 插入行
                </Button>
              </Tooltip>
              <Tooltip title="删除当前行">
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => editor.chain().focus().deleteRow().run()}
                >
                  删除行
                </Button>
              </Tooltip>
            </Space.Compact>

            {/* 列操作 */}
            <Space.Compact>
              <Tooltip title="在左侧插入列">
                <Button
                  size="small"
                  onClick={() => editor.chain().focus().addColumnBefore().run()}
                >
                  ← 插入列
                </Button>
              </Tooltip>
              <Tooltip title="在右侧插入列">
                <Button
                  size="small"
                  onClick={() => editor.chain().focus().addColumnAfter().run()}
                >
                  → 插入列
                </Button>
              </Tooltip>
              <Tooltip title="删除当前列">
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => editor.chain().focus().deleteColumn().run()}
                >
                  删除列
                </Button>
              </Tooltip>
            </Space.Compact>

            {/* 单元格操作 */}
            <Space.Compact>
              <Tooltip title="合并单元格 (需要先选中多个单元格)">
                <Button
                  size="small"
                  icon={<MergeCellsOutlined />}
                  onClick={() => editor.chain().focus().mergeCells().run()}
                  disabled={!editor.can().mergeCells()}
                >
                  合并
                </Button>
              </Tooltip>
              <Tooltip title="拆分单元格">
                <Button
                  size="small"
                  icon={<SplitCellsOutlined />}
                  onClick={() => editor.chain().focus().splitCell().run()}
                  disabled={!editor.can().splitCell()}
                >
                  拆分
                </Button>
              </Tooltip>
            </Space.Compact>

            {/* 表格样式 */}
            <Space.Compact>
              <Tooltip title="切换表头行">
                <Button
                  size="small"
                  type={editor.isActive('tableHeader') ? 'primary' : 'default'}
                  onClick={() => editor.chain().focus().toggleHeaderRow().run()}
                >
                  表头行
                </Button>
              </Tooltip>
              <Tooltip title="切换表头列">
                <Button
                  size="small"
                  type={editor.isActive('tableHeader') ? 'primary' : 'default'}
                  onClick={() => editor.chain().focus().toggleHeaderColumn().run()}
                >
                  表头列
                </Button>
              </Tooltip>
            </Space.Compact>

            {/* 删除整个表格 */}
            <Tooltip title="删除整个表格">
              <Button
                size="small"
                danger
                type="primary"
                icon={<DeleteOutlined />}
                onClick={() => editor.chain().focus().deleteTable().run()}
              >
                删除表格
              </Button>
            </Tooltip>
          </>
        )}
      </Space>
    </div>
  )
}

export default TableToolbar
