/**
 * 实时预览面板
 *
 * 在右侧显示模板的实时预览效果
 */
import React, { useState, useEffect } from 'react'
import { Card, Button, Space, Alert, Drawer, Form, Input, Typography } from 'antd'
import {
  EyeOutlined,
  ReloadOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import nunjucks from 'nunjucks'

const { Paragraph } = Typography
const { TextArea } = Input

interface PreviewPanelProps {
  htmlContent: string
  variables: Array<{ name: string; type: string }>
  visible: boolean
  onClose: () => void
}

const PreviewPanel: React.FC<PreviewPanelProps> = ({
  htmlContent,
  variables,
  visible,
  onClose,
}) => {
  const [previewHtml, setPreviewHtml] = useState<string>('')
  const [sampleData, setSampleData] = useState<Record<string, any>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [settingsVisible, setSettingsVisible] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [form] = Form.useForm()

  // 初始化示例数据
  useEffect(() => {
    const initialData: Record<string, any> = {}
    variables.forEach(v => {
      // 根据变量名生成合理的示例数据
      if (v.name.includes('name')) {
        initialData[v.name] = '张三'
      } else if (v.name.includes('date') || v.name.includes('time')) {
        initialData[v.name] = new Date().toLocaleDateString('zh-CN')
      } else if (v.name.includes('count') || v.name.includes('number')) {
        initialData[v.name] = '30'
      } else if (v.name.includes('steps') || v.name.includes('activities')) {
        initialData[v.name] = [
          { title: '导入新课', content: '复习旧知识，引入新概念', duration: '5分钟' },
          { title: '讲解新知', content: '详细讲解知识点', duration: '20分钟' },
          { title: '练习巩固', content: '课堂练习与讨论', duration: '15分钟' },
        ]
      } else if (v.name.includes('goals')) {
        initialData[v.name] = '1. 知识目标\n2. 能力目标\n3. 情感目标'
      } else {
        initialData[v.name] = `示例_${v.name}`
      }
    })
    setSampleData(initialData)
    form.setFieldsValue(initialData)
  }, [variables, form])

  // 渲染预览
  const renderPreview = () => {
    setIsLoading(true)
    setError(null)

    try {
      // 从 HTML 中恢复 Jinja2 语法
      let jinjaTemplate = htmlContent

      // 从 data-jinja 属性中提取 Jinja2 代码
      const parser = new DOMParser()
      const doc = parser.parseFromString(htmlContent, 'text/html')
      const jinjaElements = doc.querySelectorAll('[data-jinja]')

      jinjaElements.forEach(element => {
        const jinjaCode = element.getAttribute('data-jinja')
        if (jinjaCode) {
          // 解码 HTML 实体
          const decoded = jinjaCode
            .replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>')
            .replace(/&#123;/g, '{')
            .replace(/&#125;/g, '}')
            .replace(/&quot;/g, '"')
            .replace(/&#39;/g, "'")
            .replace(/&amp;/g, '&')

          // 替换整个 span 元素为 Jinja2 代码
          const outerHTML = element.outerHTML
          jinjaTemplate = jinjaTemplate.replace(outerHTML, decoded)
        }
      })

      // 配置 nunjucks
      const env = nunjucks.configure({ autoescape: false })

      // 渲染模板
      const rendered = env.renderString(jinjaTemplate, sampleData)

      setPreviewHtml(rendered)
    } catch (err: any) {
      console.error('渲染预览失败:', err)
      setError(err.message || '渲染失败')
    } finally {
      setIsLoading(false)
    }
  }

  // 自动刷新
  useEffect(() => {
    if (autoRefresh && visible) {
      renderPreview()
    }
  }, [htmlContent, sampleData, autoRefresh, visible])

  // 手动刷新
  const handleRefresh = () => {
    renderPreview()
  }

  // 更新示例数据
  const handleUpdateSampleData = async () => {
    try {
      const values = await form.validateFields()

      // 尝试解析 JSON 格式的字段
      const parsedData: Record<string, any> = {}
      Object.keys(values).forEach(key => {
        const value = values[key]
        if (typeof value === 'string' && (value.trim().startsWith('[') || value.trim().startsWith('{'))) {
          try {
            parsedData[key] = JSON.parse(value)
          } catch {
            parsedData[key] = value
          }
        } else {
          parsedData[key] = value
        }
      })

      setSampleData(parsedData)
      setSettingsVisible(false)
      renderPreview()
    } catch (error) {
      console.error('更新示例数据失败:', error)
    }
  }

  return (
    <>
      <Drawer
        title={
          <Space>
            <EyeOutlined />
            实时预览
          </Space>
        }
        placement="right"
        open={visible}
        onClose={onClose}
        width="50%"
        extra={
          <Space>
            <Button
              size="small"
              icon={<SettingOutlined />}
              onClick={() => setSettingsVisible(true)}
            >
              配置数据
            </Button>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              loading={isLoading}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* 提示信息 */}
          <Alert
            message="实时预览"
            description="使用示例数据渲染模板，可以点击'配置数据'修改示例值"
            type="info"
            showIcon
            closable
          />

          {/* 自动刷新开关 */}
          <Card size="small">
            <Space>
              <span>自动刷新:</span>
              <Button
                size="small"
                type={autoRefresh ? 'primary' : 'default'}
                onClick={() => setAutoRefresh(!autoRefresh)}
              >
                {autoRefresh ? '已开启' : '已关闭'}
              </Button>
            </Space>
          </Card>

          {/* 错误提示 */}
          {error && (
            <Alert
              message="渲染错误"
              description={error}
              type="error"
              showIcon
              closable
              onClose={() => setError(null)}
            />
          )}

          {/* 预览内容 */}
          <Card
            title="预览内容"
            size="small"
            loading={isLoading}
            style={{ minHeight: '400px' }}
          >
            {previewHtml ? (
              <div
                className="preview-content"
                style={{
                  padding: '16px',
                  background: '#fff',
                  border: '1px solid #f0f0f0',
                  borderRadius: '4px',
                  minHeight: '400px',
                }}
                dangerouslySetInnerHTML={{ __html: previewHtml }}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: '50px', color: '#999' }}>
                <EyeOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                <div>点击'刷新'按钮生成预览</div>
              </div>
            )}
          </Card>
        </Space>
      </Drawer>

      {/* 示例数据配置抽屉 */}
      <Drawer
        title="配置示例数据"
        placement="right"
        open={settingsVisible}
        onClose={() => setSettingsVisible(false)}
        width={400}
        extra={
          <Button type="primary" onClick={handleUpdateSampleData}>
            应用
          </Button>
        }
      >
        <Form form={form} layout="vertical">
          <Alert
            message="提示"
            description="列表/对象类型请使用 JSON 格式，如: [{'title': '步骤1'}]"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          {variables.map(v => (
            <Form.Item
              key={v.name}
              label={v.name}
              name={v.name}
              tooltip={`类型: ${v.type}`}
            >
              {v.name.includes('steps') || v.name.includes('activities') ? (
                <TextArea
                  rows={4}
                  placeholder='[{"title": "步骤1", "content": "内容", "duration": "5分钟"}]'
                />
              ) : v.name.includes('goals') || v.name.includes('points') ? (
                <TextArea
                  rows={3}
                  placeholder="1. 第一条&#10;2. 第二条&#10;3. 第三条"
                />
              ) : (
                <Input placeholder={`输入 ${v.name} 的示例值`} />
              )}
            </Form.Item>
          ))}
        </Form>
      </Drawer>
    </>
  )
}

export default PreviewPanel
