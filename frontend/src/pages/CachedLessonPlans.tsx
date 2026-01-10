/**
 * Cached Lesson Plans Management Page
 *
 * Manages pre-generated draft lesson plans with:
 * - Filter by template, subject, grade, search keywords
 * - Batch operations (publish, delete)
 * - Single operations (view details, publish, delete)
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
  Modal,
  Typography,
  Popconfirm,
  Input,
  Select,
  Row,
  Col,
  Tooltip,
} from 'antd';
import {
  FileTextOutlined,
  DeleteOutlined,
  ReloadOutlined,
  CloudUploadOutlined,
  SearchOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import type { LessonPlan, TemplateInfo } from '@/types';
import lessonPlanApi from '@/services/lessonPlanApi';
import api from '@/services/api';

const { Title, Text } = Typography;
const { Search } = Input;

const CachedLessonPlans: React.FC = () => {
  const navigate = useNavigate();
  const [lessonPlans, setLessonPlans] = useState<LessonPlan[]>([]);
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [publishing, setPublishing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [total, setTotal] = useState(0);

  // Filter states
  const [filters, setFilters] = useState({
    status: 'draft_cached',
    template_id: undefined as string | undefined,
    subject: undefined as string | undefined,
    grade: undefined as string | undefined,
    search: undefined as string | undefined,
  });
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
  });

  // Load templates on mount
  useEffect(() => {
    loadTemplates();
  }, []);

  // Load lesson plans when filters or pagination change
  useEffect(() => {
    loadLessonPlans();
  }, [filters, pagination]);

  const loadTemplates = async () => {
    try {
      const response = await api.get('/api/templates');
      setTemplates(response.data);
    } catch (error: any) {
      console.error('Failed to load templates:', error);
    }
  };

  const loadLessonPlans = async () => {
    setLoading(true);
    try {
      const response = await lessonPlanApi.listLessonPlans({
        ...filters,
        ...pagination,
      });
      setLessonPlans(response.lesson_plans);
      setTotal(response.total);
    } catch (error: any) {
      message.error(error.message || '加载教案列表失败');
    } finally {
      setLoading(false);
    }
  };

  const refreshLessonPlans = async () => {
    setRefreshing(true);
    try {
      const response = await lessonPlanApi.listLessonPlans({
        ...filters,
        ...pagination,
      });
      setLessonPlans(response.lesson_plans);
      setTotal(response.total);
    } catch (error) {
      console.error('Auto-refresh failed:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const handlePublishSingle = async (lessonPlanId: string) => {
    try {
      const response = await lessonPlanApi.publishLessonPlan(lessonPlanId);
      message.success('发布成功');

      // Trigger download
      const downloadUrl = response.download_url;
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.click();

      // Refresh list
      loadLessonPlans();
    } catch (error: any) {
      message.error(error.message || '发布失败');
    }
  };

  const handleBatchPublish = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要发布的教案');
      return;
    }

    Modal.confirm({
      title: '批量发布',
      content: `确定要发布选中的 ${selectedRowKeys.length} 份教案吗？将自动生成Word文档并打包下载。`,
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        setPublishing(true);
        try {
          const blob = await lessonPlanApi.batchPublish({
            lesson_plan_ids: selectedRowKeys,
            group_by_document: true,
          });

          // Trigger download
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
          lessonPlanApi.downloadBlob(blob, `lesson_plans_${timestamp}.zip`);

          message.success('批量发布成功');
          setSelectedRowKeys([]);
          loadLessonPlans();
        } catch (error: any) {
          message.error(error.message || '批量发布失败');
        } finally {
          setPublishing(false);
        }
      },
    });
  };

  const handleDeleteSingle = async (lessonPlanId: string) => {
    try {
      await lessonPlanApi.deleteLessonPlan(lessonPlanId);
      message.success('删除成功');
      loadLessonPlans();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要删除的教案');
      return;
    }

    Modal.confirm({
      title: '批量删除',
      content: (
        <div>
          <ExclamationCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
          确定要删除选中的 {selectedRowKeys.length} 份教案吗？
          <br />
          <Text type="danger">删除后无法恢复！</Text>
        </div>
      ),
      okText: '确定',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        setDeleting(true);
        try {
          const response = await lessonPlanApi.batchDelete({
            lesson_plan_ids: selectedRowKeys,
          });

          if (response.failed_ids.length > 0) {
            message.warning(
              `删除完成：成功 ${response.deleted_count} 份，失败 ${response.failed_ids.length} 份`
            );
          } else {
            message.success(`成功删除 ${response.deleted_count} 份教案`);
          }

          setSelectedRowKeys([]);
          loadLessonPlans();
        } catch (error: any) {
          message.error(error.message || '批量删除失败');
        } finally {
          setDeleting(false);
        }
      },
    });
  };

  const handleViewDetails = (lessonPlan: LessonPlan) => {
    // If lesson plan is part of a batch task, navigate to batch task detail page
    if (lessonPlan.batch_task_id) {
      navigate(`/batch-tasks/${lessonPlan.batch_task_id}`);
    } else {
      // Otherwise, open a modal to show details
      Modal.info({
        title: lessonPlan.title,
        width: 800,
        content: (
          <div>
            <p><strong>学科：</strong>{lessonPlan.subject}</p>
            <p><strong>年级：</strong>{lessonPlan.grade}</p>
            <p><strong>课题：</strong>{lessonPlan.topic}</p>
            <p><strong>状态：</strong>{getStatusTag(lessonPlan.status)}</p>
            <p><strong>创建时间：</strong>{new Date(lessonPlan.created_at).toLocaleString('zh-CN')}</p>
          </div>
        ),
      });
    }
  };

  const getStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; text: string }> = {
      draft: { color: 'default', text: '草稿' },
      draft_cached: { color: 'blue', text: '已缓存' },
      generated: { color: 'cyan', text: '已生成' },
      published: { color: 'success', text: '已发布' },
    };

    const config = statusConfig[status] || statusConfig.draft;
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getTemplateName = (templateId: string) => {
    const template = templates.find(t => t.id === templateId);
    return template?.name || '-';
  };

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 250,
      render: (text: string) => (
        <Tooltip title={text}>
          <Text strong ellipsis style={{ maxWidth: 230, display: 'inline-block' }}>
            {text}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: '课题',
      dataIndex: 'topic',
      key: 'topic',
      width: 180,
      render: (text?: string) => text || '-',
    },
    {
      title: '学科',
      dataIndex: 'subject',
      key: 'subject',
      width: 100,
      render: (text?: string) => text || '-',
    },
    {
      title: '年级',
      dataIndex: 'grade',
      key: 'grade',
      width: 100,
      render: (text?: string) => text || '-',
    },
    {
      title: '模板',
      dataIndex: 'template_id',
      key: 'template_id',
      width: 180,
      render: (templateId: string) => (
        <Tooltip title={getTemplateName(templateId)}>
          <Text ellipsis style={{ maxWidth: 160, display: 'inline-block' }}>
            {getTemplateName(templateId)}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
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
      }),
    },
    {
      title: '操作',
      key: 'actions',
      fixed: 'right' as const,
      width: 180,
      render: (_: any, record: LessonPlan) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetails(record)}
            />
          </Tooltip>

          <Tooltip title="发布">
            <Button
              type="text"
              size="small"
              icon={<CloudUploadOutlined />}
              onClick={() => handlePublishSingle(record.id)}
            >
              发布
            </Button>
          </Tooltip>

          <Popconfirm
            title="确定删除此教案？"
            description="删除后无法恢复"
            onConfirm={() => handleDeleteSingle(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys as string[]);
    },
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <Title level={2} style={{ margin: 0 }}>
                草稿箱
              </Title>
              <Text type="secondary">
                管理预生成的教案草稿
              </Text>
            </div>

            <Space>
              <Button
                icon={<ReloadOutlined spin={refreshing} />}
                onClick={refreshLessonPlans}
                loading={refreshing}
              >
                刷新
              </Button>
            </Space>
          </div>

          {/* Filter Bar */}
          <Row gutter={16}>
            <Col span={6}>
              <Select
                style={{ width: '100%' }}
                placeholder="选择模板"
                allowClear
                value={filters.template_id}
                onChange={(value) => setFilters({ ...filters, template_id: value })}
              >
                {templates.map(t => (
                  <Select.Option key={t.id} value={t.id}>
                    {t.name}
                  </Select.Option>
                ))}
              </Select>
            </Col>

            <Col span={4}>
              <Select
                style={{ width: '100%' }}
                placeholder="选择学科"
                allowClear
                value={filters.subject}
                onChange={(value) => setFilters({ ...filters, subject: value })}
              >
                <Select.Option value="语文">语文</Select.Option>
                <Select.Option value="数学">数学</Select.Option>
                <Select.Option value="英语">英语</Select.Option>
                <Select.Option value="物理">物理</Select.Option>
                <Select.Option value="化学">化学</Select.Option>
                <Select.Option value="生物">生物</Select.Option>
                <Select.Option value="大数据技术">大数据技术</Select.Option>
                <Select.Option value="Python程序设计">Python程序设计</Select.Option>
              </Select>
            </Col>

            <Col span={4}>
              <Select
                style={{ width: '100%' }}
                placeholder="选择年级"
                allowClear
                value={filters.grade}
                onChange={(value) => setFilters({ ...filters, grade: value })}
              >
                <Select.Option value="大一">大一</Select.Option>
                <Select.Option value="大二">大二</Select.Option>
                <Select.Option value="大三">大三</Select.Option>
                <Select.Option value="大四">大四</Select.Option>
                <Select.Option value="2023级">2023级</Select.Option>
                <Select.Option value="2024级">2024级</Select.Option>
                <Select.Option value="2025级">2025级</Select.Option>
              </Select>
            </Col>

            <Col span={10}>
              <Search
                placeholder="搜索标题或课题"
                allowClear
                enterButton={<SearchOutlined />}
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value || undefined })}
                onSearch={(value) => setFilters({ ...filters, search: value || undefined })}
              />
            </Col>
          </Row>
        </div>

        {/* Batch Actions */}
        {selectedRowKeys.length > 0 && (
          <div style={{ marginBottom: 16, padding: '12px', background: '#e6f7ff', borderRadius: '4px' }}>
            <Space>
              <CheckCircleOutlined style={{ color: '#1890ff' }} />
              <Text>已选择 {selectedRowKeys.length} 项</Text>
              <Button
                type="primary"
                size="small"
                icon={<CloudUploadOutlined />}
                onClick={handleBatchPublish}
                loading={publishing}
              >
                批量发布
              </Button>
              <Button
                danger
                size="small"
                icon={<DeleteOutlined />}
                onClick={handleBatchDelete}
                loading={deleting}
              >
                批量删除
              </Button>
              <Button
                type="link"
                size="small"
                onClick={() => setSelectedRowKeys([])}
              >
                取消选择
              </Button>
            </Space>
          </div>
        )}

        <Table
          columns={columns}
          dataSource={lessonPlans}
          rowKey="id"
          loading={loading}
          rowSelection={rowSelection}
          pagination={{
            current: pagination.page,
            pageSize: pagination.limit,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
            onChange: (page, pageSize) => {
              setPagination({ page, limit: pageSize || 20 });
            },
          }}
          scroll={{ x: 1400 }}
        />
      </Card>
    </div>
  );
};

export default CachedLessonPlans;
