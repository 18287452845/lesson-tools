import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, Button, Card, Col, Progress, Row, Select, Space, Statistic, Table, Typography, message } from 'antd';
import { ArrowLeftOutlined, CheckCircleOutlined, DollarOutlined, FieldTimeOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { analyticsApi } from '@/services/workspaceApi';
import type { AIAnalyticsSummary, QualityAnalyticsSummary } from '@/types';

const { Title, Text } = Typography;
const dimensionLabels: Record<string, string> = {
  completeness: '内容完整度', structure: '结构规范', interaction: '师生互动',
  time_design: '时间设计', actionability: '可执行性',
};

export default function AIAnalyticsDashboard() {
  const navigate = useNavigate();
  const [days, setDays] = useState(30);
  const [ai, setAi] = useState<AIAnalyticsSummary | null>(null);
  const [quality, setQuality] = useState<QualityAnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const load = async () => {
    setLoading(true);
    try { const [a, q] = await Promise.all([analyticsApi.aiSummary(days), analyticsApi.qualitySummary(days)]); setAi(a); setQuality(q); }
    catch (error) { message.error(error instanceof Error ? error.message : '分析数据加载失败'); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, [days]);
  const summary = ai?.summary;
  return <div style={{ maxWidth: 1260, margin: '0 auto' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 18 }}>
      <Space><Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>返回</Button><Title level={2} style={{ margin: 0 }}>AI 成本与质量面板</Title></Space>
      <Select value={days} onChange={setDays} options={[{ value: 7, label: '近 7 天' }, { value: 30, label: '近 30 天' }, { value: 90, label: '近 90 天' }]} />
    </div>
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} lg={6}><Card loading={loading}><Statistic title="AI 调用" value={summary?.calls || 0} prefix={<ThunderboltOutlined />} /></Card></Col>
      <Col xs={24} sm={12} lg={6}><Card loading={loading}><Statistic title="估算成本（USD）" value={summary?.estimated_cost || 0} precision={4} prefix={<DollarOutlined />} /></Card></Col>
      <Col xs={24} sm={12} lg={6}><Card loading={loading}><Statistic title="成功率" value={summary?.success_rate || 0} suffix="%" prefix={<CheckCircleOutlined />} /></Card></Col>
      <Col xs={24} sm={12} lg={6}><Card loading={loading}><Statistic title="平均响应" value={Math.round(summary?.avg_latency_ms || 0)} suffix="ms" prefix={<FieldTimeOutlined />} /></Card></Col>
    </Row>
    <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
      <Col xs={24} lg={14}><Card title="模型用量" loading={loading}><Table rowKey={(r) => `${r.provider}-${r.model}`} pagination={false} dataSource={ai?.by_model || []} columns={[
        { title: '模型', dataIndex: 'model' }, { title: '调用', dataIndex: 'calls' },
        { title: 'Token', dataIndex: 'total_tokens', render: (v) => Number(v || 0).toLocaleString() },
        { title: '估算成本', dataIndex: 'estimated_cost', render: (v) => `$${Number(v || 0).toFixed(4)}` },
        { title: '平均耗时', dataIndex: 'avg_latency_ms', render: (v) => `${Math.round(v || 0)}ms` },
      ]} /></Card></Col>
      <Col xs={24} lg={10}><Card title="生成质量" loading={loading}>
        <Space direction="vertical" style={{ width: '100%' }} size={14}>
          <Statistic title="平均质量分" value={quality?.average_score || 0} suffix="/ 100" />
          <Text>80 分以上占比：{quality?.pass_rate || 0}%</Text>
          {Object.entries(quality?.dimensions || {}).map(([key, value]) => {
            const max = key === 'completeness' ? 30 : key === 'structure' ? 25 : key === 'interaction' ? 20 : key === 'time_design' ? 15 : 10;
            return <div key={key}><Text>{dimensionLabels[key] || key}</Text><Progress percent={Math.round(value / max * 100)} size="small" /></div>;
          })}
        </Space>
      </Card></Col>
    </Row>
    {ai?.cost_notice && <Alert style={{ marginTop: 16 }} type="info" showIcon message={ai.cost_notice} />}
  </div>;
}
