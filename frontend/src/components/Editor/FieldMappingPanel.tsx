/**
 * 字段映射面板组件
 *
 * 显示字段名与中文名的对应关系，支持添加、编辑、删除字段
 */
import React, { useState, useEffect } from 'react'
import {
  Drawer,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  message,
  Tag,
  Popconfirm,
  Typography,
  Divider,
  Alert,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SaveOutlined,
  TagsOutlined,
} from '@ant-design/icons'
import { useTemplateEditorStore } from '../../stores/templateEditorStore'
import type { FieldConfig } from '@/types'

const { Text } = Typography

interface FieldMappingPanelProps {
  visible: boolean
  onClose: () => void
}

const FIELD_TYPES = [
  { value: 'text', label: '文本 (text)' },
  { value: 'textarea', label: '多行文本 (textarea)' },
  { value: 'json', label: 'JSON 对象 (json)' },
  { value: 'array', label: '数组 (array)' },
]

const FieldMappingPanel: React.FC<FieldMappingPanelProps> = ({
  visible,
  onClose,
}) => {
  const {
    fieldsConfig,
    standardFields,
    isFieldsDirty,
    isFieldsSaving,
    loadFieldsConfig,
    loadStandardFields,
    addField,
    updateField,
    removeField,
    saveFieldsConfig,
  } = useTemplateEditorStore()

  const [addModalVisible, setAddModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingField, setEditingField] = useState<FieldConfig | null>(null)
  const [form] = Form.useForm()

  // 加载数据
  useEffect(() => {
    if (visible) {
      loadFieldsConfig()
      loadStandardFields()
    }
  }, [visible, loadFieldsConfig, loadStandardFields])

  // 处理添加字段
  const handleAdd = () => {
    form.resetFields()
    setAddModalVisible(true)
  }

  // 处理编辑字段
  const handleEdit = (field: FieldConfig) => {
    setEditingField(field)
    form.setFieldsValue(field)
    setEditModalVisible(true)
  }

  // 处理删除字段
  const handleDelete = (name: string) => {
    removeField(name)
    message.success('字段已删除')
  }

  // 提交添加表单
  const handleAddSubmit = async () => {
    try {
      const values = await form.validateFields()
      // 检查是否已存在
      if (fieldsConfig.some(f => f.name === values.name)) {
        message.error('字段名已存在')
        return
      }
      addField(values as FieldConfig)
      setAddModalVisible(false)
      message.success('字段已添加')
    } catch (error) {
      // 验证失败
    }
  }

  // 提交编辑表单
  const handleEditSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingField) {
        updateField(editingField.name, values)
        setEditModalVisible(false)
        message.success('字段已更新')
      }
    } catch (error) {
      // 验证失败
    }
  }

  // 保存配置
  const handleSave = async () => {
    try {
      await saveFieldsConfig()
      message.success('字段配置已保存')
    } catch (error: any) {
      message.error('保存失败: ' + error.message)
    }
  }

  // 从标准字段添加
  const handleAddFromStandard = (field: FieldConfig) => {
    if (fieldsConfig.some(f => f.name === field.name)) {
      message.warning('该字段已存在')
      return
    }
    addField(field)
    message.success(`已添加字段: ${field.display_name}`)
  }

  // 表格列定义
  const columns = [
    {
      title: '字段名 (英文)',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (text: string) => <code>{text}</code>,
    },
    {
      title: '中文名',
      dataIndex: 'display_name',
      key: 'display_name',
      width: 120,
    },
    {
      title: '类型',
      dataIndex: 'field_type',
      key: 'field_type',
      width: 100,
      render: (type: string) => {
        const colors: Record<string, string> = {
          text: 'blue',
          textarea: 'cyan',
          json: 'purple',
          array: 'orange',
        }
        return <Tag color={colors[type] || 'default'}>{type}</Tag>
      },
    },
    {
      title: '必填',
      dataIndex: 'required',
      key: 'required',
      width: 60,
      render: (required: boolean) => (
        <Tag color={required ? 'red' : 'default'}>
          {required ? '是' : '否'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: FieldConfig) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="确定删除此字段?"
            onConfirm={() => handleDelete(record.name)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 表单内容
  const renderForm = () => (
    <Form form={form} layout="vertical">
      <Form.Item
        name="name"
        label="字段名 (英文)"
        rules={[
          { required: true, message: '请输入字段名' },
          { pattern: /^[a-z][a-z0-9_]*$/, message: '只能使用小写字母、数字和下划线，且以字母开头' },
        ]}
      >
        <Input placeholder="如: custom_field" disabled={editModalVisible} />
      </Form.Item>
      <Form.Item
        name="display_name"
        label="中文名"
        rules={[{ required: true, message: '请输入中文名' }]}
      >
        <Input placeholder="如: 自定义字段" />
      </Form.Item>
      <Form.Item
        name="field_type"
        label="字段类型"
        initialValue="text"
        rules={[{ required: true, message: '请选择字段类型' }]}
      >
        <Select options={FIELD_TYPES} />
      </Form.Item>
      <Form.Item
        name="required"
        label="是否必填"
        valuePropName="checked"
        initialValue={false}
      >
        <Switch />
      </Form.Item>
      <Form.Item
        name="description"
        label="描述"
      >
        <Input.TextArea rows={2} placeholder="可选，字段描述" />
      </Form.Item>
    </Form>
  )

  return (
    <>
      <Drawer
        title={
          <Space>
            <TagsOutlined />
            字段配置
          </Space>
        }
        placement="right"
        onClose={onClose}
        open={visible}
        width={600}
        extra={
          <Space>
            {isFieldsDirty && (
              <Tag color="orange">有未保存的修改</Tag>
            )}
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={isFieldsSaving}
              disabled={!isFieldsDirty}
            >
              保存配置
            </Button>
          </Space>
        }
      >
        <Alert
          message="字段配置说明"
          description="配置模板中使用的字段，设置中文名和类型。字段名对应模板中的 {{ 变量名 }}。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <div style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加字段
          </Button>
        </div>

        <Table
          dataSource={fieldsConfig}
          columns={columns}
          rowKey="name"
          size="small"
          pagination={false}
        />

        {/* 标准字段参考 */}
        <Divider>标准字段参考（点击添加）</Divider>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {standardFields.map(field => {
            const exists = fieldsConfig.some(f => f.name === field.name)
            return (
              <Tag
                key={field.name}
                color={exists ? 'default' : 'blue'}
                style={{ cursor: exists ? 'not-allowed' : 'pointer', margin: 0 }}
                onClick={() => !exists && handleAddFromStandard(field)}
              >
                {field.display_name} ({field.name})
                {exists && ' ✓'}
              </Tag>
            )
          })}
        </div>
      </Drawer>

      {/* 添加字段弹窗 */}
      <Modal
        title="添加字段"
        open={addModalVisible}
        onOk={handleAddSubmit}
        onCancel={() => setAddModalVisible(false)}
        okText="确定"
        cancelText="取消"
      >
        {renderForm()}
      </Modal>

      {/* 编辑字段弹窗 */}
      <Modal
        title="编辑字段"
        open={editModalVisible}
        onOk={handleEditSubmit}
        onCancel={() => setEditModalVisible(false)}
        okText="确定"
        cancelText="取消"
      >
        {renderForm()}
      </Modal>
    </>
  )
}

export default FieldMappingPanel
