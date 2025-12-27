/**
 * Batch Lesson Plan Generation Page
 *
 * 3-Step Wizard:
 * 1. Fill basic information (total hours, chapters)
 * 2. Review and edit AI-generated/manual chapters
 * 3. Monitor generation progress
 *
 * Now supports hours-based generation:
 * - Total hours (64, 72, etc.)
 * - Hours per lesson (default 2)
 * - Manual or AI chapter input
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
  Alert,
} from 'antd';
import {
  FileTextOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  HistoryOutlined,
  EditOutlined,
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

  // Mode selection: 'new' (AI generate chapters) or 'existing' (use cached) or 'manual' (user input)
  const [mode, setMode] = useState<'new' | 'existing' | 'manual'>('new');

  // Chapter input mode for new courses: 'ai' or 'manual'
  const [chapterInputMode, setChapterInputMode] = useState<'ai' | 'manual'>('ai');

  // Step 1: Basic information
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [cachedTemplates, setCachedTemplates] = useState<CourseChapterTemplate[]>([]);
  const [loading, setLoading] = useState(false);

  // Saved form values (preserved across step changes)
  const [savedFormValues, setSavedFormValues] = useState<any>({});

  // Step 2: Chapters
  const [chapters, setChapters] = useState<ChapterInfo[]>([]);
  const [splittingChapters, setSplittingChapters] = useState(false);
  const [totalLessons, setTotalLessons] = useState(0);

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

      // Prepare form values
      const formValues: any = {
        course_name: selected.course_name,
        subject: selected.subject,
        grade: selected.grade,
        total_hours: selected.total_hours,
        hours_per_lesson: selected.hours_per_lesson || 2,
      };

      // Only include template_id if it has a value (to preserve user's selection)
      if (currentTemplateId) {
        formValues.template_id = currentTemplateId;
      }

      // Auto-fill form fields
      form.setFieldsValue(formValues);

      // Load chapters but stay on step 1 to let user select lesson plan template
      setChapters(selected.chapters);
      setTotalLessons(selected.chapters.length);

      if (currentTemplateId) {
        message.success(`已加载 ${selected.course_name} 的 ${selected.chapters.length} 份教案章节`);
      } else {
        message.success(`已加载 ${selected.course_name} 的 ${selected.chapters.length} 份教案章节，请选择教案模板后继续`);
      }
    }
  };

  // Step 1: Submit basic info and split chapters
  const handleSplitChapters = async (values: any) => {
    // Save form values before switching step
    setSavedFormValues(values);

    const request: ChapterSplitRequest = {
      course_name: values.course_name,
      subject: values.subject,
      grade: values.grade,
      total_hours: values.total_hours,
      hours_per_lesson: values.hours_per_lesson || 2,
      chapters_input: chapterInputMode === 'manual' ? values.chapters_input : undefined,
      additional_info: values.additional_info,
    };

    setSplittingChapters(true);
    try {
      const response = await batchApi.splitChapters(request);
      setChapters(response.chapters);
      setTotalLessons(response.total_lessons);
      setCurrentStep(1);
      const numDocs = Math.ceil(response.total_lessons / 2);
      message.success(`成功生成 ${response.total_lessons} 份教案（${numDocs} 个文档）`);
    } catch (error: any) {
      message.error(error.message || '章节生成失败');
    } finally {
      setSplittingChapters(false);
    }
  };

  // Step 2: Create batch task
  const handleCreateBatchTask = async () => {
    // Use saved form values instead of form.getFieldsValue()
    const values = savedFormValues;

    // Validate required fields
    if (!values.template_id) {
      message.error('请选择教案模板');
      return;
    }

    if (!values.course_name || !values.subject || !values.grade) {
      message.error('请填写完整的课程信息');
      return;
    }

    if (!values.total_hours) {
      message.error('请填写总课时数');
      return;
    }

    if (!chapters || chapters.length === 0) {
      message.error('章节信息为空，请先生成章节或选择已有模板');
      return;
    }

    const request: BatchTaskCreateRequest = {
      course_name: values.course_name,
      subject: values.subject,
      grade: values.grade,
      template_id: values.template_id,
      total_hours: values.total_hours,
      hours_per_lesson: values.hours_per_lesson || 2,
      chapters: chapters,
      additional_requirements: values.additional_requirements,
    };

    setLoading(true);
    try {
      const response = await batchApi.createBatchTask(request);
      setTaskId(response.task_id);
      setCurrentStep(2);
      message.success('批量任务已创建，正在后台生成...');
    } catch (error: any) {
      message.error(error.message || '创建任务失败');
    } finally {
      setLoading(false);
    }
  };

  // Chapter table columns
  const chapterColumns = [
    {
      title: '序号',
      dataIndex: 'lesson_number',
      key: 'lesson_number',
      width: 80,
      render: (num: number) => `教案${num}`,
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
          {concepts?.map((concept, idx) => (
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
              total_hours: 64,
              hours_per_lesson: 2,
            }}
            preserve={true}
          >
            {/* Mode selection */}
            <Form.Item label="选择方式">
              <Radio.Group
                value={mode}
                onChange={(e) => {
                  setMode(e.target.value);
                  setChapters([]);
                  setTotalLessons(0);
                }}
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
                      label: `${t.course_name} - ${t.subject} - ${t.grade} (${t.total_hours}课时, ${t.chapters?.length || 0}份教案, 使用${t.use_count}次)`,
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
              <Input placeholder="例如：Java程序设计" size="large" disabled={mode === 'existing' && chapters.length > 0} />
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
                  disabled={mode === 'existing' && chapters.length > 0}
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
                  disabled={mode === 'existing' && chapters.length > 0}
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
                >
                  {templates.map((t) => (
                    <Select.Option key={t.id} value={t.id}>
                      {t.name}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Space>

            <Space size="large" align="start">
              <Form.Item
                name="total_hours"
                label="总课时数"
                rules={[{ required: true, type: 'number', min: 2, message: '请输入总课时数' }]}
              >
                <InputNumber
                  min={2}
                  max={200}
                  step={2}
                  disabled={mode === 'existing' && chapters.length > 0}
                  addonAfter="课时"
                  style={{ width: 150 }}
                />
              </Form.Item>

              <Form.Item
                name="hours_per_lesson"
                label="每份教案课时"
                rules={[{ required: true, type: 'number', min: 1 }]}
              >
                <InputNumber
                  min={1}
                  max={4}
                  disabled={mode === 'existing' && chapters.length > 0}
                  addonAfter="课时"
                  style={{ width: 150 }}
                />
              </Form.Item>

              <Form.Item label="生成统计" style={{ marginTop: 0 }}>
                <Alert
                  message={(() => {
                    const totalHours = form.getFieldValue('total_hours') || 64;
                    const hoursPerLesson = form.getFieldValue('hours_per_lesson') || 2;
                    const numLessons = Math.floor(totalHours / hoursPerLesson);
                    const numDocs = Math.ceil(numLessons / 2);
                    return `将生成 ${numLessons} 份教案，共 ${numDocs} 个文档`;
                  })()}
                  type="info"
                  showIcon
                />
              </Form.Item>
            </Space>

            {/* Chapter input mode for new courses */}
            {mode === 'new' && (
              <>
                <Divider orientation="left">章节内容</Divider>
                <Form.Item label="章节来源">
                  <Radio.Group
                    value={chapterInputMode}
                    onChange={(e) => setChapterInputMode(e.target.value)}
                  >
                    <Radio value="ai">
                      <FileTextOutlined /> AI自动生成章节
                    </Radio>
                    <Radio value="manual">
                      <EditOutlined /> 手动输入章节标题
                    </Radio>
                  </Radio.Group>
                </Form.Item>

                {chapterInputMode === 'manual' && (
                  <Form.Item
                    name="chapters_input"
                    label="章节标题（每行一个）"
                    rules={[{ required: true, message: '请输入章节标题' }]}
                    extra={`请输入 ${Math.floor((form.getFieldValue('total_hours') || 64) / (form.getFieldValue('hours_per_lesson') || 2))} 个章节标题，每行一个`}
                  >
                    <TextArea
                      rows={10}
                      placeholder={`第一章：Java语言概述\n第二章：Java基本语法\n第三章：面向对象编程基础\n...`}
                    />
                  </Form.Item>
                )}
              </>
            )}

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
                    {splittingChapters ? '生成中...' : (chapterInputMode === 'ai' ? '下一步：AI生成章节' : '下一步：解析章节')}
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

                      if (!values.template_id) {
                        message.error('请先选择教案模板');
                        return;
                      }

                      form.validateFields(['template_id', 'course_name', 'subject', 'grade', 'total_hours', 'hours_per_lesson'])
                        .then(() => {
                          // Save form values before switching step
                          setSavedFormValues(values);
                          setCurrentStep(1);
                          message.success('进入章节确认步骤');
                        })
                        .catch(() => {
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
            <Title level={4}>
              已准备 {chapters.length} 份教案，请审核并修改：
            </Title>
            <Paragraph type="secondary">
              您可以直接在表格中编辑课题和内容概述。每份教案 {savedFormValues.hours_per_lesson || 2} 课时，每个文档包含2份教案。
            </Paragraph>

            {/* Show course info and template selection */}
            <Card style={{ marginBottom: 16, backgroundColor: '#f5f5f5' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text strong>课程信息：</Text>
                  <Text style={{ marginLeft: 8 }}>
                    {savedFormValues.course_name} - {savedFormValues.subject} - {savedFormValues.grade}
                  </Text>
                  <Text style={{ marginLeft: 16 }}>
                    （{savedFormValues.total_hours}课时，{chapters.length}份教案，{Math.ceil(chapters.length / 2)}个文档）
                  </Text>
                </div>

                <div>
                  <Text strong>教案模板：</Text>
                  {savedFormValues.template_id ? (
                    <Text style={{ marginLeft: 8, color: '#52c41a' }}>
                      ✓ {templates.find(t => t.id === savedFormValues.template_id)?.name || '已选择'}
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
              rowKey="lesson_number"
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
                  disabled={!savedFormValues.template_id}
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
