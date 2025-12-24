/**
 * Home page - Main landing page
 */
import { useNavigate } from 'react-router-dom';
import { Card, Row, Col, Typography, Space, Button, FloatButton } from 'antd';
import {
  FileTextOutlined,
  EditOutlined,
  FolderOutlined,
  HistoryOutlined,
  SettingOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

function Home() {
  const navigate = useNavigate();

  const features = [
    {
      icon: <FileTextOutlined style={{ fontSize: 48, color: '#1890ff' }} />,
      title: '新建教案',
      description: '选择模板，AI自动生成完整教案内容',
      action: () => navigate('/new'),
    },
    {
      icon: <EditOutlined style={{ fontSize: 48, color: '#52c41a' }} />,
      title: '编辑旧教案',
      description: '上传已有教案，智能识别并AI辅助修改',
      action: () => navigate('/edit'),
    },
    {
      icon: <FolderOutlined style={{ fontSize: 48, color: '#faad14' }} />,
      title: '模板管理',
      description: '上传、管理和编辑教案模板',
      action: () => navigate('/templates'),
    },
    {
      icon: <HistoryOutlined style={{ fontSize: 48, color: '#722ed1' }} />,
      title: '历史记录',
      description: '查看和管理生成的教案记录',
      action: () => navigate('/history'),
    },
  ];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 20px' }}>
      <div style={{ textAlign: 'center', marginBottom: 60 }}>
        <Title level={1}>智能教案助手</Title>
        <Text type="secondary" style={{ fontSize: 18 }}>
          AI驱动的教案生成与编辑工具，让教学备课更高效
        </Text>
      </div>

      <Row gutter={[24, 24]}>
        {features.map((feature) => (
          <Col xs={24} sm={12} lg={6} key={feature.title}>
            <Card
              hoverable
              onClick={feature.action}
              style={{ height: '100%', textAlign: 'center' }}
              bodyStyle={{ padding: '32px' }}
            >
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                {feature.icon}
                <Title level={4} style={{ margin: 0 }}>
                  {feature.title}
                </Title>
                <Text type="secondary">{feature.description}</Text>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      <div style={{ marginTop: 60, textAlign: 'center' }}>
        <Title level={3}>核心功能</Title>
        <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
          <Col xs={24} md={8}>
            <Card>
              <Title level={5}>AI智能生成</Title>
              <Text type="secondary">
                基于教学大纲和学情分析，自动生成专业的教案内容
              </Text>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Title level={5}>格式保持</Title>
              <Text type="secondary">
                支持自定义Word模板，生成后保持原有格式和样式
              </Text>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Title level={5}>智能编辑</Title>
              <Text type="secondary">
                自动识别教案各部分内容，支持AI辅助修改和优化
              </Text>
            </Card>
          </Col>
        </Row>
      </div>

      {/* 浮动设置按钮 */}
      <FloatButton
        icon={<SettingOutlined />}
        type="primary"
        tooltip="AI设置"
        onClick={() => navigate('/settings')}
        style={{ right: 24, bottom: 24 }}
      />
    </div>
  );
}

export default Home;
