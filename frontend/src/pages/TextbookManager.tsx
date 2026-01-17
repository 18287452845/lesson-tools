/**
 * Textbook Management Page - Full CRUD operations with chapter management
 */
import React, { useEffect, useState } from 'react';
import {
  Badge,
  Button,
  Card,
  Checkbox,
  Col,
  Divider,
  Drawer,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  BookOutlined,
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  PlusOutlined,
  SaveOutlined,
  ThunderboltOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import type {
  TextbookChapterCreateRequest,
  TextbookChapterInfo,
  TextbookCreateRequest,
  TextbookInfo,
  TextbookUpdateRequest,
} from '@/types';
import { useTextbookStore } from '@/stores/textbookStore';
import { SUBJECT_OPTIONS, GRADE_OPTIONS } from '@/types';

const { Title, Text } = Typography;
const { TextArea } = Input;

const buildChapterDrafts = (chapters: TextbookChapterInfo[]): TextbookChapterCreateRequest[] => {
  const sorted = [...chapters].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  return sorted.map((chapter, index) => ({
    chapter_number: chapter.chapter_number || `第${index + 1}章`,
    chapter_title: chapter.chapter_title || '',
    content_summary: chapter.content_summary ?? '',
    key_concepts: chapter.key_concepts ?? [],
    sort_order: chapter.sort_order ?? index + 1,
    hours_required: chapter.hours_required,
    parent_chapter_id: chapter.parent_chapter_id,
  }));
};

const normalizeDraftsForSave = (
  drafts: TextbookChapterCreateRequest[]
): TextbookChapterCreateRequest[] =>
  drafts.map((chapter, index) => ({
    chapter_number: chapter.chapter_number?.trim()
      ? chapter.chapter_number.trim()
      : `第${index + 1}章`,
    chapter_title: chapter.chapter_title?.trim()
      ? chapter.chapter_title.trim()
      : `章节${index + 1}`,
    content_summary: chapter.content_summary?.trim() || '',
    key_concepts: chapter.key_concepts?.filter(Boolean) || [],
    sort_order: index + 1,
    hours_required: chapter.hours_required,
    parent_chapter_id: chapter.parent_chapter_id,
  }));

const parseChapterLines = (
  input: string,
  startIndex: number
): TextbookChapterCreateRequest[] => {
  const lines = input
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  let autoIndex = startIndex;

  return lines.map((line) => {
    const fullMatch = line.match(/^(第?\s*\d+(?:\.\d+)?\s*章)\s*(.*)$/);
    if (fullMatch) {
      const chapterNumber = fullMatch[1].replace(/\s+/g, '');
      const chapterTitle = fullMatch[2].trim() || chapterNumber;
      return {
        chapter_number: chapterNumber,
        chapter_title: chapterTitle,
        content_summary: '',
        key_concepts: [],
      };
    }

    const numberMatch = line.match(/^(\d+(?:\.\d+)?)\s*[\\.、-]?\s*(.+)$/);
    if (numberMatch) {
      return {
        chapter_number: `第${numberMatch[1]}章`,
        chapter_title: numberMatch[2].trim() || `章节${numberMatch[1]}`,
        content_summary: '',
        key_concepts: [],
      };
    }

    const chapterNumber = `第${autoIndex}章`;
    autoIndex += 1;
    return {
      chapter_number: chapterNumber,
      chapter_title: line || chapterNumber,
      content_summary: '',
      key_concepts: [],
    };
  });
};

const TextbookManager: React.FC = () => {
  const {
    textbooks,
    loading,
    error,
    total,
    currentPage,
    pageSize,
    selectedTextbook,
    fetchTextbooks,
    createTextbook,
    updateTextbook,
    deleteTextbook,
    getTextbook,
    generateChapters,
    saveChapters,
    clearError,
    setPage,
  } = useTextbookStore();

  const [modalVisible, setModalVisible] = useState(false);
  const [editingTextbook, setEditingTextbook] = useState<TextbookInfo | null>(null);
  const [chapterDrawerVisible, setChapterDrawerVisible] = useState(false);
  const [chapterDrafts, setChapterDrafts] = useState<TextbookChapterCreateRequest[]>([]);
  const [draftLoadedTextbookId, setDraftLoadedTextbookId] = useState<string | null>(null);
  const [chapterModalVisible, setChapterModalVisible] = useState(false);
  const [generatingChapters, setGeneratingChapters] = useState(false);
  const [savingChapters, setSavingChapters] = useState(false);
  const [batchImportVisible, setBatchImportVisible] = useState(false);
  const [batchImportReplace, setBatchImportReplace] = useState(false);
  const [batchImportText, setBatchImportText] = useState('');
  const [filterSubject, setFilterSubject] = useState<string | undefined>();
  const [filterGrade, setFilterGrade] = useState<string | undefined>();

  const [form] = Form.useForm<TextbookCreateRequest | TextbookUpdateRequest>();
  const [generateForm] = Form.useForm();

  useEffect(() => {
    loadTextbooks();
  }, [currentPage, filterSubject, filterGrade]);

  useEffect(() => {
    if (error) {
      message.error(error);
      clearError();
    }
  }, [error]);

  useEffect(() => {
    if (!chapterDrawerVisible || !selectedTextbook) {
      return;
    }

    if (draftLoadedTextbookId === selectedTextbook.id) {
      return;
    }

    const drafts = buildChapterDrafts(selectedTextbook.chapters || []);
    setChapterDrafts(drafts);
    setDraftLoadedTextbookId(selectedTextbook.id);
  }, [chapterDrawerVisible, selectedTextbook, draftLoadedTextbookId]);

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

        Modal.confirm({
          title: '生成章节？',
          content: '教材创建成功！是否使用AI生成章节大纲？',
          okText: '生成章节',
          cancelText: '稍后添加',
          onOk: () => {
            handleManageChapters(newTextbook, true);
          },
        });
      }

      setModalVisible(false);
    } catch (error: any) {
      // Error handled by store or form validation
    }
  };

  const handleManageChapters = async (textbook: TextbookInfo, openAi = false) => {
    try {
      setChapterDrawerVisible(true);
      setDraftLoadedTextbookId(null);
      await getTextbook(textbook.id);
      if (openAi) {
        openAiGenerateModal(textbook);
      }
    } catch (error: any) {
      // Error handled by store
    }
  };

  const openAiGenerateModal = (textbook: TextbookInfo) => {
    generateForm.setFieldsValue({
      textbook_name: textbook.name,
      isbn: textbook.isbn,
      subject: textbook.subject,
      grade: textbook.grade,
      additional_info: '',
    });
    setChapterModalVisible(true);
  };

  const confirmAiOverwrite = () => {
    if (!selectedTextbook) {
      message.warning('请先选择教材');
      return;
    }

    if (chapterDrafts.length === 0) {
      openAiGenerateModal(selectedTextbook);
      return;
    }

    Modal.confirm({
      title: 'AI覆盖章节？',
      content: 'AI生成将覆盖当前章节内容，是否继续？',
      okText: '覆盖',
      cancelText: '取消',
      onOk: () => openAiGenerateModal(selectedTextbook),
    });
  };

  const handleGenerateSubmit = async () => {
    if (!selectedTextbook) {
      message.warning('请先选择教材');
      return;
    }

    try {
      const values = await generateForm.validateFields();
      setGeneratingChapters(true);

      const response = await generateChapters(selectedTextbook.id, values);
      setChapterDrafts(
        response.chapters.map((chapter, index) => ({
          chapter_number: chapter.chapter_number || `第${index + 1}章`,
          chapter_title: chapter.chapter_title || '',
          content_summary: chapter.content_summary ?? '',
          key_concepts: chapter.key_concepts ?? [],
          sort_order: chapter.sort_order ?? index + 1,
          hours_required: chapter.hours_required,
          parent_chapter_id: chapter.parent_chapter_id,
        }))
      );
      setChapterModalVisible(false);
      message.success(response.message || '章节生成成功');
    } catch (error: any) {
      // Error handled by store
    } finally {
      setGeneratingChapters(false);
    }
  };

  const handleAddChapter = () => {
    setChapterDrafts((prev) => [
      ...prev,
      {
        chapter_number: `第${prev.length + 1}章`,
        chapter_title: '',
        content_summary: '',
        key_concepts: [],
        sort_order: prev.length + 1,
      },
    ]);
  };

  const handleUpdateChapter = (
    index: number,
    patch: Partial<TextbookChapterCreateRequest>
  ) => {
    setChapterDrafts((prev) =>
      prev.map((chapter, idx) => (idx === index ? { ...chapter, ...patch } : chapter))
    );
  };

  const handleMoveChapter = (from: number, to: number) => {
    setChapterDrafts((prev) => {
      if (to < 0 || to >= prev.length) {
        return prev;
      }
      const next = [...prev];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
  };

  const handleDeleteChapter = (index: number) => {
    setChapterDrafts((prev) => prev.filter((_, idx) => idx !== index));
  };

  const validateDrafts = () => {
    for (let i = 0; i < chapterDrafts.length; i += 1) {
      const chapter = chapterDrafts[i];
      if (!chapter.chapter_number?.trim()) {
        message.error(`第 ${i + 1} 条章节编号为空`);
        return false;
      }
      if (!chapter.chapter_title?.trim()) {
        message.error(`第 ${i + 1} 条章节标题为空`);
        return false;
      }
    }
    return true;
  };

  const handleSaveChapters = async () => {
    if (!selectedTextbook) {
      message.warning('请先选择教材');
      return;
    }
    if (!validateDrafts()) {
      return;
    }

    try {
      setSavingChapters(true);
      await saveChapters(selectedTextbook.id, normalizeDraftsForSave(chapterDrafts));
      message.success('章节保存成功');
      setDraftLoadedTextbookId(null);
    } catch (error: any) {
      // Error handled by store
    } finally {
      setSavingChapters(false);
    }
  };

  const handleBatchImportSubmit = () => {
    const startIndex = batchImportReplace ? 1 : chapterDrafts.length + 1;
    const imported = parseChapterLines(batchImportText, startIndex);
    if (imported.length === 0) {
      message.warning('没有可导入的内容');
      return;
    }

    setChapterDrafts((prev) =>
      batchImportReplace ? imported : [...prev, ...imported]
    );
    setBatchImportVisible(false);
    setBatchImportText('');
    setBatchImportReplace(false);
    message.success(`已导入 ${imported.length} 个章节`);
  };

  const handleCloseDrawer = () => {
    setChapterDrawerVisible(false);
    setDraftLoadedTextbookId(null);
    setChapterDrafts([]);
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
          {record.isbn && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              ISBN: {record.isbn}
            </Text>
          )}
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
          {record.publisher && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.publisher}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '学科',
      dataIndex: 'subject',
      key: 'subject',
      width: 120,
      render: (text: string) => (text ? <Tag color="blue">{text}</Tag> : '-'),
    },
    {
      title: '年级',
      dataIndex: 'grade',
      key: 'grade',
      width: 100,
      render: (text: string) => (text ? <Tag color="green">{text}</Tag> : '-'),
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
      width: 260,
      render: (_: any, record: TextbookInfo) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<FileTextOutlined />}
            onClick={() => handleManageChapters(record)}
          >
            章节管理
          </Button>
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
                  options={SUBJECT_OPTIONS.map((s) => ({ label: s, value: s }))}
                />
                <Select
                  placeholder="年级筛选"
                  style={{ width: 120 }}
                  allowClear
                  value={filterGrade}
                  onChange={setFilterGrade}
                  options={GRADE_OPTIONS.map((g) => ({ label: g, value: g }))}
                />
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
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
                  options={SUBJECT_OPTIONS.map((s) => ({ label: s, value: s }))}
                  showSearch
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="适用年级" name="grade">
                <Select
                  placeholder="请选择年级"
                  options={GRADE_OPTIONS.map((g) => ({ label: g, value: g }))}
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
            <Form.Item label="教材名称" name="textbook_name" rules={[{ required: true }]}>
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
              <TextArea rows={3} placeholder="补充说明，帮助AI更准确地生成章节（可选）" />
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
        onClose={handleCloseDrawer}
        width={900}
      >
        <Spin spinning={loading} tip="加载章节中...">
          {selectedTextbook && (
            <>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">
                  {selectedTextbook.author && `作者：${selectedTextbook.author}`}
                  {selectedTextbook.publisher && ` | 出版社：${selectedTextbook.publisher}`}
                </Text>
              </div>

              <Space wrap style={{ marginBottom: 16 }}>
                <Button icon={<PlusOutlined />} onClick={handleAddChapter}>
                  新增章节
                </Button>
                <Button icon={<UploadOutlined />} onClick={() => setBatchImportVisible(true)}>
                  批量导入
                </Button>
                <Button icon={<ThunderboltOutlined />} onClick={confirmAiOverwrite}>
                  AI覆盖
                </Button>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSaveChapters}
                  loading={savingChapters}
                >
                  保存章节
                </Button>
              </Space>

              <Text type="secondary">
                这里是教材章节的唯一编辑列表，保存后将替换教材章节。章节数量可与教材不一致，AI生成时会自动调整。
              </Text>

              <Divider />

              {chapterDrafts.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '32px 0' }}>
                  <Text type="secondary">暂无章节</Text>
                  <div style={{ marginTop: 16 }}>
                    <Space>
                      <Button type="primary" icon={<PlusOutlined />} onClick={handleAddChapter}>
                        新增章节
                      </Button>
                      <Button icon={<ThunderboltOutlined />} onClick={confirmAiOverwrite}>
                        AI生成章节
                      </Button>
                    </Space>
                  </div>
                </div>
              ) : (
                <List
                  dataSource={chapterDrafts}
                  renderItem={(chapter, index) => (
                    <List.Item key={`${chapter.chapter_number}-${index}`}>
                      <Card
                        size="small"
                        style={{ width: '100%' }}
                        title={
                          <Space>
                            <Text type="secondary">#{index + 1}</Text>
                            <Input
                              value={chapter.chapter_number}
                              onChange={(e) =>
                                handleUpdateChapter(index, { chapter_number: e.target.value })
                              }
                              placeholder="第1章"
                              style={{ width: 110 }}
                            />
                            <Input
                              value={chapter.chapter_title}
                              onChange={(e) =>
                                handleUpdateChapter(index, { chapter_title: e.target.value })
                              }
                              placeholder="章节标题"
                              style={{ width: 260 }}
                            />
                          </Space>
                        }
                        extra={
                          <Space>
                            <Button
                              size="small"
                              icon={<ArrowUpOutlined />}
                              disabled={index === 0}
                              onClick={() => handleMoveChapter(index, index - 1)}
                            />
                            <Button
                              size="small"
                              icon={<ArrowDownOutlined />}
                              disabled={index === chapterDrafts.length - 1}
                              onClick={() => handleMoveChapter(index, index + 1)}
                            />
                            <Popconfirm
                              title="删除章节？"
                              onConfirm={() => handleDeleteChapter(index)}
                              okText="删除"
                              cancelText="取消"
                            >
                              <Button size="small" danger icon={<DeleteOutlined />} />
                            </Popconfirm>
                          </Space>
                        }
                      >
                        <Row gutter={16}>
                          <Col span={16}>
                            <Text type="secondary">内容概述</Text>
                            <TextArea
                              value={chapter.content_summary}
                              onChange={(e) =>
                                handleUpdateChapter(index, { content_summary: e.target.value })
                              }
                              rows={3}
                              style={{ marginTop: 8 }}
                              placeholder="简要描述本章内容"
                            />
                          </Col>
                          <Col span={8}>
                            <Text type="secondary">核心概念</Text>
                            <Select
                              mode="tags"
                              tokenSeparators={[',', '，', ';', '；']}
                              value={chapter.key_concepts}
                              onChange={(value) =>
                                handleUpdateChapter(index, { key_concepts: value as string[] })
                              }
                              style={{ width: '100%', marginTop: 8 }}
                              placeholder="输入后回车或逗号分隔"
                            />
                            <div style={{ marginTop: 12 }}>
                              <Text type="secondary">建议课时</Text>
                              <InputNumber
                                min={0}
                                step={0.5}
                                value={chapter.hours_required}
                                onChange={(value) =>
                                  handleUpdateChapter(index, {
                                    hours_required: typeof value === 'number' ? value : undefined,
                                  })
                                }
                                style={{ width: '100%', marginTop: 8 }}
                                placeholder="例如：2"
                              />
                            </div>
                          </Col>
                        </Row>
                      </Card>
                    </List.Item>
                  )}
                />
              )}
            </>
          )}
        </Spin>
      </Drawer>

      {/* Batch Import Modal */}
      <Modal
        title="批量导入章节"
        open={batchImportVisible}
        onOk={handleBatchImportSubmit}
        onCancel={() => {
          setBatchImportVisible(false);
          setBatchImportText('');
          setBatchImportReplace(false);
        }}
        width={600}
        destroyOnClose
      >
        <TextArea
          rows={8}
          value={batchImportText}
          onChange={(e) => setBatchImportText(e.target.value)}
          placeholder="每行一个章节，例如：&#10;第1章 计算机基础&#10;第2章 程序结构&#10;3 数据类型"
        />
        <div style={{ marginTop: 12 }}>
          <Checkbox
            checked={batchImportReplace}
            onChange={(e) => setBatchImportReplace(e.target.checked)}
          >
            覆盖现有章节
          </Checkbox>
        </div>
      </Modal>
    </div>
  );
};

export default TextbookManager;
