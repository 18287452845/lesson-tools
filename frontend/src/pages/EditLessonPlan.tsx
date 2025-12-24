/**
 * Edit Lesson Plan page - Edit existing lesson plans
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Card,
  Upload,
  Typography,
  Space,
  Alert,
  List,
  Tag,
  Modal,
  Input,
  Select,
  message,
  Spin,
  Divider,
  Row,
  Col,
  Form,
} from 'antd';
import {
  ArrowLeftOutlined,
  UploadOutlined,
  SaveOutlined,
  UndoOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useEditorStore } from '@/stores/editorStore';
import { downloadBlob } from '@/services/fileService';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

function EditLessonPlan() {
  const navigate = useNavigate();
  const {
    documentId,
    filename,
    parsedSections,
    editHistory,
    isUploading,
    isEditing,
    isSaving,
    error,
    uploadDocument,
    editSection,
    aiEnhanceSection,
    addSection,
    saveDocument,
    undoEdit,
    clearCurrentDocument,
    clearError,
  } = useEditorStore();

  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [editForm] = Form.useForm();
  const [addForm] = Form.useForm();

  const sectionNames: Record<string, string> = {
    teaching_goals: '教学目标',
    key_points: '教学重点',
    difficult_points: '教学难点',
    teaching_tools: '教具准备',
    teaching_methods: '教学方法',
    student_analysis: '学情分析',
    textbook_analysis: '教材分析',
    teaching_process: '教学过程',
    homework: '作业布置',
    reflection: '教学反思',
    blackboard_design: '板书设计',
  };

  const handleUpload = async (file: File) => {
    try {
      await uploadDocument(file);
      message.success('文档上传成功，已自动识别各部分内容');
    } catch (err) {
      // Error is handled by the store
    }
    return false;
  };

  const handleEditSection = (sectionName: string) => {
    setSelectedSection(sectionName);
    const section = parsedSections[sectionName];
    editForm.setFieldsValue({
      operation: 'ai_modify',
      content: section?.content || '',
      ai_instruction: '',
    });
    setEditModalOpen(true);
  };

  const handleEditSubmit = async () => {
    if (!selectedSection) return;

    try {
      const values = await editForm.validateFields();
      await editSection({
        section_name: selectedSection,
        operation: values.operation,
        content: values.content,
        ai_instruction: values.ai_instruction,
      });
      message.success('编辑成功');
      setEditModalOpen(false);
    } catch (err) {
      // Error is handled by the store
    }
  };

  const handleAddSection = async () => {
    try {
      const values = await addForm.validateFields();
      await addSection(
        values.section_name,
        true,
        values.manual_content
      );
      message.success('添加成功');
      setAddModalOpen(false);
      addForm.resetFields();
    } catch (err) {
      // Error is handled by the store
    }
  };

  const handleSave = async () => {
    try {
      const blob = await saveDocument();
      downloadBlob(blob, filename!.replace('.docx', '_edited.docx'));
      message.success('文档已保存');
    } catch (err) {
      // Error is handled by the store
    }
  };

  const handleUndo = async () => {
    try {
      await undoEdit();
      message.success('撤销成功');
    } catch (err) {
      // Error is handled by the store
    }
  };

  const handleAiEnhance = async (sectionName: string, type: string) => {
    try {
      await aiEnhanceSection(sectionName, type);
      message.success('AI增强成功');
    } catch (err) {
      // Error is handled by the store
    }
  };

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
          返回首页
        </Button>
      </div>

      <Title level={2}>编辑旧教案</Title>

      {!documentId ? (
        <Card style={{ textAlign: 'center', padding: '60px 20px' }}>
          <Upload.Dragger
            accept=".docx"
            beforeUpload={handleUpload}
            showUploadList={false}
            disabled={isUploading}
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: 48 }} />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">
              支持 .docx 格式的教案文档，上传后自动识别各部分内容
            </p>
          </Upload.Dragger>

          {error && (
            <Alert
              type="error"
              message={error}
              closable
              onClose={clearError}
              style={{ marginTop: 16 }}
            />
          )}
        </Card>
      ) : (
        <>
          <div style={{ marginBottom: 16 }}>
            <Space>
              <Text strong>当前文档：</Text>
              <Text>{filename}</Text>
              <Button size="small" onClick={clearCurrentDocument}>
                重新上传
              </Button>
            </Space>
          </div>

          <Row gutter={16}>
            <Col xs={24} lg={8}>
              <Card
                title="文档结构"
                extra={
                  <Button
                    type="primary"
                    size="small"
                    icon={<SaveOutlined />}
                    onClick={handleSave}
                    loading={isSaving}
                  >
                    保存文档
                  </Button>
                }
              >
                <List
                  dataSource={Object.entries(parsedSections)}
                  renderItem={(item) => {
                    const [key, section] = item;
                    const displayName = sectionNames[key] || key;
                    return (
                      <List.Item
                        actions={[
                          section.found ? (
                            <Button
                              size="small"
                              onClick={() => handleEditSection(key)}
                            >
                              编辑
                            </Button>
                          ) : (
                            <Button
                              size="small"
                              type="dashed"
                              onClick={() => {
                                addForm.setFieldsValue({ section_name: key });
                                setAddModalOpen(true);
                              }}
                            >
                              添加
                            </Button>
                          ),
                        ]}
                      >
                        <List.Item.Meta
                          avatar={
                            section.found ? (
                              <CheckCircleOutlined style={{ color: '#52c41a' }} />
                            ) : (
                              <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                            )
                          }
                          title={displayName}
                          description={section.found ? '已识别' : '未找到'}
                        />
                      </List.Item>
                    );
                  }}
                />

                {editHistory.length > 0 && (
                  <>
                    <Divider />
                    <div style={{ marginBottom: 8 }}>
                      <Text strong>编辑历史</Text>
                    </div>
                    <Button
                      size="small"
                      icon={<UndoOutlined />}
                      onClick={handleUndo}
                      disabled={editHistory.length === 0}
                    >
                      撤销
                    </Button>
                    <List
                      size="small"
                      dataSource={editHistory.slice().reverse()}
                      renderItem={(edit) => (
                        <List.Item>
                          <Text type="secondary">
                            {new Date(edit.timestamp).toLocaleTimeString()} - {' '}
                            {sectionNames[edit.section] || edit.section} ({edit.operation})
                          </Text>
                        </List.Item>
                      )}
                    />
                  </>
                )}
              </Card>
            </Col>

            <Col xs={24} lg={16}>
              {selectedSection && parsedSections[selectedSection] ? (
                <Card
                  title={sectionNames[selectedSection]}
                  extra={
                    <Space>
                      <Button size="small" onClick={() => handleAiEnhance(selectedSection, 'detailed')}>
                        更详细
                      </Button>
                      <Button size="small" onClick={() => handleAiEnhance(selectedSection, 'professional')}>
                        更专业
                      </Button>
                    </Space>
                  }
                >
                  {isEditing ? (
                    <div style={{ textAlign: 'center', padding: 40 }}>
                      <Spin />
                    </div>
                  ) : (
                    <Paragraph>
                      <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                        {parsedSections[selectedSection].content || '（暂无内容）'}
                      </pre>
                    </Paragraph>
                  )}
                </Card>
              ) : (
                <Card>
                  <div style={{ textAlign: 'center', padding: 40 }}>
                    <Text type="secondary">请从左侧选择要编辑的部分</Text>
                  </div>
                </Card>
              )}
            </Col>
          </Row>
        </>
      )}

      {/* Edit Modal */}
      <Modal
        title={`编辑${selectedSection ? sectionNames[selectedSection] : ''}`}
        open={editModalOpen}
        onOk={handleEditSubmit}
        onCancel={() => setEditModalOpen(false)}
        confirmLoading={isEditing}
        width={600}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item label="编辑方式" name="operation">
            <Select>
              <Select.Option value="ai_modify">AI辅助修改</Select.Option>
              <Select.Option value="replace">直接替换</Select.Option>
              <Select.Option value="append">追加内容</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="修改说明" name="ai_instruction">
            <TextArea
              rows={3}
              placeholder="描述您希望如何修改，例如：增加实践环节、简化表述等..."
            />
          </Form.Item>

          <Form.Item label="内容预览" name="content">
            <TextArea rows={6} placeholder="原内容..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* Add Section Modal */}
      <Modal
        title="添加缺失部分"
        open={addModalOpen}
        onOk={handleAddSection}
        onCancel={() => setAddModalOpen(false)}
        confirmLoading={isEditing}
      >
        <Form form={addForm} layout="vertical">
          <Form.Item label="部分名称" name="section_name">
            <Select>
              {Object.entries(parsedSections)
                .filter(([, s]) => !s.found)
                .map(([key]) => (
                  <Select.Option key={key} value={key}>
                    {sectionNames[key]}
                  </Select.Option>
                ))}
            </Select>
          </Form.Item>

          <Form.Item label="手动输入内容（可选）">
            <TextArea rows={6} placeholder="留空则由AI自动生成" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default EditLessonPlan;
