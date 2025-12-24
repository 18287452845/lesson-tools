/**
 * Lesson Plan Detail page - View and export a generated lesson plan
 */
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Button,
  Card,
  Descriptions,
  Typography,
  Space,
  Spin,
  Alert,
  Tag,
  Divider,
  message,
  Modal,
} from 'antd';
import {
  ArrowLeftOutlined,
  DownloadOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { generateApi } from '@/services/api';

const { Title, Paragraph, Text } = Typography;

interface LessonPlanData {
  id: string;
  title: string;
  subject: string;
  grade: string;
  topic: string;
  status: string;
  created_at: string;
  input: any;
  generated_content: any;
  output_file_path?: string;
}

function LessonPlanDetail() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const lessonPlanId = searchParams.get('id');

  const [lessonPlan, setLessonPlan] = useState<LessonPlanData | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (lessonPlanId) {
      fetchLessonPlan();
    } else {
      setError('教案ID不存在');
    }
  }, [lessonPlanId]);

  const fetchLessonPlan = async () => {
    if (!lessonPlanId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await generateApi.getLessonPlan(lessonPlanId);
      setLessonPlan(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取教案详情失败');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!lessonPlanId) return;
    setExporting(true);
    try {
      const blob = await generateApi.exportLessonPlan(lessonPlanId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `教案_${lessonPlan?.topic || '未命名'}_${Date.now()}.docx`;
      link.click();
      URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch (err) {
      message.error('导出失败：' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setExporting(false);
    }
  };

  const handleDelete = () => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个教案吗？删除后无法恢复。',
      okText: '确定',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        if (!lessonPlanId) return;
        try {
          await generateApi.deleteLessonPlan(lessonPlanId);
          message.success('删除成功');
          navigate('/history');
        } catch (err) {
          message.error('删除失败');
        }
      },
    });
  };

  if (loading) {
    return (
      <div style={{ maxWidth: 1200, margin: '0 auto', textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ marginBottom: 24 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/history')}>
            返回历史记录
          </Button>
        </div>
        <Alert type="error" message={error} showIcon />
      </div>
    );
  }

  if (!lessonPlan) {
    return null;
  }

  const content = lessonPlan.generated_content || {};

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/history')}>
          返回历史记录
        </Button>
      </div>

      <Card>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Header with title and actions */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <Title level={2}>{lessonPlan.title}</Title>
              <Space>
                <Tag color="blue">{lessonPlan.subject}</Tag>
                <Tag color="green">{lessonPlan.grade}</Tag>
                <Tag>{lessonPlan.status === 'generated' ? '已生成' : lessonPlan.status}</Tag>
              </Space>
            </div>
            <Space>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                onClick={handleExport}
                loading={exporting}
              >
                导出Word
              </Button>
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={handleDelete}
              >
                删除
              </Button>
            </Space>
          </div>

          <Divider />

          {/* Basic Info */}
          <Descriptions title="基本信息" column={2} bordered>
            <Descriptions.Item label="学科">{lessonPlan.subject}</Descriptions.Item>
            <Descriptions.Item label="年级">{lessonPlan.grade}</Descriptions.Item>
            <Descriptions.Item label="课题">{lessonPlan.topic}</Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {new Date(lessonPlan.created_at).toLocaleString()}
            </Descriptions.Item>
          </Descriptions>

          {/* Generated Content */}
          <div>
            <Title level={4}>教案内容</Title>

            {/* Teaching Objectives */}
            {content.teaching_goals && (
              <Card title="教学目标" size="small" style={{ marginBottom: 16 }}>
                {typeof content.teaching_goals === 'string' ? (
                  <Paragraph>{content.teaching_goals}</Paragraph>
                ) : (
                  <>
                    {content.teaching_goals.knowledge && (
                      <div style={{ marginBottom: 12 }}>
                        <Text strong>知识目标：</Text>
                        <Paragraph>{content.teaching_goals.knowledge}</Paragraph>
                      </div>
                    )}
                    {content.teaching_goals.ability && (
                      <div style={{ marginBottom: 12 }}>
                        <Text strong>能力目标：</Text>
                        <Paragraph>{content.teaching_goals.ability}</Paragraph>
                      </div>
                    )}
                    {content.teaching_goals.quality && (
                      <div>
                        <Text strong>素质目标：</Text>
                        <Paragraph>{content.teaching_goals.quality}</Paragraph>
                      </div>
                    )}
                  </>
                )}
              </Card>
            )}

            {/* Key Points */}
            {content.key_points && (
              <Card title="教学重点" size="small" style={{ marginBottom: 16 }}>
                <Paragraph>{content.key_points}</Paragraph>
              </Card>
            )}

            {/* Difficult Points */}
            {content.difficult_points && (
              <Card title="教学难点" size="small" style={{ marginBottom: 16 }}>
                <Paragraph>{content.difficult_points}</Paragraph>
              </Card>
            )}

            {/* Teaching Methods */}
            {content.teaching_methods && (
              <Card title="教学方法" size="small" style={{ marginBottom: 16 }}>
                <Paragraph>{content.teaching_methods}</Paragraph>
              </Card>
            )}

            {/* Teaching Tools */}
            {content.teaching_tools && (
              <Card title="教具准备" size="small" style={{ marginBottom: 16 }}>
                <Paragraph>{content.teaching_tools}</Paragraph>
              </Card>
            )}

            {/* Teaching Process */}
            {content.teaching_steps && (
              <Card title="教学过程" size="small" style={{ marginBottom: 16 }}>
                {Array.isArray(content.teaching_steps) ? (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {content.teaching_steps.map((step: any, index: number) => (
                      <Card key={index} size="small" type="inner">
                        {typeof step === 'string' || typeof step === 'number' ? (
                          <Paragraph>{step}</Paragraph>
                        ) : step.title || step.stage ? (
                          <>
                            <Title level={5}>{step.title || step.stage || `步骤 ${index + 1}`}</Title>
                            {step.duration && <Text type="secondary">时长：{step.duration}</Text>}
                            {step.content && <Paragraph style={{ marginTop: 8 }}>{step.content}</Paragraph>}
                            {step.teacher_activity && (
                              <Paragraph><Text strong>教师活动：</Text>{step.teacher_activity}</Paragraph>
                            )}
                            {step.student_activity && (
                              <Paragraph><Text strong>学生活动：</Text>{step.student_activity}</Paragraph>
                            )}
                            {step.design_intent && (
                              <Paragraph><Text strong>设计意图：</Text>{step.design_intent}</Paragraph>
                            )}
                          </>
                        ) : (
                          <Paragraph>{JSON.stringify(step)}</Paragraph>
                        )}
                      </Card>
                    ))}
                  </Space>
                ) : (
                  <Paragraph>{content.teaching_steps}</Paragraph>
                )}
              </Card>
            )}

            {/* Homework */}
            {content.homework && (
              <Card title="作业布置" size="small" style={{ marginBottom: 16 }}>
                {typeof content.homework === 'string' ? (
                  <Paragraph>{content.homework}</Paragraph>
                ) : (
                  <>
                    {content.homework.required && (
                      <div style={{ marginBottom: 8 }}>
                        <Text strong>必做题：</Text>
                        <Paragraph>{content.homework.required}</Paragraph>
                      </div>
                    )}
                    {content.homework.optional && (
                      <div>
                        <Text strong>选做题：</Text>
                        <Paragraph>{content.homework.optional}</Paragraph>
                      </div>
                    )}
                  </>
                )}
              </Card>
            )}

            {/* Blackboard Design */}
            {content.blackboard_design && (
              <Card title="板书设计" size="small" style={{ marginBottom: 16 }}>
                <Paragraph>{content.blackboard_design}</Paragraph>
              </Card>
            )}

            {/* Reflection */}
            {content.reflection && (
              <Card title="教学反思" size="small" style={{ marginBottom: 16 }}>
                <Paragraph>{content.reflection}</Paragraph>
              </Card>
            )}

            {/* Additional fields */}
            {content.student_analysis && (
              <Card title="学情分析" size="small" style={{ marginBottom: 16 }}>
                <Paragraph>{content.student_analysis}</Paragraph>
              </Card>
            )}

            {content.textbook_analysis && (
              <Card title="教材分析" size="small" style={{ marginBottom: 16 }}>
                <Paragraph>{content.textbook_analysis}</Paragraph>
              </Card>
            )}
          </div>
        </Space>
      </Card>
    </div>
  );
}

export default LessonPlanDetail;
