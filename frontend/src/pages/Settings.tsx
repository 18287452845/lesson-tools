/**
 * Settings page - Configure AI provider and API keys
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Card,
  Form,
  Input,
  Select,
  Typography,
  Space,
  Alert,
  Divider,
  Tag,
  message,
  Spin,
  Radio,
} from 'antd';
import {
  ArrowLeftOutlined,
  SaveOutlined,
  CheckCircleOutlined,
  ApiOutlined,
  KeyOutlined,
  RocketOutlined,
  LockOutlined,
} from '@ant-design/icons';
import { useSettingsStore } from '@/stores/settingsStore';

const { Title, Text, Paragraph } = Typography;
const { Password } = Input;
type ProviderId = 'deepseek' | 'anthropic';

function SettingsPage() {
  const navigate = useNavigate();
  const {
    currentProvider,
    availableProviders,
    loading,
    error,
    savedApiKeys,
    fetchCurrentConfig,
    fetchProviders,
    setProviderConfig,
    clearError,
  } = useSettingsStore();

  const [form] = Form.useForm();
  const [selectedProvider, setSelectedProvider] = useState<ProviderId>('deepseek');
  const [selectedModel, setSelectedModel] = useState<string>('deepseek-chat');

  useEffect(() => {
    fetchCurrentConfig();
    fetchProviders();
  }, [fetchCurrentConfig, fetchProviders]);

  useEffect(() => {
    if (currentProvider) {
      setSelectedProvider(currentProvider.provider as 'deepseek' | 'anthropic');
      setSelectedModel(currentProvider.model);
    }
  }, [currentProvider]);

  useEffect(() => {
    if (error) {
      message.error(error);
      clearError();
    }
  }, [error, clearError]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      await setProviderConfig(selectedProvider, values.api_key, selectedModel);
      message.success('AI配置已保存');
    } catch (err) {
      // Error handled by store
    }
  };

  const getProviderInfo = (providerId: string) => {
    return availableProviders.find((p) => p.id === providerId);
  };

  const currentProviderInfo = getProviderInfo(selectedProvider);
  const providerKeys: Record<ProviderId, string | undefined> = {
    deepseek: savedApiKeys.deepseek,
    anthropic: savedApiKeys.anthropic,
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
          返回首页
        </Button>
      </div>

      <Title level={2}>AI设置</Title>

      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 当前配置状态 */}
        <Card
          title={
            <Space>
              <ApiOutlined />
              <span>当前配置</span>
            </Space>
          }
        >
          {currentProvider ? (
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <div>
                <Text strong>AI提供商：</Text>
                <Tag color={currentProvider.configured ? 'success' : 'default'}>
                  {currentProvider.provider === 'deepseek' ? 'DeepSeek' : 'Anthropic Claude'}
                </Tag>
                {currentProvider.configured && (
                  <CheckCircleOutlined style={{ color: '#52c41a', marginLeft: 8 }} />
                )}
              </div>
              <div>
                <Text strong>模型：</Text>
                <Text code>{currentProvider.model}</Text>
              </div>
              {!currentProvider.has_api_key && (
                <Alert
                  type="warning"
                  message="未配置API密钥"
                  description="请在下方配置API密钥以使用AI功能"
                  showIcon
                />
              )}
            </Space>
          ) : (
            <Spin />
          )}
        </Card>

        {/* 配置表单 */}
        <Card
          title={
            <Space>
              <KeyOutlined />
              <span>API配置</span>
            </Space>
          }
          extra={<Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={loading}>
            保存配置
          </Button>
        }>
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              provider: 'deepseek',
              api_key: savedApiKeys.deepseek || savedApiKeys.anthropic || '',
            }}
          >
            <Form.Item label="选择AI提供商" name="provider">
              <Radio.Group
                value={selectedProvider}
                onChange={(e) => {
                  const provider = e.target.value as ProviderId;
                  setSelectedProvider(provider);
                  const providerInfo = getProviderInfo(provider);
                  if (providerInfo) {
                    setSelectedModel(providerInfo.default_model);
                  }
                  form.setFieldValue('api_key', providerKeys[provider] || '');
                }}
              >
                <Space direction="vertical">
                  <Radio value="deepseek">
                    <Space>
                      <RocketOutlined />
                      <Text strong>DeepSeek</Text>
                      <Tag color="blue">推荐</Tag>
                      <Text type="secondary">- 高性能中文AI模型，性价比高</Text>
                    </Space>
                  </Radio>
                  <Radio value="anthropic">
                    <Space>
                      <ApiOutlined />
                      <Text strong>Anthropic Claude</Text>
                      <Text type="secondary">- 高质量AI助手</Text>
                    </Space>
                  </Radio>
                </Space>
              </Radio.Group>
            </Form.Item>

            <Form.Item
              label="选择模型"
              tooltip="选择要使用的AI模型"
            >
              <Select
                value={selectedModel}
                onChange={setSelectedModel}
                options={(currentProviderInfo?.models ?? []).map((m) => ({
                  label: m.name,
                  value: m.id,
                }))}
              />
            </Form.Item>

            <Form.Item
              label="API密钥"
              name="api_key"
              rules={[{ required: true, message: '请输入API密钥' }]}
              tooltip="您的API密钥将仅保存在本地浏览器中"
            >
              <Password
                placeholder={selectedProvider === 'deepseek' ? 'sk-...' : 'sk-ant-...'}
                prefix={<LockOutlined />}
                style={{ fontFamily: 'monospace' }}
              />
            </Form.Item>

            {selectedProvider === 'deepseek' && (
              <Alert
                type="info"
                message="获取DeepSeek API密钥"
                description={
                  <span>
                    访问{' '}
                    <a href="https://platform.deepseek.com/" target="_blank" rel="noopener noreferrer">
                      DeepSeek开放平台
                    </a>
                    {' '}注册并获取API密钥
                  </span>
                }
                showIcon
              />
            )}

            {selectedProvider === 'anthropic' && (
              <Alert
                type="info"
                message="获取Anthropic API密钥"
                description={
                  <span>
                    访问{' '}
                    <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer">
                      Anthropic Console
                    </a>
                    {' '}注册并获取API密钥
                  </span>
                }
                showIcon
              />
            )}
          </Form>
        </Card>

        {/* 关于AI提供商 */}
        <Card
          title={
            <Space>
              <ApiOutlined />
              <span>关于AI提供商</span>
            </Space>
          }
        >
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {availableProviders.map((provider) => (
              <div key={provider.id}>
                <Space>
                  <Text strong>{provider.name}</Text>
                  <Tag>{provider.models.length} 个模型</Tag>
                </Space>
                <Paragraph type="secondary">{provider.description}</Paragraph>
                <div>
                  <Text strong>可用模型：</Text>
                  <div style={{ marginTop: 8 }}>
                    {provider.models.map((model) => (
                      <Tag key={model.id} color={model.id === provider.default_model ? 'blue' : 'default'}>
                        {model.name}
                        {model.id === provider.default_model && ' (默认)'}
                      </Tag>
                    ))}
                  </div>
                </div>
                {provider.id !== selectedProvider && (
                  <Button
                    size="small"
                    type="link"
                    onClick={() => {
                      const targetProvider = provider.id as ProviderId;
                      setSelectedProvider(targetProvider);
                      setSelectedModel(provider.default_model);
                      form.setFieldValue('api_key', providerKeys[targetProvider] || '');
                    }}
                  >
                    切换到 {provider.name}
                  </Button>
                )}
                <Divider style={{ margin: '8px 0' }} />
              </div>
            ))}
          </Space>
        </Card>

        {/* 隐私说明 */}
        <Alert
          type="info"
          message="关于隐私安全"
          description="您的API密钥仅保存在本地浏览器中，直接发送到对应的AI提供商服务器。我们的服务器不会存储或记录您的API密钥。"
          showIcon
        />
      </Space>
    </div>
  );
}

export default SettingsPage;
