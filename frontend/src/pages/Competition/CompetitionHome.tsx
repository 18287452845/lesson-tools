/**
 * Competition Home - 比赛专区入口页
 *
 * Layout:
 *   - Hero header
 *   - Two big cards: 创建参赛教案 / 创建实施报告
 *   - Recent projects list with quick actions
 */
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Typography,
  Button,
  Empty,
  Tag,
  Space,
  Spin,
  message,
  Popconfirm,
} from 'antd';
import {
  TrophyOutlined,
  FileTextOutlined,
  AuditOutlined,
  PlusOutlined,
  EyeOutlined,
  DeleteOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { useCompetitionStore } from '@/stores/competitionStore';

const { Title, Text, Paragraph } = Typography;

const heroGradient = 'linear-gradient(135deg, #ea580c 0%, #c2410c 100%)';
const lessonPlanGradient = 'linear-gradient(135deg, #0d9488 0%, #0f766e 100%)';
const reportGradient = 'linear-gradient(135deg, #0891b2 0%, #0e7490 100%)';

function CompetitionHome() {
  const navigate = useNavigate();
  const { projects, loadingProjects, fetchProjects, deleteProject } = useCompetitionStore();

  useEffect(() => {
    fetchProjects().catch(() => {
      message.error('加载项目列表失败');
    });
  }, [fetchProjects]);

  const handleDelete = async (projectId: string) => {
    try {
      await deleteProject(projectId);
      message.success('项目已删除');
    } catch (err) {
      message.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  return (
    <div style={{ background: '#f8fafc', minHeight: '100vh', paddingBottom: 80 }}>
      {/* Hero */}
      <div
        style={{
          background: heroGradient,
          padding: '56px 20px 80px',
          textAlign: 'center',
          color: '#fff',
          position: 'relative',
        }}
      >
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/')}
          style={{
            position: 'absolute',
            left: 24,
            top: 24,
            background: 'rgba(255,255,255,0.15)',
            color: '#fff',
            border: 'none',
          }}
        >
          返回首页
        </Button>
        <div
          style={{
            display: 'inline-block',
            padding: '8px 24px',
            background: 'rgba(255,255,255,0.18)',
            borderRadius: 24,
            marginBottom: 16,
          }}
        >
          <TrophyOutlined style={{ marginRight: 8 }} />
          教学能力比赛专区
        </div>
        <Title style={{ color: '#fff', fontSize: 40, marginBottom: 16 }}>
          参赛教案与实施报告生成
        </Title>
        <Paragraph
          style={{ color: 'rgba(255,255,255,0.9)', fontSize: 16, maxWidth: 700, margin: '0 auto' }}
        >
          AI 一键生成符合国赛/省赛规范的参赛教案与教学实施报告,涵盖整体设计、多任务详细教案、
          实施过程、学习效果与反思改进
        </Paragraph>
      </div>

      <div style={{ maxWidth: 1200, margin: '-40px auto 0', padding: '0 20px' }}>
        {/* Action Cards */}
        <Row gutter={[24, 24]}>
          <Col xs={24} md={12}>
            <Card
              hoverable
              onClick={() => navigate('/competition/new?type=lesson_plan')}
              style={{
                borderRadius: 16,
                border: 'none',
                boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
                cursor: 'pointer',
              }}
              styles={{ body: { padding: 32 } }}
            >
              <div
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: 16,
                  background: lessonPlanGradient,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: 24,
                }}
              >
                <FileTextOutlined style={{ fontSize: 32, color: '#fff' }} />
              </div>
              <Title level={3} style={{ marginBottom: 8 }}>
                生成参赛教案
              </Title>
              <Paragraph type="secondary" style={{ fontSize: 14 }}>
                自动生成包含整体设计与多个详细教案的完整参赛文档,涵盖课前/课中/课后全流程,
                融合岗课赛证理念
              </Paragraph>
              <Button type="primary" icon={<PlusOutlined />} size="large">
                创建项目
              </Button>
            </Card>
          </Col>

          <Col xs={24} md={12}>
            <Card
              hoverable
              onClick={() => navigate('/competition/new?type=report')}
              style={{
                borderRadius: 16,
                border: 'none',
                boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
                cursor: 'pointer',
              }}
              styles={{ body: { padding: 32 } }}
            >
              <div
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: 16,
                  background: reportGradient,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: 24,
                }}
              >
                <AuditOutlined style={{ fontSize: 32, color: '#fff' }} />
              </div>
              <Title level={3} style={{ marginBottom: 8 }}>
                生成实施报告
              </Title>
              <Paragraph type="secondary" style={{ fontSize: 14 }}>
                生成结构完整的教学实施报告,包含整体设计、实施过程、学习效果、反思改进,
                可关联已生成的参赛教案
              </Paragraph>
              <Button type="primary" icon={<PlusOutlined />} size="large">
                创建项目
              </Button>
            </Card>
          </Col>
        </Row>

        {/* Recent Projects */}
        <div style={{ marginTop: 64 }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 24,
            }}
          >
            <Title level={3} style={{ margin: 0 }}>
              我的比赛项目
            </Title>
          </div>

          {loadingProjects ? (
            <div style={{ textAlign: 'center', padding: 60 }}>
              <Spin size="large" />
            </div>
          ) : projects.length === 0 ? (
            <Card style={{ borderRadius: 12, border: 'none' }}>
              <Empty description="还没有比赛项目,点击上方卡片创建" />
            </Card>
          ) : (
            <Row gutter={[16, 16]}>
              {projects.map((project) => (
                <Col xs={24} md={12} lg={8} key={project.id}>
                  <Card
                    hoverable
                    style={{ borderRadius: 12, border: 'none' }}
                    styles={{ body: { padding: 20 } }}
                    onClick={() => navigate(`/competition/${project.id}`)}
                  >
                    <Title level={5} style={{ marginBottom: 8 }}>
                      {project.name}
                    </Title>
                    <Space size={4} wrap style={{ marginBottom: 12 }}>
                      {project.competition_year && (
                        <Tag color="orange">{project.competition_year}</Tag>
                      )}
                      {project.competition_region && (
                        <Tag color="cyan">{project.competition_region}</Tag>
                      )}
                      {project.group_name && <Tag color="blue">{project.group_name}</Tag>}
                    </Space>
                    <Text type="secondary" style={{ display: 'block', fontSize: 12, marginBottom: 12 }}>
                      {project.course_name || '未设置课程'} · {project.total_hours} 学时
                    </Text>

                    <Space>
                      <Button
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/competition/${project.id}`);
                        }}
                      >
                        查看
                      </Button>
                      <Popconfirm
                        title="确认删除此项目?"
                        description="项目及其所有生成结果将被删除"
                        onConfirm={(e) => {
                          e?.stopPropagation();
                          handleDelete(project.id);
                        }}
                        okText="确认"
                        cancelText="取消"
                      >
                        <Button
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={(e) => e.stopPropagation()}
                        >
                          删除
                        </Button>
                      </Popconfirm>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </div>
      </div>
    </div>
  );
}

export default CompetitionHome;
