/**
 * Template Manager page
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Table,
  Space,
  Popconfirm,
  message,
  Modal,
  Form,
  Input,
  Select,
  Upload,
  Typography,
} from 'antd';
import { UploadOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { useTemplateStore } from '@/stores/templateStore';
import { SUBJECT_OPTIONS, GRADE_OPTIONS } from '@/types';

const { Title } = Typography;
const { TextArea } = Input;

function TemplateManager() {
  const navigate = useNavigate();
  const {
    templates,
    loading,
    error,
    fetchTemplates,
    uploadTemplate,
    deleteTemplate,
    clearError,
  } = useTemplateStore();

  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadForm] = Form.useForm();
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  useEffect(() => {
    if (error) {
      message.error(error);
      clearError();
    }
  }, [error, clearError]);

  const handleUpload = async () => {
    try {
      const values = await uploadForm.validateFields();
      if (fileList.length === 0) {
        message.error('请选择模板文件');
        return;
      }

      await uploadTemplate(fileList[0].originFileObj!, values);
      message.success('模板上传成功');
      setUploadModalOpen(false);
      setFileList([]);
      uploadForm.resetFields();
    } catch (err) {
      // Error is handled by the store
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteTemplate(id);
      message.success('模板删除成功');
    } catch (err) {
      // Error is handled by the store
    }
  };

  const columns = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '学科',
      dataIndex: 'subject',
      key: 'subject',
      render: (subject?: string) => subject || '-',
    },
    {
      title: '年级',
      dataIndex: 'grade',
      key: 'grade',
      render: (grade?: string) => grade || '-',
    },
    {
      title: '使用次数',
      dataIndex: 'use_count',
      key: 'use_count',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: any) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => navigate(`/templates/${record.id}/edit`)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个模板吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2}>模板管理</Title>
        <Space>
          <Button onClick={() => navigate('/')}>返回首页</Button>
          <Button type="primary" onClick={() => setUploadModalOpen(true)}>
            上传模板
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={templates}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

      <Modal
        title="上传模板"
        open={uploadModalOpen}
        onOk={handleUpload}
        onCancel={() => {
          setUploadModalOpen(false);
          setFileList([]);
          uploadForm.resetFields();
        }}
        confirmLoading={loading}
        width={600}
      >
        <Form form={uploadForm} layout="vertical">
          <Form.Item
            label="模板文件"
            name="file"
            rules={[{ required: true, message: '请选择模板文件' }]}
          >
            <Upload
              fileList={fileList}
              onChange={({ fileList }) => setFileList(fileList)}
              beforeUpload={() => false}
              accept=".docx"
              maxCount={1}
            >
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
          </Form.Item>

          <Form.Item
            label="模板名称"
            name="name"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="例如：小学语文通用教案模板" />
          </Form.Item>

          <Form.Item label="描述" name="description">
            <TextArea rows={3} placeholder="模板的简要描述" />
          </Form.Item>

          <Form.Item label="学科" name="subject">
            <Select
              options={SUBJECT_OPTIONS.map((s) => ({ label: s, value: s }))}
              placeholder="选择学科（可选）"
              allowClear
            />
          </Form.Item>

          <Form.Item label="年级" name="grade">
            <Select
              options={GRADE_OPTIONS.map((g) => ({ label: g, value: g }))}
              placeholder="选择年级（可选）"
              allowClear
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default TemplateManager;
