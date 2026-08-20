/**
 * Batch Task Detail Page
 *
 * Displays a batch task with all associated lesson plans.
 * Features:
 * - Task information card
 * - Lesson plan list with field-level editing
 * - Batch export selected lesson plans
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Descriptions,
  Button,
  Space,
  message,
  Spin,
  Typography,
  Tag,
  Collapse,
  Empty,
  Checkbox,
  Progress,
  Alert,
} from 'antd';
import {
  ArrowLeftOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  RedoOutlined,
} from '@ant-design/icons';
import type { BatchTask, LessonPlan, GeneratedContent as GeneratedContentType } from '@/types';
import { batchApi } from '@/services/batchApi';
import lessonPlanApi from '@/services/lessonPlanApi';
import GeneratedContent from '@/components/generator/GeneratedContent';

const { Title, Text } = Typography;

const BatchTaskDetail: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [task, setTask] = useState<BatchTask | null>(null);
  const [lessonPlans, setLessonPlans] = useState<LessonPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPlanIds, setSelectedPlanIds] = useState<string[]>([]);
  const [exporting, setExporting] = useState(false);
  const [regeneratingField, setRegeneratingField] = useState<{ planId: string; fieldName: string } | null>(null);

  useEffect(() => {
    if (taskId) {
      loadTaskDetails();
      loadLessonPlans();
    }
  }, [taskId]);

  useEffect(() => {
    if (!taskId || !task || !['pending', 'processing'].includes(task.status)) return;
    const timer = window.setInterval(() => {
      void loadTaskDetails();
    }, 2000);
    return () => window.clearInterval(timer);
  }, [taskId, task?.status]);

  const loadTaskDetails = async () => {
    try {
      const taskData = await batchApi.getBatchTask(taskId!);
      setTask(taskData);
    } catch (error: any) {
      message.error(error.message || '加载任务详情失败');
    }
  };

  const loadLessonPlans = async () => {
    setLoading(true);
    try {
      const response = await batchApi.getTaskLessonPlans(taskId!, { page: 1, limit: 100 });
      setLessonPlans(response.lesson_plans);
      setTask(response.task);
    } catch (error: any) {
      message.error(error.message || '加载教案列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateField = async (planId: string, fieldName: string, value: any) => {
    try {
      await lessonPlanApi.updateField(planId, { field_name: fieldName, field_value: value });
      message.success('字段更新成功');
      // Reload lesson plans to get updated data
      loadLessonPlans();
    } catch (error: any) {
      message.error(error.message || '字段更新失败');
      throw error;
    }
  };

  const handleRegenerateField = async (planId: string, fieldName: string, instruction?: string) => {
    setRegeneratingField({ planId, fieldName });
    try {
      const response = await lessonPlanApi.regenerateField(planId, {
        field_name: fieldName,
        additional_instruction: instruction,
      });
      message.success('字段重新生成成功');
      // Update the specific lesson plan with new field value
      setLessonPlans(prev => prev.map(plan => {
        if (plan.id === planId) {
          const content = lessonPlanApi.parseGeneratedContent(plan);
          content[fieldName] = response.field_value;
          if (plan.final_content) {
            const finalContent = JSON.parse(plan.final_content);
            finalContent[fieldName] = response.field_value;
            return {
              ...plan,
              final_content: JSON.stringify(finalContent),
            };
          }
          return {
            ...plan,
            generated_content: JSON.stringify(content),
          };
        }
        return plan;
      }));
    } catch (error: any) {
      message.error(error.message || '字段重新生成失败');
    } finally {
      setRegeneratingField(null);
    }
  };

  const handleExportSelected = async () => {
    if (selectedPlanIds.length === 0) {
      message.warning('请选择要导出的教案');
      return;
    }

    setExporting(true);
    try {
      const blob = await batchApi.exportSelectedLessonPlans(taskId!, {
        lesson_plan_ids: selectedPlanIds,
        group_by_document: true,
      });

      // Trigger download
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      lessonPlanApi.downloadBlob(blob, `selected_lesson_plans_${timestamp}.zip`);

      message.success('导出成功');
    } catch (error: any) {
      message.error(error.message || '导出失败');
    } finally {
      setExporting(false);
    }
  };

  const handleRestart = async (failedOnly: boolean) => {
    try {
      if (failedOnly) await batchApi.retryFailed(taskId!); else await batchApi.resume(taskId!);
      message.success(failedOnly ? '失败课次已进入重试队列' : '任务已从断点继续');
      await loadTaskDetails();
    } catch (error: any) {
      message.error(error.message || '任务启动失败');
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { icon: React.ReactNode; color: string; text: string }> = {
      pending: { icon: <ClockCircleOutlined />, color: 'default', text: '等待中' },
      processing: { icon: <Spin size="small" />, color: 'processing', text: '生成中' },
      completed: { icon: <CheckCircleOutlined />, color: 'success', text: '已完成' },
      failed: { icon: <ExclamationCircleOutlined />, color: 'error', text: '失败' },
      cancelled: { icon: <ExclamationCircleOutlined />, color: 'warning', text: '已取消' },
    };

    const config = statusConfig[status] || statusConfig.pending;
    return (
      <Tag icon={config.icon} color={config.color}>
        {config.text}
      </Tag>
    );
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedPlanIds(lessonPlans.map(p => p.id));
    } else {
      setSelectedPlanIds([]);
    }
  };

  const handleSelectPlan = (planId: string, checked: boolean) => {
    if (checked) {
      setSelectedPlanIds(prev => [...prev, planId]);
    } else {
      setSelectedPlanIds(prev => prev.filter(id => id !== planId));
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (!task) {
    return (
      <div style={{ padding: '24px' }}>
        <Empty description="任务不存在" />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/batch-downloads')}>
            返回
          </Button>
          <Title level={2} style={{ margin: 0 }}>
            批量任务详情
          </Title>
        </Space>
        <Space>
          {task.failed_count > 0 && task.status !== 'processing' && task.status !== 'pending' && (
            <Button type="primary" icon={<RedoOutlined />} onClick={() => void handleRestart(true)}>重试失败课次</Button>
          )}
          {['failed', 'cancelled'].includes(task.status) && (
            <Button icon={<RedoOutlined />} onClick={() => void handleRestart(false)}>从断点续跑</Button>
          )}
        </Space>
      </div>

      {/* Task Info Card */}
      <Card title="任务信息" style={{ marginBottom: 16 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="课程名称">{task.course_name}</Descriptions.Item>
          <Descriptions.Item label="状态">{getStatusBadge(task.status)}</Descriptions.Item>
          <Descriptions.Item label="专业">{task.subject}</Descriptions.Item>
          <Descriptions.Item label="年级">{task.grade}</Descriptions.Item>
          <Descriptions.Item label="总课时">{task.total_hours}课时</Descriptions.Item>
          <Descriptions.Item label="每份教案课时">{task.hours_per_lesson}课时</Descriptions.Item>
          <Descriptions.Item label="教案总数">{task.total_count}份</Descriptions.Item>
          <Descriptions.Item label="完成数量">
            {task.completed_count} / {task.total_count}
            {task.failed_count > 0 && (
              <Text type="danger"> (失败 {task.failed_count})</Text>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间" span={2}>
            {new Date(task.created_at).toLocaleString('zh-CN')}
          </Descriptions.Item>
        </Descriptions>

        {/* Progress Bar */}
        <div style={{ marginTop: 16 }}>
          <Progress
            percent={Math.round((task.completed_count / task.total_count) * 100)}
            status={
              task.status === 'completed'
                ? 'success'
                : task.status === 'failed'
                ? 'exception'
                : 'active'
            }
          />
        </div>
      </Card>

      {/* Lesson Plans Section */}
      <Card
        title={
          <Space>
            <span>教案列表</span>
            <Text type="secondary">({lessonPlans.length}份)</Text>
          </Space>
        }
        extra={
          <Space>
            <Checkbox
              checked={selectedPlanIds.length === lessonPlans.length && lessonPlans.length > 0}
              indeterminate={selectedPlanIds.length > 0 && selectedPlanIds.length < lessonPlans.length}
              onChange={(e) => handleSelectAll(e.target.checked)}
            >
              全选
            </Checkbox>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleExportSelected}
              loading={exporting}
              disabled={selectedPlanIds.length === 0}
            >
              导出选中 ({selectedPlanIds.length})
            </Button>
          </Space>
        }
      >
        {lessonPlans.length === 0 ? (
          <Empty description="暂无教案数据" />
        ) : (
          <Collapse
            accordion
            items={lessonPlans.map((plan, index) => {
              const content = lessonPlanApi.parseGeneratedContent(plan);
              const inputData = lessonPlanApi.parseInputData(plan);

              return {
                key: plan.id,
                label: (
                  <Space>
                    <Checkbox
                      checked={selectedPlanIds.includes(plan.id)}
                      onChange={(e) => {
                        e.stopPropagation();
                        handleSelectPlan(plan.id, e.target.checked);
                      }}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <Text strong>
                      第{plan.lesson_number || index + 1}份: {plan.topic || plan.title}
                    </Text>
                    <Tag color="blue">{inputData.duration || '2课时'}</Tag>
                  </Space>
                ),
                children: (
                  <div>
                    {/* Basic Info */}
                    <Alert
                      message="教案信息"
                      description={
                        <Descriptions size="small" column={2}>
                          <Descriptions.Item label="课题">{plan.topic}</Descriptions.Item>
                          <Descriptions.Item label="课时">{inputData.duration}</Descriptions.Item>
                          <Descriptions.Item label="专业">{plan.subject}</Descriptions.Item>
                          <Descriptions.Item label="年级">{plan.grade}</Descriptions.Item>
                          {inputData.textbook_name && (
                            <Descriptions.Item label="教材" span={2}>
                              {inputData.textbook_name}
                            </Descriptions.Item>
                          )}
                          {inputData.location && (
                            <Descriptions.Item label="地点" span={2}>
                              {inputData.location}
                            </Descriptions.Item>
                          )}
                        </Descriptions>
                      }
                      type="info"
                      style={{ marginBottom: 16 }}
                    />

                    {/* Generated Content with Field Editing */}
                    <GeneratedContent
                      content={content as GeneratedContentType}
                      onRegenerateField={(fieldName, instruction) =>
                        handleRegenerateField(plan.id, fieldName, instruction)
                      }
                      onUpdateField={(fieldName, value) =>
                        handleUpdateField(plan.id, fieldName, value)
                      }
                      isRegenerating={
                        regeneratingField?.planId === plan.id &&
                        regeneratingField?.fieldName !== null
                      }
                      regeneratingField={
                        regeneratingField?.planId === plan.id
                          ? regeneratingField.fieldName
                          : null
                      }
                    />
                  </div>
                ),
              };
            })}
          />
        )}
      </Card>
    </div>
  );
};

export default BatchTaskDetail;
