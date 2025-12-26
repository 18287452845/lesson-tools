/**
 * New Lesson Plan page - Generate a new lesson plan
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Card,
  Form,
  Input,
  Select,
  Steps,
  Typography,
  Space,
  Spin,
  Alert,
  Divider,
} from 'antd';
import { ArrowLeftOutlined, LoadingOutlined } from '@ant-design/icons';
import { useTemplateStore } from '@/stores/templateStore';
import { useGeneratorStore } from '@/stores/generatorStore';
import { SUBJECT_OPTIONS, GRADE_OPTIONS, DURATION_OPTIONS } from '@/types';
import GeneratedContent from '@/components/generator/GeneratedContent';

const { Title, Text } = Typography;
const { TextArea } = Input;

function NewLessonPlan() {
  const navigate = useNavigate();
  const { templates, loading: templatesLoading, fetchTemplates } = useTemplateStore();
  const {
    currentLessonPlan,
    generatedContent,
    isGenerating,
    isRegenerating,
    regeneratingField,
    error,
    generateLessonPlan,
    regenerateField,
    updateField,
    exportLessonPlan,
    clearCurrentLessonPlan,
    clearError,
  } = useGeneratorStore();

  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();

  // Fetch templates on mount
  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleGenerate = async () => {
    try {
      const values = await form.validateFields();
      // Ensure template_id is included
      if (!values.template_id) {
        form.setFields([
          {
            name: 'template_id',
            errors: ['请选择教案模板'],
          },
        ]);
        return;
      }
      await generateLessonPlan(values);
      setCurrentStep(2);
    } catch (err) {
      // Error is handled by the store
    }
  };

  const handleExport = async () => {
    try {
      const blob = await exportLessonPlan();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `教案_${form.getFieldValue('topic')}_${Date.now()}.docx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      // Error is handled by the store
    }
  };

  const steps = [
    {
      title: '选择模板',
      content: (
        <Card>
          <Form.Item
            label="选择模板"
            name="template_id"
            rules={[{ required: true, message: '请选择一个模板' }]}
          >
            <Select
              placeholder="选择教案模板"
              loading={templatesLoading}
              options={templates.map((t) => ({
                label: `${t.name} ${t.subject ? `(${t.subject})` : ''}`,
                value: t.id,
              }))}
            />
          </Form.Item>
        </Card>
      ),
    },
    {
      title: '填写信息',
      content: (
        <Card>
          <Title level={5}>基本信息</Title>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Form.Item
              label="学科"
              name="subject"
              rules={[{ required: true, message: '请选择学科' }]}
            >
              <Select
                placeholder="选择学科"
                options={SUBJECT_OPTIONS.map((s) => ({ label: s, value: s }))}
              />
            </Form.Item>

            <Form.Item
              label="年级"
              name="grade"
              rules={[{ required: true, message: '请选择年级' }]}
            >
              <Select
                placeholder="选择年级"
                options={GRADE_OPTIONS.map((g) => ({ label: g, value: g }))}
              />
            </Form.Item>

            <Form.Item
              label="课题"
              name="topic"
              rules={[{ required: true, message: '请输入课题' }]}
            >
              <Input placeholder="例如：分数的初步认识" />
            </Form.Item>

            <Form.Item
              label="课时"
              name="duration"
              rules={[{ required: true, message: '请选择课时' }]}
            >
              <Select
                placeholder="选择课时"
                options={DURATION_OPTIONS.map((d) => ({ label: d, value: d }))}
              />
            </Form.Item>
          </Space>

          <Divider />

          <Title level={5}>教材信息（可选）</Title>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Form.Item label="教材版本" name="textbook_version">
              <Input placeholder="例如：人教版" />
            </Form.Item>

            <Form.Item label="单元名称" name="unit_name">
              <Input placeholder="例如：第三单元 分数的初步认识" />
            </Form.Item>
          </Space>

          <Divider />

          <Title level={5}>学情说明（可选）</Title>
          <Form.Item label="学生已有知识" name="prior_knowledge">
            <TextArea
              rows={3}
              placeholder="描述学生对本课内容的已有知识基础..."
            />
          </Form.Item>

          <Title level={5}>特殊要求（可选）</Title>
          <Form.Item label="其他要求" name="additional_requirements">
            <TextArea
              rows={3}
              placeholder="例如：需要包含小组合作环节、突出探究过程等..."
            />
          </Form.Item>
        </Card>
      ),
    },
    {
      title: '生成结果',
      content: (
        <>
          {error && (
            <Alert
              type="error"
              message="生成失败"
              description={error}
              closable
              onClose={clearError}
              style={{ marginBottom: 16 }}
            />
          )}
          {isGenerating ? (
            <Card>
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
                <div style={{ marginTop: 16 }}>
                  <Text>正在生成教案，请稍候...</Text>
                </div>
              </div>
            </Card>
          ) : (
            generatedContent && (
              <GeneratedContent
                content={generatedContent}
                onRegenerateField={regenerateField}
                onUpdateField={updateField}
                isRegenerating={isRegenerating}
                regeneratingField={regeneratingField}
              />
            )
          )}
        </>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
          返回首页
        </Button>
      </div>

      <Title level={2}>新建教案</Title>

      <Steps current={currentStep} style={{ marginBottom: 32 }}>
        {steps.map((step, index) => (
          <Steps.Step key={index} title={step.title} />
        ))}
      </Steps>

      <Form form={form} layout="vertical">
        <div className="step-content">{steps[currentStep].content}</div>
      </Form>

      <div style={{ marginTop: 24, textAlign: 'center' }}>
        <Space>
          {currentStep > 0 && currentStep < 2 && (
            <Button onClick={() => setCurrentStep(currentStep - 1)}>
              上一步
            </Button>
          )}
          {currentStep === 0 && (
            <Button
              type="primary"
              onClick={async () => {
                try {
                  await form.validateFields(['template_id']);
                  setCurrentStep(1);
                } catch {
                  // Validation failed
                }
              }}
            >
              下一步
            </Button>
          )}
          {currentStep === 1 && (
            <>
              <Button onClick={() => setCurrentStep(0)}>上一步</Button>
              <Button
                type="primary"
                onClick={handleGenerate}
                loading={isGenerating}
              >
                开始生成
              </Button>
            </>
          )}
          {currentStep === 2 && generatedContent && (
            <>
              <Button onClick={() => setCurrentStep(1)}>返回修改</Button>
              <Button onClick={() => clearCurrentLessonPlan()}>
                重新生成
              </Button>
              <Button type="primary" onClick={handleExport}>
                导出Word
              </Button>
            </>
          )}
        </Space>
      </div>
    </div>
  );
}

export default NewLessonPlan;
