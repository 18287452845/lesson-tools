/**
 * Batch Downloads Page
 *
 * Lists all batch tasks with:
 * - Auto-refresh for in-progress tasks
 * - Download ZIP functionality
 * - Task deletion
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  message,
  Progress,
  Spin,
  Typography,
  Popconfirm,
} from 'antd';
import {
  DownloadOutlined,
  DeleteOutlined,
  ReloadOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import type { BatchTask } from '@/types';
import { batchApi } from '@/services/batchApi';

const { Title, Text } = Typography;

const BatchDownloads: React.FC = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<BatchTask[]>([]);
  const [loading, setLoading] = useState(true);

  // Load tasks on mount
  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const response = await batchApi.listBatchTasks();
      setTasks(response.tasks);
    } catch (error: any) {
      message.error(error.message || '加载任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (task: BatchTask) => {
    try {
      await batchApi.downloadBatchZip(task.id, task.course_name);
      message.success('下载成功');
    } catch (error: any) {
      message.error(error.message || '下载失败');
    }
  };

  const handleDelete = async (taskId: string) => {
    try {
      await batchApi.deleteBatchTask(taskId);
      message.success('删除成功');
      loadTasks();
    } catch (error: any) {
      message.error(error.message || '删除失败');
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

  const columns = [
    {
      title: '课程名称',
      dataIndex: 'course_name',
      key: 'course_name',
      width: 200,
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '专业/年级',
      key: 'subject_grade',
      width: 150,
      render: (_: any, record: BatchTask) => (
        <div>
          <div>{record.subject}</div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.grade}
          </Text>
        </div>
      ),
    },
    {
      title: '课时信息',
      key: 'hours',
      width: 120,
      render: (_: any, record: BatchTask) => (
        <div>
          <div>{record.total_hours}课时</div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.total_count}份教案
          </Text>
        </div>
      ),
    },
    {
      title: '任务类型',
      key: 'task_type',
      width: 100,
      render: (_: any, record: BatchTask) => {
        const extendedTask = record as import('@/types').ExtendedBatchTask;
        const taskType = extendedTask.task_type || 'normal';
        return taskType === 'draft' ? (
          <Tag color="blue">草稿</Tag>
        ) : (
          <Tag color="green">正常</Tag>
        );
      },
    },
    {
      title: '进度',
      key: 'progress',
      width: 200,
      render: (_: any, record: BatchTask) => (
        <div>
          <Progress
            percent={Math.round((record.completed_count / record.total_count) * 100)}
            size="small"
            status={
              record.status === 'completed'
                ? 'success'
                : record.status === 'failed'
                ? 'exception'
                : 'active'
            }
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.completed_count} / {record.total_count}
            {record.failed_count > 0 && (
              <Text type="danger"> (失败 {record.failed_count})</Text>
            )}
          </Text>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => getStatusBadge(status),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => new Date(text).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }),
    },
    {
      title: '操作',
      key: 'actions',
      fixed: 'right' as const,
      width: 180,
      render: (_: any, record: BatchTask) => {
        const extendedTask = record as import('@/types').ExtendedBatchTask;
        const taskType = extendedTask.task_type || 'normal';
        const isDraft = taskType === 'draft';

        return (
          <Space>
            {isDraft && record.status === 'completed' && (
              <Button
                type="primary"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => navigate(`/batch-tasks/${record.id}`)}
              >
                查看详情
              </Button>
            )}

            {!isDraft && record.status === 'completed' && (
              <Button
                type="primary"
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => handleDownload(record)}
              >
                下载
              </Button>
            )}

            {record.status === 'processing' && (
              <Spin size="small" />
            )}

            <Popconfirm
              title="确定删除此任务？"
              description={
                record.status === 'processing'
                  ? '任务正在进行中，删除后将取消任务'
                  : '删除后无法恢复'
              }
              onConfirm={() => handleDelete(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
              >
                删除
              </Button>
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} style={{ margin: 0 }}>
              批量下载
            </Title>
            <Text type="secondary">
              查看和下载批量生成的教案
            </Text>
          </div>

          <Space>
            <Button
              icon={<ReloadOutlined spin={loading} />}
              onClick={loadTasks}
              loading={loading}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/batch-generate')}
            >
              新建批量任务
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  );
};

export default BatchDownloads;
