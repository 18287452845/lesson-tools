/**
 * Textbook Management Page - Full CRUD operations with AI chapter generation
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
  Tag,
  Drawer,
  List,
  Spin,
  Select,
  Row,
  Col,
  Divider,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  BookOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import type {
  TextbookInfo,
  TextbookCreateRequest,
  TextbookUpdateRequest,
  TextbookChapterCreateRequest,
  TextbookChapterGenerateRequest,
  Subject,
  GradeLevel,
} from '@/types';
import { useTextbookStore } from '@/stores/textbookStore';
import { SUBJECT_OPTIONS, GRADE_OPTIONS } from '@/types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const TextbookManager: React.FC = () => {
  const {
    textbooks,
    loading,
    error,
    total,
    currentPage,
    pageSize,
    selectedTextbook,
    generatedChapters,
    fetchTextbooks,
    createTextbook,
    updateTextbook,
    deleteTextbook,
    getTextbook,
    generateChapters,
    setGeneratedChapters,
    saveChapters,
    clearError,
    setPage,
  } = useTextbookStore();

  const [modalVisible, setModalVisible] = useState(false);
  const [editingTextbook, setEditingTextbook] = useState<TextbookInfo | null>(null);
  const [chapterModalVisible, setChapterModalVisible] = useState(false);
  const [chapterDrawerVisible, setChapterDrawerVisible] = useState(false);
  const [generatingChapters, setGeneratingChapters] = useState(false);
  const [form] = Form.useForm();
  const [generateForm] = Form.useForm();
  const [filterSubject, setFilterSubject] = useState<string | undefined>();
  const [filterGrade, setFilterGrade] = useState<string | undefined>();

  useEffect(() => {
    loadTextbooks();
  }, [currentPage, filterSubject, filterGrade]);

  useEffect(() => {
    if (error) {
      message.error(error);
      clearError();
    }
  }, [error]);

  const loadTextbooks = async () => {
    try {
      await fetchTextbooks({
        page: currentPage,
        limit: pageSize,
        subject: filterSubject,
        grade: filterGrade,
        status: 'active',
      });
    } catch (error: any) {
      // Error handled by store
    }
  };

  const handleCreate = () => {
    setEditingTextbook(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (textbook: TextbookInfo) => {
    setEditingTextbook(textbook);
    form.setFieldsValue({
      name: textbook.name,
      isbn: textbook.isbn,
      author: textbook.author,
      publisher: textbook.publisher,
      edition: textbook.edition,
      subject: textbook.subject,
      grade: textbook.grade,
      description: textbook.description,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteTextbook(id);
      message.success('删除成功');
    } catch (error: any) {
      // Error handled by store
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (editingTextbook) {
        await updateTextbook(editingTextbook.id, values);
        message.success('更新成功');
      } else {
        const newTextbook = await createTextbook(values);
        message.success('创建成功');

        // Ask if user wants to generate chapters
        Modal.confirm({
          title: '生成章节？',
          content: '教材创建成功！是否使用AI生成章节大纲？',
          okText: '生成章节',
          cancelText: '稍后添加',
          onOk: () => {
            handleGenerateChapters(newTextbook);
          },
        });
      }

      setModalVisible(false);
    } catch (error: any) {
      // Error handled by store or form validation
    }
  };

  const handleGenerateChapters = async (textbook: TextbookInfo) => {
    generateForm.setFieldsValue({
      textbook_name: textbook.name,
      isbn: textbook.isbn,
      subject: textbook.subject,
      grade: textbook.grade,
    });
    setEditingTextbook(textbook);
    setChapterModalVisible(true);
  };

  const handleGenerateSubmit = async () => {
    try {
      const values = await generateForm.validateFields();
      setGeneratingChapters(true);

      const response = await generateChapters(editingTextbook!.id, values);
      message.success(response.message);
      setChapterModalVisible(false);

      // Show generated chapters for review
      Modal.confirm({
        title: `已生成 ${response.chapters.length} 个章节`,
        content: '请在章节预览中审核并保存章节',
        okText: '查看章节',
        cancelText: '关闭',
        onOk: () => {
          handleViewChapters(editingTextbook!);
        },
      });
    } catch (error: any) {
      // Error handled by store
    } finally {
      setGeneratingChapters(false);
    }
  };

  const handleViewChapters = async (textbook: TextbookInfo) => {
    try {
      await getTextbook(textbook.id);
      setChapterDrawerVisible(true);
    } catch (error: any) {
      // Error handled by store
    }
  };

  const handleSaveGeneratedChapters = async () => {
    if (!selectedTextbook || generatedChapters.length === 0) {
      message.warning('没有待保存的章节');
      return;
    }

    try {
      await saveChapters(selectedTextbook.id, generatedChapters);
      message.success('章节保存成功');
      setChapterDrawerVisible(false);
    } catch (error: any) {
      // Error handled by store
    }
  };

  const handleEditChapter = (index: number, field: string, value: any) => {
    const updatedChapters = [...generatedChapters];
    updatedChapters[index] = {
      ...updatedChapters[index],
      [field]: value,
    };
    setGeneratedChapters(updatedChapters);
  };

  const handlePageChange = (page: number) => {
    setPage(page);
  };

  const columns = [
    {
      title: '教材名称',
      dataIndex: 'name',
      key: 'name',
      width: 250,
      render: (text: string, record: TextbookInfo) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text}</Text>
          {record.isbn && <Text type="secondary" style={{ fontSize: 12 }}>ISBN: {record.isbn}</Text>}
        </Space>
      ),
    },
    {
      title: '作者/出版社',
      key: 'author_publisher',
      width: 200,
      render: (_: any, record: TextbookInfo) => (
        <Space direction="vertical" size={0}>
          {record.author && <Text>{record.author}</Text>}
          {record.publisher && <Text type="secondary" style={{ fontSize: 12 }}>{record.publisher}</Text>}
        </Space>
      ),
    },
    {
      title: '学科',
      dataIndex: 'subject',
      key: 'subject',
      width: 120,
      render: (text: string) => text ? <Tag color="blue">{text}</Tag> : '-',
    },
    {
      title: '年级',
      dataIndex: 'grade',
      key: 'grade',
      width: 100,
      render: (text: string) => text ? <Tag color="green">{text}</Tag> : '-',
    },
    {
      title: '章节数',
      key: 'chapters_count',
      width: 100,
      align: 'center' as const,
      render: (_: any, record: TextbookInfo) => (
        <Badge count={record.chapters?.length || 0} showZero color="blue" />
      ),
    },
    {
      title: '使用次数',
      dataIndex: 'use_count',
      key: 'use_count',
      width: 100,
      align: 'center' as const,
    },
    {
      title: '操作',
      key: 'actions',
      width: 250,
      render: (_: any, record: TextbookInfo) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewChapters(record)}
          >
            查看章节
          </Button>
          {(!record.chapters || record.chapters.length === 0) && (
            <Button
              type="link"
              size="small"
              icon={<ThunderboltOutlined />}
              onClick={() => handleGenerateChapters(record)}
            >
              生成章节
            </Button>
          )}
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除？"
            description="删除后教材将被标记为不可用"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]} align="middle">
            <Col flex="auto">
              <Title level={3} style={{ margin: 0 }}>
                <BookOutlined /> 教材管理
              </Title>
            </Col>
            <Col>
              <Space>
                <Select
                  placeholder="学科筛选"
                  style={{ width: 150 }}
                  allowClear
                  value={filterSubject}
                  onChange={setFilterSubject}
                  options={SUBJECT_OPTIONS.map(s => ({ label: s, value: s }))}
                />
                <Select
                  placeholder="年级筛选"
                  style={{ width: 120 }}
                  allowClear
                  value={filterGrade}
                  onChange={setFilterGrade}
                  options={GRADE_OPTIONS.map(g => ({ label: g, value: g }))}
                />
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleCreate}
                >
                  新建教材
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        <Table
          columns={columns}
          dataSource={textbooks}
          rowKey="id"
          loading={loading}
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            onChange: handlePageChange,
            showSizeChanger: false,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      {/* Create/Edit Textbook Modal */}
      <Modal
        title={editingTextbook ? '编辑教材' : '新建教材'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                label="教材名称"
                name="name"
                rules={[{ required: true, message: '请输入教材名称' }]}
              >
                <Input placeholder="例如：Java程序设计（第5版）" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="ISBN" name="isbn">
                <Input placeholder="978-7-04-037123-4" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="版本/版次" name="edition">
                <Input placeholder="第5版" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="作者" name="author">
                <Input placeholder="作者姓名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="出版社" name="publisher">
                <Input placeholder="高等教育出版社" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="学科" name="subject">
                <Select
                  placeholder="请选择学科"
                  options={SUBJECT_OPTIONS.map(s => ({ label: s, value: s }))}
                  showSearch
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="适用年级" name="grade">
                <Select
                  placeholder="请选择年级"
                  options={GRADE_OPTIONS.map(g => ({ label: g, value: g }))}
                  showSearch
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="教材简介" name="description">
            <TextArea rows={4} placeholder="教材的主要特点和内容简介" />
          </Form.Item>
        </Form>
      </Modal>

      {/* AI Chapter Generation Modal */}
      <Modal
        title={
          <Space>
            <ThunderboltOutlined />
            AI生成章节大纲
          </Space>
        }
        open={chapterModalVisible}
        onOk={handleGenerateSubmit}
        onCancel={() => setChapterModalVisible(false)}
        confirmLoading={generatingChapters}
        width={600}
        destroyOnClose
      >
        <Spin spinning={generatingChapters} tip="AI正在生成章节大纲...">
          <Form form={generateForm} layout="vertical">
            <Form.Item
              label="教材名称"
              name="textbook_name"
              rules={[{ required: true }]}
            >
              <Input disabled />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="ISBN" name="isbn">
                  <Input placeholder="可选" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="学科" name="subject">
                  <Input placeholder="可选" />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item label="年级" name="grade">
              <Input placeholder="可选" />
            </Form.Item>
            <Form.Item label="补充说明" name="additional_info">
              <TextArea
                rows={3}
                placeholder="补充说明，帮助AI更准确地生成章节（可选）"
              />
            </Form.Item>
          </Form>
        </Spin>
      </Modal>

      {/* Chapters Drawer */}
      <Drawer
        title={
          <Space>
            <FileTextOutlined />
            {selectedTextbook?.name} - 章节管理
          </Space>
        }
        open={chapterDrawerVisible}
        onClose={() => setChapterDrawerVisible(false)}
        width={700}
        extra={
          generatedChapters.length > 0 && (
            <Button type="primary" onClick={handleSaveGeneratedChapters}>
              保存章节（{generatedChapters.length}个）
            </Button>
          )
        }
      >
        {selectedTextbook && (
          <>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">
                {selectedTextbook.author && `作者：${selectedTextbook.author}`}
                {selectedTextbook.publisher && ` | 出版社：${selectedTextbook.publisher}`}
              </Text>
            </div>

            {generatedChapters.length > 0 ? (
              <>
                <Divider>待审核章节（共{generatedChapters.length}个）</Divider>
                <List
                  dataSource={generatedChapters}
                  renderItem={(chapter, index) => (
                    <List.Item key={index}>
                      <Card
                        size="small"
                        style={{ width: '100%' }}
                        title={
                          <Space>
                            <Text strong>{chapter.chapter_number}</Text>
                            <Input
                              value={chapter.chapter_title}
                              onChange={(e) =>
                                handleEditChapter(index, 'chapter_title', e.target.value)
                              }
                              bordered={false}
                              style={{ fontWeight: 'bold' }}
                            />
                          </Space>
                        }
                      >
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <div>
                            <Text type="secondary">内容概述：</Text>
                            <TextArea
                              value={chapter.content_summary}
                              onChange={(e) =>
                                handleEditChapter(index, 'content_summary', e.target.value)
                              }
                              rows={2}
                              style={{ marginTop: 4 }}
                            />
                          </div>
                          <div>
                            <Text type="secondary">核心概念：</Text>
                            <div style={{ marginTop: 4 }}>
                              {chapter.key_concepts?.map((concept, i) => (
                                <Tag key={i} color="blue">
                                  {concept}
                                </Tag>
                              ))}
                            </div>
                          </div>
                          {chapter.hours_required && (
                            <Text type="secondary">
                              建议课时：{chapter.hours_required} 课时
                            </Text>
                          )}
                        </Space>
                      </Card>
                    </List.Item>
                  )}
                />
              </>
            ) : selectedTextbook.chapters && selectedTextbook.chapters.length > 0 ? (
              <>
                <Divider>已保存章节（共{selectedTextbook.chapters.length}个）</Divider>
                <List
                  dataSource={selectedTextbook.chapters}
                  renderItem={(chapter) => (
                    <List.Item key={chapter.id}>
                      <Card size="small" style={{ width: '100%' }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Text strong>
                            {chapter.chapter_number} {chapter.chapter_title}
                          </Text>
                          {chapter.content_summary && (
                            <Paragraph type="secondary" style={{ marginBottom: 8 }}>
                              {chapter.content_summary}
                            </Paragraph>
                          )}
                          {chapter.key_concepts && chapter.key_concepts.length > 0 && (
                            <div>
                              {chapter.key_concepts.map((concept, i) => (
                                <Tag key={i} color="blue">
                                  {concept}
                                </Tag>
                              ))}
                            </div>
                          )}
                          {chapter.hours_required && (
                            <Text type="secondary">
                              建议课时：{chapter.hours_required} 课时
                            </Text>
                          )}
                        </Space>
                      </Card>
                    </List.Item>
                  )}
                />
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <Text type="secondary">暂无章节</Text>
                <div style={{ marginTop: 16 }}>
                  <Button
                    type="primary"
                    icon={<ThunderboltOutlined />}
                    onClick={() => {
                      setChapterDrawerVisible(false);
                      handleGenerateChapters(selectedTextbook);
                    }}
                  >
                    AI生成章节
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
};

export default TextbookManager;
