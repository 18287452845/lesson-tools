/**
 * 模板编辑器主页面（OnlyOffice 模式）
 *
 * 提供 OnlyOffice 在线编辑能力，移除 HTML 模式。
 */
import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Layout,
  Button,
  Space,
  message,
  Alert,
  Spin,
  Drawer,
  Descriptions,
  Tag,
} from 'antd'
import {
  CloudSyncOutlined,
  HistoryOutlined,
  InfoCircleOutlined,
  LeftOutlined,
  TagsOutlined,
} from '@ant-design/icons'
import { useTemplateEditorStore } from '../stores/templateEditorStore'
import FieldMappingPanel from '../components/Editor/FieldMappingPanel'
import VersionHistory from '../components/Editor/VersionHistory'
import OnlyOfficeEditor from '../components/Editor/OnlyOfficeEditor'

const { Header, Content } = Layout

const TemplateEditor: React.FC = () => {
  const { templateId } = useParams<{ templateId: string }>()
  const navigate = useNavigate()

  const {
    templateName,
    metadata,
    isLoading,
    error,
    loadTemplate,
    resetEditor,
  } = useTemplateEditorStore()

  const [metadataVisible, setMetadataVisible] = useState(false)
  const [variablesVisible, setVariablesVisible] = useState(false)
  const [versionHistoryVisible, setVersionHistoryVisible] = useState(false)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    if (templateId) {
      loadTemplate(templateId).catch(err => {
        message.error('加载模板失败: ' + (err?.message || err))
      })
    }

    return () => {
      resetEditor()
    }
  }, [templateId])

  const handleReloadTemplate = async () => {
    if (!templateId) return
    setSyncing(true)
    try {
      await loadTemplate(templateId)
      message.success('已同步最新模板内容')
    } catch (err: any) {
      message.error(err?.message || '同步失败')
    } finally {
      setSyncing(false)
    }
  }

  const handleBack = () => {
    navigate('/templates')
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
      <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space size="large">
            <Button icon={<LeftOutlined />} onClick={handleBack}>
              返回
            </Button>
            <h2 style={{ margin: 0 }}>
              编辑模板: {templateName}
              <Tag color="blue" style={{ marginLeft: 8 }}>
                OnlyOffice 模式
              </Tag>
            </h2>
          </Space>

          <Space size="middle">
            <Button
              icon={<CloudSyncOutlined />}
              onClick={handleReloadTemplate}
              loading={syncing}
            >
              同步模板
            </Button>
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
        <Alert
          message="仅保留 OnlyOffice 编辑，HTML 模式已移除"
          description="在 OnlyOffice 工具栏中点击保存后，文档将通过回调写回模板并同步到版本历史。"
          type="info"
          showIcon
        />
        <div style={{ flex: 1, minHeight: 0 }}>
          {templateId && (
            <OnlyOfficeEditor
              templateId={templateId}
              onRefresh={handleReloadTemplate}
              style={{
                height: '100%',
                minHeight: 'calc(100vh - 180px)',
              }}
            />
          )}
        </div>
      </Content>

      <Drawer
        title="模板元数据"
        placement="right"
        onClose={() => setMetadataVisible(false)}
        open={metadataVisible}
        width={400}
      >
        {metadata ? (
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
        ) : (
          <Alert message="暂无元数据信息" type="warning" showIcon />
        )}
      </Drawer>

      <FieldMappingPanel
        visible={variablesVisible}
        onClose={() => setVariablesVisible(false)}
      />

      <VersionHistory
        visible={versionHistoryVisible}
        onClose={() => setVersionHistoryVisible(false)}
        templateId={templateId || ''}
        onRestore={handleReloadTemplate}
      />
    </Layout>
  )
}

export default TemplateEditor
