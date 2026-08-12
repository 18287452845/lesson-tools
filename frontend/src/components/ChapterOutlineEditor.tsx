import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Button, Empty, Input, Modal, Space, Tag, Tooltip, Typography } from 'antd';
import {
  ApartmentOutlined,
  CaretDownOutlined,
  CaretRightOutlined,
  DeleteOutlined,
  EditOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusOutlined,
} from '@ant-design/icons';

const { Text } = Typography;
const { TextArea } = Input;

const INDENT_SIZE = 2;
const MAX_DEPTH = 4;
const LEVEL_LABELS = ['章', '节', '目', '点', '项'];

type OutlineEntry = {
  title: string;
  depth: number;
};

type ChapterOutlineEditorProps = {
  value?: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
  id?: string;
};

const parseOutline = (value = ''): OutlineEntry[] => {
  const entries: OutlineEntry[] = [];

  value.split(/\r?\n/).forEach((line) => {
    const expandedLine = line.replace(/^\t+/, (tabs) => ' '.repeat(tabs.length * INDENT_SIZE));
    const title = expandedLine.trim();
    if (!title) return;

    const leadingSpaces = expandedLine.length - expandedLine.trimStart().length;
    const requestedDepth = Math.min(MAX_DEPTH, Math.floor(leadingSpaces / INDENT_SIZE));
    const previousDepth = entries.at(-1)?.depth ?? 0;
    const depth = entries.length === 0 ? 0 : Math.min(requestedDepth, previousDepth + 1);
    entries.push({ title, depth });
  });

  return entries;
};

const serializeOutline = (entries: OutlineEntry[]) =>
  entries
    .filter((entry) => entry.title.trim())
    .map((entry) => `${' '.repeat(entry.depth * INDENT_SIZE)}${entry.title.trim()}`)
    .join('\n');

