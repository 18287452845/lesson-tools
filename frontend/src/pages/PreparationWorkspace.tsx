import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Divider,
  Form,
  Input,
  Result,
  Row,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  ArrowLeftOutlined,
  CheckCircleFilled,
  CloudDownloadOutlined,
  FilePptOutlined,
  FileTextOutlined,
  FormOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';

import { classApi, preparationApi, templateApi } from '@/services/api';
import { textbookApi } from '@/services/textbookApi';
import { DURATION_OPTIONS, GRADE_OPTIONS, SUBJECT_OPTIONS } from '@/types';
import type {
  ClassInfo,
  PreparationArtifactType,
  PreparationGenerateRequest,
  PreparationResponse,
  TemplateValidation,
  TextbookInfo,
} from '@/types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const artifactOptions: Array<{
  value: PreparationArtifactType;
  title: string;
  description: string;
  icon: ReactNode;
}> = [
  {
    value: 'lesson_plan',
    title: '云林教案',
    description: '按学校固定格式生成教师教案',
    icon: <FileTextOutlined />,
  },
  {
    value: 'handout',
    title: '学生讲义',
    description: '包含学习目标、课堂学习单与课后巩固',
    icon: <FormOutlined />,
  },
  {
    value: 'presentation',
    title: '课堂 PPT',
    description: '自动拆分教学环节并生成演示文稿',
    icon: <FilePptOutlined />,
  },
];

