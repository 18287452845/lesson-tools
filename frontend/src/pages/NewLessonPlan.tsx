/**
 * New Lesson Plan page - Generate a new lesson plan
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  Select,
  Steps,
  Typography,
  Space,
  Spin,
  Alert,
  Divider,
  Progress,
} from 'antd';
import { ArrowLeftOutlined, LoadingOutlined } from '@ant-design/icons';
import { useTemplateStore } from '@/stores/templateStore';
import { useGeneratorStore } from '@/stores/generatorStore';
import { SUBJECT_OPTIONS, GRADE_OPTIONS, DURATION_OPTIONS } from '@/types';
import type { ClassInfo, TextbookInfo, TextbookChapterInfo } from '@/types';
import { classApi } from '@/services/api';
import { textbookApi } from '@/services/textbookApi';
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
    generationProgress,
    generationMessage,
    error,
    generateLessonPlanStream,
    regenerateField,
    updateField,
    exportLessonPlan,
    clearCurrentLessonPlan,
    clearError,
  } = useGeneratorStore();

  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [textbooks, setTextbooks] = useState<TextbookInfo[]>([]);
  const [selectedTextbookId, setSelectedTextbookId] = useState<string | undefined>();
  const [chapters, setChapters] = useState<TextbookChapterInfo[]>([]);

  // Fetch templates and classes on mount
  useEffect(() => {
    fetchTemplates();
    loadClasses();
    loadTextbooks();
  }, [fetchTemplates]);

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

  const handleSelectTextbook = async (textbookId: string) => {
    if (!textbookId) {
      setSelectedTextbookId(undefined);
      setChapters([]);
      return;
    }

    try {
      const textbook = await textbookApi.getTextbook(textbookId);
      setSelectedTextbookId(textbookId);
      setChapters(textbook.chapters || []);

      // Auto-fill textbook_name field
      form.setFieldsValue({
        textbook_name: textbook.name,
      });
    } catch (error: any) {
      console.error('Failed to load textbook:', error);
    }
  };

  const handleSelectChapter = (chapterId: string) => {
    const chapter = chapters.find((ch) => ch.id === chapterId);
    if (chapter) {
      // Auto-fill form fields from chapter
      form.setFieldsValue({
        topic: chapter.chapter_title,
        unit_name: `${chapter.chapter_number} ${chapter.chapter_title}`,
        prior_knowledge: chapter.content_summary
          ? `章节概述：${chapter.content_summary}\n核心概念：${chapter.key_concepts?.join('、') || ''}`
          : undefined,
      });
    }
  };

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
      await generateLessonPlanStream(values);
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

            <Form.Item
              name="class_ids"
              label="授课班级"
              tooltip="可多选，留空则不显示授课班级"
            >
              <Select
                mode="multiple"
                placeholder="选择班级"
                options={classes.map((c) => ({ label: c.name, value: c.id }))}
                allowClear
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
              />
            </Form.Item>

            <Form.Item
              name="generateReflection"
              valuePropName="checked"
              tooltip="勾选后将在生成教案时包含教学反思内容，否则显示为「（待课后填写）」"
            >
              <Checkbox>同时生成教学反思</Checkbox>
            </Form.Item>
          </Space>

          <Divider />

          <Title level={5}>教学设置（可选）</Title>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Form.Item label="授课地点" name="location">
              <Input placeholder="例如：教学楼301教室" />
            </Form.Item>

            <Form.Item
              label="选择教材"
              name="textbook_id"
              tooltip="选择教材后可以选择对应的章节快速填充信息"
            >
              <Select
                placeholder="选择教材（可选）"
                showSearch
                allowClear
                value={selectedTextbookId}
                onChange={handleSelectTextbook}
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={textbooks.map((t) => ({
                  label: `${t.name}${t.author ? ' - ' + t.author : ''}`,
                  value: t.id,
                }))}
              />
            </Form.Item>

            {selectedTextbookId && chapters.length > 0 && (
              <Form.Item
                label="选择章节"
                name="chapter_id"
                tooltip="选择章节后将自动填充课题和单元名称"
              >
                <Select
                  placeholder="选择章节（可选）"
                  showSearch
                  allowClear
                  onChange={handleSelectChapter}
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                  options={chapters.map((ch) => ({
                    label: `${ch.chapter_number} ${ch.chapter_title}`,
                    value: ch.id,
                  }))}
                />
              </Form.Item>
            )}

            <Form.Item label="教材名称" name="textbook_name">
              <Input placeholder="例如：《Python程序设计基础》第3版" />
            </Form.Item>

            <Form.Item
              label="网络资源（AI生成）"
              name="online_resources"
              tooltip="留空则由AI根据课题自动生成相关网络资源，也可手动填写"
              extra="留空将由AI自动生成，或手动填写相关链接"
            >
              <TextArea
                rows={2}
                placeholder="留空由AI生成，或填写：https://www.example.com, 慕课平台相关课程等"
              />
            </Form.Item>
          </Space>

          <Divider />

          <Title level={5}>教材信息（可选）</Title>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
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
                <div style={{ marginTop: 24, marginBottom: 16 }}>
                  <Progress
                    percent={generationProgress}
                    status="active"
                    strokeColor={{
                      '0%': '#108ee9',
                      '100%': '#87d068',
                    }}
                  />
                </div>
                <div style={{ marginTop: 16 }}>
                  <Text strong style={{ fontSize: 16 }}>
                    {generationMessage || '正在生成教案，请稍候...'}
                  </Text>
                </div>
                {generationProgress > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary">
                      已完成 {generationProgress}%
                    </Text>
                  </div>
                )}
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
