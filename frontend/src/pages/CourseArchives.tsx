import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button, Card, Col, Form, Input, InputNumber, Modal, Popconfirm, Row, Select,
  Space, Table, Tag, Typography, message,
} from 'antd';
import { ArrowLeftOutlined, DeleteOutlined, EditOutlined, PlusOutlined, RocketOutlined } from '@ant-design/icons';
import { courseArchiveApi, resourceApi } from '@/services/workspaceApi';
import { classApi } from '@/services/api';
import { textbookApi } from '@/services/textbookApi';
import type { ClassInfo, CourseArchive, CourseArchiveInput, TeachingResource, TextbookInfo } from '@/types';

const { Title, Text } = Typography;
const currentYear = new Date().getFullYear();

export default function CourseArchives() {
  const navigate = useNavigate();
  const [form] = Form.useForm<CourseArchiveInput>();
  const [items, setItems] = useState<CourseArchive[]>([]);
  const [resources, setResources] = useState<TeachingResource[]>([]);
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [textbooks, setTextbooks] = useState<TextbookInfo[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<CourseArchive | null>(null);
  const [loading, setLoading] = useState(false);
  const load = async () => {
    setLoading(true);
    try {
      const [archiveData, resourceData, classData, textbookData] = await Promise.all([
        courseArchiveApi.list({ limit: 100 }), resourceApi.list({ limit: 100 }),
        classApi.listClasses(), textbookApi.listAllTextbooks({ status: 'active' }),
      ]);
      setItems(archiveData.archives); setResources(resourceData.resources);
      setClasses(classData.classes); setTextbooks(textbookData);
    } catch (error) { message.error(error instanceof Error ? error.message : '档案加载失败'); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);
  const edit = (archive?: CourseArchive) => {
    setEditing(archive || null);
    form.setFieldsValue(archive || {
      academic_year: `${currentYear}-${currentYear + 1}`, semester: 1, total_hours: 64,
      hours_per_lesson: 2, start_week: 1, class_ids: [], resource_ids: [],
    });
    setOpen(true);
  };
  const save = async () => {
    const values = await form.validateFields();
    if (editing) await courseArchiveApi.update(editing.id, values); else await courseArchiveApi.create(values);
    message.success(editing ? '课程档案已更新' : '课程档案已建立'); setOpen(false); await load();
  };
  return <div style={{ maxWidth: 1260, margin: '0 auto' }}>
    <Space style={{ marginBottom: 18 }}><Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>返回</Button><Title level={2} style={{ margin: 0 }}>课程 / 学期档案中心</Title></Space>
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 18 }}>
        <Text type="secondary">沉淀课程、教师、学期、课时、班级和教学资源关联，跨学期复用。</Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => edit()}>新建档案</Button>
      </div>
      <Table rowKey="id" dataSource={items} loading={loading} pagination={{ pageSize: 12 }} columns={[
        { title: '课程', dataIndex: 'course_name', render: (value, row) => <Space direction="vertical" size={0}><Text strong>{value}</Text><Text type="secondary">{row.subject} · {row.grade}</Text></Space> },
        { title: '学年学期', width: 170, render: (_, row) => <Tag color="blue">{row.academic_year} · 第{row.semester}学期</Tag> },
        { title: '教师', dataIndex: 'teacher_name', width: 110, render: (v) => v || '—' },
        { title: '课时', width: 105, render: (_, row) => `${row.total_hours} / ${row.hours_per_lesson}` },
        { title: '资源', dataIndex: 'resource_ids', width: 72, render: (v: string[]) => v.length },
        { title: '成果', width: 100, render: (_, row) => `${row.batch_task_count} 批 / ${row.lesson_plan_count} 份` },
        { title: '操作', width: 230, render: (_, row) => <Space>
          <Button size="small" type="primary" icon={<RocketOutlined />} onClick={() => navigate(`/batch-generate?course_archive_id=${row.id}`)}>开始备课</Button>
          <Button type="text" icon={<EditOutlined />} onClick={() => edit(row)} />
          <Popconfirm title="归档该课程？" onConfirm={async () => { await courseArchiveApi.remove(row.id); await load(); }}><Button danger type="text" icon={<DeleteOutlined />} /></Popconfirm>
        </Space> },
      ]} />
    </Card>
    <Modal open={open} title={editing ? '编辑课程档案' : '新建课程档案'} onCancel={() => setOpen(false)} onOk={() => void save()} width={760} destroyOnClose>
      <Form form={form} layout="vertical">
        <Row gutter={16}>
          <Col span={12}><Form.Item name="course_name" label="课程名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
          <Col span={6}><Form.Item name="subject" label="学科 / 专业" rules={[{ required: true }]}><Input /></Form.Item></Col>
          <Col span={6}><Form.Item name="grade" label="年级" rules={[{ required: true }]}><Input /></Form.Item></Col>
          <Col span={8}><Form.Item name="academic_year" label="学年" rules={[{ required: true }, { pattern: /^\d{4}-\d{4}$/, message: '格式如 2026-2027' }]}><Input /></Form.Item></Col>
          <Col span={6}><Form.Item name="semester" label="学期" rules={[{ required: true }]}><Select options={[{ value: 1, label: '第一学期' }, { value: 2, label: '第二学期' }]} /></Form.Item></Col>
          <Col span={10}><Form.Item name="teacher_name" label="授课教师"><Input /></Form.Item></Col>
          <Col span={6}><Form.Item name="total_hours" label="总课时"><InputNumber min={1} style={{ width: '100%' }} /></Form.Item></Col>
          <Col span={6}><Form.Item name="hours_per_lesson" label="每份教案课时"><InputNumber min={1} style={{ width: '100%' }} /></Form.Item></Col>
          <Col span={6}><Form.Item name="start_week" label="起始周"><InputNumber min={1} style={{ width: '100%' }} /></Form.Item></Col>
          <Col span={6}><Form.Item name="location" label="授课地点"><Input /></Form.Item></Col>
          <Col span={12}><Form.Item name="class_ids" label="授课班级"><Select mode="multiple" allowClear options={classes.map((item) => ({ value: item.id, label: item.name }))} /></Form.Item></Col>
          <Col span={12}><Form.Item name="textbook_id" label="使用教材"><Select allowClear showSearch optionFilterProp="label" options={textbooks.map((item) => ({ value: item.id, label: item.name }))} /></Form.Item></Col>
          <Col span={24}><Form.Item name="resource_ids" label="关联教学资源"><Select mode="multiple" allowClear optionFilterProp="label" options={resources.map((r) => ({ value: r.id, label: r.title }))} /></Form.Item></Col>
          <Col span={24}><Form.Item name="notes" label="档案备注"><Input.TextArea rows={3} /></Form.Item></Col>
        </Row>
      </Form>
    </Modal>
  </div>;
}
