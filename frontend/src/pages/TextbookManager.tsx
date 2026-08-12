/**
 * Textbook Management Page - Full CRUD operations with hierarchical chapter management
 */
import React, { useEffect, useState } from 'react';
import {
  Badge,
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Divider,
  Drawer,
  Form,
  Input,
  InputNumber,
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
  TextbookCatalogPreviewResponse,
  TextbookInfo,
  TextbookSearchCandidate,
  TextbookSearchRequest,
  TextbookUpdateRequest,
} from '@/types';
import { SUBJECT_OPTIONS, GRADE_OPTIONS } from '@/types';
import { useTextbookStore } from '@/stores/textbookStore';
import { textbookApi } from '@/services/textbookApi';

const { Title, Text } = Typography;
const { TextArea } = Input;

const MAX_LEVEL = 5;

const isAppendixChapter = (
  chapter: TextbookChapterInfo | TextbookChapterCreateRequest
): boolean => [chapter.chapter_number, chapter.chapter_title].some(
  (value) => /^(附录|appendix(?:\s|$))/i.test(String(value || '').trim())
);

const isNumberedChapter = (
  chapter: TextbookChapterInfo | TextbookChapterCreateRequest
): boolean => /^(?:第\s*[一二三四五六七八九十百零〇\d]+\s*章|chapter\s+[\w一二三四五六七八九十]+)\s*$/i.test(
  String(chapter.chapter_number || '').normalize('NFKC').trim()
);

const countMainChapters = (
  chapters: Array<TextbookChapterInfo | TextbookChapterCreateRequest> = []
): number => {
  const eligible = chapters.filter((chapter) => !isAppendixChapter(chapter));
  const numberedChapters = eligible.filter(isNumberedChapter);
  if (numberedChapters.length > 0) {
    return numberedChapters.length;
  }
  return eligible.filter((chapter) => !chapter.parent_chapter_id).length;
};

const getMainChapterCount = (textbook: TextbookInfo): number => (
  textbook.main_chapter_count ?? countMainChapters(textbook.chapters)
);

const buildChapterDepthMap = (
  chapters: TextbookChapterCreateRequest[]
): Map<string, number> => {
  const byId = new Map(
    chapters
      .filter((chapter) => chapter.client_id)
      .map((chapter) => [chapter.client_id as string, chapter]),
  );
  const depths = new Map<string, number>();

  const resolveDepth = (chapter: TextbookChapterCreateRequest, visited = new Set<string>()): number => {
    const id = chapter.client_id;
    if (!id || !chapter.parent_chapter_id || visited.has(id)) {
      return 1;
    }
    const cached = depths.get(id);
    if (cached) {
      return cached;
    }
    const parent = byId.get(chapter.parent_chapter_id);
    if (!parent) {
      return 1;
    }
    const nextVisited = new Set(visited);
    nextVisited.add(id);
    const depth = Math.min(MAX_LEVEL, resolveDepth(parent, nextVisited) + 1);
    depths.set(id, depth);
    return depth;
  };

  chapters.forEach((chapter) => {
    if (chapter.client_id) {
      depths.set(chapter.client_id, resolveDepth(chapter));
    }
  });
  return depths;
};

interface ChapterNode extends TextbookChapterCreateRequest {
  client_id: string;
  children: ChapterNode[];
  level: number;
}

interface DiscoveryImportMeta {
  source_url?: string;
  ai_enrich?: boolean;
  subject?: string;
  grade?: string;
  description?: string;
}

