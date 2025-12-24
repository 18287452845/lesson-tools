/**
 * TipTap 自定义扩展：Jinja2 占位符
 *
 * 将 Jinja2 语法（{{variable}}, {% for %}, 等）渲染为不可编辑的徽章
 */
import { Node, mergeAttributes } from '@tiptap/core'
import { ReactNodeViewRenderer } from '@tiptap/react'
import JinjaPlaceholderView from './JinjaPlaceholderView'

export interface JinjaPlaceholderOptions {
  HTMLAttributes: Record<string, any>
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    jinjaPlaceholder: {
      /**
       * 插入 Jinja2 占位符
       */
      setJinjaPlaceholder: (attributes: { jinja: string; type: string }) => ReturnType
    }
  }
}

/**
 * Jinja2 占位符扩展
 *
 * 将包含 data-jinja 属性的 span 标签渲染为不可编辑的徽章
 */
export const JinjaPlaceholder = Node.create<JinjaPlaceholderOptions>({
  name: 'jinjaPlaceholder',

  group: 'inline',

  inline: true,

  atom: true,  // 原子节点，不可拆分

  addOptions() {
    return {
      HTMLAttributes: {},
    }
  },

  addAttributes() {
    return {
      jinja: {
        default: null,
        parseHTML: element => element.getAttribute('data-jinja'),
        renderHTML: attributes => {
          if (!attributes.jinja) {
            return {}
          }

          return {
            'data-jinja': attributes.jinja,
          }
        },
      },
      type: {
        default: 'variable',
        parseHTML: element => element.getAttribute('data-type') || 'variable',
        renderHTML: attributes => {
          return {
            'data-type': attributes.type,
          }
        },
      },
      blockType: {
        default: null,
        parseHTML: element => element.getAttribute('data-block-type'),
        renderHTML: attributes => {
          if (!attributes.blockType) {
            return {}
          }

          return {
            'data-block-type': attributes.blockType,
          }
        },
      },
      id: {
        default: null,
        parseHTML: element => element.getAttribute('id'),
        renderHTML: attributes => {
          if (!attributes.id) {
            return {}
          }

          return {
            id: attributes.id,
          }
        },
      },
    }
  },

  parseHTML() {
    return [
      {
        tag: 'span[data-jinja]',
        getAttrs: element => {
          const el = element as HTMLElement
          return {
            jinja: el.getAttribute('data-jinja'),
            type: el.getAttribute('data-type') || 'variable',
            blockType: el.getAttribute('data-block-type'),
            id: el.getAttribute('id'),
          }
        },
      },
    ]
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(
        this.options.HTMLAttributes,
        HTMLAttributes,
        {
          class: 'jinja-placeholder',
          contenteditable: 'false',
        }
      ),
      HTMLAttributes.jinja || '',
    ]
  },

  addNodeView() {
    return ReactNodeViewRenderer(JinjaPlaceholderView)
  },

  addCommands() {
    return {
      setJinjaPlaceholder:
        attributes =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs: attributes,
          })
        },
    }
  },
})
