import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag,
  Typography, message,
} from 'antd';
import { ArrowLeftOutlined, DeleteOutlined, EditOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { resourceApi } from '@/services/workspaceApi';
import type { TeachingResource, TeachingResourceInput, TeachingResourceType } from '@/types';

const { Title, Text } = Typography;
const { TextArea } = Input;
const typeLabels: Record<TeachingResourceType, string> = {
  case: '教学案例', activity: '课堂活动', assignment: '作业任务', rubric: '评价量规',
  ideology: '课程思政', reference: '参考资料', experiment: '实验资源',
};

export default function ResourceLibrary() {
  const navigate = useNavigate();
  const [form] = Form.useForm<TeachingResourceInput>();
  const [items, setItems] = useState<TeachingResource[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<TeachingResource | null>(null);
  const [search, setSearch] = useState('');

  const load = async () => {
    setLoading(true);
    try { setItems((await resourceApi.list({ search: search || undefined, limit: 100 })).resources); }
    catch (error) { message.error(error instanceof Error ? error.message : '资源加载失败'); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);

  const showEditor = (resource?: TeachingResource) => {
    setEditing(resource || null);
    form.setFieldsValue(resource ? {
      title: resource.title, resource_type: resource.resource_type, subject: resource.subject,
      grade: resource.grade, content: resource.content, source_url: resource.source_url, tags: resource.tags,
    } : { resource_type: 'case', tags: [] });
    setOpen(true);
  };
  const save = async () => {
    const values = await form.validateFields();
    if (editing) await resourceApi.update(editing.id, values);
    else await resourceApi.create(values);
    message.success(editing ? '资源已更新' : '资源已加入资源库');
    setOpen(false); form.resetFields(); await load();
  };

  return <div style={{ maxWidth: 1260, margin: '0 auto' }}>
    <Space style={{ marginBottom: 18 }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>返回</Button>
      <Title level={2} style={{ margin: 0 }}>教学资源库</Title>
    </Space>
    <Card>
      <Space wrap style={{ marginBottom: 18, width: '100%', justifyContent: 'space-between' }}>
        <Input.Search
          allowClear value={search} onChange={(e) => setSearch(e.target.value)} onSearch={() => void load()}
          prefix={<SearchOutlined />} placeholder="搜索标题、正文或标签" style={{ width: 340 }}
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={() => showEditor()}>新增资源</Button>
      </Space>
      <Table rowKey="id" loading={loading} dataSource={items} pagination={{ pageSize: 12 }} columns={[
        { title: '资源', dataIndex: 'title', render: (value, row) => <Space direction="vertical" size={1}><Text strong>{value}</Text><Text type="secondary" ellipsis style={{ maxWidth: 440 }}>{row.content}</Text></Space> },
        { title: '类型', dataIndex: 'resource_type', width: 120, render: (value: TeachingResourceType) => <Tag color="green">{typeLabels[value]}</Tag> },
        { title: '学科 / 年级', width: 160, render: (_, row) => `${row.subject || '通用'} / ${row.grade || '通用'}` },
        { title: '标签', dataIndex: 'tags', render: (tags: string[]) => tags.slice(0, 3).map((tag) => <Tag key={tag}>{tag}</Tag>) },
        { title: '使用', dataIndex: 'use_count', width: 72 },
        { title: '操作', width: 130, render: (_, row) => <Space>
          <Button type="text" icon={<EditOutlined />} onClick={() => showEditor(row)} />
          <Popconfirm title="归档这条资源？" onConfirm={async () => { await resourceApi.remove(row.id); await load(); }}><Button danger type="text" icon={<DeleteOutlined />} /></Popconfirm>
        </Space> },
      ]} />
    </Card>
    <Modal open={open} title={editing ? '编辑教学资源' : '新增教学资源'} onCancel={() => setOpen(false)} onOk={() => void save()} width={720} destroyOnClose>
      <Form form={form} layout="vertical">
        <Form.Item name="title" label="资源标题" rules={[{ required: true }]}><Input /></Form.Item>
        <Space align="start" style={{ width: '100%' }} size="large">
          <Form.Item name="resource_type" label="资源类型" rules={[{ required: true }]}><Select style={{ width: 180 }} options={Object.entries(typeLabels).map(([value, label]) => ({ value, label }))} /></Form.Item>
          <Form.Item name="subject" label="学科"><Input style={{ width: 180 }} /></Form.Item>
          <Form.Item name="grade" label="年级"><Input style={{ width: 150 }} /></Form.Item>
        </Space>
        <Form.Item name="content" label="资源内容" rules={[{ required: true }]}><TextArea rows={9} placeholder="粘贴案例、任务、量规或参考内容" /></Form.Item>
        <Form.Item name="tags" label="标签"><Select mode="tags" tokenSeparators={[',', '，']} /></Form.Item>
        <Form.Item name="source_url" label="来源链接"><Input /></Form.Item>
      </Form>
    </Modal>
  </div>;
}
