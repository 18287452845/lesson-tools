/**
 * Subject Management Page - Full CRUD operations with category grouping
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Space,
  message,
  Popconfirm,
  Typography,
  Badge,
  Select,
  Collapse,
  Tooltip,
  Tag,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { SubjectInfo, SubjectWithUsageStats, SubjectCreateRequest, SubjectUpdateRequest } from '@/types';
import { subjectApi } from '@/services/api';

const { Title, Text } = Typography;
const { Panel } = Collapse;

const SubjectManager: React.FC = () => {
  const [subjects, setSubjects] = useState<SubjectInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingSubject, setEditingSubject] = useState<SubjectInfo | null>(null);
  const [selectedSubjectStats, setSelectedSubjectStats] = useState<SubjectWithUsageStats | null>(null);
  const [statsModalVisible, setStatsModalVisible] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    loadSubjects();
  }, []);

  const loadSubjects = async () => {
    setLoading(true);
    try {
      const data = await subjectApi.listSubjects();
      setSubjects(data.subjects);
    } catch (error: any) {
      message.error(error.message || '加载学科失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingSubject(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (subject: SubjectInfo) => {
    setEditingSubject(subject);
    form.setFieldsValue({
      name: subject.name,
      category: subject.category,
      description: subject.description,
    });
    setModalVisible(true);
  };

  const handleViewStats = async (subject: SubjectInfo) => {
    try {
      const stats = await subjectApi.getSubject(subject.id);
      setSelectedSubjectStats(stats);
      setStatsModalVisible(true);
    } catch (error: any) {
      message.error(error.message || '加载使用统计失败');
    }
  };

  const handleDelete = async (id: string, name: string) => {
    try {
      await subjectApi.deleteSubject(id);
      message.success('删除成功');
      loadSubjects();
    } catch (error: any) {
      message.error(error.response?.data?.detail || error.message || '删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (editingSubject) {
        await subjectApi.updateSubject(editingSubject.id, values);
        message.success('更新成功');
      } else {
        await subjectApi.createSubject(values);
        message.success('创建成功');
      }

      setModalVisible(false);
      loadSubjects();
    } catch (error: any) {
      message.error(error.response?.data?.detail || error.message || '操作失败');
    }
  };

  const getCategoryLabel = (category: string) => {
    const labels: Record<string, string> = {
      university_course: '大学课程',
      basic_subject: '基础学科',
    };
    return labels[category] || category;
  };

  const columns = [
    {
      title: '学科名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: SubjectInfo) => (
        <Space>
          {text}
          {record.is_preset && (
            <Badge count="预设" style={{ backgroundColor: '#52c41a' }} />
          )}
        </Space>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => (
        <Tag color={category === 'university_course' ? 'blue' : 'green'}>
          {getCategoryLabel(category)}
        </Tag>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (text: string) => text || '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: SubjectInfo) => (
        <Space>
          <Tooltip title="查看使用统计">
            <Button
              type="link"
              size="small"
              icon={<InfoCircleOutlined />}
              onClick={() => handleViewStats(record)}
            >
              统计
            </Button>
          </Tooltip>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          {!record.is_preset && (
            <Popconfirm
              title="确定删除？"
              description="如果该学科正在被使用，将无法删除"
              onConfirm={() => handleDelete(record.id, record.name)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          )}
          {record.is_preset && (
            <Tooltip title="预设学科不能删除">
              <Button type="link" size="small" danger icon={<DeleteOutlined />} disabled>
                删除
              </Button>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  // Group subjects by category
  const universitySubjects = subjects.filter(s => s.category === 'university_course');
  const basicSubjects = subjects.filter(s => s.category === 'basic_subject');

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px' }}>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={3}>学科管理</Title>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            新建学科
          </Button>
        </div>

        <Collapse defaultActiveKey={['university_course', 'basic_subject']}>
          <Panel
            header={
              <Space>
                <Text strong>大学课程</Text>
                <Badge count={universitySubjects.length} showZero style={{ backgroundColor: '#1890ff' }} />
              </Space>
            }
            key="university_course"
          >
            <Table
              columns={columns}
              dataSource={universitySubjects}
              rowKey="id"
              loading={loading}
              pagination={false}
              size="small"
            />
          </Panel>

          <Panel
            header={
              <Space>
                <Text strong>基础学科</Text>
                <Badge count={basicSubjects.length} showZero style={{ backgroundColor: '#52c41a' }} />
              </Space>
            }
            key="basic_subject"
          >
            <Table
              columns={columns}
              dataSource={basicSubjects}
              rowKey="id"
              loading={loading}
              pagination={false}
              size="small"
            />
          </Panel>
        </Collapse>
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingSubject ? '编辑学科' : '新建学科'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="学科名称"
            name="name"
            rules={[{ required: true, message: '请输入学科名称' }]}
          >
            <Input
              placeholder="例如：机器学习"
              disabled={editingSubject?.is_preset}
            />
          </Form.Item>

          {!editingSubject && (
            <Form.Item
              label="分类"
              name="category"
              rules={[{ required: true, message: '请选择分类' }]}
            >
              <Select placeholder="选择学科分类">
                <Select.Option value="university_course">大学课程</Select.Option>
                <Select.Option value="basic_subject">基础学科</Select.Option>
              </Select>
            </Form.Item>
          )}

          {editingSubject && (
            <Form.Item label="分类">
              <Input value={getCategoryLabel(editingSubject.category)} disabled />
            </Form.Item>
          )}

          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="学科描述（可选）" />
          </Form.Item>

          {editingSubject?.is_preset && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              注意：预设学科只能修改描述信息，不能修改名称和分类
            </Text>
          )}
        </Form>
      </Modal>

      {/* Usage Statistics Modal */}
      <Modal
        title="使用统计"
        open={statsModalVisible}
        onCancel={() => setStatsModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setStatsModalVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        {selectedSubjectStats && (
          <div>
            <Title level={4}>{selectedSubjectStats.name}</Title>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text strong>分类：</Text>
                <Tag color={selectedSubjectStats.category === 'university_course' ? 'blue' : 'green'}>
                  {getCategoryLabel(selectedSubjectStats.category)}
                </Tag>
              </div>
              <div>
                <Text strong>类型：</Text>
                {selectedSubjectStats.is_preset ? (
                  <Badge count="预设" style={{ backgroundColor: '#52c41a' }} />
                ) : (
                  <Badge count="自定义" style={{ backgroundColor: '#1890ff' }} />
                )}
              </div>
              {selectedSubjectStats.description && (
                <div>
                  <Text strong>描述：</Text>
                  <Text>{selectedSubjectStats.description}</Text>
                </div>
              )}
              <div style={{ marginTop: 16 }}>
                <Text strong>使用情况：</Text>
                <ul>
                  <li>模板数量：{selectedSubjectStats.usage_stats.template_count}</li>
                  <li>教案数量：{selectedSubjectStats.usage_stats.lesson_plan_count}</li>
                  <li>教材数量：{selectedSubjectStats.usage_stats.textbook_count}</li>
                  <li>批量任务数量：{selectedSubjectStats.usage_stats.batch_task_count}</li>
                </ul>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  总计使用：{
                    selectedSubjectStats.usage_stats.template_count +
                    selectedSubjectStats.usage_stats.lesson_plan_count +
                    selectedSubjectStats.usage_stats.textbook_count +
                    selectedSubjectStats.usage_stats.batch_task_count
                  } 处
                </Text>
              </div>
            </Space>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default SubjectManager;
