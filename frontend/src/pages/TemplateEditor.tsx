/**
 * 模板编辑器主页面
 *
 * 提供完整的模板在线编辑功能
 */
import React, { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Layout,
  Button,
  Space,
  message,
  Modal,
  Descriptions,
  Tag,
  Alert,
  Spin,
  Drawer,
  Form,
  Input,
  Switch,
} from 'antd'
import {
  SaveOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  LeftOutlined,
  InfoCircleOutlined,
  TagsOutlined,
  PlusOutlined,
  CloudSyncOutlined,
  HistoryOutlined,
  DownloadOutlined,
  EyeInvisibleOutlined,
} from '@ant-design/icons'
import { useTemplateEditorStore } from '../stores/templateEditorStore'
import { useAutoSave } from '../hooks/useAutoSave'
import TipTapEditor from '../components/Editor/TipTapEditor'
import JinjaInsertModal from '../components/Editor/JinjaInsertModal'
import PreviewPanel from '../components/Editor/PreviewPanel'
import VersionHistory from '../components/Editor/VersionHistory'
import FieldMappingPanel from '../components/Editor/FieldMappingPanel'
import OnlyOfficeEditor from '../components/Editor/OnlyOfficeEditor'
import type { Editor } from '@tiptap/react'
import axios from 'axios'

const { Header, Content } = Layout
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

