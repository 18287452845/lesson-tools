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
 * - Optional chapter references, AI always splits by hours
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
  Radio,
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
  EditOutlined,
  BookOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import type {
  ChapterInfo,
  ChapterSplitRequest,
  ChapterSplitResponse,
  BatchTaskCreateRequest,
  BatchTask,
  TemplateInfo,
  CourseChapterTemplate,
  ClassInfo,
  TextbookInfo,
  FixedTemplateValidation,
  CoursePlanArtifactType,
} from '@/types';
import {
  SUBJECT_OPTIONS,
  GRADE_OPTIONS,
} from '@/types';
import { batchApi } from '@/services/batchApi';
import { templateApi, classApi } from '@/services/api';
import { textbookApi } from '@/services/textbookApi';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const OUTLINE_INDENT = 2;

const formatLocalDate = (value: Date): string => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const currentDate = new Date();
const academicYearStart = currentDate.getMonth() >= 7
  ? currentDate.getFullYear()
  : currentDate.getFullYear() - 1;
const defaultAcademicYear = `${academicYearStart}-${academicYearStart + 1}`;

type OutlineNode = {
  title: string;
  level: number;
  children: OutlineNode[];
};

const flattenOutlineToLines = (nodes: OutlineNode[], indent = 0): string[] => {
  const lines: string[] = [];
  nodes.forEach((node) => {
    lines.push(`${' '.repeat(indent)}${node.title}`);
    if (node.children.length > 0) {
      lines.push(...flattenOutlineToLines(node.children, indent + OUTLINE_INDENT));
    }
  });
  return lines;
};

const buildOutlineFromTextbook = (chapters: TextbookInfo['chapters']): OutlineNode[] => {
  const map = new Map<string, OutlineNode>();
  const sorted = [...chapters].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  const roots: OutlineNode[] = [];

  sorted.forEach((chapter) => {
    map.set(chapter.id, {
      title: chapter.chapter_title || chapter.chapter_number || '章节',
      level: 1,
      children: [],
    });
  });

  sorted.forEach((chapter) => {
    const node = map.get(chapter.id);
    if (!node) {
      return;
    }
    if (chapter.parent_chapter_id && map.has(chapter.parent_chapter_id)) {
      map.get(chapter.parent_chapter_id)?.children.push(node);
    } else {
      roots.push(node);
    }
  });

  return roots;
};

