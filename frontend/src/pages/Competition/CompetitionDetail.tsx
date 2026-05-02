/**
 * Competition Detail - 项目详情 + 输出管理
 *
 * Shows:
 *   - Project info
 *   - List of outputs with status, progress, download/delete actions
 *   - Buttons to start new lesson_plan / report generation
 *
 * URL params:
 *   - /competition/:projectId
 *   - ?output=<output_id>  (auto-subscribe to that output's progress on mount)
 */
import { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  Card,
  Button,
  Space,
  Tag,
  Typography,
  Row,
  Col,
  Progress,
  Empty,
  Spin,
  message,
  Descriptions,
  Popconfirm,
  Modal,
  Input,
} from 'antd';
import {
  ArrowLeftOutlined,
  DownloadOutlined,
  DeleteOutlined,
  ReloadOutlined,
  FileTextOutlined,
  AuditOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { useCompetitionStore } from '@/stores/competitionStore';
import type { CompetitionOutput, CompetitionOutputStatus } from '@/types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const STATUS_LABELS: Record<CompetitionOutputStatus, { color: string; text: string }> = {
  pending: { color: 'default', text: '等待中' },
  processing: { color: 'processing', text: '生成中' },
  completed: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
  cancelled: { color: 'warning', text: '已取消' },
};

function CompetitionDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialOutputId = searchParams.get('output');

  const {
    currentProject,
    outputs,
    loadingOutputs,
    fetchProject,
    fetchProjectOutputs,
    subscribeOutputProgress,
    deleteOutput,
    downloadOutput,
    generateLessonPlan,
    generateReport,
  } = useCompetitionStore();

  const [generateModalOpen, setGenerateModalOpen] = useState<'lesson_plan' | 'report' | null>(null);
  const [topicsInput, setTopicsInput] = useState('');
  const [additionalRequirements, setAdditionalRequirements] = useState('');
  const [relatedOutputId, setRelatedOutputId] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Load project + outputs
  useEffect(() => {
    if (!projectId) return;
    fetchProject(projectId).catch(() => message.error('加载项目失败'));
    fetchProjectOutputs(projectId).catch(() => {});
  }, [projectId, fetchProject, fetchProjectOutputs]);

  // Auto-subscribe to in-progress output if URL has ?output=
  useEffect(() => {
    if (!initialOutputId) return;
    const cleanup = subscribeOutputProgress(initialOutputId);
    return cleanup;
  }, [initialOutputId, subscribeOutputProgress]);

  // Periodic refresh of outputs while any is in-progress
  useEffect(() => {
    if (!projectId) return;
    const hasInProgress = outputs.some(
      (o) => o.status === 'pending' || o.status === 'processing'
    );
    if (!hasInProgress) return;

    const timer = setInterval(() => {
      fetchProjectOutputs(projectId).catch(() => {});
    }, 4000);
    return () => clearInterval(timer);
  }, [projectId, outputs, fetchProjectOutputs]);

  const handleStartGeneration = async () => {
    if (!projectId || !generateModalOpen) return;
    setSubmitting(true);
    try {
      if (generateModalOpen === 'lesson_plan') {
        await generateLessonPlan(projectId, {
          topics_input: topicsInput || undefined,
          additional_requirements: additionalRequirements || undefined,
        });
      } else {
        await generateReport(projectId, {
          related_output_id: relatedOutputId || undefined,
          additional_requirements: additionalRequirements || undefined,
        });
      }
      message.success('已启动生成');
      setGenerateModalOpen(null);
      setTopicsInput('');
      setAdditionalRequirements('');
      setRelatedOutputId('');
      await fetchProjectOutputs(projectId);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '启动失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteOutput = async (outputId: string) => {
    try {
      await deleteOutput(outputId);
      message.success('已删除');
    } catch (err) {
      message.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  const copyOutputId = (outputId: string) => {
    navigator.clipboard?.writeText(outputId).then(
      () => message.success('已复制 output_id'),
      () => message.error('复制失败')
    );
  };

  if (!currentProject) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ background: '#f8fafc', minHeight: '100vh', padding: '24px 0 80px' }}>
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '0 20px' }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/competition')}
          style={{ marginBottom: 16 }}
        >
          返回比赛专区
        </Button>

        {/* Project Info */}
        <Card style={{ borderRadius: 16, border: 'none', boxShadow: '0 2px 12px rgba(0,0,0,0.05)', marginBottom: 24 }}>
          <Title level={3} style={{ marginBottom: 8 }}>
            {currentProject.name}
          </Title>
          <Space size={4} wrap style={{ marginBottom: 16 }}>
            {currentProject.competition_year && (
              <Tag color="orange">{currentProject.competition_year}</Tag>
            )}
            {currentProject.competition_region && (
              <Tag color="cyan">{currentProject.competition_region}</Tag>
            )}
            {currentProject.competition_level && (
              <Tag color="gold">{currentProject.competition_level}</Tag>
            )}
            {currentProject.group_name && <Tag color="blue">{currentProject.group_name}</Tag>}
          </Space>

          <Descriptions size="small" column={2} bordered>
            <Descriptions.Item label="作品名称">
              {currentProject.work_name || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="课程名称">
              {currentProject.course_name || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="专业大类">
              {currentProject.major_category || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="专业名称">
              {currentProject.major_name || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="授课班级">
              {currentProject.class_name || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="授课地点">
              {currentProject.location || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="总学时" span={2}>
              {currentProject.total_hours} 学时(单教案 {currentProject.hours_per_lesson} 学时)
            </Descriptions.Item>
          </Descriptions>
        </Card>

        {/* Action Buttons */}
        <Card style={{ borderRadius: 16, border: 'none', boxShadow: '0 2px 12px rgba(0,0,0,0.05)', marginBottom: 24 }}>
          <Space size={12} wrap>
            <Button
              type="primary"
              icon={<FileTextOutlined />}
              onClick={() => setGenerateModalOpen('lesson_plan')}
            >
              生成新参赛教案
            </Button>
            <Button
              type="primary"
              icon={<AuditOutlined />}
              onClick={() => setGenerateModalOpen('report')}
              style={{ background: '#0891b2', borderColor: '#0891b2' }}
            >
              生成新实施报告
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => projectId && fetchProjectOutputs(projectId)}
            >
              刷新
            </Button>
          </Space>
        </Card>

        {/* Outputs List */}
        <Title level={4}>生成历史</Title>
        {loadingOutputs ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin />
          </div>
        ) : outputs.length === 0 ? (
          <Card style={{ borderRadius: 12, border: 'none' }}>
            <Empty description="还没有生成结果,点击上方按钮开始生成" />
          </Card>
        ) : (
          <Row gutter={[16, 16]}>
            {outputs.map((output) => (
              <Col xs={24} key={output.id}>
                <OutputCard
                  output={output}
                  onDownload={() => downloadOutput(output.id)}
                  onDelete={() => handleDeleteOutput(output.id)}
                  onCopyId={() => copyOutputId(output.id)}
                />
              </Col>
            ))}
          </Row>
        )}

        {/* Generation Modals */}
        <Modal
          open={generateModalOpen !== null}
          title={
            generateModalOpen === 'lesson_plan'
              ? '生成新参赛教案'
              : '生成新实施报告'
          }
          onCancel={() => setGenerateModalOpen(null)}
          onOk={handleStartGeneration}
          confirmLoading={submitting}
          okText="启动生成"
          cancelText="取消"
          width={620}
        >
          {generateModalOpen === 'lesson_plan' ? (
            <>
              <Paragraph type="secondary" style={{ fontSize: 13 }}>
                可选:输入任务清单(每行一个),不填则由 AI 根据课程总学时自动拆分。
              </Paragraph>
              <TextArea
                rows={6}
                value={topicsInput}
                onChange={(e) => setTopicsInput(e.target.value)}
                placeholder="任务一名称\n任务二名称\n..."
                style={{ marginBottom: 12 }}
              />
            </>
          ) : (
            <>
              <Paragraph type="secondary" style={{ fontSize: 13 }}>
                可选:关联本项目已生成的教案 output_id 作为上下文。
              </Paragraph>
              <Input
                value={relatedOutputId}
                onChange={(e) => setRelatedOutputId(e.target.value)}
                placeholder="留空则独立生成"
                style={{ marginBottom: 12 }}
              />
            </>
          )}
          <Paragraph type="secondary" style={{ fontSize: 13 }}>
            可选:其他特殊要求
          </Paragraph>
          <TextArea
            rows={3}
            value={additionalRequirements}
            onChange={(e) => setAdditionalRequirements(e.target.value)}
            placeholder="如:重点突出 1+X 对接、增加课程思政等"
          />
        </Modal>
      </div>
    </div>
  );
}

interface OutputCardProps {
  output: CompetitionOutput;
  onDownload: () => void;
  onDelete: () => void;
  onCopyId: () => void;
}

function OutputCard({ output, onDownload, onDelete, onCopyId }: OutputCardProps) {
  const status = STATUS_LABELS[output.status];
  const isInProgress = output.status === 'pending' || output.status === 'processing';
  const isCompleted = output.status === 'completed';
  const isFailed = output.status === 'failed';

  const progressPercent =
    output.progress_total > 0
      ? Math.round((output.progress_current / output.progress_total) * 100)
      : 0;

  const typeLabel = output.output_type === 'lesson_plan' ? '参赛教案' : '实施报告';
  const typeIcon =
    output.output_type === 'lesson_plan' ? (
      <FileTextOutlined />
    ) : (
      <AuditOutlined />
    );

  return (
    <Card style={{ borderRadius: 12, border: 'none', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
      <Row gutter={16} align="middle">
        <Col xs={24} md={14}>
          <Space size={12} style={{ marginBottom: 8 }}>
            <span style={{ fontSize: 18, color: '#0d9488' }}>{typeIcon}</span>
            <Title level={5} style={{ margin: 0 }}>
              {typeLabel}
            </Title>
            <Tag color={status.color}>{status.text}</Tag>
          </Space>
          <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
            创建于 {new Date(output.created_at).toLocaleString('zh-CN')}
          </Text>
          {output.completed_at && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
              完成于 {new Date(output.completed_at).toLocaleString('zh-CN')}
            </Text>
          )}
          {isInProgress && (
            <div style={{ marginTop: 8 }}>
              <Progress percent={progressPercent} status="active" size="small" />
              <Text type="secondary" style={{ fontSize: 12 }}>
                进度:{output.progress_current}/{output.progress_total}
              </Text>
            </div>
          )}
          {isFailed && output.error_message && (
            <Text type="danger" style={{ fontSize: 12, display: 'block', marginTop: 8 }}>
              错误:{output.error_message}
            </Text>
          )}
        </Col>

        <Col xs={24} md={10} style={{ textAlign: 'right' }}>
          <Space wrap>
            {isCompleted && (
              <Button type="primary" icon={<DownloadOutlined />} onClick={onDownload}>
                下载
              </Button>
            )}
            {output.output_type === 'lesson_plan' && isCompleted && (
              <Button size="small" icon={<CopyOutlined />} onClick={onCopyId}>
                复制 ID
              </Button>
            )}
            <Popconfirm
              title={isInProgress ? '取消生成?' : '删除此结果?'}
              onConfirm={onDelete}
              okText="确认"
              cancelText="取消"
            >
              <Button danger size="small" icon={<DeleteOutlined />}>
                {isInProgress ? '取消' : '删除'}
              </Button>
            </Popconfirm>
          </Space>
        </Col>
      </Row>
    </Card>
  );
}

export default CompetitionDetail;
