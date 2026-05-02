/**
 * Competition New - 创建比赛项目并启动生成
 *
 * URL params:
 *   ?type=lesson_plan | report
 *
 * Steps:
 *   1. 基本信息 (项目名/年份/级别/作品名/课程/专业/总学时...)
 *   2. (lesson_plan) 任务清单 / (report) 关联教案
 *   3. 确认 + 启动生成 -> 跳转到详情页
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Card,
  Steps,
  Form,
  Input,
  InputNumber,
  Button,
  Select,
  Space,
  message,
  Row,
  Col,
  Typography,
  Alert,
} from 'antd';
import { ArrowLeftOutlined, RocketOutlined } from '@ant-design/icons';
import { useCompetitionStore } from '@/stores/competitionStore';
import type { CompetitionOutputType } from '@/types';

const { Title, Text } = Typography;
const { TextArea } = Input;

function CompetitionNew() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialType = (searchParams.get('type') || 'lesson_plan') as CompetitionOutputType;

  const [outputType, setOutputType] = useState<CompetitionOutputType>(initialType);
  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const {
    createProject,
    generateLessonPlan,
    generateReport,
    fetchProjects,
  } = useCompetitionStore();

  useEffect(() => {
    // For report mode, load projects to pick related lesson_plan from
    if (outputType === 'report') {
      fetchProjects().catch(() => {});
    }
  }, [outputType, fetchProjects]);

  const next = async () => {
    try {
      await form.validateFields();
      setCurrentStep((s) => s + 1);
    } catch (err) {
      // validation error already shown by form
    }
  };

  const prev = () => setCurrentStep((s) => Math.max(0, s - 1));

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const values = form.getFieldsValue(true);

      // Step 1: create project
      const project = await createProject({
        name: values.name,
        competition_year: values.competition_year,
        competition_region: values.competition_region,
        competition_level: values.competition_level,
        work_name: values.work_name,
        course_name: values.course_name,
        major_category: values.major_category,
        major_name: values.major_name,
        group_name: values.group_name,
        total_hours: values.total_hours || 16,
        hours_per_lesson: values.hours_per_lesson || 2,
        class_name: values.class_name,
        location: values.location,
      });

      // Step 2: trigger generation
      let outputId: string;
      if (outputType === 'lesson_plan') {
        outputId = await generateLessonPlan(project.id, {
          topics_input: values.topics_input,
          additional_requirements: values.additional_requirements,
        });
      } else {
        outputId = await generateReport(project.id, {
          related_output_id: values.related_output_id,
          additional_requirements: values.additional_requirements,
        });
      }

      message.success('已启动生成,正在跳转到项目详情页');
      navigate(`/competition/${project.id}?output=${outputId}`);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '创建失败');
      setSubmitting(false);
    }
  };

  // Filter eligible related lesson plans for report mode
  // (Currently we'd need to fetch outputs across all projects; for simplicity
  //  let user paste the output_id manually if needed in v1)

  const steps = [
    { title: '基本信息', description: '项目名称与封面信息' },
    {
      title: outputType === 'lesson_plan' ? '任务设置' : '关联与要求',
      description: outputType === 'lesson_plan' ? '任务清单与额外要求' : '关联教案与额外要求',
    },
    { title: '确认提交', description: '检查信息并启动 AI 生成' },
  ];

  return (
    <div style={{ background: '#f8fafc', minHeight: '100vh', padding: '24px 0 80px' }}>
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '0 20px' }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/competition')}
          style={{ marginBottom: 16 }}
        >
          返回比赛专区
        </Button>

        <Card style={{ borderRadius: 16, border: 'none', boxShadow: '0 2px 12px rgba(0,0,0,0.05)' }}>
          <div style={{ marginBottom: 24 }}>
            <Title level={3} style={{ marginBottom: 8 }}>
              {outputType === 'lesson_plan' ? '创建参赛教案项目' : '创建实施报告项目'}
            </Title>
            <Text type="secondary">
              {outputType === 'lesson_plan'
                ? '生成包含整体设计与多个详细教案的完整参赛文档'
                : '生成结构完整的教学实施报告(可关联已有参赛教案)'}
            </Text>
          </div>

          <div style={{ marginBottom: 32 }}>
            <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
              <Button
                type={outputType === 'lesson_plan' ? 'primary' : 'default'}
                onClick={() => setOutputType('lesson_plan')}
                style={{ flex: 1 }}
                disabled={currentStep > 0}
              >
                参赛教案
              </Button>
              <Button
                type={outputType === 'report' ? 'primary' : 'default'}
                onClick={() => setOutputType('report')}
                style={{ flex: 1 }}
                disabled={currentStep > 0}
              >
                实施报告
              </Button>
            </Space.Compact>
          </div>

          <Steps current={currentStep} items={steps} style={{ marginBottom: 32 }} />

          <Form
            form={form}
            layout="vertical"
            initialValues={{
              competition_year: '2024年',
              competition_region: '云南省',
              competition_level: '省赛',
              total_hours: 16,
              hours_per_lesson: 2,
              group_name: '专业二组',
            }}
          >
            {/* Step 1: Basic Info */}
            <div style={{ display: currentStep === 0 ? 'block' : 'none' }}>
              <Form.Item
                label="项目名称"
                name="name"
                rules={[{ required: true, message: '请输入项目名称' }]}
              >
                <Input placeholder="如:JS技术-2024云南省赛" maxLength={200} />
              </Form.Item>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item label="参赛年份" name="competition_year">
                    <Input placeholder="2024年" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="参赛地区" name="competition_region">
                    <Input placeholder="云南省 / 全国" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="赛事级别" name="competition_level">
                    <Select>
                      <Select.Option value="省赛">省赛</Select.Option>
                      <Select.Option value="国赛">国赛</Select.Option>
                      <Select.Option value="校赛">校赛</Select.Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                label="作品名称"
                name="work_name"
                rules={[{ required: true, message: '请输入作品名称' }]}
              >
                <Input placeholder="如:基于JS的职业技能大赛网站前端特效实现" />
              </Form.Item>

              <Form.Item
                label="课程名称"
                name="course_name"
                rules={[{ required: true, message: '请输入课程名称' }]}
              >
                <Input placeholder="如:《JavaScript编程技术》" />
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="专业大类" name="major_category">
                    <Input placeholder="如:电子与信息大类-计算机类" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="专业名称" name="major_name">
                    <Input placeholder="如:计算机应用技术" />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item label="参赛组别" name="group_name">
                    <Input placeholder="专业二组" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="授课班级" name="class_name">
                    <Input placeholder="计算机应用技术211班" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="授课地点" name="location">
                    <Input placeholder="软件开发实训室" />
                  </Form.Item>
                </Col>
              </Row>

              {outputType === 'lesson_plan' && (
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="总学时"
                      name="total_hours"
                      rules={[{ required: true, message: '请输入总学时' }]}
                    >
                      <InputNumber min={2} max={128} step={2} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="单个教案学时"
                      name="hours_per_lesson"
                      rules={[{ required: true, message: '请输入单个教案学时' }]}
                    >
                      <InputNumber min={1} max={8} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>
              )}
            </div>

            {/* Step 2: Specifics */}
            <div style={{ display: currentStep === 1 ? 'block' : 'none' }}>
              {outputType === 'lesson_plan' ? (
                <>
                  <Alert
                    type="info"
                    showIcon
                    message="任务清单(可选)"
                    description="若不填,AI 会根据课程主题和总学时自动拆分。每行一个任务名称,如:识读施工图"
                    style={{ marginBottom: 16 }}
                  />
                  <Form.Item label="任务清单(每行一个)" name="topics_input">
                    <TextArea
                      rows={8}
                      placeholder={`识读施工图\n深化施工图\n生产叠合板\n运输与堆放\n吊装前准备\n...`}
                    />
                  </Form.Item>
                </>
              ) : (
                <>
                  <Alert
                    type="info"
                    showIcon
                    message="关联教案(可选)"
                    description="可关联已生成的参赛教案 output_id 作为生成上下文,使报告与教案保持一致"
                    style={{ marginBottom: 16 }}
                  />
                  <Form.Item label="关联的教案 output_id(可留空)" name="related_output_id">
                    <Input placeholder="可在某个项目详情页复制 output_id" />
                  </Form.Item>
                </>
              )}

              <Form.Item label="额外要求(可选)" name="additional_requirements">
                <TextArea
                  rows={4}
                  placeholder="如:重点突出 1+X 证书对接;增加思政元素;课堂以小组合作为主等"
                />
              </Form.Item>
            </div>

            {/* Step 3: Confirm */}
            <div style={{ display: currentStep === 2 ? 'block' : 'none' }}>
              <Alert
                type="warning"
                showIcon
                message="即将启动 AI 生成"
                description={
                  outputType === 'lesson_plan'
                    ? '将生成多份完整教案,预计耗时 2-5 分钟。生成中不会消耗你的 UI 时间,可前往项目详情页查看进度。'
                    : '将生成完整教学实施报告,预计耗时 1-3 分钟。'
                }
                style={{ marginBottom: 16 }}
              />
              <Card type="inner" title="提交摘要" style={{ marginBottom: 16 }}>
                <Form.Item
                  label="项目名称"
                  shouldUpdate
                  style={{ marginBottom: 8 }}
                >
                  {() => <Text strong>{form.getFieldValue('name')}</Text>}
                </Form.Item>
                <Form.Item label="作品名称" shouldUpdate style={{ marginBottom: 8 }}>
                  {() => <Text>{form.getFieldValue('work_name')}</Text>}
                </Form.Item>
                <Form.Item label="课程名称" shouldUpdate style={{ marginBottom: 8 }}>
                  {() => <Text>{form.getFieldValue('course_name')}</Text>}
                </Form.Item>
                {outputType === 'lesson_plan' && (
                  <Form.Item label="预估教案数量" shouldUpdate style={{ marginBottom: 0 }}>
                    {() => {
                      const total = form.getFieldValue('total_hours') || 16;
                      const each = form.getFieldValue('hours_per_lesson') || 2;
                      return <Text>{Math.max(1, Math.floor(total / each))} 份(每份 {each} 学时)</Text>;
                    }}
                  </Form.Item>
                )}
              </Card>
            </div>
          </Form>

          {/* Step navigation */}
          <div style={{ marginTop: 24, textAlign: 'right' }}>
            <Space>
              {currentStep > 0 && <Button onClick={prev}>上一步</Button>}
              {currentStep < steps.length - 1 && (
                <Button type="primary" onClick={next}>
                  下一步
                </Button>
              )}
              {currentStep === steps.length - 1 && (
                <Button
                  type="primary"
                  icon={<RocketOutlined />}
                  loading={submitting}
                  onClick={handleSubmit}
                >
                  启动生成
                </Button>
              )}
            </Space>
          </div>
        </Card>
      </div>
    </div>
  );
}

export default CompetitionNew;