const BatchGenerate: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const selectedSupplementalArtifacts = (
    Form.useWatch('supplemental_artifacts', form) || []
  ) as CoursePlanArtifactType[];

  // Step state
  const [currentStep, setCurrentStep] = useState(0);

  // Chapter input mode for new courses: 'ai' or 'manual'
  const [chapterInputMode, setChapterInputMode] = useState<'ai' | 'manual'>('ai');

  // Selected cached template ID (for existing mode)
  const [selectedCachedTemplateId, setSelectedCachedTemplateId] = useState<string | undefined>();

  // Task type: 'normal' (generate and export ZIP) or 'draft' (save as drafts only)
  const [taskType, setTaskType] = useState<'normal' | 'draft'>('normal');

  // Step 1: Basic information
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [cachedTemplates, setCachedTemplates] = useState<CourseChapterTemplate[]>([]);
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [textbooks, setTextbooks] = useState<TextbookInfo[]>([]);
  const [fixedTemplateReports, setFixedTemplateReports] = useState<FixedTemplateValidation[]>([]);
  const [selectedTextbookId, setSelectedTextbookId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);

  // Saved form values (preserved across step changes)
  const [savedFormValues, setSavedFormValues] = useState<any>({});

  // Step 2: Chapters
  const [chapters, setChapters] = useState<ChapterInfo[]>([]);
  const [chapterOutline, setChapterOutline] = useState<string[][]>([]);
  const [splittingChapters, setSplittingChapters] = useState(false);

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
    loadTextbooks();
    templateApi.validateAllTemplates()
      .then(setFixedTemplateReports)
      .catch(() => setFixedTemplateReports([]));
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

  const loadTextbooks = async () => {
    try {
      const data = await textbookApi.listTextbooks({ status: 'active' });
      setTextbooks(data.textbooks);
    } catch (error) {
      console.error('Failed to load textbooks:', error);
    }
  };

  const applyChapters = (nextChapters: ChapterInfo[], outlines?: string[][]) => {
    setChapters(nextChapters);
    setChapterOutline(outlines ?? nextChapters.map(() => []));
  };

  // Handle selecting an existing cached template
  const handleSelectCachedTemplate = (templateId: string) => {
    const selected = cachedTemplates.find((t) => t.id === templateId);
    if (selected) {
      setSelectedCachedTemplateId(templateId);

      // Get current template_id to preserve it
      const currentTemplateId = form.getFieldValue('template_id');

      // Prepare form values
      const formValues: any = {
        course_name: selected.course_name,
        subject: selected.subject,
        grade: selected.grade,
        total_hours: selected.total_hours,
        hours_per_lesson: selected.hours_per_lesson ?? 2,
      };

      // Only include template_id if it has a value (to preserve user's selection)
      if (currentTemplateId) {
        formValues.template_id = currentTemplateId;
      }

      // Auto-fill form fields
      form.setFieldsValue(formValues);

      const chapterTitles = selected.chapters
        .map((chapter) => chapter.topic?.trim())
        .filter(Boolean)
        .join('\n');
      if (chapterTitles) {
        form.setFieldValue('chapters_input', chapterTitles);
      }

      // Load cached chapters as reference
      applyChapters(selected.chapters);

      if (currentTemplateId) {
        message.success(`已加载 ${selected.course_name} 的 ${selected.chapters.length} 个章节参考`);
      } else {
        message.success(`已加载 ${selected.course_name} 的 ${selected.chapters.length} 个章节参考，请选择教案模板后继续`);
      }
    }
  };

  // Handle selecting a textbook
  const handleSelectTextbook = async (textbookId: string) => {
    if (!textbookId) {
      setSelectedTextbookId(undefined);
      applyChapters([]);
      form.setFieldValue('chapters_input', '');
      return;
    }

    try {
      const textbook = await textbookApi.getTextbook(textbookId);
      setSelectedTextbookId(textbookId);
      // Clear cached template selection when textbook is selected
      setSelectedCachedTemplateId(undefined);

      // Get current template_id to preserve it
      const currentTemplateId = form.getFieldValue('template_id');

      // Prepare form values
      const formValues: any = {
        course_name: textbook.name,
        subject: textbook.subject,
        grade: textbook.grade,
        textbook_name: textbook.name,
      };

      // Only include template_id if it has a value
      if (currentTemplateId) {
        formValues.template_id = currentTemplateId;
      }

      // Auto-fill form fields
      form.setFieldsValue(formValues);

      // Pre-fill chapters_input with chapter titles (AI reference)
      const sortedChapters = [...textbook.chapters].sort(
        (a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)
      );
      const outline = buildOutlineFromTextbook(sortedChapters);
      const rootChapters = sortedChapters.filter((ch) => !ch.parent_chapter_id);
      const chapterTitles = flattenOutlineToLines(outline).join('\n');
      form.setFieldValue('chapters_input', chapterTitles);

      const chapters: ChapterInfo[] = rootChapters.map((ch, idx) => ({
        lesson_number: idx + 1,
        topic: ch.chapter_title || ch.chapter_number || `第${idx + 1}章`,
        content_summary: ch.content_summary || '',
        key_concepts: ch.key_concepts || [],
      }));

      applyChapters(chapters);

      message.success(`已加载 ${textbook.name} 的 ${chapters.length} 个章节参考`);
    } catch (error: any) {
      message.error(error.message || '加载教材失败');
    }
  };

  // Step 1: Submit basic info and split chapters
  const handleSplitChapters = async (values: any) => {
    const totalHours = Number(values.total_hours ?? form.getFieldValue('total_hours') ?? 0);
    const hoursPerLesson = Number(values.hours_per_lesson ?? form.getFieldValue('hours_per_lesson') ?? 2);
    const chaptersInput = values.chapters_input?.trim();

    // Save form values before switching step
    setSavedFormValues(values);

    const request: ChapterSplitRequest = {
      course_name: values.course_name,
      subject: values.subject,
      grade: values.grade,
      total_hours: values.total_hours,
      hours_per_lesson: values.hours_per_lesson ?? 2,
      additional_info: values.additional_info,
      chapters_input: chaptersInput || undefined,
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
          const expectedCount = Math.max(1, Math.floor(totalHours / hoursPerLesson));
          if (response.chapters.length !== expectedCount) {
            message.error(`AI生成章节数量为 ${response.chapters.length}，应为 ${expectedCount}。请重试。`);
            setSplittingChapters(false);
            return;
          }
          applyChapters(response.chapters);
          setCurrentStep(1);
          const numDocs = Math.ceil(response.chapters.length / 2);
          message.success(`成功生成 ${response.chapters.length} 份教案（${numDocs} 个文档）`);
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

    const expectedCount = Math.max(
      1,
      Math.floor(Number(values.total_hours) / Number(values.hours_per_lesson ?? 2)),
    );
    if (chapters.length !== expectedCount) {
      message.error(`章节数量为 ${chapters.length}，应为 ${expectedCount}。请返回上一步重新生成。`);
      return;
    }

    const requestedPlans = (values.supplemental_artifacts || []) as CoursePlanArtifactType[];
    const invalidPlanTemplate = fixedTemplateReports.find(
      (report) => requestedPlans.includes(report.type as CoursePlanArtifactType) && !report.is_valid,
    );
    if (taskType === 'normal' && invalidPlanTemplate) {
      message.error(`${invalidPlanTemplate.name}校验失败，请先恢复固定模板资源`);
      return;
    }

    setLoading(true);
    try {
      if (taskType === 'draft') {
        // Create draft task (no ZIP generation)
        const draftRequest: import('@/types').DraftTaskCreateRequest = {
          course_name: values.course_name,
          subject: values.subject,
          grade: values.grade,
          template_id: values.template_id,
          total_hours: values.total_hours,
          hours_per_lesson: values.hours_per_lesson ?? 2,
          chapters,
          textbook_name: values.textbook_name,
          location: values.location,
          online_resources: values.online_resources,
          generate_reflection: values.generate_reflection ?? false,
        };

        const response = await batchApi.createDraftTask(draftRequest);
        setTaskId(response.task_id);
        setCurrentStep(2);
        message.success('草稿任务已创建，正在后台生成教案内容...');
      } else {
        // Create normal batch task (with ZIP generation)
        const request: BatchTaskCreateRequest = {
          course_name: values.course_name,
          subject: values.subject,
          grade: values.grade,
          template_id: values.template_id,
          total_hours: values.total_hours,
          hours_per_lesson: values.hours_per_lesson ?? 2,
          chapters,
          start_week: values.start_week ?? 1,
          class_ids: values.class_ids ?? [],
          location: values.location,
          textbook_name: values.textbook_name,
          online_resources: values.online_resources,
          additional_requirements: values.additional_requirements,
          generate_reflection: values.generate_reflection ?? false,
          supplemental_artifacts: values.supplemental_artifacts ?? [],
          academic_year: values.academic_year,
          semester: values.semester,
          teacher_name: values.teacher_name,
          plan_date: values.plan_date,
          first_class_date: values.first_class_date,
          class_periods: values.class_periods,
        };

        const response = await batchApi.createBatchTask(request);
        setTaskId(response.task_id);
        setCurrentStep(2);
        message.success('批量任务已创建，正在后台生成...');
      }
    } catch (error: any) {
      message.error(error.message || '创建任务失败');
    } finally {
      setLoading(false);
    }
  };

  // Handle adding a new chapter
  const handleAddChapter = () => {
    const newChapter: ChapterInfo = {
      lesson_number: chapters.length + 1,
      topic: '',
      content_summary: '',
      key_concepts: [],
      experiment_name: '',
    };
    const nextChapters = [...chapters, newChapter];
    const nextOutline = [...chapterOutline, []];
    applyChapters(nextChapters, nextOutline);
    message.success('已添加新章节');
  };

  // Handle deleting a chapter
  const handleDeleteChapter = (index: number) => {
    if (chapters.length <= 1) {
      message.warning('至少需要保留一个章节');
      return;
    }

    const newChapters = chapters.filter((_, i) => i !== index);
    const newOutline = chapterOutline.filter((_, i) => i !== index);
    // Re-number chapters
    const renumberedChapters = newChapters.map((ch, idx) => ({
      ...ch,
      lesson_number: idx + 1,
    }));
    applyChapters(renumberedChapters, newOutline);
    message.success('已删除章节');
  };

  // Handle moving chapter up
  const handleMoveChapterUp = (index: number) => {
    if (index === 0) return;
    const newChapters = [...chapters];
    [newChapters[index - 1], newChapters[index]] = [newChapters[index], newChapters[index - 1]];
    const newOutline = [...chapterOutline];
    [newOutline[index - 1], newOutline[index]] = [newOutline[index], newOutline[index - 1]];
    // Re-number chapters
    const renumberedChapters = newChapters.map((ch, idx) => ({
      ...ch,
      lesson_number: idx + 1,
    }));
    applyChapters(renumberedChapters, newOutline);
  };

  // Handle moving chapter down
  const handleMoveChapterDown = (index: number) => {
    if (index === chapters.length - 1) return;
    const newChapters = [...chapters];
    [newChapters[index], newChapters[index + 1]] = [newChapters[index + 1], newChapters[index]];
    const newOutline = [...chapterOutline];
    [newOutline[index], newOutline[index + 1]] = [newOutline[index + 1], newOutline[index]];
    // Re-number chapters
    const renumberedChapters = newChapters.map((ch, idx) => ({
      ...ch,
      lesson_number: idx + 1,
    }));
    applyChapters(renumberedChapters, newOutline);
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
      render: (text: string, _record: ChapterInfo, index: number) => {
        const outlineLines = chapterOutline[index] || [];
        return (
          <div>
            <Input
              value={text}
              placeholder="请输入课题名称"
              onChange={(e) => {
                const newChapters = [...chapters];
                newChapters[index].topic = e.target.value;
                setChapters(newChapters);
              }}
            />
            {outlineLines.length > 0 && (
              <Text
                type="secondary"
                style={{ display: 'block', marginTop: 6, whiteSpace: 'pre-wrap', fontSize: 12 }}
              >
                {outlineLines.join('\n')}
              </Text>
            )}
          </div>
        );
      },
    },
    {
      title: '内容概述',
      dataIndex: 'content_summary',
      key: 'content_summary',
      render: (text: string, _record: ChapterInfo, index: number) => (
        <TextArea
          value={text}
          rows={2}
          placeholder="请输入内容概述"
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
      render: (concepts: string[] = [], _record: ChapterInfo, index: number) => (
        <Select
          mode="tags"
          value={concepts}
          placeholder="输入后按回车添加"
          style={{ width: '100%' }}
          onChange={(value: string[]) => {
            const newChapters = [...chapters];
            newChapters[index].key_concepts = value;
            setChapters(newChapters);
          }}
          tokenSeparators={[',', '，']}
        />
      ),
    },
    {
      title: '实验项目（可选）',
      dataIndex: 'experiment_name',
      key: 'experiment_name',
      width: 220,
      render: (text: string | undefined, _record: ChapterInfo, index: number) => (
        <Input
          value={text}
          placeholder="留空则按每周课题自动生成"
          onChange={(e) => {
            const newChapters = [...chapters];
            newChapters[index].experiment_name = e.target.value;
            setChapters(newChapters);
          }}
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, _record: ChapterInfo, index: number) => (
        <Space>
          <Button
            type="text"
            size="small"
            disabled={index === 0}
            onClick={() => handleMoveChapterUp(index)}
            title="上移"
          >
            ↑
          </Button>
          <Button
            type="text"
            size="small"
            disabled={index === chapters.length - 1}
            onClick={() => handleMoveChapterDown(index)}
            title="下移"
          >
            ↓
          </Button>
          <Button
            type="text"
            danger
            size="small"
            disabled={chapters.length <= 1}
            onClick={() => handleDeleteChapter(index)}
            title="删除"
          >
            删除
          </Button>
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

  const shouldShowFailureAlert = Boolean(
    batchTask
    && batchTask.failed_count > 0
    && (batchTask.status === 'completed' || batchTask.status === 'failed')
  );

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
              supplemental_artifacts: [],
              academic_year: defaultAcademicYear,
              semester: 2,
              plan_date: formatLocalDate(currentDate),
            }}
            preserve={true}
          >
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
              {/* Cached Template Selection - Optional */}
              {cachedTemplates.length > 0 && (
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={24}>
                    <Form.Item
                      label="快速填充（可选）"
                      tooltip="选择已有的课程章节模板，快速填充课程信息"
                      style={{ marginBottom: 0 }}
                    >
                      <Select
                        placeholder="选择已有的课程章节模板"
                        size="large"
                        showSearch
                        allowClear
                        value={selectedCachedTemplateId}
                        filterOption={(input, option) =>
                          (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                        }
                        options={cachedTemplates.map((t) => ({
                          label: `${t.course_name} - ${t.subject} - ${t.grade} (${t.total_hours}课时, ${t.chapters?.length || 0}份教案)`,
                          value: t.id,
                        }))}
                        onChange={(value) => {
                          if (value) {
                            handleSelectCachedTemplate(value);
                          } else {
                            setSelectedCachedTemplateId(undefined);
                            applyChapters([]);
                          }
                        }}
                      />
                    </Form.Item>
                  </Col>
                </Row>
              )}

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
                      disabled={!!selectedCachedTemplateId && chapters.length > 0}
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
                      disabled={!!selectedCachedTemplateId && chapters.length > 0}
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
                      disabled={!!selectedCachedTemplateId && chapters.length > 0}
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

              <Row gutter={16}>
                <Col xs={24} sm={12}>
                  <Form.Item
                    label="选择教材（可选）"
                    tooltip="选择教材后将自动加载章节信息"
                  >
                    <Select
                      placeholder="选择教材"
                      size="large"
                      showSearch
                      allowClear
                      value={selectedTextbookId}
                      onChange={handleSelectTextbook}
                      disabled={!!selectedCachedTemplateId && chapters.length > 0}
                      filterOption={(input, option) =>
                        (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                      }
                      options={textbooks.map((t) => ({
                        label: `${t.name}${t.author ? ' - ' + t.author : ''}${t.chapters?.length ? ` (${t.chapters.length}章节)` : ''}`,
                        value: t.id,
                      }))}
                    />
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary">
                        选择后将自动填充课程信息和章节内容
                      </Text>
                    </div>
                  </Form.Item>
                </Col>
                {selectedTextbookId && (
                  <Col xs={24} sm={12}>
                    <div style={{ paddingTop: 30 }}>
                      <Tag color="blue" icon={<BookOutlined />}>
                        已加载 {chapters.length} 个教材章节
                      </Tag>
                    </div>
                  </Col>
                )}
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
                      disabled={!!selectedCachedTemplateId && chapters.length > 0}
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
                      disabled={!!selectedCachedTemplateId && chapters.length > 0}
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
                      disabled={!!selectedCachedTemplateId && chapters.length > 0}
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
                  const numLessons = Math.max(1, Math.floor(totalHours / hoursPerLesson));
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
                    rules={[
                      {
                        required: selectedSupplementalArtifacts.length > 0,
                        message: '同步生成授课/实验计划时必须选择班级',
                      },
                    ]}
                  >
                    <Select
                      mode="multiple"
                      placeholder="选择班级（可多选）"
                      size="large"
                      disabled={!!selectedCachedTemplateId && chapters.length > 0}
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
                    rules={[
                      {
                        required: selectedSupplementalArtifacts.includes('experiment_plan'),
                        message: '生成实验计划时请填写实验室/授课地点',
                      },
                    ]}
                  >
                    <Input
                      placeholder="例如：教学楼301教室"
                      size="large"
                      disabled={!!selectedCachedTemplateId && chapters.length > 0}
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
                      disabled={!!selectedCachedTemplateId && chapters.length > 0}
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
                      disabled={!!selectedCachedTemplateId && chapters.length > 0}
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

            <Card
              title={
                <Space>
                  <FileTextOutlined />
                  <span>同步生成学期计划（可选）</span>
                </Space>
              }
              style={{ marginBottom: 16 }}
            >
              <Form.Item
                name="supplemental_artifacts"
                label="固定格式计划"
                extra="授课计划按课程生成 1 份并合并班级；实验计划按课程与班级分别生成。"
              >
                <Checkbox.Group
                  disabled={taskType === 'draft'}
                  options={[
                    { label: '教师授课计划表', value: 'teaching_plan' },
                    { label: '课程实验计划表', value: 'experiment_plan' },
                  ]}
                />
              </Form.Item>

              {selectedSupplementalArtifacts.length > 0 && (
                <>
                  <Alert
                    type="info"
                    showIcon
                    message="计划将与批量教案一起打包"
                    description="系统以每两份教案作为一周课表：授课计划最多 16 周，实验计划最多 18 条。实验项目可在下一步逐项填写；全部留空时按课题自动生成。"
                    style={{ marginBottom: 16 }}
                  />
                  <Space wrap style={{ marginBottom: 16 }}>
                    {selectedSupplementalArtifacts.map((type) => {
                      const report = fixedTemplateReports.find((item) => item.type === type);
                      const label = type === 'teaching_plan' ? '云林授课计划模板' : '云林实验计划模板';
                      return (
                        <Tag key={type} color={report?.is_valid ? 'success' : report ? 'error' : 'default'}>
                          {label} · {report?.is_valid ? '校验通过' : report ? '校验失败' : '生成前校验'}
                        </Tag>
                      );
                    })}
                  </Space>
                  <Row gutter={16}>
                    <Col xs={24} sm={12} lg={6}>
                      <Form.Item
                        name="academic_year"
                        label="学年"
                        rules={[
                          { required: true, message: '请输入学年' },
                          { pattern: /^\d{4}-\d{4}$/, message: '格式示例：2025-2026' },
                        ]}
                      >
                        <Input placeholder="2025-2026" />
                      </Form.Item>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                      <Form.Item name="semester" label="学期" rules={[{ required: true }]}>
                        <Select options={[{ label: '第1学期', value: 1 }, { label: '第2学期', value: 2 }]} />
                      </Form.Item>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                      <Form.Item name="teacher_name" label="教师姓名" rules={[{ required: true, message: '请输入教师姓名' }]}>
                        <Input placeholder="例如：李阳" />
                      </Form.Item>
                    </Col>
                    {selectedSupplementalArtifacts.includes('experiment_plan') && (
                      <>
                        <Col xs={24} sm={12} lg={6}>
                          <Form.Item name="plan_date" label="制表日期" rules={[{ required: true, message: '请选择制表日期' }]}>
                            <Input type="date" />
                          </Form.Item>
                        </Col>
                        <Col xs={24} sm={12}>
                          <Form.Item
                            name="first_class_date"
                            label="首课日期"
                            tooltip="系统按每周一次自动推算后续实验日期"
                            rules={[{ required: true, message: '请选择首课日期' }]}
                          >
                            <Input type="date" />
                          </Form.Item>
                        </Col>
                        <Col xs={24} sm={12}>
                          <Form.Item
                            name="class_periods"
                            label="上课节次"
                            rules={[{ required: true, message: '请输入上课节次' }]}
                          >
                            <Input placeholder="例如：3-4" />
                          </Form.Item>
                        </Col>
                      </>
                    )}
                  </Row>
                </>
              )}
            </Card>

            {/* Chapter Content Card */}
            <Card
              title={
                <Space>
                  <EditOutlined />
                  <span>章节内容</span>
                  {(selectedTextbookId || selectedCachedTemplateId) && chapters.length > 0 && (
                    <Tag color="blue">已加载 {chapters.length} 个章节参考</Tag>
                  )}
                </Space>
              }
              style={{ marginBottom: 16 }}
            >
              {/* Show chapter source selection only if no textbook/cache selected */}
              {!selectedTextbookId && !selectedCachedTemplateId && (
                <Form.Item label="章节来源（参考）">
                  <Radio.Group
                    value={chapterInputMode}
                    onChange={(e) => setChapterInputMode(e.target.value)}
                    size="large"
                  >
                    <Radio value="ai">
                      <FileTextOutlined /> AI根据课时自动生成
                    </Radio>
                    <Radio value="manual">
                      <EditOutlined /> 提供章节参考（可选）
                    </Radio>
                  </Radio.Group>
                </Form.Item>
              )}

              {/* Show chapters_input if manual mode or textbook/cache selected */}
              {(chapterInputMode === 'manual' || selectedTextbookId || selectedCachedTemplateId) && (
                <Form.Item
                  name="chapters_input"
                  label={selectedTextbookId || selectedCachedTemplateId ? "章节标题（参考，可编辑）" : "章节标题（参考，每行一个）"}
                  extra={selectedTextbookId || selectedCachedTemplateId
                    ? "已从教材/模板加载章节，AI将根据总课时重新划分"
                    : "可选填写，AI将根据总课时重新划分；支持用空格缩进表示子章节"}
                >
                  <TextArea
                    rows={10}
                    placeholder={`第一章：Java语言概述\n  1.1 发展历史\n  1.2 生态与应用\n第二章：Java基本语法\n  2.1 数据类型\n  2.2 流程控制\n第三章：面向对象编程基础\n...`}
                  />
                </Form.Item>
              )}

              <Form.Item name="additional_info" label="补充说明（可选）">
                <TextArea
                  rows={3}
                  placeholder="例如：本课程侧重实践操作，每周需包含实验环节..."
                />
              </Form.Item>
            </Card>

            {/* Action Buttons */}
            <Form.Item style={{ marginBottom: 0 }}>
              <Space size="large">
                <Button
                  type="primary"
                  htmlType="submit"
                  size="large"
                  loading={splittingChapters}
                  icon={<FileTextOutlined />}
                >
                  {splittingChapters
                    ? '生成中...'
                    : '下一步：AI生成章节'
                  }
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
            <Card
              title={
                <Space>
                  <span>章节列表</span>
                  <Tag color="blue">{chapters.length} 个章节</Tag>
                </Space>
              }
              extra={
                <Button
                  type="primary"
                  size="small"
                  onClick={handleAddChapter}
                  icon={<PlusOutlined />}
                >
                  新增章节
                </Button>
              }
              style={{ marginBottom: 16 }}
            >
              <Alert
                message="编辑提示"
                description="可直接修改课题、内容概述、核心概念和实验项目。实验项目全部留空时会按每周课题自动生成；只填写部分时，仅填写过的周次进入实验计划。"
                type="info"
                showIcon
                closable
                style={{ marginBottom: 16 }}
              />
              <Table
                columns={chapterColumns}
                dataSource={chapters}
                rowKey="lesson_number"
                pagination={false}
                scroll={{ y: 400 }}
              />
            </Card>

            {/* Task Type Selection Card */}
            <Card
              title={
                <Space>
                  <FileTextOutlined />
                  <span>任务类型</span>
                </Space>
              }
              style={{ marginBottom: 16 }}
            >
              <Radio.Group
                value={taskType}
                onChange={(e) => {
                  const nextType = e.target.value as 'normal' | 'draft';
                  setTaskType(nextType);
                  if (nextType === 'draft' && savedFormValues.supplemental_artifacts?.length) {
                    message.info('草稿模式不导出文件，因此不会同步生成授课计划或实验计划');
                  }
                }}
                size="large"
              >
                <Space direction="vertical" size="middle">
                  <Radio value="normal">
                    <Space direction="vertical" size={0}>
                      <Text strong>正常生成（导出ZIP）</Text>
                      <Text type="secondary" style={{ fontSize: 12, marginLeft: 24 }}>
                        立即生成完整教案Word文档，打包为ZIP文件供下载
                      </Text>
                    </Space>
                  </Radio>
                  <Radio value="draft">
                    <Space direction="vertical" size={0}>
                      <Text strong>预生成草稿（仅保存到草稿箱）</Text>
                      <Text type="secondary" style={{ fontSize: 12, marginLeft: 24 }}>
                        生成教案内容并保存到草稿箱，可随时编辑、重新生成字段，再选择性导出
                      </Text>
                    </Space>
                  </Radio>
                </Space>
              </Radio.Group>
              {taskType === 'draft' && savedFormValues.supplemental_artifacts?.length > 0 && (
                <Alert
                  type="warning"
                  showIcon
                  message="草稿模式仅保存教案内容，已选学期计划不会生成"
                  style={{ marginTop: 16 }}
                />
              )}
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

              {shouldShowFailureAlert && (
                <Alert
                  message={`仍有 ${batchTask.failed_count} 份教案未成功生成，可稍后重试`}
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