const ChapterOutlineEditor: React.FC<ChapterOutlineEditorProps> = ({
  value = '',
  onChange,
  disabled = false,
  id,
}) => {
  const entries = useMemo(() => parseOutline(value), [value]);
  const [bulkEditorOpen, setBulkEditorOpen] = useState(false);
  const [bulkDraft, setBulkDraft] = useState('');
  const [expandedMainChapters, setExpandedMainChapters] = useState<Set<number>>(new Set());
  const lastEmittedValue = useRef(value);

  const mainChapterCount = entries.filter((entry) => entry.depth === 0).length;
  const expandableMainChapters = useMemo(() => {
    const result = new Set<number>();
    let mainChapterIndex = -1;
    entries.forEach((entry, index) => {
      if (entry.depth !== 0) return;
      mainChapterIndex += 1;
      if (entries[index + 1]?.depth > 0) result.add(mainChapterIndex);
    });
    return result;
  }, [entries]);

  useEffect(() => {
    if (value !== lastEmittedValue.current) {
      setExpandedMainChapters(new Set());
      lastEmittedValue.current = value;
    }
  }, [value]);

  const emitValue = (nextValue: string) => {
    lastEmittedValue.current = nextValue;
    onChange?.(nextValue);
  };

  const commit = (nextEntries: OutlineEntry[]) => {
    emitValue(serializeOutline(nextEntries));
  };

  const updateTitle = (index: number, title: string) => {
    const nextEntries = entries.map((entry, entryIndex) =>
      entryIndex === index ? { ...entry, title } : entry,
    );
    emitValue(
      nextEntries
        .map((entry) => `${' '.repeat(entry.depth * INDENT_SIZE)}${entry.title}`)
        .join('\n'),
    );
  };

  const addEntry = (index: number | null, asChild = false) => {
    const nextEntries = [...entries];
    const depth = index === null
      ? 0
      : Math.min(MAX_DEPTH, entries[index].depth + (asChild ? 1 : 0));
    const insertIndex = index === null ? nextEntries.length : index + 1;
    nextEntries.splice(insertIndex, 0, {
      title: depth === 0 ? '新章节' : '新子章节',
      depth,
    });
    if (index !== null && asChild) {
      const parentMainChapterIndex = entries
        .slice(0, index + 1)
        .filter((entry) => entry.depth === 0).length - 1;
      setExpandedMainChapters((current) => new Set(current).add(parentMainChapterIndex));
    }
    commit(nextEntries);
  };

  const changeDepth = (index: number, direction: -1 | 1) => {
    const entry = entries[index];
    const previousDepth = index > 0 ? entries[index - 1].depth : 0;
    const maxAllowedDepth = index === 0 ? 0 : Math.min(MAX_DEPTH, previousDepth + 1);
    const nextDepth = Math.max(0, Math.min(maxAllowedDepth, entry.depth + direction));
    if (nextDepth === entry.depth) return;

    const delta = nextDepth - entry.depth;
    const nextEntries = entries.map((item, entryIndex) => {
      if (entryIndex === index) return { ...item, depth: nextDepth };
      if (entryIndex > index && item.depth > entry.depth) {
        return { ...item, depth: Math.max(0, Math.min(MAX_DEPTH, item.depth + delta)) };
      }
      return item;
    });
    if (entry.depth === 0 || nextDepth === 0) setExpandedMainChapters(new Set());
    commit(nextEntries);
  };

  const removeEntry = (index: number) => {
    const removedDepth = entries[index].depth;
    let endIndex = index + 1;
    while (endIndex < entries.length && entries[endIndex].depth > removedDepth) {
      endIndex += 1;
    }
    if (removedDepth === 0) setExpandedMainChapters(new Set());
    commit([...entries.slice(0, index), ...entries.slice(endIndex)]);
  };

  const toggleMainChapter = (mainChapterIndex: number) => {
    setExpandedMainChapters((current) => {
      const next = new Set(current);
      if (next.has(mainChapterIndex)) next.delete(mainChapterIndex);
      else next.add(mainChapterIndex);
      return next;
    });
  };

  const openBulkEditor = () => {
    setBulkDraft(value);
    setBulkEditorOpen(true);
  };

  return (
    <div
      id={id}
      style={{
        border: '1px solid #d9e2ef',
        borderRadius: 12,
        background: '#f6f8fb',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          padding: '12px 14px',
          background: '#fff',
          borderBottom: '1px solid #e7ebf1',
          flexWrap: 'wrap',
        }}
      >
        <Space size={10} wrap aria-live="polite">
          <ApartmentOutlined style={{ color: '#1677ff', fontSize: 18 }} />
          <Text strong>目录结构</Text>
          <Tag bordered={false} color="blue">{mainChapterCount} 个大章节</Tag>
        </Space>
        <Space size={8} wrap>
          <Button
            type="text"
            size="small"
            icon={<CaretDownOutlined />}
            onClick={() => setExpandedMainChapters(new Set(expandableMainChapters))}
            disabled={expandableMainChapters.size === 0}
          >
            全部展开
          </Button>
          <Button
            type="text"
            size="small"
            icon={<CaretRightOutlined />}
            onClick={() => setExpandedMainChapters(new Set())}
            disabled={expandedMainChapters.size === 0}
          >
            全部收起
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={openBulkEditor}
            disabled={disabled}
          >
            批量编辑
          </Button>
          <Button
            size="small"
            type="primary"
            ghost
            icon={<PlusOutlined />}
            onClick={() => addEntry(null)}
            disabled={disabled}
          >
            添加大章节
          </Button>
        </Space>
      </div>

      <div style={{ maxHeight: 390, overflow: 'auto', padding: entries.length ? '10px 12px' : 0 }}>
        {entries.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无章节结构"
            style={{ margin: '30px 0' }}
          >
            <Button
              type="primary"
              ghost
              icon={<PlusOutlined />}
              onClick={() => addEntry(null)}
              disabled={disabled}
            >
              添加第一个大章节
            </Button>
          </Empty>
        ) : (
          entries.map((entry, index) => {
            const isMainChapter = entry.depth === 0;
            const mainChapterIndex = entries
              .slice(0, index + 1)
              .filter((item) => item.depth === 0).length - 1;
            const isExpanded = expandedMainChapters.has(mainChapterIndex);
            const hasChildren = isMainChapter && expandableMainChapters.has(mainChapterIndex);
            if (!isMainChapter && !isExpanded) return null;
            const levelLabel = LEVEL_LABELS[entry.depth] ?? `L${entry.depth + 1}`;
            return (
              <div
                key={`${index}-${entry.depth}`}
                style={{
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 9,
                  minHeight: 46,
                  margin: isMainChapter ? '7px 0' : '1px 0',
                  marginLeft: entry.depth * 28,
                  padding: isMainChapter ? '6px 8px 6px 10px' : '4px 8px',
                  border: isMainChapter ? '1px solid #dce6f3' : '1px solid transparent',
                  borderRadius: isMainChapter ? 9 : 7,
                  background: isMainChapter ? '#fff' : 'transparent',
                  boxShadow: isMainChapter ? '0 3px 10px rgba(31, 45, 61, 0.04)' : 'none',
                }}
              >
                {entry.depth > 0 && (
                  <>
                    <span
                      aria-hidden="true"
                      style={{
                        position: 'absolute',
                        left: -15,
                        top: -9,
                        bottom: 22,
                        width: 12,
                        borderLeft: '1px solid #b8c6d9',
                        borderBottom: '1px solid #b8c6d9',
                        borderBottomLeftRadius: 6,
                      }}
                    />
                    {Array.from({ length: Math.max(0, entry.depth - 1) }).map((_, guideIndex) => (
                      <span
                        key={guideIndex}
                        aria-hidden="true"
                        style={{
                          position: 'absolute',
                          left: -15 - (entry.depth - guideIndex - 1) * 28,
                          top: -9,
                          bottom: -9,
                          borderLeft: '1px solid #e0e6ef',
                        }}
                      />
                    ))}
                  </>
                )}

                <span
                  style={{
                    flex: '0 0 auto',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 28,
                    height: 28,
                    borderRadius: isMainChapter ? 8 : 14,
                    color: isMainChapter ? '#fff' : '#52657d',
                    background: isMainChapter ? '#1677ff' : '#e8edf4',
                    fontSize: 12,
                    fontWeight: 600,
                  }}
                  title={`第 ${entry.depth + 1} 层`}
                >
                  {levelLabel}
                </span>

                <Input
                  value={entry.title}
                  variant="borderless"
                  disabled={disabled}
                  aria-label={`${levelLabel}标题`}
                  onChange={(event) => updateTitle(index, event.target.value)}
                  style={{
                    flex: 1,
                    minWidth: 160,
                    paddingInline: 4,
                    fontWeight: isMainChapter ? 600 : 400,
                    color: isMainChapter ? '#1f2d3d' : '#3d4d60',
                  }}
                />

                <Space size={2} style={{ flex: '0 0 auto' }}>
                  {isMainChapter && hasChildren && (
                    <Tooltip title={isExpanded ? '收起子章节' : '展开子章节'}>
                      <Button
                        type="text"
                        size="small"
                        icon={isExpanded ? <CaretDownOutlined /> : <CaretRightOutlined />}
                        aria-label={`${isExpanded ? '收起' : '展开'}“${entry.title}”`}
                        aria-expanded={isExpanded}
                        onClick={() => toggleMainChapter(mainChapterIndex)}
                      />
                    </Tooltip>
                  )}
                  <Tooltip title="添加子章节">
                    <Button
                      type="text"
                      size="small"
                      icon={<PlusOutlined />}
                      aria-label={`在“${entry.title}”下添加子章节`}
                      onClick={() => addEntry(index, true)}
                      disabled={disabled || entry.depth >= MAX_DEPTH}
                    />
                  </Tooltip>
                  <Tooltip title="提升层级">
                    <Button
                      type="text"
                      size="small"
                      icon={<MenuUnfoldOutlined />}
                      aria-label={`提升“${entry.title}”的层级`}
                      onClick={() => changeDepth(index, -1)}
                      disabled={disabled || entry.depth === 0}
                    />
                  </Tooltip>
                  <Tooltip title="降低层级">
                    <Button
                      type="text"
                      size="small"
                      icon={<MenuFoldOutlined />}
                      aria-label={`降低“${entry.title}”的层级`}
                      onClick={() => changeDepth(index, 1)}
                      disabled={disabled || index === 0 || entry.depth >= entries[index - 1].depth + 1}
                    />
                  </Tooltip>
                  <Tooltip title={isMainChapter ? '删除该章节及其子章节' : '删除'}>
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      aria-label={`删除“${entry.title}”`}
                      onClick={() => removeEntry(index)}
                      disabled={disabled}
                    />
                  </Tooltip>
                </Space>
              </div>
            );
          })
        )}
      </div>

      <Modal
        title="批量编辑章节目录"
        open={bulkEditorOpen}
        okText="应用目录"
        cancelText="取消"
        onCancel={() => setBulkEditorOpen(false)}
        onOk={() => {
          setExpandedMainChapters(new Set());
          emitValue(serializeOutline(parseOutline(bulkDraft)));
          setBulkEditorOpen(false);
        }}
      >
        <Text type="secondary">
          每行一个章节，使用两个空格表示一级缩进。应用后会自动转换为目录结构。
        </Text>
        <TextArea
          rows={14}
          value={bulkDraft}
          onChange={(event) => setBulkDraft(event.target.value)}
          placeholder={'第一章 课程概述\n  1.1 基础知识\n    1.1.1 核心概念'}
          style={{ marginTop: 12, fontFamily: 'Consolas, "Microsoft YaHei", monospace' }}
        />
      </Modal>
    </div>
  );
};

export default ChapterOutlineEditor;
