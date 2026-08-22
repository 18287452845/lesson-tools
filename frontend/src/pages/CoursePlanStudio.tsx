/**
 * 学期计划制作（授课计划 / 实验计划）
 *
 * 从已生成的教案中勾选多份，生成学期级授课计划表与课程实验计划表；
 * 导出前可编辑每课的课题、重点、难点、作业与实验名称。
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Collapse,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  message,
  Popconfirm,
  Select,
  Space,
  Steps,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  ArrowLeftOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  FileDoneOutlined,
  PlusOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { TableRowSelection } from 'antd/es/table/interface';
import { classApi, templateApi } from '../services/api';
import lessonPlanApi from '../services/lessonPlanApi';
import coursePlanApi from '../services/coursePlanApi';
import type {
  ClassInfo,
  CoursePlanArtifactType,
  CoursePlanChapter,
  CoursePlanDetail,
  CoursePlanListItem,
  CoursePlanCreateRequest,
  CoursePlanUpdateRequest,
  ExperimentClassSchedule,
  FixedTemplateValidation,
  LessonPlan,
} from '../types';

const { Title, Text } = Typography;

const MAX_LESSONS = 36;
const WEEKDAY_LABELS = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'];
const PLAN_TYPE_LABELS: Record<CoursePlanArtifactType, string> = {
  teaching_plan: '授课计划',
  experiment_plan: '实验计划',
};
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

function displayWidth(value: string): number {
  let width = 0;
  for (const char of value) {
    width += /[\u2e80-\ua4cf\uac00-\ud7af\uf900-\ufaff\uff00-\uffef]/.test(char) ? 2 : 1;
  }
  return width;
}

function validateExperimentNameClient(name: string, group: number): string | null {
  if (!name.trim()) return `第 ${group} 组实验名称不能为空`;
  if (name.length > 18) return `第 ${group} 组实验名称不能超过 18 个字符`;
  if (displayWidth(name) > 36) return `第 ${group} 组实验名称过宽，无法在模板中保持单行`;
  return null;
}

function homeworkLines(homework: CoursePlanChapter['homework']): string[] {
  if (!homework) return [];
  if (typeof homework === 'string') return homework.trim() ? [homework.trim()] : [];
  return [homework.required, homework.optional]
    .map((line) => (line || '').trim())
    .filter(Boolean);
}

function parseIsoDate(value: string): Date | null {
  if (!DATE_PATTERN.test(value || '')) return null;
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

interface MetaFormValues {
  plan_types?: CoursePlanArtifactType[];
  course_name: string;
  grade: string;
  class_names: string[];
  academic_year: string;
  semester: 1 | 2;
  teacher_name: string;
  hours_per_lesson: number;
  start_week: number;
  total_hours?: number;
  location?: string;
  plan_date?: string;
  first_class_date?: string;
  class_periods?: string;
}

function buildMetaPayload(values: MetaFormValues) {
  return {
    course_name: values.course_name.trim(),
    grade: values.grade.trim(),
    class_names: values.class_names.map((name) => name.trim()).filter(Boolean),
    academic_year: values.academic_year.trim(),
    semester: values.semester,
    teacher_name: values.teacher_name.trim(),
    hours_per_lesson: values.hours_per_lesson,
    start_week: values.start_week,
    location: values.location?.trim() || '',
    plan_date: values.plan_date?.trim() || '',
    first_class_date: values.first_class_date?.trim() || '',
    class_periods: values.class_periods?.trim() || '',
  };
}

function validateSchedules(
  schedules: ExperimentClassSchedule[]
): string | null {
  for (const row of schedules) {
    if (!row.class_name) return '班级名称不能为空';
    if (!row.class_periods.trim()) return `${row.class_name} 的上课节次不能为空`;
    if (!row.classroom.trim()) return `${row.class_name} 的实验教室不能为空`;
    const date = parseIsoDate(row.first_class_date);
    if (!date) return `${row.class_name} 的第一周日期必须是 YYYY-MM-DD 格式`;
    if (date.getDay() === 0 ? 7 : date.getDay()) {
      const weekday = date.getDay() === 0 ? 7 : date.getDay();
      if (weekday !== row.weekday) {
        return `${row.class_name} 的第一周日期与星期设置不一致`;
      }
    }
  }
  return null;
}

interface ScheduleState {
  class_name: string;
  weekday: 1 | 2 | 3 | 4 | 5 | 6 | 7;
  class_periods: string;
  first_class_date: string;
  classroom: string;
}

function ScheduleCards({
  schedules,
  onChange,
  defaultDate,
  defaultPeriods,
  defaultClassroom,
}: {
  schedules: ScheduleState[];
  onChange: (rows: ScheduleState[]) => void;
  defaultDate: string;
  defaultPeriods: string;
  defaultClassroom: string;
}) {
  const update = (index: number, patch: Partial<ScheduleState>) => {
    onChange(schedules.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  };
  const inputStyle = { width: 130 };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={12}>
      {schedules.length === 0 && (
        <Text type="secondary">请先选择授课班级，再为每个班填写实验课安排。</Text>
      )}
      {schedules.map((row, index) => (
        <Card key={row.class_name} size="small" title={row.class_name}>
          <Space wrap size={12}>
            <Select
              style={{ width: 110 }}
              value={row.weekday}
              onChange={(value) => update(index, { weekday: value })}
              options={WEEKDAY_LABELS.map((label, i) => ({
                value: (i + 1) as ScheduleState['weekday'],
                label,
              }))}
            />
            <Input
              style={inputStyle}
              placeholder="节次，如 3-4"
              value={row.class_periods}
              onChange={(event) => update(index, { class_periods: event.target.value })}
            />
            <Input
              style={inputStyle}
              placeholder="第一周日期"
              value={row.first_class_date}
              onChange={(event) => update(index, { first_class_date: event.target.value })}
            />
            <Input
              style={{ width: 150 }}
              placeholder="实验教室"
              value={row.classroom}
              onChange={(event) => update(index, { classroom: event.target.value })}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              默认值取「首课日期 / 节次 / 地点」，可单独调整
            </Text>
          </Space>
        </Card>
      ))}
      <Space size={4}>
        <Button
          size="small"
          onClick={() =>
            onChange(
              schedules.map((row) => ({
                ...row,
                first_class_date: row.first_class_date || defaultDate,
                class_periods: row.class_periods || defaultPeriods,
                classroom: row.classroom || defaultClassroom,
              }))
            )
          }
        >
          用默认值填充空白项
        </Button>
      </Space>
    </Space>
  );
}

function CoursePlanStudio() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [messageApi, contextHolder] = message.useMessage();

  const [drafts, setDrafts] = useState<CoursePlanListItem[]>([]);
  const [draftsLoading, setDraftsLoading] = useState(false);

  const [step, setStep] = useState(0);
  const [mode, setMode] = useState<'list' | 'studio'>('list');

  const [lessons, setLessons] = useState<LessonPlan[]>([]);
  const [lessonsTotal, setLessonsTotal] = useState(0);
  const [lessonsLoading, setLessonsLoading] = useState(false);
  const [lessonSearch, setLessonSearch] = useState('');
  const [lessonPage, setLessonPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const [classOptions, setClassOptions] = useState<ClassInfo[]>([]);
  const [validations, setValidations] = useState<FixedTemplateValidation[]>([]);

  const [metaForm] = Form.useForm<MetaFormValues>();
  const planTypes = Form.useWatch('plan_types', metaForm) || [];
  const classNames = Form.useWatch('class_names', metaForm) || [];
  const hasExperiment = planTypes.includes('experiment_plan');

  const [schedules, setSchedules] = useState<ScheduleState[]>([]);
  const [metaFormKey, setMetaFormKey] = useState(0);

  const [detail, setDetail] = useState<CoursePlanDetail | null>(null);
  const [chapters, setChapters] = useState<CoursePlanChapter[]>([]);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);

  const refreshDrafts = useCallback(async () => {
    setDraftsLoading(true);
    try {
      const response = await coursePlanApi.listCoursePlans({ limit: 100 });
      setDrafts(response.course_plans);
    } catch (error) {
      messageApi.error(`学期计划列表加载失败：${(error as Error).message}`);
    } finally {
      setDraftsLoading(false);
    }
  }, [messageApi]);

  const loadLessons = useCallback(
    async (page: number, search: string) => {
      setLessonsLoading(true);
      try {
        const response = await lessonPlanApi.listLessonPlans({
          page,
          limit: 20,
          search: search || undefined,
        });
        setLessons(response.lesson_plans);
        setLessonsTotal(response.total);
      } catch (error) {
        messageApi.error(`教案列表加载失败：${(error as Error).message}`);
      } finally {
        setLessonsLoading(false);
      }
    },
    [messageApi]
  );

  const openDraft = useCallback(
    async (coursePlanId: string) => {
      try {
        const loaded = await coursePlanApi.getCoursePlan(coursePlanId);
        setDetail(loaded);
        setChapters(loaded.chapters.map((chapter) => ({ ...chapter })));
        setSchedules(
          loaded.class_schedules.length
            ? loaded.class_schedules.map((row) => ({ ...row }))
            : []
        );
        setMetaFormKey((key) => key + 1);
        metaForm.setFieldsValue({
          course_name: loaded.course_name,
          grade: loaded.grade,
          class_names: loaded.class_names,
          academic_year: loaded.academic_year,
          semester: loaded.semester as 1 | 2,
          teacher_name: loaded.teacher_name,
          hours_per_lesson: loaded.hours_per_lesson,
          start_week: loaded.start_week,
          total_hours: loaded.total_hours,
          location: loaded.location,
          plan_date: loaded.plan_date,
          first_class_date: loaded.first_class_date,
          class_periods: loaded.class_periods,
        });
        setMode('studio');
        setStep(2);
        setSearchParams({ id: coursePlanId }, { replace: true });
      } catch (error) {
        messageApi.error(`学期计划加载失败：${(error as Error).message}`);
      }
    },
    [metaForm, messageApi, setSearchParams]
  );

  useEffect(() => {
    refreshDrafts();
    loadLessons(1, '');
    classApi
      .listClasses({ limit: 100 })
      .then((response) => setClassOptions(response.classes))
      .catch(() => undefined);
    templateApi
      .validateAllTemplates()
      .then((response) => setValidations(response || []))
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const coursePlanId = searchParams.get('id');
    if (coursePlanId && mode === 'list' && !detail) {
      openDraft(coursePlanId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // 让每班排课行与所选班级保持同步
  useEffect(() => {
    setSchedules((current) => {
      const next = classNames
        .map((name) => name.trim())
        .filter(Boolean)
        .map(
          (name) =>
            current.find((row) => row.class_name === name) || {
              class_name: name,
              weekday: 1 as ScheduleState['weekday'],
              class_periods: '',
              first_class_date: '',
              classroom: '',
            }
        );
      return next;
    });
  }, [classNames]);

  const selectedLessons = useMemo(
    () => selectedIds.map((id) => lessons.find((lesson) => lesson.id === id)),
    [selectedIds, lessons]
  );

  const teachingGroups = useMemo(() => {
    const groups: CoursePlanChapter[][] = [];
    for (let index = 0; index < chapters.length; index += 2) {
      groups.push(chapters.slice(index, index + 2));
    }
    return groups;
  }, [chapters]);

  const templateReport = (type: CoursePlanArtifactType) =>
    validations.find((report) => report.type === type);
  const templatesReady = ['teaching_plan', 'experiment_plan'].every(
    (type) => templateReport(type as CoursePlanArtifactType)?.is_valid
  );

  const startWizard = () => {
    setMode('studio');
    setStep(0);
    setDetail(null);
    setChapters([]);
    setSelectedIds([]);
    setSearchParams({}, { replace: true });
  };

  const backToList = () => {
    setMode('list');
    setDetail(null);
    setSearchParams({}, { replace: true });
    refreshDrafts();
  };

  const moveSelected = (index: number, offset: -1 | 1) => {
    const next = [...selectedIds];
    const target = index + offset;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setSelectedIds(next);
  };

  const handleCreate = async () => {
    const values = await metaForm.validateFields();
    const scheduleRows = hasExperiment ? schedules : [];
    if (hasExperiment) {
      const scheduleError = validateSchedules(scheduleRows);
      if (scheduleError) {
        messageApi.error(scheduleError);
        return;
      }
    }
    setCreating(true);
    try {
      const request: CoursePlanCreateRequest = {
        lesson_plan_ids: selectedIds,
        plan_types: values.plan_types || [],
        ...buildMetaPayload(values),
        total_hours: values.total_hours || undefined,
        class_schedules: scheduleRows,
      };
      const created = await coursePlanApi.createCoursePlan(request);
      setDetail(created);
      setChapters(created.chapters.map((chapter) => ({ ...chapter })));
      messageApi.success('学期计划草稿已创建，可在导出前编辑内容');
      setStep(2);
      setSearchParams({ id: created.id }, { replace: true });
      refreshDrafts();
    } catch (error) {
      messageApi.error(`创建失败：${(error as Error).message}`);
    } finally {
      setCreating(false);
    }
  };

  const collectUpdateRequest = (
    values: MetaFormValues,
    planTypesValue: CoursePlanArtifactType[]
  ): CoursePlanUpdateRequest => ({
    ...buildMetaPayload(values),
    total_hours: values.total_hours || chapters.length * values.hours_per_lesson,
    chapters,
    class_schedules: planTypesValue.includes('experiment_plan') ? schedules : [],
  });

  const handleSave = async () => {
    if (!detail) return;
    const values = await metaForm.validateFields();
    const planTypesValue = detail.plan_types;
    if (planTypesValue.includes('experiment_plan')) {
      const scheduleError = validateSchedules(schedules);
      if (scheduleError) {
        messageApi.error(scheduleError);
        return;
      }
      for (let index = 0; index < teachingGroups.length; index += 1) {
        const group = teachingGroups[index];
        const names = group
          .map((chapter) => chapter.experiment_name.trim())
          .filter(Boolean);
        if (names.length !== 1) {
          messageApi.error(`第 ${index + 1} 组实验必须且只能有一个实验名称`);
          return;
        }
        const nameError = validateExperimentNameClient(names[0], index + 1);
        if (nameError) {
          messageApi.error(nameError);
          return;
        }
      }
    }
    setSaving(true);
    try {
      const updated = await coursePlanApi.updateCoursePlan(
        detail.id,
        collectUpdateRequest(values, planTypesValue)
      );
      setDetail(updated);
      messageApi.success('草稿已保存');
      refreshDrafts();
    } catch (error) {
      messageApi.error(`保存失败：${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async () => {
    if (!detail) return;
    const values = await metaForm.validateFields();
    if (detail.plan_types.includes('experiment_plan')) {
      for (let index = 0; index < teachingGroups.length; index += 1) {
        const names = teachingGroups[index]
          .map((chapter) => chapter.experiment_name.trim())
          .filter(Boolean);
        if (names.length !== 1) {
          messageApi.error(`第 ${index + 1} 组实验必须且只能有一个实验名称（导出前请先修正）`);
          return;
        }
        const nameError = validateExperimentNameClient(names[0], index + 1);
        if (nameError) {
          messageApi.error(nameError);
          return;
        }
      }
    }
    setExporting(true);
    try {
      await coursePlanApi.updateCoursePlan(
        detail.id,
        collectUpdateRequest(values, detail.plan_types)
      );
      const filename = await coursePlanApi.exportCoursePlan(detail.id);
      messageApi.success(`已导出：${filename}`);
      const refreshed = await coursePlanApi.getCoursePlan(detail.id);
      setDetail(refreshed);
      refreshDrafts();
    } catch (error) {
      messageApi.error(`导出失败：${(error as Error).message}`);
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteDraft = async (coursePlanId: string) => {
    try {
      await coursePlanApi.deleteCoursePlan(coursePlanId);
      messageApi.success('已删除');
      refreshDrafts();
    } catch (error) {
      messageApi.error(`删除失败：${(error as Error).message}`);
    }
  };

  // ------------------------------------------------------------- 草稿列表视图

  const draftColumns: ColumnsType<CoursePlanListItem> = [
    {
      title: '课程',
      dataIndex: 'course_name',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.course_name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.grade} · {record.teacher_name} · {record.class_names.length} 个班
          </Text>
        </Space>
      ),
    },
    {
      title: '计划类型',
      dataIndex: 'plan_types',
      render: (types: CoursePlanArtifactType[]) => (
        <Space size={4} wrap>
          {types.map((type) => (
            <Tag key={type} color={type === 'teaching_plan' ? 'green' : 'orange'}>
              {PLAN_TYPE_LABELS[type]}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: string) =>
        status === 'exported' ? <Tag color="green">已导出</Tag> : <Tag color="blue">草稿</Tag>,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 180,
      render: (value: string) => <Text type="secondary">{value?.slice(0, 19)}</Text>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openDraft(record.id)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除该学期计划草稿？"
            onConfirm={() => handleDeleteDraft(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (mode === 'list') {
    return (
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        {contextHolder}
        <Space direction="vertical" size={18} style={{ width: '100%' }}>
          <Space style={{ justifyContent: 'space-between', width: '100%' }}>
            <div>
              <Title level={3} style={{ margin: 0 }}>
                学期计划制作
              </Title>
              <Text type="secondary">
                从已生成的教案派生云林授课计划表与课程实验计划表，导出前可编辑内容。
              </Text>
            </div>
            <Button type="primary" icon={<PlusOutlined />} onClick={startWizard}>
              新建学期计划
            </Button>
          </Space>
          <Card>
            <Table
              rowKey="id"
              columns={draftColumns}
              dataSource={drafts}
              loading={draftsLoading}
              pagination={false}
              locale={{
                emptyText: (
                  <Empty description="还没有学期计划草稿，点击右上角新建" />
                ),
              }}
            />
          </Card>
        </Space>
      </div>
    );
  }

  // ------------------------------------------------------------- 第 1 步：选教案

  const lessonColumns: ColumnsType<LessonPlan> = [
    {
      title: '课题',
      dataIndex: 'topic',
      ellipsis: true,
      render: (_, record) => record.topic || record.title,
    },
    { title: '学科', dataIndex: 'subject', width: 110 },
    { title: '年级', dataIndex: 'grade', width: 110 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: string) => {
        const map: Record<string, { color: string; label: string }> = {
          draft_cached: { color: 'blue', label: '草稿' },
          generated: { color: 'green', label: '已生成' },
          completed: { color: 'green', label: '已完成' },
          published: { color: 'purple', label: '已发布' },
          draft: { color: 'default', label: '待生成' },
        };
        const item = map[status] || { color: 'default', label: status };
        return <Tag color={item.color}>{item.label}</Tag>;
      },
    },
    {
      title: '生成时间',
      dataIndex: 'created_at',
      width: 170,
      render: (value: string) => <Text type="secondary">{value?.slice(0, 19)}</Text>,
    },
  ];

  const rowSelection: TableRowSelection<LessonPlan> = {
    selectedRowKeys: selectedIds,
    preserveSelectedRowKeys: true,
    onChange: (keys) => setSelectedIds(keys as string[]),
    getCheckboxProps: (record) => ({
      disabled:
        (!record.generated_content && !selectedIds.includes(record.id)) ||
        (!selectedIds.includes(record.id) && selectedIds.length >= MAX_LESSONS),
    }),
  };

  const renderSelectLessons = () => (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        message="按上课顺序勾选教案：每 2 份教案组成 1 周（授课计划 1 行、实验计划 1 条），固定模板最多 18 周 / 36 份教案。"
      />
      <Space wrap>
        <Input.Search
          placeholder="搜索课题 / 标题"
          style={{ width: 260 }}
          allowClear
          onSearch={(value) => {
            setLessonSearch(value);
            setLessonPage(1);
            loadLessons(1, value);
          }}
        />
        {['teaching_plan', 'experiment_plan'].map((type) => {
          const report = templateReport(type as CoursePlanArtifactType);
          return (
            <Tag key={type} color={report?.is_valid ? 'green' : 'red'}>
              {PLAN_TYPE_LABELS[type as CoursePlanArtifactType]}模板 ·{' '}
              {report?.is_valid ? '校验通过' : '校验失败'}
            </Tag>
          );
        })}
      </Space>
      <Table
        rowKey="id"
        columns={lessonColumns}
        dataSource={lessons}
        loading={lessonsLoading}
        rowSelection={rowSelection}
        pagination={{
          current: lessonPage,
          pageSize: 20,
          total: lessonsTotal,
          showSizeChanger: false,
          onChange: (page) => {
            setLessonPage(page);
            loadLessons(page, lessonSearch);
          },
        }}
      />
      <Card
        size="small"
        title={`已选教案（${selectedIds.length}/${MAX_LESSONS}），顺序即周次配对顺序`}
      >
        {selectedIds.length === 0 ? (
          <Text type="secondary">尚未选择教案</Text>
        ) : (
          <List
            size="small"
            dataSource={selectedLessons}
            renderItem={(lesson, index) => (
              <List.Item
                actions={[
                  <Button
                    key="up"
                    type="text"
                    size="small"
                    icon={<ArrowUpOutlined />}
                    disabled={index === 0}
                    onClick={() => moveSelected(index, -1)}
                  />,
                  <Button
                    key="down"
                    type="text"
                    size="small"
                    icon={<ArrowDownOutlined />}
                    disabled={index === selectedIds.length - 1}
                    onClick={() => moveSelected(index, 1)}
                  />,
                  <Button
                    key="remove"
                    type="text"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() =>
                      setSelectedIds(selectedIds.filter((id) => id !== lesson?.id))
                    }
                  />,
                ]}
              >
                <Space>
                  <Tag>
                    第{Math.floor(index / 2) + 1}周·{index % 2 === 0 ? '①' : '②'}
                  </Tag>
                  {lesson ? lesson.topic || lesson.title : `教案 ${selectedIds[index]}`}
                </Space>
              </List.Item>
            )}
          />
        )}
      </Card>
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Button icon={<ArrowLeftOutlined />} onClick={backToList}>
          返回列表
        </Button>
        <Button
          type="primary"
          disabled={selectedIds.length === 0 || !templatesReady}
          onClick={() => {
            const plannedTypes: CoursePlanArtifactType[] = ['teaching_plan'];
            metaForm.setFieldsValue({ plan_types: plannedTypes });
            if (!metaForm.getFieldValue('hours_per_lesson')) {
              metaForm.setFieldsValue({
                hours_per_lesson: 2,
                start_week: 1,
                semester: 1,
              });
            }
            setStep(1);
          }}
        >
          下一步：填写课程信息
        </Button>
      </Space>
      {!templatesReady && (
        <Text type="danger">固定模板校验未通过，暂无法生成学期计划。</Text>
      )}
    </Space>
  );

  // ------------------------------------------------------------- 第 2 步：课程信息

  const renderMetaForm = () => (
    <Form
      form={metaForm}
      key={metaFormKey}
      layout="vertical"
      initialValues={{ hours_per_lesson: 2, start_week: 1, semester: 1 }}
    >
      {detail ? (
        <Form.Item label="计划类型">
          <Space size={4}>
            {detail.plan_types.map((type) => (
              <Tag key={type} color={type === 'teaching_plan' ? 'green' : 'orange'}>
                {PLAN_TYPE_LABELS[type]}
              </Tag>
            ))}
            <Text type="secondary" style={{ fontSize: 12 }}>
              创建后不可更改
            </Text>
          </Space>
        </Form.Item>
      ) : (
        <Form.Item
          name="plan_types"
          label="计划类型"
          rules={[{ required: true, message: '请选择要制作的计划类型' }]}
        >
          <Checkbox.Group
            options={[
              { label: '教师授课计划表', value: 'teaching_plan' },
              { label: '课程实验计划表', value: 'experiment_plan' },
            ]}
          />
        </Form.Item>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0 16px' }}>
        <Form.Item
          name="course_name"
          label="课程名称"
          rules={[{ required: true, message: '请输入课程名称' }]}
        >
          <Input placeholder="如 Python 程序设计" />
        </Form.Item>
        <Form.Item
          name="grade"
          label="年级"
          rules={[{ required: true, message: '请输入年级' }]}
        >
          <Input placeholder="如 2024级" />
        </Form.Item>
        <Form.Item
          name="class_names"
          label="授课班级"
          rules={[{ required: true, message: '请选择或输入至少一个班级' }]}
        >
          <Select
            mode="tags"
            placeholder="选择班级，也可直接输入名称"
            allowClear
            options={classOptions.map((item) => ({ value: item.name, label: item.name }))}
          />
        </Form.Item>
        <Form.Item
          name="teacher_name"
          label="授课教师"
          rules={[{ required: true, message: '请输入授课教师姓名' }]}
        >
          <Input placeholder="教师姓名" />
        </Form.Item>
        <Form.Item
          name="academic_year"
          label="学年"
          rules={[
            { required: true, message: '请输入学年' },
            { pattern: /^\d{4}-\d{4}$/, message: '学年格式如 2025-2026' },
          ]}
        >
          <Input placeholder="2025-2026" />
        </Form.Item>
        <Form.Item name="semester" label="学期" rules={[{ required: true }]}>
          <Select
            options={[
              { value: 1, label: '第一学期' },
              { value: 2, label: '第二学期' },
            ]}
          />
        </Form.Item>
        <Form.Item
          name="hours_per_lesson"
          label="每份教案课时"
          rules={[{ required: true, message: '请填写课时' }]}
        >
          <InputNumber min={1} max={8} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item
          name="start_week"
          label="起始周次"
          rules={[{ required: true, message: '请填写起始周次' }]}
        >
          <InputNumber min={1} max={40} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item
          name="total_hours"
          label="总课时（留空按教案数自动计算）"
          tooltip="授课计划表末行显示的总课时"
        >
          <InputNumber
            min={1}
            style={{ width: '100%' }}
            placeholder={String(
              (detail ? chapters.length : selectedIds.length) *
                (metaForm.getFieldValue('hours_per_lesson') || 2)
            )}
          />
        </Form.Item>
        <Form.Item name="location" label="授课 / 实验地点">
          <Input placeholder="如 机房、实验楼101" />
        </Form.Item>
      </div>
      {hasExperiment && (
        <Card size="small" title="实验计划信息" style={{ marginTop: 8 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0 16px' }}>
            <Form.Item
              name="plan_date"
              label="制表日期"
              rules={[{ required: true, message: '请填写制表日期' }]}
            >
              <Input placeholder="YYYY-MM-DD" />
            </Form.Item>
            <Form.Item name="first_class_date" label="默认首课日期">
              <Input placeholder="YYYY-MM-DD" />
            </Form.Item>
            <Form.Item name="class_periods" label="默认上课节次">
              <Input placeholder="如 3-4" />
            </Form.Item>
          </div>
          <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
            每个班级需填写实验课排课（星期、节次、第一周日期、教室），第一周日期须与星期一致。
          </Text>
          <ScheduleCards
            schedules={schedules}
            onChange={setSchedules}
            defaultDate={metaForm.getFieldValue('first_class_date') || ''}
            defaultPeriods={metaForm.getFieldValue('class_periods') || ''}
            defaultClassroom={metaForm.getFieldValue('location') || ''}
          />
        </Card>
      )}
    </Form>
  );

  const renderStepMeta = () => (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        message={`已选 ${selectedIds.length} 份教案，将组成 ${Math.ceil(selectedIds.length / 2)} 周。创建草稿后可继续编辑内容再导出。`}
      />
      {renderMetaForm()}
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Button onClick={() => setStep(0)}>上一步</Button>
        <Button type="primary" loading={creating} onClick={handleCreate}>
          创建草稿，进入编辑
        </Button>
      </Space>
    </Space>
  );

  // ------------------------------------------------------------- 第 3 步：编辑导出

  const hoursPerLesson = metaForm.getFieldValue('hours_per_lesson') || detail?.hours_per_lesson || 2;
  const startWeek = metaForm.getFieldValue('start_week') || detail?.start_week || 1;

  const teachingPreviewRows = teachingGroups.map((group, index) => {
    const weekly = group.length * hoursPerLesson;
    const theory = Math.floor(weekly / 2);
    const topics = group.map((chapter) => chapter.topic).filter(Boolean);
    const focus =
      group.map((chapter) => chapter.key_points).filter(Boolean).join('\n') ||
      `掌握${topics.join('、')}`;
    const difficulty =
      group.map((chapter) => chapter.difficult_points).filter(Boolean).join('\n') ||
      `综合运用${topics.join('、')}`;
    const homework = Array.from(
      new Set(group.flatMap((chapter) => homeworkLines(chapter.homework)))
    );
    return {
      key: index,
      week: startWeek + index,
      topics: topics.join('\n'),
      theory,
      practice: weekly - theory,
      total: weekly,
      focus,
      difficulty,
      homework: homework.join('\n') || '课后练习、实验评估',
    };
  });

  const teachingPreviewColumns: ColumnsType<(typeof teachingPreviewRows)[number]> = [
    { title: '课序周次', dataIndex: 'week', width: 90 },
    { title: '内容摘要', dataIndex: 'topics' },
    { title: '理论', dataIndex: 'theory', width: 70 },
    { title: '实践', dataIndex: 'practice', width: 70 },
    { title: '合计', dataIndex: 'total', width: 70 },
    { title: '教学重点', dataIndex: 'focus' },
    { title: '教学难点', dataIndex: 'difficulty' },
    { title: '作业', dataIndex: 'homework' },
  ];

  const experimentTabs = useMemo(() => {
    if (!detail?.plan_types.includes('experiment_plan')) return [];
    const sources = schedules.length
      ? schedules
      : detail.class_schedules.length
        ? detail.class_schedules
        : detail.class_names.map((name) => ({
            class_name: name,
            weekday: (parseIsoDate(detail.first_class_date)?.getDay() || 1) as ScheduleState['weekday'],
            class_periods: detail.class_periods,
            first_class_date: detail.first_class_date,
            classroom: detail.location,
          }));
    return sources.map((row) => {
      const firstDate = parseIsoDate(row.first_class_date);
      return {
        key: row.class_name,
        label: row.class_name,
        children: (
          <Table
            size="small"
            rowKey="group"
            pagination={false}
            dataSource={teachingGroups.map((group, index) => ({
              key: index,
              group: index + 1,
              week: startWeek + index,
              name: group[0]?.experiment_name || '',
              date: firstDate
                ? formatDate(new Date(firstDate.getTime() + index * 7 * 86400000))
                : '待填写首课日期',
              weekday: WEEKDAY_LABELS[row.weekday - 1],
              periods: row.class_periods || '待填写',
              classroom: row.classroom || '待填写',
            }))}
            columns={[
              { title: '实验序号', dataIndex: 'group', width: 90 },
              { title: '实验项目名称', dataIndex: 'name' },
              { title: '周次', dataIndex: 'week', width: 80 },
              { title: '授课时间', dataIndex: 'date', width: 130 },
              { title: '星期', dataIndex: 'weekday', width: 90 },
              { title: '节次', dataIndex: 'periods', width: 90 },
              { title: '实验室', dataIndex: 'classroom', width: 120 },
            ]}
          />
        ),
      };
    });
  }, [detail, schedules, teachingGroups, startWeek]);

  const renderStepEdit = () => {
    if (!detail) return null;
    const updateChapter = (index: number, patch: Partial<CoursePlanChapter>) => {
      setChapters((current) =>
        current.map((chapter, i) => (i === index ? { ...chapter, ...patch } : chapter))
      );
    };

    return (
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          type={detail.status === 'exported' ? 'success' : 'info'}
          showIcon
          message={
            detail.status === 'exported'
              ? '该计划已导出过；修改内容后可再次导出新文件。'
              : '导出前可编辑下方内容；每 2 份教案 = 1 周（实验计划 1 条）。'
          }
        />

        <Collapse
          items={[
            {
              key: 'meta',
              label: '课程信息（可修改）',
              forceRender: true,
              children: renderMetaForm(),
            },
          ]}
        />

        <Card
          size="small"
          title={
            <Space>
              <FileDoneOutlined />
              教案内容编辑
            </Space>
          }
        >
          <Table
            size="small"
            rowKey="lesson_number"
            pagination={false}
            scroll={{ x: 1100 }}
            dataSource={chapters}
            columns={[
              {
                title: '课序',
                dataIndex: 'lesson_number',
                width: 70,
                render: (_, __, index) => (
                  <Tag>
                    第{Math.floor(index / 2) + 1}周·{index % 2 === 0 ? '①' : '②'}
                  </Tag>
                ),
              },
              {
                title: '课题',
                dataIndex: 'topic',
                width: 180,
                render: (_, chapter, index) => (
                  <Input
                    value={chapter.topic}
                    onChange={(event) => updateChapter(index, { topic: event.target.value })}
                  />
                ),
              },
              {
                title: '教学重点',
                dataIndex: 'key_points',
                render: (_, chapter, index) => (
                  <Input.TextArea
                    autoSize={{ minRows: 1, maxRows: 4 }}
                    value={chapter.key_points}
                    onChange={(event) => updateChapter(index, { key_points: event.target.value })}
                  />
                ),
              },
              {
                title: '教学难点',
                dataIndex: 'difficult_points',
                render: (_, chapter, index) => (
                  <Input.TextArea
                    autoSize={{ minRows: 1, maxRows: 4 }}
                    value={chapter.difficult_points}
                    onChange={(event) =>
                      updateChapter(index, { difficult_points: event.target.value })
                    }
                  />
                ),
              },
              {
                title: '作业（必做 / 选做）',
                dataIndex: 'homework',
                width: 240,
                render: (_, chapter, index) => {
                  const required =
                    typeof chapter.homework === 'object' && chapter.homework !== null
                      ? chapter.homework.required || ''
                      : '';
                  const optional =
                    typeof chapter.homework === 'object' && chapter.homework !== null
                      ? chapter.homework.optional || ''
                      : '';
                  return (
                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      <Input
                        size="small"
                        placeholder="必做"
                        value={required}
                        onChange={(event) =>
                          updateChapter(index, {
                            homework: {
                              required: event.target.value,
                              optional,
                            },
                          })
                        }
                      />
                      <Input
                        size="small"
                        placeholder="选做"
                        value={optional}
                        onChange={(event) =>
                          updateChapter(index, {
                            homework: {
                              required,
                              optional: event.target.value,
                            },
                          })
                        }
                      />
                    </Space>
                  );
                },
              },
              ...(detail.plan_types.includes('experiment_plan')
                ? [
                    {
                      title: '实验名称（每组仅第一课填写）',
                      dataIndex: 'experiment_name',
                      width: 200,
                      render: (_: unknown, chapter: CoursePlanChapter, index: number) => {
                        const isGroupHead = index % 2 === 0;
                        if (!isGroupHead) {
                          return (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              随第 {Math.floor(index / 2) + 1} 组
                            </Text>
                          );
                        }
                        const error = validateExperimentNameClient(
                          chapter.experiment_name,
                          Math.floor(index / 2) + 1
                        );
                        return (
                          <Input
                            status={chapter.experiment_name && error ? 'error' : undefined}
                            maxLength={18}
                            value={chapter.experiment_name}
                            placeholder="≤18 字符"
                            onChange={(event) =>
                              updateChapter(index, { experiment_name: event.target.value })
                            }
                          />
                        );
                      },
                    } as ColumnsType<CoursePlanChapter>[number],
                  ]
                : []),
            ]}
          />
        </Card>

        {detail.plan_types.includes('teaching_plan') && (
          <Card size="small" title="授课计划预览">
            <Table
              size="small"
              rowKey="key"
              pagination={false}
              scroll={{ x: 1000 }}
              columns={teachingPreviewColumns}
              dataSource={teachingPreviewRows}
            />
          </Card>
        )}

        {detail.plan_types.includes('experiment_plan') && (
          <Card size="small" title="实验计划预览（按班级）">
            <Tabs items={experimentTabs} />
          </Card>
        )}

        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <Button icon={<ArrowLeftOutlined />} onClick={backToList}>
            返回列表
          </Button>
          <Space>
            <Button icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
              保存草稿
            </Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              loading={exporting}
              onClick={handleExport}
            >
              导出 Word
            </Button>
          </Space>
        </Space>
      </Space>
    );
  };

  // ------------------------------------------------------------- 页面主体

  const stepItems = [
    { title: '选择教案', description: '从已生成的教案勾选' },
    { title: '课程信息', description: '班级、学年与排课' },
    { title: '编辑导出', description: '改内容后下载 Word' },
  ];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      {contextHolder}
      <Space direction="vertical" size={20} style={{ width: '100%' }}>
        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <div>
            <Title level={3} style={{ margin: 0 }}>
              学期计划制作
            </Title>
            <Text type="secondary">依据已生成的教案制作授课计划 / 实验计划，导出前可编辑。</Text>
          </div>
          <Button onClick={() => navigate('/')}>返回工作台</Button>
        </Space>
        <Steps current={step} items={stepItems} size="small" />
        <Card>
          {step === 0 && renderSelectLessons()}
          {step === 1 && renderStepMeta()}
          {step === 2 && renderStepEdit()}
        </Card>
      </Space>
    </div>
  );
}

export default CoursePlanStudio;