const generateClientId = () =>
  `client-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

const recalcLevels = (nodes: ChapterNode[], level = 1): ChapterNode[] =>
  nodes.map((node, index) => ({
    ...node,
    level,
    sort_order: index + 1,
    children: recalcLevels(node.children || [], level + 1),
  }));

const sortTreeByOrder = (nodes: ChapterNode[]): ChapterNode[] =>
  nodes
    .map((node) => ({
      ...node,
      children: sortTreeByOrder(node.children || []),
    }))
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));

const buildChapterTree = (
  chapters: Array<TextbookChapterInfo | TextbookChapterCreateRequest>
): ChapterNode[] => {
  const map = new Map<string, ChapterNode>();
  const roots: ChapterNode[] = [];

  const sorted = [...chapters].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));

  sorted.forEach((chapter, index) => {
    const node: ChapterNode = {
      id: chapter.id,
      client_id: chapter.id || generateClientId(),
      chapter_number: chapter.chapter_number || `第${index + 1}章`,
      chapter_title: chapter.chapter_title || '',
      content_summary: chapter.content_summary ?? '',
      key_concepts: chapter.key_concepts ?? [],
      sort_order: chapter.sort_order ?? index + 1,
      hours_required: chapter.hours_required,
      parent_chapter_id: chapter.parent_chapter_id,
      source_id: chapter.source_id,
      content_origin: chapter.content_origin,
      confidence: chapter.confidence,
      children: [],
      level: 1,
    };
    map.set(node.client_id, node);
  });

  map.forEach((node) => {
    if (node.parent_chapter_id && map.has(node.parent_chapter_id)) {
      const parent = map.get(node.parent_chapter_id);
      parent?.children.push(node);
    } else {
      roots.push(node);
    }
  });

  return recalcLevels(sortTreeByOrder(roots), 1);
};

const flattenChapterTreeForSave = (nodes: ChapterNode[]): TextbookChapterCreateRequest[] => {
  const result: TextbookChapterCreateRequest[] = [];
  let counter = 0;

  const walk = (list: ChapterNode[], parentKey?: string) => {
    list.forEach((node) => {
      const clientKey = node.client_id || node.id || generateClientId();
      counter += 1;
      result.push({
        id: node.id,
        client_id: clientKey,
        chapter_number: node.chapter_number?.trim() || `章节${counter}`,
        chapter_title: node.chapter_title?.trim() || node.chapter_number || `章节${counter}`,
        content_summary: node.content_summary?.trim() || '',
        key_concepts: node.key_concepts?.filter(Boolean) || [],
        sort_order: counter,
        hours_required: node.hours_required,
        parent_chapter_id: parentKey,
        source_id: node.source_id,
        content_origin: node.content_origin,
        confidence: node.confidence,
      });
      if (node.children?.length) {
        walk(node.children, clientKey);
      }
    });
  };

  walk(nodes);
  return result;
};

const applyEnrichmentToTree = (
  nodes: ChapterNode[],
  enrichments: TextbookChapterCreateRequest[]
): ChapterNode[] => {
  const map = new Map<string, TextbookChapterCreateRequest>();
  enrichments.forEach((item) => {
    const key = item.client_id || item.id || item.chapter_title;
    if (key) {
      map.set(key, item);
    }
  });

  const walk = (list: ChapterNode[]): ChapterNode[] =>
    list.map((node) => {
      const key = node.client_id || node.id || node.chapter_title;
      const enriched = key ? map.get(key) : undefined;
      const merged: ChapterNode = {
        ...node,
        chapter_number: enriched?.chapter_number || node.chapter_number,
        chapter_title: enriched?.chapter_title || node.chapter_title,
        content_summary:
          enriched?.content_summary !== undefined
            ? enriched.content_summary ?? node.content_summary
            : node.content_summary,
        key_concepts:
          enriched?.key_concepts && enriched.key_concepts.length > 0
            ? enriched.key_concepts
            : node.key_concepts || [],
      };
      return {
        ...merged,
        children: walk(node.children || []),
      };
    });

  return walk(nodes);
};

const parseChapterLines = (input: string, startIndex: number): ChapterNode[] => {
  const lines = input
    .split(/\r?\n/)
    .map((raw) => {
      const normalized = raw.replace(/\t/g, '  ');
      const match = normalized.match(/^(\s*)(.*)$/);
      return {
        indent: match?.[1]?.length ?? 0,
        text: match?.[2]?.trim() ?? '',
      };
    })
    .filter((item) => item.text);

  if (lines.length === 0) {
    return [];
  }

  const positiveIndents = lines.map((item) => item.indent).filter((value) => value > 0);
  const indentUnit = positiveIndents.length > 0 ? Math.min(...positiveIndents) : 2;
  const roots: ChapterNode[] = [];
  const stack: Array<{ level: number; node: ChapterNode }> = [];
  const counters = Array.from({ length: MAX_LEVEL + 1 }, () => 0);
  counters[1] = Math.max(0, startIndex - 1);

  const buildChapterNumber = (level: number, provided?: string) => {
    if (provided) {
      return provided;
    }
    if (level === 1) return `第${counters[1]}章`;
    return counters.slice(1, level + 1).join('.');
  };

  const parseLine = (text: string, level: number): ChapterNode => {
    const fullMatch = text.match(/^(第?\s*\d+(?:\.\d+){0,4}\s*章)\s*(.*)$/);
    const numberMatch = text.match(/^(\d+(?:\.\d+){0,4})\s*[\\.、-]?\s*(.+)$/);

    counters[level] = (counters[level] || 0) + 1;
    for (let i = level + 1; i < counters.length; i += 1) {
      counters[i] = 0;
    }

    const chapterNumber = buildChapterNumber(
      level,
      fullMatch
        ? fullMatch[1].replace(/\s+/g, '')
        : numberMatch
        ? numberMatch[1]
        : undefined
    );

    const chapterTitle =
      fullMatch?.[2]?.trim() ||
      numberMatch?.[2]?.trim() ||
      text ||
      chapterNumber ||
      '章节';

    return {
      client_id: generateClientId(),
      chapter_number: chapterNumber,
      chapter_title: chapterTitle,
      content_summary: '',
      key_concepts: [],
      children: [],
      level,
    } as ChapterNode;
  };

  lines.forEach(({ indent, text }) => {
    const level = Math.min(MAX_LEVEL, Math.floor(indent / indentUnit) + 1);
    while (stack.length && stack[stack.length - 1].level >= level) {
      stack.pop();
    }

    const parentChildren = stack.length ? stack[stack.length - 1].node.children : roots;

    const node = parseLine(text, level);
    node.sort_order = parentChildren.length + 1;

    if (stack.length) {
      const parentNode = stack[stack.length - 1].node;
      node.parent_chapter_id = parentNode.client_id;
      parentNode.children.push(node);
    } else {
      roots.push(node);
    }

    stack.push({ level, node });
  });

  return roots;
};

const createChapterNode = (level: number, order: number): ChapterNode => ({
  client_id: generateClientId(),
  chapter_number: level === 1 ? `第${order}章` : `第${level}-${order}节`,
  chapter_title: '',
  content_summary: '',
  key_concepts: [],
  sort_order: order,
  hours_required: undefined,
  children: [],
  level,
});

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
    enrichChapters,
    clearError,
    setPage,
  } = useTextbookStore();

  const [modalVisible, setModalVisible] = useState(false);
  const [editingTextbook, setEditingTextbook] = useState<TextbookInfo | null>(null);
  const [chapterDrawerVisible, setChapterDrawerVisible] = useState(false);
  const [chapterTree, setChapterTree] = useState<ChapterNode[]>([]);
  const [draftLoadedTextbookId, setDraftLoadedTextbookId] = useState<string | null>(null);
  const [chapterModalVisible, setChapterModalVisible] = useState(false);
  const [generatingChapters, setGeneratingChapters] = useState(false);
  const [savingChapters, setSavingChapters] = useState(false);
  const [batchImportVisible, setBatchImportVisible] = useState(false);
  const [batchImportReplace, setBatchImportReplace] = useState(false);
  const [batchImportText, setBatchImportText] = useState('');
  const [batchImportLoading, setBatchImportLoading] = useState(false);
  const [filterSubject, setFilterSubject] = useState<string | undefined>();
  const [filterGrade, setFilterGrade] = useState<string | undefined>();
  const [discoveryVisible, setDiscoveryVisible] = useState(false);
  const [searchingBooks, setSearchingBooks] = useState(false);
  const [previewingCatalog, setPreviewingCatalog] = useState(false);
  const [importingBook, setImportingBook] = useState(false);
  const [bookCandidates, setBookCandidates] = useState<TextbookSearchCandidate[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<TextbookSearchCandidate | null>(null);
  const [catalogPreview, setCatalogPreview] = useState<TextbookCatalogPreviewResponse | null>(null);
  const [sourceErrors, setSourceErrors] = useState<Record<string, string>>({});

  const [form] = Form.useForm<TextbookCreateRequest | TextbookUpdateRequest>();
  const [generateForm] = Form.useForm();
  const [searchForm] = Form.useForm<TextbookSearchRequest>();
  const [discoveryMetaForm] = Form.useForm<DiscoveryImportMeta>();

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

    const drafts = buildChapterTree(selectedTextbook.chapters || []);
    setChapterTree(drafts);
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
    } catch {
      // Error handled by store
    }
  };

  const handleCreate = () => {
    setEditingTextbook(null);
    form.resetFields();
    setModalVisible(true);
  };

  const openDiscovery = () => {
    searchForm.resetFields();
    discoveryMetaForm.resetFields();
    discoveryMetaForm.setFieldsValue({ ai_enrich: true });
    setBookCandidates([]);
    setSelectedCandidate(null);
    setCatalogPreview(null);
    setSourceErrors({});
    setDiscoveryVisible(true);
  };

  const handleBookSearch = async () => {
    try {
      const values = await searchForm.validateFields();
      setSearchingBooks(true);
      setSelectedCandidate(null);
      setCatalogPreview(null);
      const response = await textbookApi.searchTextbooks(values);
      setBookCandidates(response.candidates);
      setSourceErrors(response.source_errors || {});
      if (response.candidates.length > 0) {
        setSelectedCandidate(response.candidates[0]);
        message.success(response.message);
      } else {
        message.warning(response.message);
      }
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      }
    } finally {
      setSearchingBooks(false);
    }
  };

  const handleCatalogPreview = async () => {
    if (!selectedCandidate) {
      message.warning('请先选择一个确切版本');
      return;
    }
    try {
      const values = await discoveryMetaForm.validateFields();
      setPreviewingCatalog(true);
      const response = await textbookApi.previewCatalog({
        candidate: selectedCandidate,
        source_url: values.source_url?.trim() || undefined,
        ai_enrich: values.ai_enrich !== false,
      });
      setCatalogPreview(response);
      message.success(response.message);
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      }
    } finally {
      setPreviewingCatalog(false);
    }
  };

  const handleDiscoveryImport = async () => {
    if (!selectedCandidate || !catalogPreview) {
      message.warning('请先获取并确认目录');
      return;
    }
    try {
      const values = await discoveryMetaForm.validateFields();
      setImportingBook(true);
      const imported = await textbookApi.importTextbook({
        candidate: selectedCandidate,
        chapters: catalogPreview.chapters,
        source_type: catalogPreview.source_type,
        source_name: catalogPreview.source_name,
        source_url: catalogPreview.source_url,
        confidence: catalogPreview.confidence,
        subject: values.subject,
        grade: values.grade,
        description: values.description,
      });
      await fetchTextbooks({
        page: currentPage,
        limit: pageSize,
        subject: filterSubject,
        grade: filterGrade,
        status: 'active',
      });
      setDiscoveryVisible(false);
      message.success(`《${imported.name}》及 ${getMainChapterCount(imported)} 个大章节已导入`);
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      }
    } finally {
      setImportingBook(false);
    }
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
    } catch {
      // Error handled by store
    }
  };

  const handleSubmit = async () => {
    try {
      const values = (await form.validateFields()) as TextbookCreateRequest;

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
    } catch {
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
    } catch {
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

    if (chapterTree.length === 0) {
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
      setChapterTree(buildChapterTree(response.chapters || []));
      setChapterModalVisible(false);
      message.success(response.message || '章节生成成功');
    } catch {
      // Error handled by store
    } finally {
      setGeneratingChapters(false);
    }
  };

  const findNodeById = (nodes: ChapterNode[], clientId: string): ChapterNode | null => {
    for (const node of nodes) {
      if (node.client_id === clientId) {
        return node;
      }
      if (node.children?.length) {
        const found = findNodeById(node.children, clientId);
        if (found) return found;
      }
    }
    return null;
  };

  const addChildNode = (
    nodes: ChapterNode[],
    parentId: string,
    child: ChapterNode
  ): ChapterNode[] =>
    nodes.map((node) => {
      if (node.client_id === parentId) {
        return { ...node, children: [...(node.children || []), child] };
      }
      if (node.children?.length) {
        const updatedChildren = addChildNode(node.children, parentId, child);
        if (updatedChildren !== node.children) {
          return { ...node, children: updatedChildren };
        }
      }
      return node;
    });

  const updateNode = (
    nodes: ChapterNode[],
    clientId: string,
    patch: Partial<ChapterNode>
  ): ChapterNode[] =>
    nodes.map((node) => {
      if (node.client_id === clientId) {
        return { ...node, ...patch };
      }
      if (node.children?.length) {
        const updatedChildren = updateNode(node.children, clientId, patch);
        if (updatedChildren !== node.children) {
          return { ...node, children: updatedChildren };
        }
      }
      return node;
    });

  const removeNode = (nodes: ChapterNode[], clientId: string): ChapterNode[] =>
    nodes
      .map((node) => ({
        ...node,
        children: removeNode(node.children || [], clientId),
      }))
      .filter((node) => node.client_id !== clientId);

  const moveNode = (
    nodes: ChapterNode[],
    clientId: string,
    delta: number
  ): { updated: ChapterNode[]; moved: boolean } => {
    const index = nodes.findIndex((node) => node.client_id === clientId);
    if (index !== -1) {
      const newIndex = index + delta;
      if (newIndex < 0 || newIndex >= nodes.length) {
        return { updated: nodes, moved: true };
      }
      const next = [...nodes];
      const [movedNode] = next.splice(index, 1);
      next.splice(newIndex, 0, movedNode);
      return { updated: next, moved: true };
    }

    for (let i = 0; i < nodes.length; i += 1) {
      const child = nodes[i];
      const { updated: updatedChildren, moved } = moveNode(
        child.children || [],
        clientId,
        delta
      );
      if (moved) {
        const updatedNode = { ...child, children: updatedChildren };
        const next = [...nodes];
        next.splice(i, 1, updatedNode);
        return { updated: next, moved: true };
      }
    }

    return { updated: nodes, moved: false };
  };

  const handleAddChapter = (parentId?: string) => {
    setChapterTree((prev) => {
      const parent = parentId ? findNodeById(prev, parentId) : null;
      const parentLevel = parent?.level ?? 0;
      const targetLevel = parentLevel + 1;
      if (targetLevel > MAX_LEVEL) {
        message.warning('目前最多支持五级章节');
        return prev;
      }

      const siblingCount = parent ? (parent.children?.length || 0) + 1 : prev.length + 1;
      const newNode = {
        ...createChapterNode(targetLevel, siblingCount),
        parent_chapter_id: parent?.client_id,
      };

      const next = parentId ? addChildNode(prev, parentId, newNode) : [...prev, newNode];
      return recalcLevels(next);
    });
  };

  const handleUpdateChapter = (clientId: string, patch: Partial<ChapterNode>) => {
    setChapterTree((prev) => recalcLevels(updateNode(prev, clientId, patch)));
  };

  const handleDeleteChapter = (clientId: string) => {
    setChapterTree((prev) => recalcLevels(removeNode(prev, clientId)));
  };

  const handleMoveChapter = (clientId: string, delta: number) => {
    setChapterTree((prev) => {
      const { updated, moved } = moveNode(prev, clientId, delta);
      return moved ? recalcLevels(updated) : prev;
    });
  };

  const handleSaveChapters = async () => {
    if (!selectedTextbook) {
      message.warning('请先选择教材');
      return;
    }

    if (chapterTree.length === 0) {
      message.warning('请先添加章节');
      return;
    }

    try {
      setSavingChapters(true);
      setDraftLoadedTextbookId(null);
      const payload = flattenChapterTreeForSave(recalcLevels(chapterTree));
      await saveChapters(selectedTextbook.id, payload);
      message.success('章节已保存');
    } catch {
      // Error handled by store
    } finally {
      setSavingChapters(false);
    }
  };

  const handleBatchImportSubmit = async () => {
    if (!selectedTextbook) {
      message.warning('请先选择教材');
      return;
    }

    if (!batchImportText.trim()) {
      message.warning('请输入章节内容');
      return;
    }

    const startIndex = batchImportReplace ? 1 : chapterTree.length + 1;
    const importedRoots = recalcLevels(parseChapterLines(batchImportText, startIndex));

    if (importedRoots.length === 0) {
      message.warning('未识别到有效章节，请检查格式');
      return;
    }

    const mergeTree = (
      currentTree: ChapterNode[],
      enrichments?: TextbookChapterCreateRequest[]
    ) => {
      const nextRoots = batchImportReplace ? importedRoots : [...currentTree, ...importedRoots];
      const recalculated = recalcLevels(nextRoots);
      if (enrichments?.length) {
        return recalcLevels(applyEnrichmentToTree(recalculated, enrichments));
      }
      return recalculated;
    };

    setBatchImportLoading(true);
    try {
      let enrichments: TextbookChapterCreateRequest[] | undefined;
      const payload = flattenChapterTreeForSave(importedRoots);

      if (payload.length > 0) {
        const response = await enrichChapters(selectedTextbook.id, payload);
        enrichments = response.chapters;
      }

      setChapterTree((prev) => mergeTree(prev, enrichments));
      message.success(
        `已导入 ${importedRoots.length} 个章节${enrichments?.length ? '，AI已生成概述和核心概念' : ''}`
      );
    } catch {
      setChapterTree((prev) => mergeTree(prev));
      message.warning('章节已导入，但AI生成概述失败，请稍后重试');
    } finally {
      setBatchImportVisible(false);
      setBatchImportText('');
      setBatchImportReplace(false);
      setBatchImportLoading(false);
    }
  };

  const handleCloseDrawer = () => {
    setChapterDrawerVisible(false);
    setDraftLoadedTextbookId(null);
    setChapterTree([]);
  };

  const handlePageChange = (page: number) => {
    setPage(page);
  };

  const renderChapterNodes = (nodes: ChapterNode[]) =>
    nodes.map((chapter, index) => (
      <div
        key={chapter.client_id}
        style={{ marginBottom: 12, marginLeft: (chapter.level - 1) * 16 }}
      >
        <Card
          size="small"
          title={
            <Space>
              <Text type="secondary">#{index + 1}</Text>
              <Input
                value={chapter.chapter_number}
                onChange={(e) =>
                  handleUpdateChapter(chapter.client_id, { chapter_number: e.target.value })
                }
                placeholder="第1章"
                style={{ width: 120 }}
              />
              <Input
                value={chapter.chapter_title}
                onChange={(e) =>
                  handleUpdateChapter(chapter.client_id, { chapter_title: e.target.value })
                }
                placeholder="章节标题"
                style={{ width: 280 }}
              />
            </Space>
          }
          extra={
            <Space size="small">
              <Button
                size="small"
                icon={<ArrowUpOutlined />}
                disabled={index === 0}
                onClick={() => handleMoveChapter(chapter.client_id, -1)}
              />
              <Button
                size="small"
                icon={<ArrowDownOutlined />}
                disabled={index === nodes.length - 1}
                onClick={() => handleMoveChapter(chapter.client_id, 1)}
              />
              {chapter.level < MAX_LEVEL && (
                <Button
                  size="small"
                  icon={<PlusOutlined />}
                  onClick={() => handleAddChapter(chapter.client_id)}
                >
                  子章节
                </Button>
              )}
              <Popconfirm
                title="删除章节？"
                onConfirm={() => handleDeleteChapter(chapter.client_id)}
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
                  handleUpdateChapter(chapter.client_id, { content_summary: e.target.value })
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
                  handleUpdateChapter(chapter.client_id, { key_concepts: value as string[] })
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
                    handleUpdateChapter(chapter.client_id, {
                      hours_required: typeof value === 'number' ? value : undefined,
                    })
                  }
                  style={{ width: '100%', marginTop: 8 }}
                  placeholder="例如：2"
                />
              </div>
            </Col>
          </Row>
          {chapter.children?.length > 0 && (
            <div style={{ marginTop: 12 }}>{renderChapterNodes(chapter.children)}</div>
          )}
        </Card>
      </div>
    ));

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
      title: '大章节数',
      key: 'chapters_count',
      width: 100,
      align: 'center' as const,
      render: (_: any, record: TextbookInfo) => (
        <Badge count={getMainChapterCount(record)} showZero color="blue" />
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
                <Button icon={<BookOutlined />} onClick={openDiscovery}>
                  联网搜索导入
                </Button>
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
            showTotal: (value) => `共 ${value} 条`,
          }}
        />
      </Card>

      <Modal
        title="联网搜索并导入教材目录"
        open={discoveryVisible}
        onCancel={() => setDiscoveryVisible(false)}
        width={1100}
        footer={null}
        destroyOnClose
        maskClosable={!importingBook}
      >
        <Alert
          type="info"
          showIcon
          message="优先使用 ISBN 精确搜索；书名和作者搜索需要手动确认具体版次。AI 只补充概述和关键词，不会修改来源目录标题。"
          style={{ marginBottom: 16 }}
        />

        <Form form={searchForm} layout="vertical">
          <Row gutter={12} align="bottom">
            <Col span={7}>
              <Form.Item label="ISBN" name="isbn">
                <Input placeholder="9787302720126" allowClear />
              </Form.Item>
            </Col>
            <Col span={7}>
              <Form.Item
                label="书名"
                name="title"
                dependencies={['isbn']}
                rules={[
                  ({ getFieldValue }) => ({
                    validator: (_, value) =>
                      value || getFieldValue('isbn')
                        ? Promise.resolve()
                        : Promise.reject(new Error('请输入 ISBN 或书名')),
                  }),
                ]}
              >
                <Input placeholder="例如：Java程序设计" allowClear />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="作者" name="author">
                <Input placeholder="可选，用于消除同名书歧义" allowClear />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item>
                <Button
                  type="primary"
                  block
                  loading={searchingBooks}
                  onClick={handleBookSearch}
                >
                  搜索书籍
                </Button>
              </Form.Item>
            </Col>
          </Row>
        </Form>

        {Object.keys(sourceErrors).length > 0 && (
          <Alert
            type="warning"
            showIcon
            message="部分来源暂时不可用，其余来源的结果仍可正常使用"
            description={Object.entries(sourceErrors)
              .map(([source, detail]) => `${source}: ${detail}`)
              .join('；')}
            style={{ marginBottom: 12 }}
          />
        )}

        {bookCandidates.length > 0 && (
          <>
            <Table<TextbookSearchCandidate>
              size="small"
              rowKey="id"
              dataSource={bookCandidates}
              pagination={false}
              scroll={{ y: 260 }}
              rowSelection={{
                type: 'radio',
                selectedRowKeys: selectedCandidate ? [selectedCandidate.id] : [],
                onChange: (_keys, rows) => {
                  setSelectedCandidate(rows[0] || null);
                  setCatalogPreview(null);
                  discoveryMetaForm.setFieldValue('source_url', undefined);
                },
              }}
              onRow={(record) => ({
                onClick: () => {
                  setSelectedCandidate(record);
                  setCatalogPreview(null);
                  discoveryMetaForm.setFieldValue('source_url', undefined);
                },
              })}
              columns={[
                {
                  title: '候选教材',
                  key: 'book',
                  render: (_, record) => (
                    <Space direction="vertical" size={0}>
                      {record.source_url ? (
                        <a href={record.source_url} target="_blank" rel="noreferrer">
                          {record.title}
                        </a>
                      ) : (
                        <Text strong>{record.title}</Text>
                      )}
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {record.authors.join('、') || '作者未知'}
                      </Text>
                    </Space>
                  ),
                },
                {
                  title: 'ISBN',
                  width: 145,
                  render: (_, record) => record.isbn_13 || record.isbn_10 || '-',
                },
                {
                  title: '出版社/日期',
                  width: 180,
                  render: (_, record) => (
                    <Space direction="vertical" size={0}>
                      <Text>{record.publisher || '-'}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {record.published_date || ''}
                      </Text>
                    </Space>
                  ),
                },
                {
                  title: '来源',
                  width: 150,
                  render: (_, record) => (
                    <Space direction="vertical" size={2}>
                      <Tag color={record.toc_available ? 'green' : 'blue'}>
                        {record.source_name}
                      </Tag>
                      {record.toc_available && <Text type="success">含官方目录</Text>}
                    </Space>
                  ),
                },
                {
                  title: '匹配度',
                  dataIndex: 'match_score',
                  width: 90,
                  render: (score: number) => <Badge count={`${score}%`} color={score >= 90 ? 'green' : 'blue'} />,
                },
              ]}
            />

            <Divider orientation="left">目录获取与导入设置</Divider>
            <Form form={discoveryMetaForm} layout="vertical">
              <Row gutter={12}>
                <Col span={12}>
                  <Form.Item
                    label="出版社目录页网址（可选）"
                    name="source_url"
                    tooltip="候选来源没有目录时，可粘贴出版社公开的 HTML 目录页"
                    rules={[{ type: 'url', message: '请输入有效的公开网址' }]}
                  >
                    <Input placeholder="https://出版社官网/图书目录页" allowClear />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item label="学科" name="subject">
                    <Select
                      allowClear
                      showSearch
                      options={SUBJECT_OPTIONS.map((value) => ({ label: value, value }))}
                    />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item label="适用年级" name="grade">
                    <Select
                      allowClear
                      showSearch
                      options={GRADE_OPTIONS.map((value) => ({ label: value, value }))}
                    />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={12} align="bottom">
                <Col span={14}>
                  <Form.Item label="教材简介补充" name="description">
                    <Input placeholder="可选；留空时使用书目来源简介" allowClear />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item name="ai_enrich" valuePropName="checked">
                    <Checkbox>AI生成章节概述和关键词</Checkbox>
                  </Form.Item>
                </Col>
                <Col span={4}>
                  <Form.Item>
                    <Button
                      block
                      type="primary"
                      loading={previewingCatalog}
                      onClick={handleCatalogPreview}
                    >
                      获取目录
                    </Button>
                  </Form.Item>
                </Col>
              </Row>
            </Form>
          </>
        )}

        {catalogPreview && (
          <>
            <Alert
              type={catalogPreview.warnings.length ? 'warning' : 'success'}
              showIcon
              message={`${catalogPreview.source_name} · 可信度 ${Math.round(
                catalogPreview.confidence * 100
              )}% · ${countMainChapters(catalogPreview.chapters)} 个大章节`}
              description={catalogPreview.warnings.join('；') || '目录已准备好，请确认后导入。'}
              style={{ marginBottom: 12 }}
            />
            <Table<TextbookChapterCreateRequest>
              size="small"
              rowKey={(record) => record.client_id || `${record.chapter_number}-${record.sort_order}`}
              dataSource={catalogPreview.chapters}
              pagination={false}
              scroll={{ y: 360 }}
              columns={[
                { title: '序号', dataIndex: 'sort_order', width: 70 },
                { title: '章节编号', dataIndex: 'chapter_number', width: 130 },
                {
                  title: '章节标题',
                  dataIndex: 'chapter_title',
                  render: (title: string, record: TextbookChapterCreateRequest) => {
                    const depth = buildChapterDepthMap(catalogPreview.chapters)
                      .get(record.client_id || '') || 1;
                    return <span style={{ paddingLeft: (depth - 1) * 18 }}>{title}</span>;
                  },
                },
                {
                  title: '处理方式',
                  dataIndex: 'content_origin',
                  width: 120,
                  render: (origin: string) => (
                    <Tag color={origin === 'ai_enriched' ? 'purple' : 'green'}>
                      {origin === 'ai_enriched' ? '来源+AI整理' : '来源目录'}
                    </Tag>
                  ),
                },
              ]}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
              <Space>
                <Button onClick={() => setCatalogPreview(null)}>重新选择</Button>
                <Button
                  type="primary"
                  icon={<UploadOutlined />}
                  loading={importingBook}
                  onClick={handleDiscoveryImport}
                >
                  确认导入教材和目录
                </Button>
              </Space>
            </div>
          </>
        )}
      </Modal>

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
        width={980}
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
                <Button icon={<PlusOutlined />} onClick={() => handleAddChapter()}>
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
                支持五级层级，批量导入时可通过空格/Tab 缩进控制父子章节。章节数量仅统计一级大章节。
              </Text>

              <Divider />

              {chapterTree.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '32px 0' }}>
                  <Text type="secondary">暂无章节</Text>
                  <div style={{ marginTop: 16 }}>
                    <Space>
                      <Button type="primary" icon={<PlusOutlined />} onClick={() => handleAddChapter()}>
                        新增章节
                      </Button>
                      <Button icon={<ThunderboltOutlined />} onClick={confirmAiOverwrite}>
                        AI生成章节
                      </Button>
                    </Space>
                  </div>
                </div>
              ) : (
                <div>{renderChapterNodes(chapterTree)}</div>
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
        confirmLoading={batchImportLoading}
        width={600}
        destroyOnClose
      >
        <Spin spinning={batchImportLoading} tip="正在导入并生成章节概述...">
          <TextArea
            rows={8}
            value={batchImportText}
            onChange={(e) => setBatchImportText(e.target.value)}
            placeholder="支持最多五级缩进：&#10;第1章 计算机基础&#10;  1.1 计算机发展史&#10;    1.1.1 计算机演进&#10;      （一）电子计算机&#10;        （1）第一代计算机"
          />
          <div style={{ marginTop: 8 }}>
            <Text type="secondary">
              同级无需缩进，子级使用空格/Tab 缩进即可自动归为下级；导入后将尝试自动生成内容概述与核心概念。
            </Text>
          </div>
          <div style={{ marginTop: 12 }}>
            <Checkbox
              checked={batchImportReplace}
              onChange={(e) => setBatchImportReplace(e.target.checked)}
              disabled={batchImportLoading}
            >
              覆盖现有章节
            </Checkbox>
          </div>
        </Spin>
      </Modal>
    </div>
  );
};

export default TextbookManager;
