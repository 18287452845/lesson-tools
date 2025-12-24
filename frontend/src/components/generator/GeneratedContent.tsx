/**
 * GeneratedContent component - Display and edit generated lesson plan content
 */
import { useState } from 'react';
import { Card, List, Button, Space, Typography, Collapse, Input, Tag, message } from 'antd';
import { ReloadOutlined, CheckOutlined } from '@ant-design/icons';
import type { GeneratedContent, TeachingGoal, TeachingStep } from '@/types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface GeneratedContentProps {
  content: GeneratedContent;
  onRegenerateField: (fieldName: string, instruction?: string) => Promise<void>;
  onUpdateField: (fieldName: string, content: any) => Promise<void>;
  isRegenerating: boolean;
  regeneratingField: string | null;
}

function GeneratedContent({
  content,
  onRegenerateField,
  onUpdateField,
  isRegenerating,
  regeneratingField,
}: GeneratedContentProps) {
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<any>('');

  const fields: Array<{
    key: string;
    title: string;
    content: any;
    type: 'text' | 'array' | 'object';
  }> = [
    {
      key: 'teaching_goals',
      title: '教学目标',
      content: content.teaching_goals,
      type: 'object',
    },
    {
      key: 'key_points',
      title: '教学重点',
      content: content.key_points,
      type: 'text',
    },
    {
      key: 'difficult_points',
      title: '教学难点',
      content: content.difficult_points,
      type: 'text',
    },
    {
      key: 'teaching_tools',
      title: '教具准备',
      content: content.teaching_tools,
      type: 'text',
    },
    {
      key: 'teaching_methods',
      title: '教学方法',
      content: content.teaching_methods,
      type: 'text',
    },
    {
      key: 'student_analysis',
      title: '学情分析',
      content: content.student_analysis,
      type: 'text',
    },
    {
      key: 'textbook_analysis',
      title: '教材分析',
      content: content.textbook_analysis,
      type: 'text',
    },
    {
      key: 'teaching_steps',
      title: '教学过程',
      content: content.teaching_steps,
      type: 'array',
    },
    {
      key: 'homework',
      title: '作业布置',
      content: content.homework,
      type: 'object',
    },
    ...(content.blackboard_design
      ? [{ key: 'blackboard_design', title: '板书设计', content: content.blackboard_design, type: 'text' as const }]
      : []),
    ...(content.reflection
      ? [{ key: 'reflection', title: '教学反思', content: content.reflection, type: 'text' as const }]
      : []),
  ];

  const handleEdit = (key: string, value: any) => {
    setEditingField(key);
    setEditValue(value);
  };

  const handleSave = async () => {
    if (!editingField) return;

    try {
      await onUpdateField(editingField, editValue);
      message.success('保存成功');
      setEditingField(null);
    } catch (err) {
      message.error('保存失败');
    }
  };

  const renderContent = (field: { key: string; title: string; content: any; type: string }) => {
    if (editingField === field.key) {
      return (
        <div>
          <TextArea
            value={typeof editValue === 'string' ? editValue : JSON.stringify(editValue, null, 2)}
            onChange={(e) => setEditValue(e.target.value)}
            rows={field.type === 'array' ? 10 : 4}
            style={{ marginBottom: 8 }}
          />
          <Space>
            <Button type="primary" size="small" icon={<CheckOutlined />} onClick={handleSave}>
              保存
            </Button>
            <Button size="small" onClick={() => setEditingField(null)}>
              取消
            </Button>
          </Space>
        </div>
      );
    }

    if (field.type === 'object' && field.content) {
      if (field.key === 'teaching_goals') {
        const goals = field.content as TeachingGoal;
        return (
          <Space direction="vertical" size="small">
            {goals.knowledge && goals.knowledge.length > 0 && (
              <div>
                <Tag color="blue">知识与技能</Tag>
                <ul style={{ marginTop: 4, paddingLeft: 20 }}>
                  {goals.knowledge.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {goals.ability && goals.ability.length > 0 && (
              <div>
                <Tag color="green">过程与方法</Tag>
                <ul style={{ marginTop: 4, paddingLeft: 20 }}>
                  {goals.ability.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {goals.emotion && goals.emotion.length > 0 && (
              <div>
                <Tag color="orange">情感态度价值观</Tag>
                <ul style={{ marginTop: 4, paddingLeft: 20 }}>
                  {goals.emotion.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </Space>
        );
      } else if (field.key === 'homework') {
        const homework = field.content as any;
        return (
          <Space direction="vertical" size="small">
            <div>
              <Tag color="red">必做</Tag>
              <Text>{homework.required}</Text>
            </div>
            {homework.optional && (
              <div>
                <Tag color="blue">选做</Tag>
                <Text>{homework.optional}</Text>
              </div>
            )}
          </Space>
        );
      }
    }

    if (field.type === 'array' && Array.isArray(field.content)) {
      const steps = field.content as TeachingStep[];
      return (
        <Collapse
          items={steps.map((step, index) => ({
            key: index,
            label: `${step.stage} (${step.duration})`,
            children: (
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <div>
                  <Text strong>教师活动：</Text>
                  <Paragraph>{step.teacher_activity}</Paragraph>
                </div>
                <div>
                  <Text strong>学生活动：</Text>
                  <Paragraph>{step.student_activity}</Paragraph>
                </div>
                <div>
                  <Text strong>设计意图：</Text>
                  <Text type="secondary">{step.design_intent}</Text>
                </div>
              </Space>
            ),
          }))}
        />
      );
    }

    return <Paragraph>{field.content}</Paragraph>;
  };

  return (
    <List
      dataSource={fields}
      renderItem={(field) => (
        <List.Item style={{ border: 'none', padding: '8px 0' }}>
          <Card
            size="small"
            title={
              <Space>
                <Title level={5} style={{ margin: 0 }}>
                  {field.title}
                </Title>
              </Space>
            }
            extra={
              <Space>
                {editingField !== field.key && (
                  <>
                    <Button
                      size="small"
                      icon={<ReloadOutlined />}
                      onClick={() => onRegenerateField(field.key)}
                      loading={isRegenerating && regeneratingField === field.key}
                    >
                      重新生成
                    </Button>
                    <Button
                      size="small"
                      onClick={() => handleEdit(field.key, field.content)}
                    >
                      编辑
                    </Button>
                  </>
                )}
              </Space>
            }
            style={{ width: '100%' }}
          >
            {renderContent(field)}
          </Card>
        </List.Item>
      )}
    />
  );
}

export default GeneratedContent;