function PreparationWorkspace() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm<PreparationGenerateRequest>();
  const [messageApi, contextHolder] = message.useMessage();
  const [validation, setValidation] = useState<TemplateValidation | null>(null);
  const [validationLoading, setValidationLoading] = useState(true);
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [textbooks, setTextbooks] = useState<TextbookInfo[]>([]);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<PreparationResponse | null>(null);

  const initialArtifact = useMemo<PreparationArtifactType>(() => {
    const requested = searchParams.get('type');
    if (requested === 'handout' || requested === 'presentation') return requested;
    return 'lesson_plan';
  }, [searchParams]);

  const loadTemplateValidation = async () => {
    setValidationLoading(true);
    try {
      setValidation(await templateApi.validateTemplate());
    } catch (error) {
      setValidation(null);
      messageApi.error(error instanceof Error ? error.message : '模板校验失败');
    } finally {
      setValidationLoading(false);
    }
  };

  useEffect(() => {
    form.setFieldValue('artifact_types', [initialArtifact]);
    void loadTemplateValidation();
    void classApi.listClasses().then((data) => setClasses(data.classes)).catch(() => setClasses([]));
    void textbookApi
      .listAllTextbooks({ status: 'active' })
      .then(setTextbooks)
      .catch(() => setTextbooks([]));
  }, [form, initialArtifact]);

  const handleGenerate = async () => {
    try {
      const values = await form.validateFields();
      setGenerating(true);
      setResult(null);
      const generated = await preparationApi.generate(values);
      setResult(generated);
      messageApi.success('备课包制作完成');
    } catch (error) {
      if (error instanceof Error) messageApi.error(error.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleTextbookChange = (id?: string) => {
    const textbook = textbooks.find((item) => item.id === id);
    form.setFieldValue('textbook_name', textbook?.name);
  };

  return (
    <div style={{ maxWidth: 1180, margin: '0 auto', paddingBottom: 56 }}>
      {contextHolder}
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')} style={{ marginBottom: 20 }}>
        返回工作台
      </Button>

      <div
        style={{
          padding: '34px 38px',
          borderRadius: 22,
          color: '#fff',
          background: 'linear-gradient(135deg, #123f35 0%, #176b52 58%, #278a69 100%)',
          boxShadow: '0 18px 50px rgba(23, 107, 82, 0.2)',
          marginBottom: 24,
        }}
      >
        <Space align="start" size={18}>
          <ThunderboltOutlined style={{ fontSize: 34, marginTop: 7, color: '#a7f3d0' }} />
          <div>
            <Title level={2} style={{ color: '#fff', margin: 0 }}>智能备课工作台</Title>
            <Paragraph style={{ color: '#d1fae5', margin: '8px 0 0', fontSize: 16 }}>
              一次填写课程信息，按需制作教案、学生讲义和课堂 PPT。
            </Paragraph>
          </div>
        </Space>
      </div>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card title="备课信息" styles={{ body: { padding: 26 } }}>
            <Form
              form={form}
              layout="vertical"
              initialValues={{ artifact_types: [initialArtifact], generate_reflection: false }}
            >
              <Form.Item
                name="artifact_types"
                label="选择要制作的资料（可多选）"
                rules={[{ required: true, message: '请至少选择一种备课资料' }]}
              >
                <Checkbox.Group style={{ width: '100%' }}>
                  <Row gutter={[12, 12]}>
                    {artifactOptions.map((option) => (
                      <Col xs={24} md={8} key={option.value}>
                        <label
                          style={{
                            display: 'block',
                            height: '100%',
                            padding: 16,
                            border: '1px solid #dbe7e1',
                            borderRadius: 12,
                            cursor: 'pointer',
                            background: '#fbfdfc',
                          }}
                        >
                          <Checkbox value={option.value}>
                            <Space align="start">
                              <span style={{ color: '#176b52', fontSize: 20 }}>{option.icon}</span>
                              <span>
                                <Text strong>{option.title}</Text>
                                <br />
                                <Text type="secondary" style={{ fontSize: 12 }}>{option.description}</Text>
                              </span>
                            </Space>
                          </Checkbox>
                        </label>
                      </Col>
                    ))}
                  </Row>
                </Checkbox.Group>
              </Form.Item>

              <Divider />
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item name="subject" label="课程 / 学科" rules={[{ required: true }]}>
                    <Select showSearch placeholder="选择或搜索课程" options={SUBJECT_OPTIONS.map((value) => ({ value, label: value }))} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="grade" label="年级" rules={[{ required: true }]}>
                    <Select showSearch placeholder="选择年级" options={GRADE_OPTIONS.map((value) => ({ value, label: value }))} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={16}>
                  <Form.Item name="topic" label="课题" rules={[{ required: true, message: '请输入课题' }]}>
                    <Input placeholder="例如：Python 列表的创建与应用" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item name="duration" label="课时" rules={[{ required: true }]}>
                    <Select placeholder="选择课时" options={DURATION_OPTIONS.map((value) => ({ value, label: value }))} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item label="教材（可选）">
                    <Select
                      allowClear
                      showSearch
                      placeholder="从教材库选择"
                      onChange={handleTextbookChange}
                      options={textbooks.map((item) => ({ value: item.id, label: item.name }))}
                    />
                  </Form.Item>
                  <Form.Item name="textbook_name" hidden><Input /></Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="class_ids" label="授课班级（可选）">
                    <Select
                      mode="multiple"
                      allowClear
                      placeholder="选择班级"
                      options={classes.map((item) => ({ value: item.id, label: item.name }))}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="location" label="授课地点（可选）">
                    <Input placeholder="例如：教学楼 301" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="unit_name" label="所属单元（可选）">
                    <Input placeholder="例如：第三单元 数据结构基础" />
                  </Form.Item>
                </Col>
                <Col span={24}>
                  <Form.Item name="prior_knowledge" label="学情与已有基础（可选）">
                    <TextArea rows={3} placeholder="说明学生已掌握的知识、常见困难等" />
                  </Form.Item>
                </Col>
                <Col span={24}>
                  <Form.Item name="additional_requirements" label="其他备课要求（可选）">
                    <TextArea rows={3} placeholder="例如：增加小组实践，突出课程思政与职业情境" />
                  </Form.Item>
                </Col>
                <Col span={24}>
                  <Form.Item name="generate_reflection" valuePropName="checked">
                    <Checkbox>同时生成教学反思建议</Checkbox>
                  </Form.Item>
                </Col>
              </Row>
            </Form>

            <Button
              type="primary"
              size="large"
              block
              icon={<ThunderboltOutlined />}
              loading={generating}
              disabled={!validation?.is_valid}
              onClick={() => void handleGenerate()}
              style={{ height: 48, background: '#176b52' }}
            >
              开始制作备课资料
            </Button>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title={<Space><SafetyCertificateOutlined />固定模板校验</Space>}>
            {validationLoading ? (
              <div style={{ textAlign: 'center', padding: 26 }}><Spin /></div>
            ) : validation ? (
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                <Space>
                  {validation.is_valid ? <CheckCircleFilled style={{ color: '#16a34a' }} /> : null}
                  <Text strong>{validation.name}</Text>
                </Space>
                <Tag color={validation.is_valid ? 'success' : 'error'}>
                  {validation.is_valid ? '校验通过 · 可生成' : '校验失败'}
                </Tag>
                <Text type="secondary">固定资源 · 只读 · 不支持上传或在线编辑</Text>
                <Text type="secondary">字段 {validation.field_count} 个</Text>
                <Text type="secondary" copyable={{ text: validation.sha256 }}>
                  资源指纹：{validation.sha256.slice(0, 12)}…
                </Text>
                {validation.errors.length > 0 && (
                  <Alert type="error" showIcon message={validation.errors.join('；')} />
                )}
                <Button onClick={() => void loadTemplateValidation()}>重新校验</Button>
              </Space>
            ) : (
              <Alert type="error" message="无法读取内置模板状态" />
            )}
          </Card>

          <Card title="制作说明" style={{ marginTop: 18 }}>
            <Paragraph type="secondary">
              三类资料共享同一份课程分析与教学设计，内容保持一致；教案严格套用内置云林模板，讲义与 PPT 使用统一校色和结构。
            </Paragraph>
          </Card>
        </Col>
      </Row>

      {generating && (
        <Card style={{ marginTop: 24, textAlign: 'center', padding: 30 }}>
          <Spin size="large" />
          <Title level={4} style={{ marginTop: 18 }}>正在生成教学内容并制作文件</Title>
          <Text type="secondary">生成多个文件时会稍多等待一会儿，请不要关闭页面。</Text>
        </Card>
      )}

      {result && !generating && (
        <Card style={{ marginTop: 24 }}>
          <Result
            status="success"
            title="备课资料制作完成"
            subTitle={`${result.template_name} · ${result.artifacts.length} 个文件`}
          />
          <Row gutter={[16, 16]}>
            {result.artifacts.map((artifact) => (
              <Col xs={24} md={8} key={artifact.type}>
                <Card size="small" style={{ background: '#f7fbf9', borderColor: '#cde5da' }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      {artifact.type === 'presentation' ? <FilePptOutlined /> : <FileTextOutlined />}
                      <Text strong>{artifact.label}</Text>
                    </Space>
                    <Text type="secondary" ellipsis={{ tooltip: artifact.filename }}>{artifact.filename}</Text>
                    <Button
                      type="primary"
                      icon={<CloudDownloadOutlined />}
                      onClick={() => window.open(preparationApi.resolveDownloadUrl(artifact.download_url), '_blank')}
                    >
                      下载文件
                    </Button>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
          <Divider />
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Text strong>教学重点</Text>
              <Paragraph type="secondary">{result.content.key_points}</Paragraph>
            </Col>
            <Col xs={24} md={12}>
              <Text strong>教学难点</Text>
              <Paragraph type="secondary">{result.content.difficult_points}</Paragraph>
            </Col>
          </Row>
        </Card>
      )}
    </div>
  );
}

export default PreparationWorkspace;
