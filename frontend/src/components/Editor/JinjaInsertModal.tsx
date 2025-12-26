/**
 * Jinja2 变量插入弹窗
 *
 * 提供可视化界面插入 Jinja2 变量、循环和条件
 */
import React, { useState } from 'react'
import { Modal, Form, Input, Select, Radio, Space, Alert, Typography } from 'antd'
import type { Editor } from '@tiptap/react'

const { Text, Paragraph } = Typography
const { TextArea } = Input

interface JinjaInsertModalProps {
  visible: boolean
  onClose: () => void
  editor: Editor | null
  existingVariables?: string[]
}

type JinjaType = 'variable' | 'for-loop' | 'if-condition'

const JinjaInsertModal: React.FC<JinjaInsertModalProps> = ({
  visible,
  onClose,
  editor,
  existingVariables = [],
}) => {
  const [form] = Form.useForm()
  const [jinjaType, setJinjaType] = useState<JinjaType>('variable')

  const handleInsert = async () => {
    try {
      const values = await form.validateFields()

      if (!editor) {
        return
      }

      let jinjaCode = ''
      let blockType = ''

      switch (jinjaType) {
        case 'variable':
          // 简单变量: {{ variable_name }}
          jinjaCode = `{{${values.variableName}}}`
          blockType = 'variable'
          break

        case 'for-loop':
          // For 循环: {% for item in items %}...{% endfor %}
          const forStart = `{% for ${values.itemName} in ${values.listName} %}`
          const forEnd = `{% endfor %}`
          const content = values.loopContent || '内容'

          // 插入开始标签
          editor.commands.setJinjaPlaceholder({
            jinja: forStart,
            type: 'block',
            blockType: 'for-start',
          })

          // 插入换行和内容
          editor.commands.insertContent('<p>' + content + '</p>')

          // 插入结束标签
          editor.commands.setJinjaPlaceholder({
            jinja: forEnd,
            type: 'block',
            blockType: 'for-end',
          })

          onClose()
          form.resetFields()
          return

        case 'if-condition':
          // If 条件: {% if condition %}...{% endif %}
          const ifStart = `{% if ${values.condition} %}`
          const ifEnd = `{% endif %}`
          const ifContent = values.ifContent || '内容'

          // 插入开始标签
          editor.commands.setJinjaPlaceholder({
            jinja: ifStart,
            type: 'block',
            blockType: 'if-start',
          })

          // 插入内容
          editor.commands.insertContent('<p>' + ifContent + '</p>')

          // 如果有 else
          if (values.hasElse) {
            editor.commands.setJinjaPlaceholder({
              jinja: '{% else %}',
              type: 'block',
              blockType: 'else',
            })
            editor.commands.insertContent('<p>' + (values.elseContent || 'Else 内容') + '</p>')
          }

          // 插入结束标签
          editor.commands.setJinjaPlaceholder({
            jinja: ifEnd,
            type: 'block',
            blockType: 'if-end',
          })

          onClose()
          form.resetFields()
          return
      }

      // 对于简单变量，直接插入
      if (jinjaCode) {
        editor.commands.setJinjaPlaceholder({
          jinja: jinjaCode,
          type: blockType,
        })
      }

      onClose()
      form.resetFields()
    } catch (error) {
      console.error('插入 Jinja2 失败:', error)
    }
  }

  const handleCancel = () => {
    onClose()
    form.resetFields()
    setJinjaType('variable')
  }

  return (
    <Modal
      title="插入 Jinja2 语法"
      open={visible}
      onOk={handleInsert}
      onCancel={handleCancel}
      width={600}
      okText="插入"
      cancelText="取消"
    >
      <Form form={form} layout="vertical">
        {/* 选择类型 */}
        <Form.Item label="选择类型" required>
          <Radio.Group
            value={jinjaType}
            onChange={(e) => setJinjaType(e.target.value)}
            buttonStyle="solid"
          >
            <Radio.Button value="variable">变量</Radio.Button>
            <Radio.Button value="for-loop">循环</Radio.Button>
            <Radio.Button value="if-condition">条件</Radio.Button>
          </Radio.Group>
        </Form.Item>

        {/* 变量输入 */}
        {jinjaType === 'variable' && (
          <>
            <Alert
              message="插入简单变量"
              description="将在光标位置插入 {{ variable_name }} 格式的变量"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Form.Item
              label="变量名"
              name="variableName"
              rules={[
                { required: true, message: '请输入变量名' },
                {
                  pattern: /^[a-zA-Z_][a-zA-Z0-9_\.]*$/,
                  message: '变量名只能包含字母、数字、下划线和点号，且不能以数字开头',
                },
              ]}
            >
              <Select
                mode="tags"
                maxCount={1}
                placeholder="输入变量名或从现有变量中选择"
                options={existingVariables.map((v) => ({ label: v, value: v }))}
              />
            </Form.Item>

            <Paragraph type="secondary" style={{ fontSize: 12 }}>
              示例: student_name, course.title, teaching_goals.knowledge
            </Paragraph>
          </>
        )}

        {/* For 循环 */}
        {jinjaType === 'for-loop' && (
          <>
            <Alert
              message="插入 For 循环"
              description={'将插入 {% for item in items %}...{% endfor %} 结构'}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Form.Item
              label="循环项名称"
              name="itemName"
              rules={[
                { required: true, message: '请输入循环项名称' },
                {
                  pattern: /^[a-zA-Z_][a-zA-Z0-9_]*$/,
                  message: '只能包含字母、数字和下划线，且不能以数字开头',
                },
              ]}
            >
              <Input placeholder="例如: step, item, activity" />
            </Form.Item>

            <Form.Item
              label="列表变量名"
              name="listName"
              rules={[
                { required: true, message: '请输入列表变量名' },
                {
                  pattern: /^[a-zA-Z_][a-zA-Z0-9_\.]*$/,
                  message: '变量名格式不正确',
                },
              ]}
            >
              <Select
                mode="tags"
                maxCount={1}
                placeholder="输入列表变量名或选择现有变量"
                options={existingVariables.map((v) => ({ label: v, value: v }))}
              />
            </Form.Item>

            <Form.Item label="循环内容" name="loopContent">
              <TextArea
                rows={3}
                placeholder="循环体中的内容（可以使用循环项变量）"
                defaultValue="{{ loop.index }}. {{ step.title }}\n内容: {{ step.content }}"
              />
            </Form.Item>

            <Paragraph type="secondary" style={{ fontSize: 12 }}>
              {'示例: {% for step in teaching_steps %} ... {% endfor %}'}
              <br />
              可用变量: loop.index (索引), loop.first (是否第一个), loop.last (是否最后一个)
            </Paragraph>
          </>
        )}

        {/* If 条件 */}
        {jinjaType === 'if-condition' && (
          <>
            <Alert
              message="插入 If 条件"
              description={'将插入 {% if condition %}...{% endif %} 结构'}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Form.Item
              label="条件表达式"
              name="condition"
              rules={[{ required: true, message: '请输入条件表达式' }]}
            >
              <Input placeholder="例如: homework, student_count > 30" />
            </Form.Item>

            <Form.Item label="条件为真时的内容" name="ifContent">
              <TextArea
                rows={2}
                placeholder="条件成立时显示的内容"
                defaultValue="作业布置: {{ homework }}"
              />
            </Form.Item>

            <Form.Item label="是否包含 Else" name="hasElse" valuePropName="checked">
              <Radio.Group>
                <Radio value={false}>不包含</Radio>
                <Radio value={true}>包含 Else 分支</Radio>
              </Radio.Group>
            </Form.Item>

            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) =>
                prevValues.hasElse !== currentValues.hasElse
              }
            >
              {({ getFieldValue }) =>
                getFieldValue('hasElse') ? (
                  <Form.Item label="Else 分支内容" name="elseContent">
                    <TextArea rows={2} placeholder="条件不成立时显示的内容" />
                  </Form.Item>
                ) : null
              }
            </Form.Item>

            <Paragraph type="secondary" style={{ fontSize: 12 }}>
              {'示例: {% if homework %}作业: {{ homework }}{% endif %}'}
            </Paragraph>
          </>
        )}
      </Form>
    </Modal>
  )
}

export default JinjaInsertModal
