/**
 * Home page - Main landing page with research-style design
 */
import { useNavigate } from 'react-router-dom';
import { Card, Row, Col, Typography, Space, Button, FloatButton, Statistic, Progress } from 'antd';
import {
  FileTextOutlined,
  EditOutlined,
  FolderOutlined,
  HistoryOutlined,
  SettingOutlined,
  AppstoreAddOutlined,
  TeamOutlined,
  RocketOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  RobotOutlined,
  ExperimentOutlined,
  DatabaseOutlined,
  LineChartOutlined,
  InboxOutlined,
  BookOutlined,
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;

// Scientific gradient colors - Academic Blue & Green theme
const gradients = {
  blue: 'linear-gradient(135deg, #0d9488 0%, #0f766e 100%)',
  cyan: 'linear-gradient(135deg, #0891b2 0%, #0e7490 100%)',
  green: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
  orange: 'linear-gradient(135deg, #ea580c 0%, #c2410c 100%)',
  teal: 'linear-gradient(135deg, #14b8a6 0%, #0d9488 100%)',
  lime: 'linear-gradient(135deg, #65a30d 0%, #4d7c0f 100%)',
  dark: 'linear-gradient(135deg, #1e3a5f 0%, #172554 100%)',
};

function Home() {
  const navigate = useNavigate();

  const features = [
    {
      icon: <FileTextOutlined />,
      title: '新建教案',
      description: '选择模板，AI自动生成完整教案内容',
      gradient: gradients.teal,
      route: '/new',
    },
    {
      icon: <AppstoreAddOutlined />,
      title: '批量生成',
      description: '一次生成整个学期的教案，支持AI自动拆分章节',
      gradient: gradients.blue,
      route: '/batch-generate',
    },
    {
      icon: <InboxOutlined />,
      title: '草稿箱',
      description: '管理预生成的教案草稿，随时编辑和导出',
      gradient: gradients.dark,
      route: '/cached-lesson-plans',
    },
    {
      icon: <EditOutlined />,
      title: '编辑旧教案',
      description: '上传已有教案，智能识别并AI辅助修改',
      gradient: gradients.green,
      route: '/edit',
    },
    {
      icon: <FolderOutlined />,
      title: '模板管理',
      description: '上传、管理和编辑教案模板',
      gradient: gradients.cyan,
      route: '/templates',
    },
    {
      icon: <HistoryOutlined />,
      title: '历史记录',
      description: '查看和管理生成的教案记录',
      gradient: gradients.lime,
      route: '/history',
    },
    {
      icon: <TeamOutlined />,
      title: '班级管理',
      description: '管理授课班级信息',
      gradient: gradients.orange,
      route: '/classes',
    },
    {
      icon: <BookOutlined />,
      title: '教材管理',
      description: '管理教材信息，AI生成章节大纲',
      gradient: gradients.dark,
      route: '/textbooks',
    },
  ];

  const stats = [
    {
      title: 'AI生成',
      value: 96,
      suffix: '%',
      prefix: <RobotOutlined />,
      color: '#0d9488',
    },
    {
      title: '效率提升',
      value: 10,
      suffix: '倍',
      prefix: <RocketOutlined />,
      color: '#059669',
    },
    {
      title: '平均耗时',
      value: 30,
      suffix: '秒',
      prefix: <ThunderboltOutlined />,
      color: '#ea580c',
    },
    {
      title: '模板支持',
      value: 100,
      suffix: '%',
      prefix: <CheckCircleOutlined />,
      color: '#0891b2',
    },
  ];

  const capabilities = [
    {
      icon: <ExperimentOutlined />,
      title: '智能教学设计',
      description: '基于认知科学和教育学原理，AI分析课程目标自动生成符合教学规律的教学方案',
      items: ['布鲁姆分类法', '认知负荷理论', '建构主义学习'],
    },
    {
      icon: <DatabaseOutlined />,
      title: '知识图谱引擎',
      description: '内置学科知识图谱，确保教学内容的科学性和系统性',
      items: ['知识点关联', '难度梯度分析', '前置知识检测'],
    },
    {
      icon: <LineChartOutlined />,
      title: '数据分析',
      description: '追踪教学效果，持续优化教案质量',
      items: ['学情分析', '教学评估', '改进建议'],
    },
  ];

  return (
    <div style={{
      background: '#f8fafc',
      minHeight: '100vh',
      paddingBottom: 80,
    }}>
      {/* Hero Section */}
      <div style={{
        background: gradients.dark,
        padding: '80px 20px',
        textAlign: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Background pattern */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundImage: `
            radial-gradient(circle at 20% 50%, rgba(13, 148, 136, 0.15) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(8, 145, 178, 0.15) 0%, transparent 50%),
            radial-gradient(circle at 40% 20%, rgba(5, 150, 105, 0.12) 0%, transparent 50%)
          `,
        }} />

        <div style={{ position: 'relative', zIndex: 1, maxWidth: 900, margin: '0 auto' }}>
          <div style={{
            display: 'inline-block',
            padding: '8px 24px',
            background: 'rgba(13, 148, 136, 0.2)',
            borderRadius: 24,
            marginBottom: 24,
            border: '1px solid rgba(13, 148, 136, 0.3)',
          }}>
            <Text style={{ color: '#5eead4', fontSize: 14, fontWeight: 500 }}>
              <RocketOutlined style={{ marginRight: 8 }} />
              AI驱动的智能教案生成系统
            </Text>
          </div>

          <Title style={{
            color: '#ffffff',
            fontSize: 48,
            fontWeight: 700,
            marginBottom: 24,
            background: 'linear-gradient(135deg, #ffffff 0%, #94a3b8 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            智能教案助手
          </Title>

          <Paragraph style={{
            color: '#94a3b8',
            fontSize: 20,
            maxWidth: 600,
            margin: '0 auto 40px',
            lineHeight: 1.8,
          }}>
            基于深度学习和教育科学原理，为教师提供专业的教案生成、编辑与管理解决方案
          </Paragraph>

          <Space size="middle">
            <Button
              type="primary"
              size="large"
              icon={<AppstoreAddOutlined />}
              onClick={() => navigate('/batch-generate')}
              style={{
                height: 50,
                padding: '0 32px',
                fontSize: 16,
                borderRadius: 8,
                background: 'linear-gradient(135deg, #0d9488 0%, #0891b2 100%)',
                border: 'none',
                boxShadow: '0 4px 20px rgba(13, 148, 136, 0.4)',
              }}
            >
              开始批量生成
            </Button>
            <Button
              size="large"
              icon={<FileTextOutlined />}
              onClick={() => navigate('/new')}
              style={{
                height: 50,
                padding: '0 32px',
                fontSize: 16,
                borderRadius: 8,
                background: 'rgba(255, 255, 255, 0.1)',
                borderColor: 'rgba(255, 255, 255, 0.2)',
                color: '#ffffff',
              }}
            >
              新建单个教案
            </Button>
          </Space>
        </div>
      </div>

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 20px' }}>
        {/* Statistics Section */}
        <div style={{ marginTop: -48, position: 'relative', zIndex: 10 }}>
          <Row gutter={[24, 24]}>
            {stats.map((stat, index) => (
              <Col xs={12} sm={6} key={index}>
                <Card
                  style={{
                    borderRadius: 16,
                    boxShadow: '0 4px 24px rgba(0, 0, 0, 0.08)',
                    border: 'none',
                    textAlign: 'center',
                  }}
                  bodyStyle={{ padding: '24px 16px' }}
                >
                  <div style={{
                    width: 48,
                    height: 48,
                    borderRadius: 12,
                    background: `${stat.color}15`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 12px',
                  }}>
                    <span style={{ fontSize: 24, color: stat.color }}>{stat.prefix}</span>
                  </div>
                  <Statistic
                    title={<Text type="secondary" style={{ fontSize: 13 }}>{stat.title}</Text>}
                    value={stat.value}
                    suffix={stat.suffix}
                    valueStyle={{
                      color: '#1e293b',
                      fontSize: 28,
                      fontWeight: 700,
                    }}
                  />
                </Card>
              </Col>
            ))}
          </Row>
        </div>

        {/* Main Features Section */}
        <div style={{ marginTop: 64 }}>
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <Title level={3} style={{ color: '#1e293b', marginBottom: 12 }}>
              核心功能
            </Title>
            <Text type="secondary" style={{ fontSize: 16 }}>
              全方位覆盖教案创作流程，提升教学效率
            </Text>
          </div>

          <Row gutter={[24, 24]}>
            {features.map((feature, index) => (
              <Col xs={24} sm={12} lg={8} key={index}>
                <Card
                  hoverable
                  onClick={() => navigate(feature.route)}
                  style={{
                    height: '100%',
                    borderRadius: 16,
                    border: 'none',
                    boxShadow: '0 2px 16px rgba(0, 0, 0, 0.06)',
                    transition: 'all 0.3s ease',
                  }}
                  bodyStyle={{ padding: '32px 24px' }}
                  styles={{
                    body: { padding: '32px 24px' }
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-4px)';
                    e.currentTarget.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.12)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 2px 16px rgba(0, 0, 0, 0.06)';
                  }}
                >
                  <div style={{
                    width: 64,
                    height: 64,
                    borderRadius: 16,
                    background: feature.gradient,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: 20,
                  }}>
                    <span style={{ fontSize: 28, color: '#ffffff' }}>{feature.icon}</span>
                  </div>
                  <Title level={4} style={{ marginBottom: 12, color: '#1e293b' }}>
                    {feature.title}
                  </Title>
                  <Paragraph type="secondary" style={{ marginBottom: 0, fontSize: 14, lineHeight: 1.6 }}>
                    {feature.description}
                  </Paragraph>
                </Card>
              </Col>
            ))}
          </Row>
        </div>

        {/* Technical Capabilities Section */}
        <div style={{ marginTop: 80 }}>
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <Title level={3} style={{ color: '#1e293b', marginBottom: 12 }}>
              技术能力
            </Title>
            <Text type="secondary" style={{ fontSize: 16 }}>
              融合前沿AI技术与教育科学研究
            </Text>
          </div>

          <Row gutter={[32, 32]}>
            {capabilities.map((cap, index) => (
              <Col xs={24} md={8} key={index}>
                <Card
                  style={{
                    height: '100%',
                    borderRadius: 16,
                    border: 'none',
                    boxShadow: '0 2px 16px rgba(0, 0, 0, 0.06)',
                  }}
                  bodyStyle={{ padding: '32px 24px' }}
                >
                  <div style={{
                    width: 56,
                    height: 56,
                    borderRadius: 14,
                    background: index === 0 ? gradients.teal : index === 1 ? gradients.blue : gradients.cyan,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: 20,
                  }}>
                    <span style={{ fontSize: 24, color: '#ffffff' }}>{cap.icon}</span>
                  </div>
                  <Title level={5} style={{ marginBottom: 12, color: '#1e293b' }}>
                    {cap.title}
                  </Title>
                  <Paragraph type="secondary" style={{ marginBottom: 20, fontSize: 14, lineHeight: 1.6 }}>
                    {cap.description}
                  </Paragraph>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {cap.items.map((item, i) => (
                      <span
                        key={i}
                        style={{
                          padding: '4px 12px',
                          background: '#f1f5f9',
                          borderRadius: 6,
                          fontSize: 12,
                          color: '#64748b',
                        }}
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </div>

        {/* Workflow Section */}
        <div style={{ marginTop: 80 }}>
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <Title level={3} style={{ color: '#1e293b', marginBottom: 12 }}>
              工作流程
            </Title>
            <Text type="secondary" style={{ fontSize: 16 }}>
              简单四步，完成专业教案创作
            </Text>
          </div>

          <Card
            style={{
              borderRadius: 20,
              border: 'none',
              boxShadow: '0 4px 32px rgba(0, 0, 0, 0.08)',
              background: '#ffffff',
            }}
            bodyStyle={{ padding: '48px 32px' }}
          >
            <Row gutter={[32, 32]}>
              {[
                { step: '01', title: '选择模板', desc: '从模板库中选择或上传自定义教案模板' },
                { step: '02', title: '填写信息', desc: '输入课程名称、学科、年级等基本信息' },
                { step: '03', title: 'AI生成', desc: 'AI自动分析并生成专业的教案内容' },
                { step: '04', title: '导出使用', desc: '下载Word格式的教案文档，直接使用' },
              ].map((item, index) => (
                <Col xs={12} sm={6} key={index}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{
                      width: 56,
                      height: 56,
                      borderRadius: '50%',
                      background: index === 3 ? gradients.green : 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 16px',
                      fontSize: 18,
                      fontWeight: 700,
                      color: index === 3 ? '#ffffff' : '#64748b',
                    }}>
                      {item.step}
                    </div>
                    <Title level={5} style={{ marginBottom: 8, color: '#1e293b' }}>
                      {item.title}
                    </Title>
                    <Text type="secondary" style={{ fontSize: 13 }}>
                      {item.desc}
                    </Text>
                    {index < 3 && (
                      <div style={{
                        position: 'absolute',
                        right: -16,
                        top: 28,
                        color: '#cbd5e1',
                        fontSize: 20,
                        display: { xs: 'none', sm: 'block' },
                      }} />
                    )}
                  </div>
                </Col>
              ))}
            </Row>
          </Card>
        </div>

        {/* CTA Section */}
        <div style={{
          marginTop: 80,
          padding: 48,
          borderRadius: 24,
          background: gradients.teal,
          textAlign: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}>
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundImage: 'radial-gradient(circle at 30% 20%, rgba(255,255,255,0.1) 0%, transparent 50%)',
          }} />

          <div style={{ position: 'relative', zIndex: 1 }}>
            <Title style={{
              color: '#ffffff',
              fontSize: 32,
              marginBottom: 16,
            }}>
              开始您的智能教案创作之旅
            </Title>
            <Paragraph style={{
              color: 'rgba(255, 255, 255, 0.9)',
              fontSize: 16,
              marginBottom: 32,
              maxWidth: 500,
              margin: '0 auto 32px',
            }}>
              立即体验AI驱动的教案生成系统，让备课变得更加高效
            </Paragraph>
            <Button
              type="primary"
              size="large"
              icon={<RocketOutlined />}
              onClick={() => navigate('/new')}
              style={{
                height: 52,
                padding: '0 40px',
                fontSize: 16,
                borderRadius: 8,
                background: '#ffffff',
                color: '#0d9488',
                border: 'none',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
              }}
            >
              立即开始
            </Button>
          </div>
        </div>
      </div>

      {/* Floating Settings Button */}
      <FloatButton.Group
        shape="circle"
        style={{ right: 24, bottom: 24 }}
      >
        <FloatButton
          icon={<SettingOutlined />}
          tooltip="AI设置"
          onClick={() => navigate('/settings')}
        />
      </FloatButton.Group>
    </div>
  );
}

export default Home;
