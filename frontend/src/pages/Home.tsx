import { useNavigate } from 'react-router-dom';
import { Button, Card, Col, Row, Space, Tag, Typography } from 'antd';
import {
  AppstoreAddOutlined,
  ApartmentOutlined,
  BookOutlined,
  CloudDownloadOutlined,
  FilePptOutlined,
  FileTextOutlined,
  FormOutlined,
  HistoryOutlined,
  RightOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import type { ReactNode } from 'react';

const { Title, Paragraph, Text } = Typography;

const preparationCards: Array<{
  title: string;
  description: string;
  type: 'lesson_plan' | 'handout' | 'presentation';
  icon: ReactNode;
  color: string;
}> = [
  {
    title: '教案设计',
    description: '使用系统内置云林标准模板，生成规范、可直接归档的 Word 教案。',
    type: 'lesson_plan',
    icon: <FileTextOutlined />,
    color: '#176b52',
  },
  {
    title: '讲义制作',
    description: '将教学设计转为学生视角的学习目标、课堂学习单和巩固任务。',
    type: 'handout',
    icon: <FormOutlined />,
    color: '#2b7a78',
  },
  {
    title: 'PPT 制作',
    description: '按教学环节自动组织课堂演示文稿，重点、活动与作业前后一致。',
    type: 'presentation',
    icon: <FilePptOutlined />,
    color: '#b4533c',
  },
];

const supportingTools = [
  { title: '学期批量备课', icon: <AppstoreAddOutlined />, route: '/batch-generate' },
  { title: '批量下载', icon: <CloudDownloadOutlined />, route: '/batch-downloads' },
  { title: '备课记录', icon: <HistoryOutlined />, route: '/history' },
  { title: '教材管理', icon: <BookOutlined />, route: '/textbooks' },
  { title: '班级管理', icon: <TeamOutlined />, route: '/classes' },
  { title: '年级管理', icon: <ApartmentOutlined />, route: '/grades' },
  { title: '比赛专区', icon: <TrophyOutlined />, route: '/competition' },
  { title: '系统设置', icon: <SettingOutlined />, route: '/settings' },
];

function Home() {
  const navigate = useNavigate();

  return (
    <div style={{ maxWidth: 1240, margin: '0 auto', paddingBottom: 64 }}>
      <section
        style={{
          position: 'relative',
          overflow: 'hidden',
          borderRadius: 26,
          padding: '64px 56px',
          color: '#fff',
          background: 'linear-gradient(125deg, #0e332a 0%, #176b52 55%, #318268 100%)',
          boxShadow: '0 24px 60px rgba(20, 84, 66, 0.23)',
        }}
      >
        <div
          style={{
            position: 'absolute',
            width: 420,
            height: 420,
            borderRadius: '50%',
            right: -90,
            top: -180,
            background: 'rgba(167, 243, 208, 0.09)',
          }}
        />
        <Tag color="green" style={{ marginBottom: 20 }}>云林固定模板 · 校验通过后生成</Tag>
        <Title style={{ color: '#fff', fontSize: 46, margin: '0 0 16px', maxWidth: 760 }}>
          从一份教学设计，完成整套备课资料
        </Title>
        <Paragraph style={{ color: '#d6f5e8', fontSize: 18, lineHeight: 1.8, maxWidth: 720 }}>
          教案、学生讲义、课堂 PPT、授课计划与实验计划共享课程分析和教学逻辑。无需上传或在线编辑模板，专注课程内容本身。
        </Paragraph>
        <Space size="middle" wrap>
          <Button
            type="primary"
            size="large"
            icon={<ThunderboltOutlined />}
            onClick={() => navigate('/prepare')}
            style={{ height: 48, background: '#fff', color: '#176b52', border: 0, fontWeight: 600 }}
          >
            开始备课
          </Button>
          <Space style={{ color: '#b9ead5' }}>
            <SafetyCertificateOutlined />
            <span>内置资源只读保护</span>
          </Space>
        </Space>
      </section>

      <section style={{ marginTop: 38 }}>
        <Space direction="vertical" size={4} style={{ marginBottom: 20 }}>
          <Title level={3} style={{ margin: 0 }}>备课成果</Title>
          <Text type="secondary">可单独制作，也可一次选择多项生成完整备课包。</Text>
        </Space>
        <Row gutter={[20, 20]}>
          {preparationCards.map((item) => (
            <Col xs={24} md={8} key={item.type}>
              <Card
                hoverable
                onClick={() => navigate(`/prepare?type=${item.type}`)}
                style={{ height: '100%', borderRadius: 18, borderColor: '#e2ebe7' }}
                styles={{ body: { padding: 26 } }}
              >
                <div
                  style={{
                    width: 54,
                    height: 54,
                    display: 'grid',
                    placeItems: 'center',
                    borderRadius: 14,
                    background: `${item.color}14`,
                    color: item.color,
                    fontSize: 25,
                    marginBottom: 18,
                  }}
                >
                  {item.icon}
                </div>
                <Title level={4}>{item.title}</Title>
                <Paragraph type="secondary" style={{ minHeight: 66 }}>{item.description}</Paragraph>
                <Text style={{ color: item.color }}>
                  立即制作 <RightOutlined style={{ fontSize: 11 }} />
                </Text>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      <section style={{ marginTop: 42 }}>
        <Title level={3}>教学资源与管理</Title>
        <Row gutter={[14, 14]}>
          {supportingTools.map((item) => (
            <Col xs={12} sm={8} md={6} key={item.route}>
              <Card
                hoverable
                size="small"
                onClick={() => navigate(item.route)}
                style={{ borderRadius: 12 }}
              >
                <Space>
                  <span style={{ color: '#176b52', fontSize: 18 }}>{item.icon}</span>
                  <Text strong>{item.title}</Text>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      </section>
    </div>
  );
}

export default Home;
