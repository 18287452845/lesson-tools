/**
 * 版本历史组件
 *
 * 显示模板的版本历史，支持对比和恢复
 */
import React, { useState, useEffect } from 'react'
import {
  Drawer,
  List,
  Card,
  Button,
  Space,
  Tag,
  Modal,
  message,
  Empty,
  Spin,
  Divider,
  Typography,
  Checkbox,
  Tooltip,
} from 'antd'
import {
  HistoryOutlined,
  RollbackOutlined,
  DiffOutlined,
  DeleteOutlined,
  ClockCircleOutlined,
  UserOutlined,
} from '@ant-design/icons'
import axios from 'axios'

const { Title, Text, Paragraph } = Typography
const { confirm } = Modal

const API_BASE = 'http://127.0.0.1:8000/api'

interface Version {
  id: string
  version_number: number
  user: string
  comment: string
  created_at: string
  content_size: number
}

interface VersionHistoryProps {
  visible: boolean
  onClose: () => void
  templateId: string
  onRestore?: () => void
}

const VersionHistory: React.FC<VersionHistoryProps> = ({
  visible,
  onClose,
  templateId,
  onRestore,
}) => {
  const [versions, setVersions] = useState<Version[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedVersions, setSelectedVersions] = useState<string[]>([])
  const [compareModalVisible, setCompareModalVisible] = useState(false)
  const [compareResult, setCompareResult] = useState<any>(null)
  const [comparing, setComparing] = useState(false)

  // 加载版本列表
  const loadVersions = async () => {
    setLoading(true)
    try {
      const response = await axios.get(
        `${API_BASE}/templates/${templateId}/versions`
      )
      setVersions(response.data.versions || [])
    } catch (error: any) {
      console.error('加载版本历史失败:', error)
      message.error('加载版本历史失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (visible && templateId) {
      loadVersions()
      setSelectedVersions([])
    }
  }, [visible, templateId])

  // 恢复版本
  const handleRestore = (version: Version) => {
    confirm({
      title: '确认恢复版本？',
      content: `确定要恢复到版本 ${version.version_number} (${new Date(version.created_at).toLocaleString()}) 吗？`,
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await axios.post(
            `${API_BASE}/templates/${templateId}/versions/${version.id}/restore`
          )
          message.success('版本恢复成功！')
          await loadVersions()
          if (onRestore) {
            onRestore()
          }
        } catch (error: any) {
          message.error('版本恢复失败: ' + error.message)
        }
      },
    })
  }

  // 对比版本
  const handleCompare = async () => {
    if (selectedVersions.length !== 2) {
      message.warning('请选择两个版本进行对比')
      return
    }

    setComparing(true)
    try {
      const response = await axios.post(
        `${API_BASE}/templates/${templateId}/versions/compare`,
        {
          version_id_1: selectedVersions[0],
          version_id_2: selectedVersions[1],
        }
      )
      setCompareResult(response.data)
      setCompareModalVisible(true)
    } catch (error: any) {
      message.error('版本对比失败: ' + error.message)
    } finally {
      setComparing(false)
    }
  }

  // 清理旧版本
  const handleCleanup = () => {
    confirm({
      title: '清理旧版本',
      content: '确定要删除旧版本吗？只保留最新的 20 个版本。',
      okText: '确认',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          const response = await axios.delete(
            `${API_BASE}/templates/${templateId}/versions/cleanup?keep_count=20`
          )
          message.success(`已删除 ${response.data.deleted_count} 个旧版本`)
          await loadVersions()
        } catch (error: any) {
          message.error('清理失败: ' + error.message)
        }
      },
    })
  }

  // 选择版本
  const handleSelectVersion = (versionId: string) => {
    setSelectedVersions((prev) => {
      if (prev.includes(versionId)) {
        return prev.filter((id) => id !== versionId)
      } else if (prev.length < 2) {
        return [...prev, versionId]
      } else {
        message.warning('最多只能选择两个版本进行对比')
        return prev
      }
    })
  }

  // 格式化文件大小
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  return (
    <>
      <Drawer
        title={
          <Space>
            <HistoryOutlined />
            版本历史
          </Space>
        }
        placement="right"
        open={visible}
        onClose={onClose}
        width={600}
        extra={
          <Space>
            {selectedVersions.length === 2 && (
              <Button
                type="primary"
                icon={<DiffOutlined />}
                onClick={handleCompare}
                loading={comparing}
              >
                对比选中版本
              </Button>
            )}
            <Button
              icon={<DeleteOutlined />}
              onClick={handleCleanup}
              danger
            >
              清理旧版本
            </Button>
          </Space>
        }
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <Spin size="large" tip="加载中..." />
          </div>
        ) : versions.length === 0 ? (
          <Empty description="暂无版本历史" />
        ) : (
          <>
            <Paragraph type="secondary">
              共 {versions.length} 个版本。选择两个版本可以进行对比。
            </Paragraph>

            <List
              dataSource={versions}
              renderItem={(version) => (
                <Card
                  size="small"
                  style={{ marginBottom: 12 }}
                  extra={
                    <Space>
                      <Checkbox
                        checked={selectedVersions.includes(version.id)}
                        onChange={() => handleSelectVersion(version.id)}
                      />
                      <Tooltip title="恢复到此版本">
                        <Button
                          size="small"
                          type="link"
                          icon={<RollbackOutlined />}
                          onClick={() => handleRestore(version)}
                        >
                          恢复
                        </Button>
                      </Tooltip>
                    </Space>
                  }
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      <Tag color="blue">v{version.version_number}</Tag>
                      <Text strong>
                        {new Date(version.created_at).toLocaleString('zh-CN')}
                      </Text>
                    </Space>

                    <Space size="large">
                      <Space size="small">
                        <UserOutlined />
                        <Text type="secondary">{version.user}</Text>
                      </Space>
                      <Space size="small">
                        <ClockCircleOutlined />
                        <Text type="secondary">
                          {formatSize(version.content_size)}
                        </Text>
                      </Space>
                    </Space>

                    {version.comment && (
                      <Text italic type="secondary">
                        {version.comment}
                      </Text>
                    )}
                  </Space>
                </Card>
              )}
            />
          </>
        )}
      </Drawer>

      {/* 对比结果模态框 */}
      <Modal
        title="版本对比结果"
        open={compareModalVisible}
        onCancel={() => setCompareModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setCompareModalVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        {compareResult && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Card size="small" title="变更统计">
              <Space size="large">
                <Text>
                  新增行: <Tag color="green">{compareResult.added_lines}</Tag>
                </Text>
                <Text>
                  删除行: <Tag color="red">{compareResult.removed_lines}</Tag>
                </Text>
                <Text>
                  总变更: <Tag color="blue">{compareResult.total_changes}</Tag>
                </Text>
              </Space>
            </Card>

            <Card size="small" title="差异详情">
              <pre
                style={{
                  background: '#f5f5f5',
                  padding: '12px',
                  borderRadius: '4px',
                  overflow: 'auto',
                  maxHeight: '400px',
                  fontSize: '12px',
                  lineHeight: '1.5',
                }}
              >
                {compareResult.diff || '无差异'}
              </pre>
            </Card>
          </Space>
        )}
      </Modal>
    </>
  )
}

export default VersionHistory
