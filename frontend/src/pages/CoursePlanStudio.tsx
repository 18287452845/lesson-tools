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
  AutoComplete,
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
  Segmented,
  Select,
  Space,
  Steps,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  AppstoreAddOutlined,
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
import { templateApi } from '../services/api';
import lessonPlanApi from '../services/lessonPlanApi';
import coursePlanApi from '../services/coursePlanApi';
import batchApi from '../services/batchApi';
import type {
  BatchTask,
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
// 与批量生成教案页面保持一致的下拉选项
const ACADEMIC_YEAR_START = (() => {
  const now = new Date();
  return now.getMonth() >= 7 ? now.getFullYear() : now.getFullYear() - 1;
})();
const ACADEMIC_YEAR_OPTIONS = Array.from({ length: 10 }, (_, index) => {
  const startYear = ACADEMIC_YEAR_START - 4 + index;
  const value = `${startYear}-${startYear + 1}`;
  return { label: value, value };
});
const CLASS_PERIOD_OPTIONS = ['1-2', '3-4', '5-6', '7-8', '9-10'].map((value) => ({
  value,
  label: `第${value}节`,
}));
// 与批量生成教案页面保持一致的专业/年级/班号选项
const BATCH_MAJOR_OPTIONS = [
  '信息安全技术应用',
  '计算机网络技术',
  '计算机应用技术',
  '软件技术',
  '大数据技术',
  '云计算技术应用',
  '人工智能技术应用',
  '移动应用开发',
];
const BATCH_GRADE_OPTIONS = Array.from({ length: 14 }, (_, index) => `${2022 + index}级`);
const CLASS_NUMBER_OPTIONS = Array.from({ length: 5 }, (_, index) => index + 1);

interface ParsedClassNames {
  grade: string;
  majors: string[];
  numbersByMajor: Record<string, number[]>;
  custom: string[];
}

/** 把既有班级名拆回“年级 + 专业 + 班号”；不匹配规则的保留为自定义班级。 */
function parseClassNames(names: string[], gradeHint: string): ParsedClassNames {
  const majors: string[] = [];
  const numbersByMajor: Record<string, number[]> = {};
  const custom: string[] = [];
  let grade = gradeHint || '';
  for (const name of names) {
    const match = name.match(/^(.+级)(.+?)([1-9]\d?)班$/);
    if (match) {
      grade = match[1];
      const major = match[2];
      if (!numbersByMajor[major]) {
        numbersByMajor[major] = [];
        majors.push(major);
      }
      const number = Number(match[3]);
      if (!numbersByMajor[major].includes(number)) numbersByMajor[major].push(number);
    } else {
      custom.push(name);
    }
  }
  return { grade, majors, numbersByMajor, custom };
}

/** 与后端 build_class_names 相同的组合规则：{年级}{专业}{班号}班 */
function composeClassNames(
  grade: string,
  majors: string[],
  numbersByMajor: Record<string, number[]>
): string[] {
  const names: string[] = [];
  const cleanGrade = (grade || '').trim();
  if (!cleanGrade) return names;
  for (const major of majors.map((m) => m.trim()).filter(Boolean)) {
    for (const number of numbersByMajor[major] || []) {
      const name = `${cleanGrade}${major}${number}班`;
      if (!names.includes(name)) names.push(name);
    }
  }
  return names;
}
const PLAN_TYPE_LABELS: Record<CoursePlanArtifactType, string> = {
  teaching_plan: '授课计划',
  experiment_plan: '实验计划',
};
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const HOMEWORK_MAX_CHARS = 6;
const HOMEWORK_BRIEF_RULES: Array<[string[], string]> = [
  [['实验报告', '实训报告', '报告'], '撰写实验报告'],
  [['练习', '习题', '题目'], '完成课后练习'],
  [['复习', '预习', '总结', '归纳'], '复习本课要点'],
  [['代码', '编程', '程序'], '完成编程练习'],
  [['实验', '实训', '上机', '实操'], '上机实操评估'],
  [['项目', '任务', '案例'], '完成项目任务'],
];
const HOMEWORK_BRIEF_FALLBACK = '课后作业';
const HOMEWORK_EMPTY_FALLBACK = '完成课后练习';
const POINTS_MAX_CHARS = 8;

function briefPointLine(line: string): string {
  const briefLines: string[] = [];
  for (const raw of line.split('\n')) {
    const text = raw.trim().replace(/\s+/g, ' ');
    if (!text) continue;
    if (text.length <= POINTS_MAX_CHARS) {
      briefLines.push(text);
      continue;
    }
    const kept: string[] = [];
    let total = 0;
    for (const part of text.split(/[；;]/)) {
      const clause = part.trim();
      if (!clause) continue;
      const extra = clause.length + (kept.length ? 1 : 0);
      if (total + extra > POINTS_MAX_CHARS) break;
      kept.push(clause);
      total += extra;
    }
    briefLines.push(kept.length ? kept.join('；') : text.slice(0, POINTS_MAX_CHARS));
  }
  return briefLines.join('\n');
}

function briefHomeworkLine(line: string): string {
  const trimmed = line.trim();
  if (trimmed.length <= HOMEWORK_MAX_CHARS) return trimmed;
  for (const [keywords, phrase] of HOMEWORK_BRIEF_RULES) {
    if (keywords.some((keyword) => trimmed.includes(keyword))) return phrase;
  }
  return HOMEWORK_BRIEF_FALLBACK;
}

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
  majors?: string[];
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

function buildMetaPayload(values: MetaFormValues, classNames: string[]) {
  return {
    course_name: values.course_name.trim(),
    grade: values.grade.trim(),
    class_names: classNames,
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
}: {
  schedules: ScheduleState[];
  onChange: (rows: ScheduleState[]) => void;
}) {
  const update = (index: number, patch: Partial<ScheduleState>) => {
    onChange(schedules.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={12}>
      {schedules.length === 0 && (
        <Text type="secondary">请先选择授课班级，再为每个班填写实验课安排。</Text>
      )}
      {schedules.map((row, index) => (
        <Card key={row.class_name} size="small" title={row.class_name}>
          <Space wrap size={12}>
            <Select
              style={{ width: 120 }}
              placeholder="选择星期"
              value={row.weekday}
              onChange={(value) => update(index, { weekday: value })}
              options={WEEKDAY_LABELS.map((label, i) => ({
                value: (i + 1) as ScheduleState['weekday'],
                label,
              }))}
            />
            <AutoComplete
              style={{ width: 140 }}
              placeholder="例如：3-4"
              value={row.class_periods}
              options={CLASS_PERIOD_OPTIONS}
              filterOption={(input, option) =>
                String(option?.value || '').includes(input)
              }
              onChange={(value) => update(index, { class_periods: value })}
            />
            <Input
              type="date"
              style={{ width: 160 }}
              value={row.first_class_date}
              onChange={(event) => update(index, { first_class_date: event.target.value })}
            />
            <Input
              style={{ width: 160 }}
              placeholder="例如：慧心楼3516"
              value={row.classroom}
              onChange={(event) => update(index, { classroom: event.target.value })}
            />
          </Space>
        </Card>
      ))}
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

  const [selectMode, setSelectMode] = useState<'batch' | 'manual'>('batch');
  const [batchTasks, setBatchTasks] = useState<BatchTask[]>([]);
  const [batchTasksLoading, setBatchTasksLoading] = useState(false);
  const [pickingBatchId, setPickingBatchId] = useState<string | null>(null);
  const [batchLessons, setBatchLessons] = useState<LessonPlan[]>([]);

  const [validations, setValidations] = useState<FixedTemplateValidation[]>([]);

  const [schedules, setSchedules] = useState<ScheduleState[]>([]);
  const [metaFormKey, setMetaFormKey] = useState(0);
  const [customClassNames, setCustomClassNames] = useState<string[]>([]);

  const [detail, setDetail] = useState<CoursePlanDetail | null>(null);
  const [chapters, setChapters] = useState<CoursePlanChapter[]>([]);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);

  const [metaForm] = Form.useForm<MetaFormValues>();
  const planTypes = Form.useWatch('plan_types', metaForm) || [];
  const watchedMajors = Form.useWatch('majors', metaForm);
  const watchedGrade = Form.useWatch('grade', metaForm);
  const watchedNumbersByMajor = (Form.useWatch(
    'class_numbers_by_major',
    metaForm
  ) || {}) as Record<string, number[]>;
  const formMounted = watchedMajors !== undefined || watchedGrade !== undefined;
  const derivedClassNames = useMemo(() => {
    const names = composeClassNames(
      watchedGrade || '',
      watchedMajors || [],
      watchedNumbersByMajor
    );
    for (const name of customClassNames) {
      if (!names.includes(name)) names.push(name);
    }
    return names;
  }, [watchedGrade, watchedMajors, watchedNumbersByMajor, customClassNames]);
  // 编辑态 plan_types 字段不在表单内（只读展示），必须依据 detail 判定，
  // 否则实验信息字段不会渲染，保存时会丢失制表日期等必填值。
  const hasExperiment = detail
    ? detail.plan_types.includes('experiment_plan')
    : planTypes.includes('experiment_plan');

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

  const loadBatchTasks = useCallback(async () => {
    setBatchTasksLoading(true);
    try {
      const response = await batchApi.listBatchTasks({ limit: 100 });
      setBatchTasks(response.tasks || []);
    } catch (error) {
      messageApi.error(`备课批次加载失败：${(error as Error).message}`);
    } finally {
      setBatchTasksLoading(false);
    }
  }, [messageApi]);

  const handlePickBatch = async (task: BatchTask) => {
    setPickingBatchId(task.id);
    try {
      const ordered: LessonPlan[] = [];
      let page = 1;
      let total = Infinity;
      while (ordered.length < total && page <= 5) {
        const response = await batchApi.getTaskLessonPlans(task.id, {
          page,
          limit: 100,
        });
        total = response.total;
        ordered.push(...response.lesson_plans);
        page += 1;
        if (response.lesson_plans.length === 0) break;
      }
      const missing = ordered.filter((lesson) => !lesson.generated_content);
      if (missing.length > 0) {
        messageApi.warning(
          `批次《${task.course_name}》中第 ${missing
            .map((lesson) => lesson.lesson_number)
            .filter((value) => value)
            .join('、')} 份教案还没有生成内容，请先生成或改用手动勾选`
        );
        return;
      }
      if (ordered.length === 0) {
        messageApi.warning(`批次《${task.course_name}》还没有教案`);
        return;
      }
      if (ordered.length > MAX_LESSONS) {
        messageApi.warning(
          `批次包含 ${ordered.length} 份教案，超过固定模板上限 ${MAX_LESSONS} 份（18 周），请改用手动勾选`
        );
        return;
      }
      setSelectedIds(ordered.map((lesson) => lesson.id));
      setBatchLessons(ordered);
      const taskClassNames = (task.class_names || '')
        .split(/[,，]/)
        .map((name) => name.trim())
        .filter(Boolean);
      const parsedClasses = parseClassNames(taskClassNames, task.grade);
      setCustomClassNames(parsedClasses.custom);
      metaForm.setFieldsValue({
        course_name: task.course_name,
        grade: parsedClasses.grade || task.grade,
        majors: parsedClasses.majors,
        ...(parsedClasses.majors.length
          ? { class_numbers_by_major: parsedClasses.numbersByMajor }
          : {}),
        hours_per_lesson: task.hours_per_lesson || 2,
        total_hours: task.total_hours,
        ...(task.teacher_name ? { teacher_name: task.teacher_name } : {}),
        ...(task.academic_year ? { academic_year: task.academic_year } : {}),
        ...(task.semester ? { semester: task.semester as 1 | 2 } : {}),
        ...(task.location ? { location: task.location } : {}),
      });
      messageApi.success(
        `已带入批次《${task.course_name}》全部 ${ordered.length} 份教案（${Math.ceil(
          ordered.length / 2
        )} 周），可在下方调整顺序或删减`
      );
    } catch (error) {
      messageApi.error(`批次教案加载失败：${(error as Error).message}`);
    } finally {
      setPickingBatchId(null);
    }
  };

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
        const parsedClasses = parseClassNames(loaded.class_names, loaded.grade);
        setCustomClassNames(parsedClasses.custom);
        metaForm.setFieldsValue({
          course_name: loaded.course_name,
          grade: parsedClasses.grade || loaded.grade,
          majors: parsedClasses.majors,
          ...(parsedClasses.majors.length
            ? { class_numbers_by_major: parsedClasses.numbersByMajor }
            : {}),
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
    loadBatchTasks();
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

  // 让每班排课行与所选班级保持同步；表单未挂载时跳过，
  // 避免把已加载草稿的排课清空。
  useEffect(() => {
    if (!formMounted) return;
    setSchedules((current) => {
      const next = derivedClassNames.map(
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
  }, [derivedClassNames, formMounted]);

  const selectedLessons = useMemo(
    () =>
      selectedIds.map(
        (id) =>
          lessons.find((lesson) => lesson.id === id) ||
          batchLessons.find((lesson) => lesson.id === id)
      ),
    [selectedIds, lessons, batchLessons]
  );

  const teachingGroups = useMemo(() => {
    const groups: CoursePlanChapter[][] = [];
    for (let index = 0; index < chapters.length; index += 2) {
      groups.push(chapters.slice(index, index + 2));
    }
    return groups;
  }, [chapters]);

  // 注意：本组件在 mode === 'list' 时提前 return，所有 hooks 必须在此之前调用。
  const hoursPerLesson =
    metaForm.getFieldValue('hours_per_lesson') || detail?.hours_per_lesson || 2;
  const startWeek = metaForm.getFieldValue('start_week') || detail?.start_week || 1;

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
    setBatchLessons([]);
    setSelectMode('batch');
    loadBatchTasks();
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
    if (derivedClassNames.length === 0) {
      messageApi.error('请选择专业与班级，生成实际的授课班级');
      return;
    }
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
        ...buildMetaPayload(values, derivedClassNames),
        total_hours: values.total_hours || undefined,
        class_schedules: scheduleRows,
      };
      const created = await coursePlanApi.createCoursePlan(request);
      setDetail(created);
      setChapters(created.chapters.map((chapter) => ({ ...chapter })));
      // 回填规范化值，保证第 3 步表单重挂载后（含实验信息字段）取值完整
      const createdClasses = parseClassNames(
        created.class_names,
        created.grade
      );
      setCustomClassNames(createdClasses.custom);
      metaForm.setFieldsValue({
        course_name: created.course_name,
        grade: createdClasses.grade || created.grade,
        majors: createdClasses.majors,
        ...(createdClasses.majors.length
          ? { class_numbers_by_major: createdClasses.numbersByMajor }
          : {}),
        academic_year: created.academic_year,
        semester: created.semester as 1 | 2,
        teacher_name: created.teacher_name,
        hours_per_lesson: created.hours_per_lesson,
        start_week: created.start_week,
        total_hours: created.total_hours,
        location: created.location,
        plan_date: created.plan_date,
        first_class_date: created.first_class_date,
        class_periods: created.class_periods,
      });
      setSchedules(
        created.class_schedules.length
          ? created.class_schedules.map((row) => ({ ...row }))
          : []
      );
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
    ...buildMetaPayload(values, derivedClassNames),
    total_hours: values.total_hours || chapters.length * values.hours_per_lesson,
    chapters,
    class_schedules: planTypesValue.includes('experiment_plan') ? schedules : [],
  });

  const handleSave = async () => {
    if (!detail) return;
    const values = await metaForm.validateFields();
    if (derivedClassNames.length === 0) {
      messageApi.error('请选择专业与班级，生成实际的授课班级');
      return;
    }
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
    if (derivedClassNames.length === 0) {
      messageApi.error('请选择专业与班级，生成实际的授课班级');
      return;
    }
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

  const batchStatusMap: Record<string, { color: string; label: string }> = {
    completed: { color: 'green', label: '已完成' },
    processing: { color: 'blue', label: '生成中' },
    pending: { color: 'default', label: '等待中' },
    failed: { color: 'red', label: '失败' },
    cancelled: { color: 'default', label: '已取消' },
  };

  const batchColumns: ColumnsType<BatchTask> = [
    {
      title: '备课批次',
      dataIndex: 'course_name',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.course_name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.subject} · {record.grade} · 每份 {record.hours_per_lesson} 课时 · 共{' '}
            {record.total_hours} 课时
          </Text>
        </Space>
      ),
    },
    {
      title: '教案进度',
      key: 'progress',
      width: 200,
      render: (_, record) => {
        const item = batchStatusMap[record.status] || {
          color: 'default',
          label: record.status,
        };
        return (
          <Space size={6}>
            <Tag color={item.color}>{item.label}</Tag>
            <Text type="secondary">
              {record.completed_count}/{record.total_count} 份
            </Text>
          </Space>
        );
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (value: string) => <Text type="secondary">{value?.slice(0, 19)}</Text>,
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<AppstoreAddOutlined />}
          loading={pickingBatchId === record.id}
          onClick={() => handlePickBatch(record)}
        >
          带入整批教案
        </Button>
      ),
    },
  ];

  const renderSelectLessons = () => (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        message="按备课批次一次带入整批教案（如 16 周 / 18 周课程），系统按课序自动配对：每 2 份教案 = 1 周，最多 18 周 / 36 份。"
      />
      <Space wrap style={{ justifyContent: 'space-between', width: '100%' }}>
        <Segmented
          value={selectMode}
          onChange={(value) => setSelectMode(value as 'batch' | 'manual')}
          options={[
            { label: '按备课批次选择', value: 'batch' },
            { label: '手动勾选教案', value: 'manual' },
          ]}
        />
        <Space size={6}>
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
      </Space>
      {selectMode === 'batch' ? (
        <Table
          rowKey="id"
          size="middle"
          columns={batchColumns}
          dataSource={batchTasks}
          loading={batchTasksLoading}
          pagination={{ pageSize: 8, showSizeChanger: false }}
          locale={{
            emptyText: (
              <Empty description="还没有备课批次，可先在「学期批量备课」生成整批教案" />
            ),
          }}
        />
      ) : (
        <>
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
        </>
      )}
      <Card
        size="small"
        title={`已选教案（${selectedIds.length}/${MAX_LESSONS} 份，约 ${Math.ceil(
          selectedIds.length / 2
        )} 周），顺序即周次配对顺序`}
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
          rules={[{ required: true, message: '请选择年级' }]}
        >
          <Select
            placeholder="选择年级"
            options={BATCH_GRADE_OPTIONS.map((g) => ({ label: g, value: g }))}
            showSearch
          />
        </Form.Item>
        <Form.Item
          name="majors"
          label="专业"
          rules={[{ required: true, message: '请选择至少一个专业' }]}
        >
          <Select
            mode="tags"
            placeholder="选择或输入专业（可多选）"
            options={BATCH_MAJOR_OPTIONS.map((major) => ({
              label: major,
              value: major,
            }))}
            showSearch
            allowClear
            tokenSeparators={[',', '，']}
            maxTagCount="responsive"
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
          rules={[{ required: true, message: '请选择学年' }]}
        >
          <Select
            placeholder="从近10个学年中选择"
            options={ACADEMIC_YEAR_OPTIONS}
            showSearch
          />
        </Form.Item>
        <Form.Item name="semester" label="学期" rules={[{ required: true }]}>
          <Select
            options={[
              { value: 1, label: '第1学期' },
              { value: 2, label: '第2学期' },
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
      {(watchedMajors || []).length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0 16px' }}>
          {(watchedMajors || [])
            .map((major) => String(major).trim())
            .filter(Boolean)
            .map((major) => (
              <Form.Item
                key={major}
                name={['class_numbers_by_major', major]}
                label={`${major}班级`}
                tooltip="每个专业独立选择实际开设的班级"
                rules={[{ required: true, message: `请选择${major}的班级` }]}
              >
                <Select
                  mode="multiple"
                  placeholder={`选择${major}的 1-5 班`}
                  options={CLASS_NUMBER_OPTIONS.map((number) => ({
                    label: `${number}班`,
                    value: number,
                  }))}
                  allowClear
                  maxTagCount="responsive"
                />
              </Form.Item>
            ))}
        </div>
      )}
      {customClassNames.length > 0 && (
        <Form.Item label="其他班级（不匹配“年级+专业+班号”的班级名）">
          <Select
            mode="tags"
            value={customClassNames}
            onChange={setCustomClassNames}
            placeholder="输入班级名后回车"
            allowClear
            tokenSeparators={[',', '，']}
          />
        </Form.Item>
      )}
      <Form.Item label="授课班级预览" style={{ marginBottom: 12 }}>
        {derivedClassNames.length > 0 ? (
          <Space size={4} wrap>
            {derivedClassNames.map((name) => (
              <Tag key={name}>{name}</Tag>
            ))}
          </Space>
        ) : (
          <Text type="secondary">选择专业与班级后自动生成，如“2025级信息安全技术应用1班”</Text>
        )}
      </Form.Item>
      {hasExperiment && (
        <Card size="small" title="实验计划信息" style={{ marginTop: 8 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0 16px' }}>
            <Form.Item
              name="plan_date"
              label="制表日期"
              rules={[{ required: true, message: '请选择制表日期' }]}
            >
              <Input type="date" style={{ width: '100%' }} />
            </Form.Item>
          </div>
          <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
            请为每个班级分别设置实验课时间和教室：第一周日期必须与所选星期一致；后续实验日期按每 7 天自动推算。
          </Text>
          <ScheduleCards schedules={schedules} onChange={setSchedules} />
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

  const teachingPreviewRows = teachingGroups.map((group, index) => {
    const weekly = group.length * hoursPerLesson;
    const theory = Math.floor(weekly / 2);
    const topics = group.map((chapter) => chapter.topic).filter(Boolean);
    const focus =
      Array.from(
        new Set(
          group
            .map((chapter) => briefPointLine(chapter.key_points))
            .filter(Boolean)
        )
      ).join('\n') || briefPointLine(`掌握${topics.join('、')}`);
    const difficulty =
      Array.from(
        new Set(
          group
            .map((chapter) => briefPointLine(chapter.difficult_points))
            .filter(Boolean)
        )
      ).join('\n') || briefPointLine(`综合运用${topics.join('、')}`);
    const homework = Array.from(
      new Set(
        group
          .flatMap((chapter) => homeworkLines(chapter.homework))
          .map(briefHomeworkLine)
      )
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
      homework: homework.join('\n') || HOMEWORK_EMPTY_FALLBACK,
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
          extra={
            <Text type="secondary" style={{ fontSize: 12 }}>
              重点/难点每课一行短语（不超过 8 字）、作业不超过 6 字，超限时保存将自动由 AI 精简
            </Text>
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
