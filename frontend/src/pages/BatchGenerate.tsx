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
  List,
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
  Checkbox,
  Row,
  Col,
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
  ClassInfo,
} from '@/types';
import {
  SUBJECT_OPTIONS,
  GRADE_OPTIONS,
} from '@/types';
import { batchApi } from '@/services/batchApi';
import { templateApi, classApi } from '@/services/api';

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
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [loading, setLoading] = useState(false);

  // Saved form values (preserved across step changes)
  const [savedFormValues, setSavedFormValues] = useState<any>({});

  // Step 2: Chapters
  const [chapters, setChapters] = useState<ChapterInfo[]>([]);
  const [splittingChapters, setSplittingChapters] = useState(false);
  const [totalLessons, setTotalLessons] = useState(0);

  // Streaming state
  const [streamProgress, setStreamProgress] = useState({ current: 0, total: 0, message: '' });
  const [streamedChapters, setStreamedChapters] = useState<ChapterInfo[]>([]);

  // Step 3: Progress
  const [batchTask, setBatchTask] = useState<BatchTask | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);

  // Load templates on mount
  useEffect(() => {
    loadTemplates();
    loadCachedTemplates();
    loadClasses();
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

  const loadClasses = async () => {
    try {
      const data = await classApi.listClasses();
      setClasses(data.classes);
    } catch (error) {
      console.error('Failed to load classes:', error);
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
    setStreamedChapters([]);
    setStreamProgress({ current: 0, total: 0, message: '初始化中...' });

    try {
      // Use streaming API
      await batchApi.splitChaptersStream(
        request,
        // onProgress callback
        (current: number, total: number, message: string) => {
          setStreamProgress({ current, total, message });
        },
        // onChapter callback
        (chapter: ChapterInfo) => {
          setStreamedChapters((prev) => [...prev, chapter]);
        },
        // onComplete callback
        (response: ChapterSplitResponse) => {
          setChapters(response.chapters);
          setTotalLessons(response.total_lessons);
          setCurrentStep(1);
          const numDocs = Math.ceil(response.total_lessons / 2);
          message.success(`成功生成 ${response.total_lessons} 份教案（${numDocs} 个文档）`);
          setSplittingChapters(false);
        },
        // onError callback
        (errorMessage: string) => {
          message.error(errorMessage || '章节生成失败');
          setSplittingChapters(false);
        }
      );
    } catch (error: any) {
      message.error(error.message || '章节生成失败');
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
      start_week: values.start_week || 1,
      class_ids: values.class_ids || [],
      additional_requirements: values.additional_requirements,
      generate_reflection: values.generate_reflection || false,
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
            {/* Mode Selection Card */}
            <Card
              title={
                <Space>
                  <FileTextOutlined />
                  <span>选择创建方式</span>
                </Space>
              }
              style={{ marginBottom: 16 }}
            >
              <Radio.Group
                value={mode}
                onChange={(e) => {
                  setMode(e.target.value);
                  setChapters([]);
                  setTotalLessons(0);
                  // Reset form when switching modes
                  form.resetFields(['course_name', 'subject', 'grade', 'total_hours', 'hours_per_lesson']);
                }}
                size="large"
                style={{ width: '100%' }}
              >
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Radio.Button value="new" style={{ width: '100%', textAlign: 'center' }}>
                      <FileTextOutlined /> 创建新课程
                    </Radio.Button>
                  </Col>
                  <Col span={12}>
                    <Radio.Button value="existing" style={{ width: '100%', textAlign: 'center' }}>
                      <HistoryOutlined /> 使用已有模板
                    </Radio.Button>
                  </Col>
                </Row>
              </Radio.Group>

              {/* Existing template selection */}
              {mode === 'existing' && (
                <div style={{ marginTop: 16 }}>
                  <Form.Item label="选择课程章节模板" style={{ marginBottom: 0 }}>
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
                        选择后将自动填充课程信息和章节内容
                      </Text>
                    </div>
                  </Form.Item>
                </div>
              )}
            </Card>

            {/* Course Information Card */}
            <Card
              title={
                <Space>
                  <FileTextOutlined />
                  <span>课程基本信息</span>
                </Space>
              }
              style={{ marginBottom: 16 }}
            >
              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item
                    name="course_name"
                    label="课程名称"
                    rules={[{ required: true, message: '请输入课程名称' }]}
                  >
                    <Input
                      placeholder="例如：Java程序设计"
                      size="large"
                      disabled={mode === 'existing' && chapters.length > 0}
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} sm={8}>
                  <Form.Item
                    name="subject"
                    label="学科"
                    rules={[{ required: true, message: '请选择学科' }]}
                  >
                    <Select
                      placeholder="选择学科"
                      size="large"
                      options={SUBJECT_OPTIONS.map((s) => ({ label: s, value: s }))}
                      showSearch
                      disabled={mode === 'existing' && chapters.length > 0}
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} sm={8}>
                  <Form.Item
                    name="grade"
                    label="年级"
                    rules={[{ required: true, message: '请选择年级' }]}
                  >
                    <Select
                      placeholder="选择年级"
                      size="large"
                      options={GRADE_OPTIONS.map((g) => ({ label: g, value: g }))}
                      showSearch
                      disabled={mode === 'existing' && chapters.length > 0}
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} sm={8}>
                  <Form.Item
                    name="template_id"
                    label="教案模板"
                    rules={[{ required: true, message: '请选择模板' }]}
                  >
                    <Select
                      placeholder="选择模板"
                      size="large"
                      showSearch
                    >
                      {templates.map((t) => (
                        <Select.Option key={t.id} value={t.id}>
                          {t.name}
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            {/* Hours Configuration Card */}
            <Card
              title={
                <Space>
                  <ClockCircleOutlined />
                  <span>课时配置</span>
                </Space>
              }
              style={{ marginBottom: 16 }}
            >
              <Row gutter={16}>
                <Col xs={24} sm={8}>
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
                      size="large"
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} sm={8}>
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
                      size="large"
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} sm={8}>
                  <Form.Item
                    name="start_week"
                    label="起始周次"
                    initialValue={1}
                    tooltip="第1个文档对应的周次"
                  >
                    <InputNumber
                      min={1}
                      max={20}
                      disabled={mode === 'existing' && chapters.length > 0}
                      addonAfter="周"
                      size="large"
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Alert
                message={(() => {
                  const totalHours = form.getFieldValue('total_hours') || 64;
                  const hoursPerLesson = form.getFieldValue('hours_per_lesson') || 2;
                  const numLessons = Math.floor(totalHours / hoursPerLesson);
                  const numDocs = Math.ceil(numLessons / 2);
                  return `预计生成 ${numLessons} 份教案，共 ${numDocs} 个文档`;
                })()}
                type="info"
                showIcon
              />
            </Card>

            {/* Class & Options Card */}
            <Card
              title={
                <Space>
                  <CheckCircleOutlined />
                  <span>授课设置</span>
                </Space>
              }
              style={{ marginBottom: 16 }}
            >
              <Row gutter={16}>
                <Col xs={24} sm={12}>
                  <Form.Item
                    name="class_ids"
                    label="授课班级"
                    tooltip="可多选，留空则不显示授课班级"
                  >
                    <Select
                      mode="multiple"
                      placeholder="选择班级（可多选）"
                      size="large"
                      disabled={mode === 'existing' && chapters.length > 0}
                      options={classes.map((c) => ({ label: c.name, value: c.id }))}
                      allowClear
                      showSearch
                      filterOption={(input, option) =>
                        (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                      }
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} sm={12}>
                  <Form.Item
                    name="location"
                    label="授课地点"
                    tooltip="所有教案共用同一地点"
                  >
                    <Input
                      placeholder="例如：教学楼301教室"
                      size="large"
                      disabled={mode === 'existing' && chapters.length > 0}
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} sm={12}>
                  <Form.Item
                    name="textbook_name"
                    label="教材名称"
                  >
                    <Input
                      placeholder="例如：《Python程序设计基础》第3版"
                      size="large"
                      disabled={mode === 'existing' && chapters.length > 0}
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} sm={12}>
                  <Form.Item
                    name="online_resources"
                    label="网络资源（AI生成）"
                    tooltip="留空则由AI根据每个教案课题自动生成相关网络资源，也可手动填写（所有教案共用）"
                    extra="留空由AI生成，或手动填写（所有教案共用）"
                  >
                    <Input
                      placeholder="留空由AI生成，或填写：慕课平台、教学视频链接等"
                      size="large"
                      disabled={mode === 'existing' && chapters.length > 0}
                    />
                  </Form.Item>
                </Col>

                <Col xs={24}>
                  <Form.Item
                    name="generate_reflection"
                    valuePropName="checked"
                    tooltip="勾选后将在生成教案时包含教学反思内容"
                  >
                    <Checkbox style={{ fontSize: 16 }}>同时生成教学反思</Checkbox>
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            {/* Chapter Content Card (for new courses only) */}
            {mode === 'new' && (
              <Card
                title={
                  <Space>
                    <EditOutlined />
                    <span>章节内容</span>
                  </Space>
                }
                style={{ marginBottom: 16 }}
              >
                <Form.Item label="章节来源">
                  <Radio.Group
                    value={chapterInputMode}
                    onChange={(e) => setChapterInputMode(e.target.value)}
                    size="large"
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
              </Card>
            )}

            {/* Additional Information Card */}
            <Card
              title={
                <Space>
                  <ExclamationCircleOutlined />
                  <span>补充信息</span>
                </Space>
              }
              style={{ marginBottom: 16 }}
            >
              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item name="additional_info" label="补充说明（可选）">
                    <TextArea
                      rows={3}
                      placeholder="例如：本课程侧重实践操作，每周需包含实验环节..."
                    />
                  </Form.Item>
                </Col>
                <Col span={24}>
                  <Form.Item name="additional_requirements" label="额外要求（可选）">
                    <TextArea
                      rows={3}
                      placeholder="对生成的教案有特殊要求，例如：教学方法、重点难点等..."
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            {/* Action Buttons */}
            {mode === 'new' && (
              <>
                <Form.Item style={{ marginBottom: 0 }}>
                  <Space size="large">
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

                {/* Streaming Progress Display */}
                {splittingChapters && (
                  <Card style={{ marginTop: 16 }} bordered={false}>
                    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                      <Progress
                        percent={streamProgress.total > 0 ? Math.round((streamProgress.current / streamProgress.total) * 100) : 0}
                        status="active"
                        strokeColor={{
                          '0%': '#108ee9',
                          '100%': '#87d068',
                        }}
                        trailColor="rgba(0, 0, 0, 0.06)"
                      />
                      <div style={{ textAlign: 'center' }}>
                        <Text type={streamProgress.message ? 'secondary' : undefined}>
                          {streamProgress.message || '正在生成章节...'}
                        </Text>
                      </div>
                      {streamedChapters.length > 0 && (
                        <div style={{ marginTop: 16 }}>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            已生成 {streamedChapters.length} 个章节：
                          </Text>
                          <List
                            size="small"
                            dataSource={streamedChapters}
                            renderItem={(chapter) => (
                              <List.Item style={{ padding: '4px 0' }}>
                                <Space>
                                  <Tag color="blue">教案{chapter.lesson_number}</Tag>
                                  <Text>{chapter.topic}</Text>
                                </Space>
                              </List.Item>
                            )}
                            style={{
                              marginTop: 8,
                              maxHeight: 200,
                              overflow: 'auto',
                              backgroundColor: '#fafafa',
                              borderRadius: 4,
                              padding: '8px 12px',
                            }}
                          />
                        </div>
                      )}
                    </Space>
                  </Card>
                )}
              </>
            )}

            {mode === 'existing' && chapters.length > 0 && (
              <Form.Item style={{ marginBottom: 0 }}>
                <Space size="large">
                  <Button
                    type="primary"
                    size="large"
                    icon={<CheckCircleOutlined />}
                    onClick={() => {
                      const values = form.getFieldsValue();
                      if (!values.template_id) {
                        message.error('请先选择教案模板');
                        return;
                      }
                      form.validateFields(['template_id', 'course_name', 'subject', 'grade', 'total_hours', 'hours_per_lesson'])
                        .then(() => {
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
            <Title level={4}>确认章节信息</Title>
            <Paragraph type="secondary">
              已准备 {chapters.length} 份教案，请审核并修改课题和内容概述
            </Paragraph>

            {/* Course Summary Card */}
            <Card
              style={{ marginBottom: 16, backgroundColor: '#f0f5ff', borderColor: '#adc6ff' }}
            >
              <Row gutter={16}>
                <Col xs={24} sm={12}>
                  <Space direction="vertical" size={4}>
                    <Text type="secondary">课程信息</Text>
                    <Text strong style={{ fontSize: 16 }}>
                      {savedFormValues.course_name} - {savedFormValues.subject} - {savedFormValues.grade}
                    </Text>
                    <Text type="secondary">
                      {savedFormValues.total_hours}课时 / {chapters.length}份教案 / {Math.ceil(chapters.length / 2)}个文档
                    </Text>
                  </Space>
                </Col>
                <Col xs={24} sm={12}>
                  <Space direction="vertical" size={4}>
                    <Text type="secondary">教案模板</Text>
                    {savedFormValues.template_id ? (
                      <>
                        <Text strong style={{ fontSize: 16, color: '#52c41a' }}>
                          <CheckCircleOutlined /> {templates.find(t => t.id === savedFormValues.template_id)?.name || '已选择'}
                        </Text>
                        <Text type="secondary">每份教案 {savedFormValues.hours_per_lesson || 2} 课时</Text>
                      </>
                    ) : (
                      <Text type="danger" strong>
                        <ExclamationCircleOutlined /> 请返回上一步选择教案模板
                      </Text>
                    )}
                  </Space>
                </Col>
              </Row>
            </Card>

            {/* Chapter Edit Table */}
            <Card title="章节列表" style={{ marginBottom: 16 }}>
              <Table
                columns={chapterColumns}
                dataSource={chapters}
                rowKey="lesson_number"
                pagination={false}
                scroll={{ y: 400 }}
              />
            </Card>

            {/* Action Buttons */}
            <Card bordered={false}>
              <Space size="large">
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
                <Button size="large" onClick={() => navigate('/')}>
                  取消
                </Button>
              </Space>
            </Card>
          </div>
        )}

        {/* Step 3: Progress */}
        {currentStep === 2 && batchTask && (
          <div>
            <Title level={4}>生成进度</Title>

            {/* Status Card */}
            <Card
              style={{ marginBottom: 16 }}
            >
              <Row gutter={16} align="middle">
                <Col xs={24} sm={12}>
                  <Space direction="vertical" size={4}>
                    <Text type="secondary">课程名称</Text>
                    <Text strong style={{ fontSize: 18 }}>{batchTask.course_name}</Text>
                  </Space>
                </Col>
                <Col xs={24} sm={12}>
                  <Space direction="vertical" size={4}>
                    <Text type="secondary">状态</Text>
                    {getStatusBadge(batchTask.status)}
                  </Space>
                </Col>
              </Row>
            </Card>

            {/* Progress Card */}
            <Card
              title={
                <Space>
                  <ClockCircleOutlined />
                  <span>生成进度</span>
                </Space>
              }
              style={{ marginBottom: 16 }}
            >
              <Progress
                percent={Math.round((batchTask.completed_count / batchTask.total_count) * 100)}
                status={
                  batchTask.status === 'completed'
                    ? 'success'
                    : batchTask.status === 'failed'
                    ? 'exception'
                    : 'active'
                }
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
              <div style={{ marginTop: 16, textAlign: 'center' }}>
                <Text strong style={{ fontSize: 16 }}>
                  {batchTask.completed_count} / {batchTask.total_count}
                </Text>
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  份教案已生成
                </Text>
              </div>

              {batchTask.failed_count > 0 && (
                <Alert
                  message={`${batchTask.failed_count} 份教案生成失败，请稍后重试`}
                  type="warning"
                  showIcon
                  style={{ marginTop: 16 }}
                />
              )}

              {batchTask.error_message && (
                <Alert
                  message={`错误：${batchTask.error_message}`}
                  type="error"
                  showIcon
                  style={{ marginTop: 16 }}
                />
              )}

              {batchTask.status === 'processing' && (
                <div style={{ marginTop: 16, textAlign: 'center' }}>
                  <Spin /> <Text type="secondary">正在生成教案，请稍候...</Text>
                </div>
              )}

              {batchTask.status === 'completed' && (
                <Alert
                  message="批量生成完成！"
                  type="success"
                  showIcon
                  style={{ marginTop: 16 }}
                />
              )}
            </Card>

            {/* Action Buttons */}
            <Card bordered={false}>
              <Space size="large">
                {batchTask.status === 'completed' && (
                  <>
                    <Button
                      type="primary"
                      size="large"
                      onClick={() => navigate('/batch-downloads')}
                      icon={<FileTextOutlined />}
                    >
                      前往下载页面
                    </Button>
                    <Button
                      size="large"
                      onClick={() => navigate('/')}
                    >
                      返回首页
                    </Button>
                  </>
                )}
                {batchTask.status === 'processing' && (
                  <Button
                    size="large"
                    onClick={() => navigate('/')}
                  >
                    返回首页
                  </Button>
                )}
                {batchTask.status === 'failed' && (
                  <>
                    <Button
                      size="large"
                      onClick={() => setCurrentStep(0)}
                    >
                      返回上一步
                    </Button>
                    <Button
                      size="large"
                      onClick={() => navigate('/')}
                    >
                      返回首页
                    </Button>
                  </>
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