const TemplateEditor: React.FC = () => {
  const { templateId } = useParams<{ templateId: string }>()
  const navigate = useNavigate()

  const {
    templateName,
    htmlContent,
    metadata,
    messages,
    variables,
    isLoading,
    isSaving,
    isDirty,
    error,
    previewHtml,
    isPreviewLoading,
    loadTemplate,
    updateHtml,
    saveTemplate,
    validateJinja,
    generatePreview,
    resetEditor,
  } = useTemplateEditorStore()

  const [previewVisible, setPreviewVisible] = useState(false)
  const [metadataVisible, setMetadataVisible] = useState(false)
  const [variablesVisible, setVariablesVisible] = useState(false)
  const [jinjaInsertVisible, setJinjaInsertVisible] = useState(false)
  const [versionHistoryVisible, setVersionHistoryVisible] = useState(false)
  const [realTimePreviewVisible, setRealTimePreviewVisible] = useState(false)
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true)
  const [editorMode, setEditorMode] = useState<'onlyoffice' | 'html'>('onlyoffice')
  const [previewForm] = Form.useForm()
  const editorRef = useRef<Editor | null>(null)

  // 自动保存功能
  useAutoSave({
    enabled: autoSaveEnabled,
    delay: 3000, // 3秒后自动保存
    onSave: saveTemplate,
    isDirty,
    content: htmlContent,
  })

  // 加载模板
  useEffect(() => {
    if (templateId) {
      loadTemplate(templateId).catch(err => {
        message.error('加载模板失败: ' + err.message)
      })
    }

    // 清理
    return () => {
      resetEditor()
    }
  }, [templateId])

  // 提示未保存的修改
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault()
        e.returnValue = ''
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [isDirty])

  // 保存处理
  const handleSave = async () => {
    try {
      await saveTemplate()
      message.success('保存成功！')
    } catch (err: any) {
      message.error('保存失败: ' + err.message)
    }
  }

  // 验证处理
  const handleValidate = async () => {
    try {
      const result = await validateJinja()
      if (result.valid) {
        message.success('Jinja2 语法验证通过！')
      } else {
        Modal.error({
          title: 'Jinja2 语法错误',
          content: (
            <div>
              {result.errors.map((err, idx) => (
                <div key={idx} style={{ marginBottom: 8 }}>
                  • {err}
                </div>
              ))}
            </div>
          ),
        })
      }
    } catch (err: any) {
      message.error('验证失败: ' + err.message)
    }
  }

  // 预览处理
  const handlePreview = async () => {
    previewForm.resetFields()

    // 为每个变量生成默认示例值
    const defaultValues: Record<string, string> = {}
    variables.forEach(v => {
      defaultValues[v.name] = `示例_${v.name}`
    })

    previewForm.setFieldsValue(defaultValues)
    setPreviewVisible(true)
  }

  // 生成预览
  const handleGeneratePreview = async () => {
    try {
      const values = await previewForm.validateFields()
      await generatePreview(values)
      message.success('预览生成成功！')
    } catch (err: any) {
      message.error('生成预览失败: ' + err.message)
    }
  }

  // 导出为 HTML
  const handleExportHTML = async () => {
    try {
      const response = await axios.post(
        `${API_BASE}/templates/${templateId}/export/html`,
        { html: htmlContent },
        { headers: { 'Content-Type': 'application/json' } }
      )

      const { download_url } = response.data

      // 下载文件
      const base = API_BASE === '/api' ? '' : API_BASE.replace('/api', '')
      window.open(`${base}${download_url}`, '_blank')
      message.success('导出成功！')
    } catch (err: any) {
      message.error('导出失败: ' + err.message)
    }
  }

  // 版本恢复后重新加载
  const handleVersionRestore = async () => {
    if (templateId) {
      await loadTemplate(templateId)
      message.success('模板已重新加载')
    }
  }

  const handleReloadTemplate = async () => {
    if (!templateId) return
    try {
      await loadTemplate(templateId)
      message.success('已同步最新模板内容')
    } catch (err: any) {
      message.error(err.message || '同步失败')
    }
  }

  // 返回
  const handleBack = () => {
    if (isDirty) {
      Modal.confirm({
        title: '确认离开？',
        content: '您有未保存的修改，确定要离开吗？',
        onOk: () => navigate('/templates'),
        okText: '离开',
        cancelText: '取消',
        okButtonProps: { danger: true },
      })
    } else {
      navigate('/templates')
    }
  }

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px' }}>
        <Spin size="large" tip="加载模板中...">
          <div style={{ minHeight: 100 }} />
        </Spin>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: '50px' }}>
        <Alert
          message="加载失败"
          description={error}
          type="error"
          showIcon
          action={
            <Button size="small" onClick={handleBack}>
              返回
            </Button>
          }
        />
      </div>
    )
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 头部 */}
      <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space size="large">
            <Button icon={<LeftOutlined />} onClick={handleBack}>
              返回
            </Button>
            <h2 style={{ margin: 0 }}>
              编辑模板: {templateName}
              {isDirty && <Tag color="orange" style={{ marginLeft: 8 }}>未保存</Tag>}
              {autoSaveEnabled && isDirty && (
                <Tag icon={<CloudSyncOutlined />} color="blue" style={{ marginLeft: 8 }}>
                  自动保存中
                </Tag>
              )}
            </h2>
          </Space>

          <Space size="middle">
            <Button.Group>
              <Button
                type={editorMode === 'onlyoffice' ? 'primary' : 'default'}
                onClick={() => setEditorMode('onlyoffice')}
              >
                OnlyOffice 编辑
              </Button>
              <Button
                type={editorMode === 'html' ? 'primary' : 'default'}
                onClick={() => setEditorMode('html')}
              >
                HTML 模式
              </Button>
            </Button.Group>

            <Button
              icon={<CloudSyncOutlined />}
              onClick={handleReloadTemplate}
            >
              同步模板
            </Button>

            {editorMode === 'html' && (
              <>
                {/* 自动保存开关 */}
                <Space>
                  <span style={{ fontSize: 12, color: '#666' }}>自动保存:</span>
                  <Switch
                    checked={autoSaveEnabled}
                    onChange={setAutoSaveEnabled}
                    checkedChildren="开"
                    unCheckedChildren="关"
                  />
                </Space>

                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setJinjaInsertVisible(true)}
                >
                  插入 Jinja2
                </Button>
                <Button
                  icon={<CheckCircleOutlined />}
                  onClick={handleValidate}
                >
                  验证语法
                </Button>
                <Button
                  icon={<EyeOutlined />}
                  onClick={handlePreview}
                  loading={isPreviewLoading}
                >
                  预览
                </Button>
                <Button
                  icon={realTimePreviewVisible ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                  type={realTimePreviewVisible ? 'primary' : 'default'}
                  onClick={() => setRealTimePreviewVisible(!realTimePreviewVisible)}
                >
                  {realTimePreviewVisible ? '关闭' : '打开'}实时预览
                </Button>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={handleExportHTML}
                >
                  导出 HTML
                </Button>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSave}
                  loading={isSaving}
                  disabled={!isDirty}
                >
                  保存
                </Button>
              </>
            )}

            <Button
              icon={<InfoCircleOutlined />}
              onClick={() => setMetadataVisible(true)}
            >
              元数据
            </Button>
            <Button
              icon={<TagsOutlined />}
              onClick={() => setVariablesVisible(true)}
            >
              字段配置
            </Button>
            <Button
              icon={<HistoryOutlined />}
              onClick={() => setVersionHistoryVisible(true)}
            >
              版本历史
            </Button>
          </Space>
        </div>
      </Header>

      {/* 内容区域 */}
      <Content
        style={{
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
          height: 'calc(100vh - 64px)',
          boxSizing: 'border-box',
          overflow: 'hidden',
        }}
      >
        {editorMode === 'onlyoffice' ? (
          <>
            <Alert
              message="OnlyOffice 模式（保持原始排版样式）"
              description="在工具栏中点击保存后，文档将通过回调写回模板文件并同步到版本历史。"
              type="info"
              showIcon
              style={{ marginBottom: 0 }}
            />
            <div style={{ flex: 1, minHeight: 0 }}>
              {templateId && (
                <OnlyOfficeEditor
                  templateId={templateId}
                  onRefresh={handleReloadTemplate}
                  style={{
                    height: '100%',
                    minHeight: 'calc(100vh - 200px)',
                  }}
                />
              )}
            </div>
          </>
        ) : (
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
            {/* 转换消息/警告 */}
            {messages.length > 0 && (
              <Alert
                message="转换提示"
                description={
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {messages.map((msg, idx) => (
                      <li key={idx}>{msg}</li>
                    ))}
                  </ul>
                }
                type="info"
                closable
                style={{ marginBottom: 16 }}
              />
            )}

            {/* 编辑器 */}
            <TipTapEditor
              content={htmlContent}
              onChange={updateHtml}
              editable={true}
              onInsertJinjaClick={() => setJinjaInsertVisible(true)}
              onEditorReady={(editor) => {
                editorRef.current = editor
              }}
            />
          </div>
        )}
      </Content>

      {/* Jinja2 插入弹窗 */}
      <JinjaInsertModal
        visible={jinjaInsertVisible}
        onClose={() => setJinjaInsertVisible(false)}
        editor={editorRef.current}
        existingVariables={variables.map(v => v.name)}
      />

      {/* 元数据抽屉 */}
      <Drawer
        title="模板元数据"
        placement="right"
        onClose={() => setMetadataVisible(false)}
        open={metadataVisible}
        width={400}
      >
        {metadata && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="文件名">{metadata.file_name}</Descriptions.Item>
            <Descriptions.Item label="标题">{metadata.title || '未设置'}</Descriptions.Item>
            <Descriptions.Item label="主题">{metadata.subject || '未设置'}</Descriptions.Item>
            <Descriptions.Item label="作者">{metadata.author || '未设置'}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{metadata.created || '未知'}</Descriptions.Item>
            <Descriptions.Item label="修改时间">{metadata.modified || '未知'}</Descriptions.Item>
            <Descriptions.Item label="文件大小">
              {metadata.file_size ? `${(metadata.file_size / 1024).toFixed(2)} KB` : '未知'}
            </Descriptions.Item>
            <Descriptions.Item label="段落数">{metadata.paragraphs_count || 0}</Descriptions.Item>
            <Descriptions.Item label="表格数">{metadata.tables_count || 0}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>

      {/* 字段配置面板 */}
      <FieldMappingPanel
        visible={variablesVisible}
        onClose={() => setVariablesVisible(false)}
      />

      {/* 预览模态框 */}
      <Modal
        title="预览模板"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        width={800}
        footer={[
          <Button key="cancel" onClick={() => setPreviewVisible(false)}>
            关闭
          </Button>,
          <Button
            key="preview"
            type="primary"
            onClick={handleGeneratePreview}
            loading={isPreviewLoading}
          >
            生成预览
          </Button>,
        ]}
      >
        <Form form={previewForm} layout="vertical">
          <Alert
            message="填写示例数据以生成预览"
            type="info"
            style={{ marginBottom: 16 }}
            showIcon
          />

          {variables.map(v => (
            <Form.Item
              key={v.name}
              label={v.name}
              name={v.name}
              rules={[{ required: true, message: '请输入示例值' }]}
            >
              <Input placeholder={`输入 ${v.name} 的示例值`} />
            </Form.Item>
          ))}

          {previewHtml && (
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="预览结果">
                <div
                  style={{
                    border: '1px solid #d9d9d9',
                    borderRadius: 4,
                    padding: 16,
                    marginTop: 8,
                    maxHeight: 400,
                    overflow: 'auto',
                  }}
                  dangerouslySetInnerHTML={{ __html: previewHtml }}
                />
              </Descriptions.Item>
            </Descriptions>
          )}
        </Form>
      </Modal>

      {/* 实时预览面板 */}
      <PreviewPanel
        htmlContent={htmlContent}
        variables={variables}
        visible={realTimePreviewVisible}
        onClose={() => setRealTimePreviewVisible(false)}
      />

      {/* 版本历史 */}
      <VersionHistory
        visible={versionHistoryVisible}
        onClose={() => setVersionHistoryVisible(false)}
        templateId={templateId || ''}
        onRestore={handleVersionRestore}
      />
    </Layout>
  )
}

export default TemplateEditor
