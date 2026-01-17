/**
 * Grade Management Page - Full CRUD operations with category grouping
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
import type { GradeInfo, GradeWithUsageStats, GradeCreateRequest, GradeUpdateRequest } from '@/types';
import { gradeApi } from '@/services/api';

const { Title, Text } = Typography;
const { Panel } = Collapse;

const GradeManager: React.FC = () => {
  const [grades, setGrades] = useState<GradeInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingGrade, setEditingGrade] = useState<GradeInfo | null>(null);
  const [selectedGradeStats, setSelectedGradeStats] = useState<GradeWithUsageStats | null>(null);
  const [statsModalVisible, setStatsModalVisible] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    loadGrades();
  }, []);

  const loadGrades = async () => {
    setLoading(true);
    try {
      const data = await gradeApi.listGrades();
      setGrades(data.grades);
    } catch (error: any) {
      message.error(error.message || '加载年级失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingGrade(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (grade: GradeInfo) => {
    setEditingGrade(grade);
    form.setFieldsValue({
      name: grade.name,
      category: grade.category,
      description: grade.description,
    });
    setModalVisible(true);
  };

  const handleViewStats = async (grade: GradeInfo) => {
    try {
      const stats = await gradeApi.getGrade(grade.id);
      setSelectedGradeStats(stats);
      setStatsModalVisible(true);
    } catch (error: any) {
      message.error(error.message || '加载使用统计失败');
    }
  };

  const handleDelete = async (id: string, name: string) => {
    try {
      await gradeApi.deleteGrade(id);
      message.success('删除成功');
      loadGrades();
    } catch (error: any) {
      message.error(error.response?.data?.detail || error.message || '删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (editingGrade) {
        await gradeApi.updateGrade(editingGrade.id, values);
        message.success('更新成功');
      } else {
        await gradeApi.createGrade(values);
        message.success('创建成功');
      }

      setModalVisible(false);
      loadGrades();
    } catch (error: any) {
      message.error(error.response?.data?.detail || error.message || '操作失败');
    }
  };

  const getCategoryLabel = (category: string) => {
    const labels: Record<string, string> = {
      university: '大学',
      high_school: '高中',
      middle_school: '初中',
      elementary: '小学',
    };
    return labels[category] || category;
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      university: 'purple',
      high_school: 'blue',
      middle_school: 'green',
      elementary: 'orange',
    };
    return colors[category] || 'default';
  };

  const columns = [
    {
      title: '年级名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: GradeInfo) => (
        <Space>
          {text}
          {record.is_preset && (
            <Badge count="预设" style={{ backgroundColor: '#52c41a' }} />
          )}
        </Space>
      ),
    },
    {
      title: '学段',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => (
        <Tag color={getCategoryColor(category)}>
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
      render: (_: any, record: GradeInfo) => (
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
              description="如果该年级正在被使用，将无法删除"
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
            <Tooltip title="预设年级不能删除">
              <Button type="link" size="small" danger icon={<DeleteOutlined />} disabled>
                删除
              </Button>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  // Group grades by category
  const universityGrades = grades.filter(g => g.category === 'university');
  const highSchoolGrades = grades.filter(g => g.category === 'high_school');
  const middleSchoolGrades = grades.filter(g => g.category === 'middle_school');
  const elementaryGrades = grades.filter(g => g.category === 'elementary');

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px' }}>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={3}>年级管理</Title>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            新建年级
          </Button>
        </div>

        <Collapse defaultActiveKey={['university', 'high_school', 'middle_school', 'elementary']}>
          <Panel
            header={
              <Space>
                <Text strong>大学</Text>
                <Badge count={universityGrades.length} showZero style={{ backgroundColor: '#722ed1' }} />
              </Space>
            }
            key="university"
          >
            <Table
              columns={columns}
              dataSource={universityGrades}
              rowKey="id"
              loading={loading}
              pagination={false}
              size="small"
            />
          </Panel>

          <Panel
            header={
              <Space>
                <Text strong>高中</Text>
                <Badge count={highSchoolGrades.length} showZero style={{ backgroundColor: '#1890ff' }} />
              </Space>
            }
            key="high_school"
          >
            <Table
              columns={columns}
              dataSource={highSchoolGrades}
              rowKey="id"
              loading={loading}
              pagination={false}
              size="small"
            />
          </Panel>

          <Panel
            header={
              <Space>
                <Text strong>初中</Text>
                <Badge count={middleSchoolGrades.length} showZero style={{ backgroundColor: '#52c41a' }} />
              </Space>
            }
            key="middle_school"
          >
            <Table
              columns={columns}
              dataSource={middleSchoolGrades}
              rowKey="id"
              loading={loading}
              pagination={false}
              size="small"
            />
          </Panel>

          <Panel
            header={
              <Space>
                <Text strong>小学</Text>
                <Badge count={elementaryGrades.length} showZero style={{ backgroundColor: '#fa8c16' }} />
              </Space>
            }
            key="elementary"
          >
            <Table
              columns={columns}
              dataSource={elementaryGrades}
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
        title={editingGrade ? '编辑年级' : '新建年级'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="年级名称"
            name="name"
            rules={[{ required: true, message: '请输入年级名称' }]}
          >
            <Input
              placeholder="例如：研一"
              disabled={editingGrade?.is_preset}
            />
          </Form.Item>

          {!editingGrade && (
            <Form.Item
              label="学段"
              name="category"
              rules={[{ required: true, message: '请选择学段' }]}
            >
              <Select placeholder="选择年级学段">
                <Select.Option value="university">大学</Select.Option>
                <Select.Option value="high_school">高中</Select.Option>
                <Select.Option value="middle_school">初中</Select.Option>
                <Select.Option value="elementary">小学</Select.Option>
              </Select>
            </Form.Item>
          )}

          {editingGrade && (
            <Form.Item label="学段">
              <Input value={getCategoryLabel(editingGrade.category)} disabled />
            </Form.Item>
          )}

          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="年级描述（可选）" />
          </Form.Item>

          {editingGrade?.is_preset && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              注意：预设年级只能修改描述信息，不能修改名称和学段
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
        {selectedGradeStats && (
          <div>
            <Title level={4}>{selectedGradeStats.name}</Title>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text strong>学段：</Text>
                <Tag color={getCategoryColor(selectedGradeStats.category)}>
                  {getCategoryLabel(selectedGradeStats.category)}
                </Tag>
              </div>
              <div>
                <Text strong>类型：</Text>
                {selectedGradeStats.is_preset ? (
                  <Badge count="预设" style={{ backgroundColor: '#52c41a' }} />
                ) : (
                  <Badge count="自定义" style={{ backgroundColor: '#1890ff' }} />
                )}
              </div>
              {selectedGradeStats.description && (
                <div>
                  <Text strong>描述：</Text>
                  <Text>{selectedGradeStats.description}</Text>
                </div>
              )}
              <div style={{ marginTop: 16 }}>
                <Text strong>使用情况：</Text>
                <ul>
                  <li>模板数量：{selectedGradeStats.usage_stats.template_count}</li>
                  <li>教案数量：{selectedGradeStats.usage_stats.lesson_plan_count}</li>
                  <li>教材数量：{selectedGradeStats.usage_stats.textbook_count}</li>
                  <li>批量任务数量：{selectedGradeStats.usage_stats.batch_task_count}</li>
                </ul>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  总计使用：{
                    selectedGradeStats.usage_stats.template_count +
                    selectedGradeStats.usage_stats.lesson_plan_count +
                    selectedGradeStats.usage_stats.textbook_count +
                    selectedGradeStats.usage_stats.batch_task_count
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

export default GradeManager;
