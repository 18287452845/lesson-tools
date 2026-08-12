/**
 * Main App component
 */
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from 'antd';
import Home from './pages/Home';
import EditLessonPlan from './pages/EditLessonPlan';
import PreparationWorkspace from './pages/PreparationWorkspace';
import History from './pages/History';
import LessonPlanDetail from './pages/LessonPlanDetail';
import Settings from './pages/Settings';
import BatchGenerate from './pages/BatchGenerate';
import BatchDownloads from './pages/BatchDownloads';
import BatchTaskDetail from './pages/BatchTaskDetail';
import CachedLessonPlans from './pages/CachedLessonPlans';
import ClassManager from './pages/ClassManager';
import TextbookManager from './pages/TextbookManager';
import SubjectManager from './pages/SubjectManager';
import GradeManager from './pages/GradeManager';
import CompetitionHome from './pages/Competition/CompetitionHome';
import CompetitionNew from './pages/Competition/CompetitionNew';
import CompetitionDetail from './pages/Competition/CompetitionDetail';
import ResourceLibrary from './pages/ResourceLibrary';
import CourseArchives from './pages/CourseArchives';
import AIAnalyticsDashboard from './pages/AIAnalyticsDashboard';

const { Content } = Layout;

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Content style={{ padding: '24px' }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/prepare" element={<PreparationWorkspace />} />
          <Route path="/new" element={<Navigate to="/prepare" replace />} />
          <Route path="/edit" element={<EditLessonPlan />} />
          <Route path="/templates" element={<Navigate to="/prepare" replace />} />
          <Route path="/templates/:templateId/edit" element={<Navigate to="/prepare" replace />} />
          <Route path="/history" element={<History />} />
          <Route path="/lesson-plan" element={<LessonPlanDetail />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/batch-generate" element={<BatchGenerate />} />
          <Route path="/batch-downloads" element={<BatchDownloads />} />
          <Route path="/batch-tasks/:taskId" element={<BatchTaskDetail />} />
          <Route path="/cached-lesson-plans" element={<CachedLessonPlans />} />
          <Route path="/classes" element={<ClassManager />} />
          <Route path="/textbooks" element={<TextbookManager />} />
          <Route path="/subjects" element={<SubjectManager />} />
          <Route path="/grades" element={<GradeManager />} />
          <Route path="/competition" element={<CompetitionHome />} />
          <Route path="/competition/new" element={<CompetitionNew />} />
          <Route path="/competition/:projectId" element={<CompetitionDetail />} />
          <Route path="/resources" element={<ResourceLibrary />} />
          <Route path="/course-archives" element={<CourseArchives />} />
          <Route path="/analytics" element={<AIAnalyticsDashboard />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Content>
    </Layout>
  );
}

export default App;
