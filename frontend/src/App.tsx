/**
 * Main App component
 */
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from 'antd';
import Home from './pages/Home';
import NewLessonPlan from './pages/NewLessonPlan';
import EditLessonPlan from './pages/EditLessonPlan';
import TemplateManager from './pages/TemplateManager';
import TemplateEditor from './pages/TemplateEditor';
import History from './pages/History';
import LessonPlanDetail from './pages/LessonPlanDetail';
import Settings from './pages/Settings';

const { Content } = Layout;

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Content style={{ padding: '24px' }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/new" element={<NewLessonPlan />} />
          <Route path="/edit" element={<EditLessonPlan />} />
          <Route path="/templates" element={<TemplateManager />} />
          <Route path="/templates/:templateId/edit" element={<TemplateEditor />} />
          <Route path="/history" element={<History />} />
          <Route path="/lesson-plan" element={<LessonPlanDetail />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Content>
    </Layout>
  );
}

export default App;
