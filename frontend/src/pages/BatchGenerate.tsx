/**
 * Batch Lesson Plan Generation Page
 *
 * 3-Step Wizard:
 * 1. Fill basic information
 * 2. Review and edit AI-split chapters
 * 3. Monitor generation progress
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Steps,
  Form,
  Input,
  Select,
  InputNumber,
  Button,
  Table,
  message,
  Progress,
  Spin,
  Space,
  Tag,
  Typography,
  Modal,
  Radio,
  Divider,
} from 'antd';
import {
  FileTextOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import type {
  ChapterInfo,
  ChapterSplitRequest,
  BatchTaskCreateRequest,
  BatchTask,
  TemplateInfo,
  CourseChapterTemplate,
} from '@/types';
import {
  SUBJECT_OPTIONS,
  GRADE_OPTIONS,
} from '@/types';
import { batchApi } from '@/services/batchApi';
import { templateApi } from '@/services/api';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const BatchGenerate: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  // Step state
  const [currentStep, setCurrentStep] = useState(0);

  // Mode selection: 'new' or 'existing'
  const [mode, setMode] = useState<'new' | 'existing'>('new');

  // Step 1: Basic information
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [cachedTemplates, setCachedTemplates] = useState<CourseChapterTemplate[]>([]);
  const [loading, setLoading] = useState(false);

  // Step 2: Chapters
  const [chapters, setChapters] = useState<ChapterInfo[]>([]);
  const [splittingChapters, setSplittingChapters] = useState(false);

  // Step 3: Progress
  const [batchTask, setBatchTask] = useState<BatchTask | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);

  // Load templates on mount
  useEffect(() => {
    loadTemplates();
    loadCachedTemplates();
  }, []);

  // Poll task status in step 3
  useEffect(() => {
    if (currentStep === 2 && taskId) {
      const interval = setInterval(async () => {
        try {
          const task = await batchApi.getBatchTask(taskId);
          setBatchTask(task);

          if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
            clearInterval(interval);
          }
        } catch (error) {
          console.error('Failed to fetch task status:', error);
        }
      }, 2000); // Poll every 2 seconds

      return () => clearInterval(interval);
    }
  }, [currentStep, taskId]);

  const loadTemplates = async () => {
    try {
      const data = await templateApi.listTemplates();
      setTemplates(data);
    } catch (error) {
      message.error('加载模板失败');
    }
  };

  const loadCachedTemplates = async () => {
    try {
      const data = await batchApi.listChapterTemplates();
      setCachedTemplates(data.templates);
    } catch (error) {
      console.error('Failed to load cached templates:', error);
      message.error('加载缓存模板失败');
    }
  };

  // Handle selecting an existing cached template
  const handleSelectCachedTemplate = (templateId: string) => {
    const selected = cachedTemplates.find((t) => t.id === templateId);
    if (selected) {
      // Get current template_id to preserve it
      const currentTemplateId = form.getFieldValue('template_id');
      console.log('🔍 [handleSelectCachedTemplate] 选择课程章节模板:', selected.course_name);
      console.log('🔍 [handleSelectCachedTemplate] 当前教案模板ID:', currentTemplateId);

      // Prepare form values
      const formValues: any = {
        course_name: selected.course_name,
        subject: selected.subject,
        grade: selected.grade,
        start_week: selected.start_week,
        end_week: selected.end_week,
      };

      // Only include template_id if it has a value (to preserve user's selection)
      if (currentTemplateId) {
        formValues.template_id = currentTemplateId;
        console.log('🔍 [handleSelectCachedTemplate] 保留教案模板ID:', currentTemplateId);
      } else {
        console.log('🔍 [handleSelectCachedTemplate] 当前无教案模板，不设置template_id字段');
      }

      // Auto-fill form fields
      form.setFieldsValue(formValues);

      console.log('🔍 [handleSelectCachedTemplate] setFieldsValue完成后，template_id =', form.getFieldValue('template_id'));

      // Load chapters but stay on step 1 to let user select lesson plan template
      setChapters(selected.chapters);

      if (currentTemplateId) {
        message.success(`已加载 ${selected.course_name} 的 ${selected.chapters.length} 个教学周次`);
      } else {
        message.success(`已加载 ${selected.course_name} 的 ${selected.chapters.length} 个教学周次，请选择教案模板后继续`);
      }
    }
  };

  // Step 1: Submit basic info and split chapters
  const handleSplitChapters = async (values: any) => {
    const request: ChapterSplitRequest = {
      course_name: values.course_name,
      subject: values.subject,
      grade: values.grade,
      start_week: values.start_week,
      end_week: values.end_week,
      additional_info: values.additional_info,
    };

    setSplittingChapters(true);
    try {
      const response = await batchApi.splitChapters(request);
      setChapters(response.chapters);
      setCurrentStep(1);
      message.success(`成功拆分为 ${response.chapters.length} 个教学周次`);
    } catch (error: any) {
      message.error(error.message || '章节拆分失败');
    } finally {
      setSplittingChapters(false);
    }
  };

  // Step 2: Create batch task
  const handleCreateBatchTask = async () => {
    const values = form.getFieldsValue();
    console.log('🔍 [handleCreateBatchTask] 开始创建批量任务');
    console.log('🔍 [handleCreateBatchTask] 表单值:', values);
    console.log('🔍 [handleCreateBatchTask] template_id =', values.template_id);

    // Validate required fields
    if (!values.template_id) {
      console.log('❌ [handleCreateBatchTask] template_id为空，显示错误');
      message.error('请选择教案模板');
      return;
    }

    if (!values.course_name || !values.subject || !values.grade) {
      message.error('请填写完整的课程信息');
      return;
    }

    if (!values.start_week || !values.end_week) {
      message.error('请填写起始和结束周次');
      return;
    }

    if (!chapters || chapters.length === 0) {
      message.error('章节信息为空，请先拆分章节或选择已有模板');
      return;
    }

    const request: BatchTaskCreateRequest = {
      course_name: values.course_name,
      subject: values.subject,
      grade: values.grade,
      template_id: values.template_id,
      start_week: values.start_week,
      end_week: values.end_week,
      chapters: chapters,
      additional_requirements: values.additional_requirements,
    };

    console.log('Creating batch task with request:', request);

    setLoading(true);
    try {
      const response = await batchApi.createBatchTask(request);
      setTaskId(response.task_id);
      setCurrentStep(2);
      message.success('批量任务已创建，正在后台生成...');
    } catch (error: any) {
      console.error('Failed to create batch task:', error);
      message.error(error.message || '创建任务失败');
    } finally {
      setLoading(false);
    }
  };

  // Chapter table columns
  const chapterColumns = [
    {
      title: '周次',
      dataIndex: 'week',
      key: 'week',
      width: 80,
      render: (week: number) => `第${week}周`,
    },
    {
      title: '课题',
      dataIndex: 'topic',
      key: 'topic',
      render: (text: string, record: ChapterInfo, index: number) => (
        <Input
          value={text}
          onChange={(e) => {
            const newChapters = [...chapters];
            newChapters[index].topic = e.target.value;
            setChapters(newChapters);
          }}
        />
      ),
    },
    {
      title: '内容概述',
      dataIndex: 'content_summary',
      key: 'content_summary',
      render: (text: string, record: ChapterInfo, index: number) => (
        <TextArea
          value={text}
          rows={2}
          onChange={(e) => {
            const newChapters = [...chapters];
            newChapters[index].content_summary = e.target.value;
            setChapters(newChapters);
          }}
        />
      ),
    },
    {
      title: '核心概念',
      dataIndex: 'key_concepts',
      key: 'key_concepts',
      render: (concepts: string[]) => (
        <Space wrap>
          {concepts.map((concept, idx) => (
            <Tag key={idx} color="blue">{concept}</Tag>
          ))}
        </Space>
      ),
    },
  ];

  // Get status badge
  const getStatusBadge = (status?: string) => {
    const statusConfig: Record<string, { icon: React.ReactNode; color: string; text: string }> = {
      pending: { icon: <ClockCircleOutlined />, color: 'default', text: '等待中' },
      processing: { icon: <Spin size="small" />, color: 'processing', text: '生成中' },
      completed: { icon: <CheckCircleOutlined />, color: 'success', text: '已完成' },
      failed: { icon: <ExclamationCircleOutlined />, color: 'error', text: '失败' },
      cancelled: { icon: <ExclamationCircleOutlined />, color: 'warning', text: '已取消' },
    };

    const config = statusConfig[status || 'pending'];
    return (
      <Tag icon={config.icon} color={config.color}>
        {config.text}
      </Tag>
    );
  };

  // Render steps
  const steps = [
    {
      title: '基本信息',
      description: '填写课程信息',
      icon: <FileTextOutlined />,
    },
    {
      title: '确认章节',
      description: '审核AI拆分结果',
      icon: <CheckCircleOutlined />,
    },
    {
      title: '生成进度',
      description: '监控生成状态',
      icon: <ClockCircleOutlined />,
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Title level={2}>批量生成教案</Title>
        <Paragraph type="secondary">
          根据课程名称自动拆分章节，批量生成一个学期的教案文档
        </Paragraph>

        <Steps current={currentStep} items={steps} style={{ marginTop: 24, marginBottom: 32 }} />

        {/* Step 1: Basic Information */}
        {currentStep === 0 && (
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSplitChapters}
            initialValues={{
              start_week: 1,
              end_week: 16,
            }}
            preserve={true}
          >
            {/* Mode selection */}
            <Form.Item label="选择方式">
              <Radio.Group
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                size="large"
              >
                <Radio.Button value="new">
                  <FileTextOutlined /> 创建新课程
                </Radio.Button>
                <Radio.Button value="existing">
                  <HistoryOutlined /> 使用已有模板
                </Radio.Button>
              </Radio.Group>
            </Form.Item>

            {/* Existing template selection */}
            {mode === 'existing' && (
              <>
                <Form.Item label="选择课程章节模板">
                  <Select
                    placeholder="选择已有的课程章节模板"
                    size="large"
                    showSearch
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                    options={cachedTemplates.map((t) => ({
                      label: `${t.course_name} - ${t.subject} - ${t.grade} (第${t.start_week}-${t.end_week}周, 使用${t.use_count}次)`,
                      value: t.id,
                    }))}
                    onChange={handleSelectCachedTemplate}
                  />
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary">
                      选择后将自动填充课程信息和章节内容，您只需选择教案模板即可
                    </Text>
                  </div>
                </Form.Item>
                <Divider>或者继续填写表单创建新课程</Divider>
              </>
            )}

            <Form.Item
              name="course_name"
              label="课程名称"
              rules={[{ required: true, message: '请输入课程名称' }]}
            >
              <Input placeholder="例如：信息安全技术基础" size="large" disabled={mode === 'existing'} />
            </Form.Item>

            <Space style={{ width: '100%' }} size="large">
              <Form.Item
                name="subject"
                label="学科"
                rules={[{ required: true, message: '请选择学科' }]}
                style={{ width: 200 }}
              >
                <Select
                  placeholder="选择学科"
                  options={SUBJECT_OPTIONS.map((s) => ({ label: s, value: s }))}
                  showSearch
                  disabled={mode === 'existing'}
                />
              </Form.Item>

              <Form.Item
                name="grade"
                label="年级"
                rules={[{ required: true, message: '请选择年级' }]}
                style={{ width: 200 }}
              >
                <Select
                  placeholder="选择年级"
                  options={GRADE_OPTIONS.map((g) => ({ label: g, value: g }))}
                  showSearch
                  disabled={mode === 'existing'}
                />
              </Form.Item>

              <Form.Item
                name="template_id"
                label="教案模板"
                rules={[{ required: true, message: '请选择模板' }]}
                style={{ width: 300 }}
              >
                <Select
                  placeholder="选择模板"
                  showSearch
                  onChange={(value) => {
                    console.log('🔍 [教案模板Select] 用户选择了教案模板:', value);
                    console.log('🔍 [教案模板Select] 模板名称:', templates.find(t => t.id === value)?.name);
                  }}
                >
                  {templates.map((t) => (
                    <Select.Option key={t.id} value={t.id}>
                      {t.name}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Space>

            <Space size="large">
              <Form.Item
                name="start_week"
                label="起始周次"
                rules={[{ required: true, type: 'number', min: 1 }]}
              >
                <InputNumber min={1} max={30} disabled={mode === 'existing'} />
              </Form.Item>

              <Form.Item
                name="end_week"
                label="结束周次"
                rules={[{ required: true, type: 'number', min: 1 }]}
              >
                <InputNumber min={1} max={30} disabled={mode === 'existing'} />
              </Form.Item>

              <Text type="secondary" style={{ marginTop: 30 }}>
                将生成 {(form.getFieldValue('end_week') || 16) - (form.getFieldValue('start_week') || 1) + 1} 个教案
              </Text>
            </Space>

            <Form.Item name="additional_info" label="补充说明（可选）">
              <TextArea
                rows={3}
                placeholder="例如：本课程侧重实践操作，每周需包含实验环节..."
              />
            </Form.Item>

            <Form.Item name="additional_requirements" label="额外要求（可选）">
              <TextArea
                rows={3}
                placeholder="对生成的教案有特殊要求，例如：教学方法、重点难点等..."
              />
            </Form.Item>

            {mode === 'new' && (
              <Form.Item>
                <Space>
                  <Button
                    type="primary"
                    htmlType="submit"
                    size="large"
                    loading={splittingChapters}
                    icon={<FileTextOutlined />}
                  >
                    {splittingChapters ? 'AI拆分中...' : '下一步：AI拆分章节'}
                  </Button>
                  <Button size="large" onClick={() => navigate('/')}>
                    取消
                  </Button>
                </Space>
              </Form.Item>
            )}

            {mode === 'existing' && chapters.length > 0 && (
              <Form.Item>
                <Space>
                  <Button
                    type="primary"
                    size="large"
                    icon={<CheckCircleOutlined />}
                    onClick={() => {
                      // Validate required fields
                      const values = form.getFieldsValue();
                      console.log('🔍 [下一步按钮] 点击下一步按钮');
                      console.log('🔍 [下一步按钮] 当前表单所有值:', values);
                      console.log('🔍 [下一步按钮] template_id =', values.template_id);

                      if (!values.template_id) {
                        console.log('❌ [下一步按钮] template_id为空，阻止进入步骤2');
                        message.error('请先选择教案模板');
                        return;
                      }

                      form.validateFields(['template_id', 'course_name', 'subject', 'grade', 'start_week', 'end_week'])
                        .then(() => {
                          console.log('✅ [下一步按钮] 验证通过，进入步骤2');
                          setCurrentStep(1);
                          message.success('进入章节确认步骤');
                        })
                        .catch((errorInfo) => {
                          console.error('❌ [下一步按钮] 验证失败:', errorInfo);
                          message.error('请完成必填项');
                        });
                    }}
                  >
                    下一步：确认章节
                  </Button>
                  <Button size="large" onClick={() => navigate('/')}>
                    取消
                  </Button>
                </Space>
              </Form.Item>
            )}
          </Form>
        )}

        {/* Step 2: Review Chapters */}
        {currentStep === 1 && (
          <div>
            {(() => {
              const currentTemplateId = form.getFieldValue('template_id');
              console.log('🔍 [步骤2渲染] 当前template_id =', currentTemplateId);
              console.log('🔍 [步骤2渲染] 所有表单值:', form.getFieldsValue());
              return null;
            })()}

            <Title level={4}>
              已准备 {chapters.length} 个教学周次，请审核并修改：
            </Title>
            <Paragraph type="secondary">
              您可以直接在表格中编辑课题和内容概述。每个教案固定为2课时。
            </Paragraph>

            {/* Show course info and template selection */}
            <Card style={{ marginBottom: 16, backgroundColor: '#f5f5f5' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text strong>课程信息：</Text>
                  <Text style={{ marginLeft: 8 }}>
                    {form.getFieldValue('course_name')} - {form.getFieldValue('subject')} - {form.getFieldValue('grade')}
                  </Text>
                  <Text style={{ marginLeft: 16 }}>
                    (第{form.getFieldValue('start_week')}-{form.getFieldValue('end_week')}周)
                  </Text>
                </div>

                <div>
                  <Text strong>教案模板：</Text>
                  {form.getFieldValue('template_id') ? (
                    <Text style={{ marginLeft: 8, color: '#52c41a' }}>
                      ✓ {templates.find(t => t.id === form.getFieldValue('template_id'))?.name || '已选择'}
                    </Text>
                  ) : (
                    <Text style={{ marginLeft: 8, color: '#ff4d4f' }}>
                      <ExclamationCircleOutlined /> 请返回上一步选择教案模板
                    </Text>
                  )}
                </div>
              </Space>
            </Card>

            <Table
              columns={chapterColumns}
              dataSource={chapters}
              rowKey="week"
              pagination={false}
              scroll={{ y: 400 }}
              style={{ marginTop: 16 }}
            />

            <div style={{ marginTop: 24 }}>
              <Space>
                <Button
                  type="primary"
                  size="large"
                  onClick={handleCreateBatchTask}
                  loading={loading}
                  icon={<CheckCircleOutlined />}
                  disabled={!form.getFieldValue('template_id')}
                >
                  确认并开始生成
                </Button>
                <Button size="large" onClick={() => setCurrentStep(0)}>
                  上一步
                </Button>
              </Space>
            </div>
          </div>
        )}

        {/* Step 3: Progress */}
        {currentStep === 2 && batchTask && (
          <div>
            <Title level={4}>生成进度</Title>

            <Card style={{ marginTop: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }} size="large">
                <div>
                  <Text strong>课程名称：</Text>
                  <Text>{batchTask.course_name}</Text>
                  <Text style={{ marginLeft: 24 }} strong>状态：</Text>
                  {getStatusBadge(batchTask.status)}
                </div>

                <div>
                  <Text strong style={{ marginBottom: 8, display: 'block' }}>
                    生成进度：{batchTask.completed_count} / {batchTask.total_count}
                  </Text>
                  <Progress
                    percent={Math.round((batchTask.completed_count / batchTask.total_count) * 100)}
                    status={
                      batchTask.status === 'completed'
                        ? 'success'
                        : batchTask.status === 'failed'
                        ? 'exception'
                        : 'active'
                    }
                  />
                </div>

                {batchTask.failed_count > 0 && (
                  <div>
                    <Text type="warning">失败：{batchTask.failed_count} 个</Text>
                  </div>
                )}

                {batchTask.error_message && (
                  <div>
                    <Text type="danger">错误信息：{batchTask.error_message}</Text>
                  </div>
                )}

                {batchTask.status === 'completed' && (
                  <div>
                    <Text type="success" strong>✓ 批量生成完成！</Text>
                    <div style={{ marginTop: 16 }}>
                      <Space>
                        <Button
                          type="primary"
                          size="large"
                          onClick={() => navigate('/batch-downloads')}
                          icon={<FileTextOutlined />}
                        >
                          前往下载页面
                        </Button>
                        <Button size="large" onClick={() => navigate('/')}>
                          返回首页
                        </Button>
                      </Space>
                    </div>
                  </div>
                )}

                {batchTask.status === 'processing' && (
                  <div>
                    <Spin /> <Text type="secondary">正在生成教案，请稍候...</Text>
                  </div>
                )}
              </Space>
            </Card>
          </div>
        )}
      </Card>
    </div>
  );
};

export default BatchGenerate;
