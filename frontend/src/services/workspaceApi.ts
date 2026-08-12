import api from './api';
import type {
  AIAnalyticsSummary,
  CourseArchive,
  CourseArchiveInput,
  QualityAnalyticsSummary,
  TeachingResource,
  TeachingResourceInput,
} from '@/types';

export const resourceApi = {
  list: async (params?: Record<string, unknown>): Promise<{ resources: TeachingResource[]; total: number }> =>
    (await api.get('/resources', { params })).data,
  create: async (data: TeachingResourceInput): Promise<TeachingResource> =>
    (await api.post('/resources', data)).data,
  update: async (id: string, data: Partial<TeachingResourceInput> & { status?: string }): Promise<TeachingResource> =>
    (await api.patch(`/resources/${id}`, data)).data,
  remove: async (id: string): Promise<void> => { await api.delete(`/resources/${id}`); },
};

export const courseArchiveApi = {
  list: async (params?: Record<string, unknown>): Promise<{ archives: CourseArchive[]; total: number }> =>
    (await api.get('/course-archives', { params })).data,
  get: async (id: string): Promise<CourseArchive> =>
    (await api.get(`/course-archives/${id}`)).data,
  create: async (data: CourseArchiveInput): Promise<CourseArchive> =>
    (await api.post('/course-archives', data)).data,
  update: async (id: string, data: Partial<CourseArchiveInput> & { status?: string }): Promise<CourseArchive> =>
    (await api.patch(`/course-archives/${id}`, data)).data,
  clone: async (id: string, academicYear: string, semester: 1 | 2): Promise<CourseArchive> =>
    (await api.post(`/course-archives/${id}/clone`, { academic_year: academicYear, semester })).data,
  remove: async (id: string): Promise<void> => { await api.delete(`/course-archives/${id}`); },
};

export const analyticsApi = {
  aiSummary: async (days = 30): Promise<AIAnalyticsSummary> =>
    (await api.get('/analytics/ai/summary', { params: { days } })).data,
  qualitySummary: async (days = 30): Promise<QualityAnalyticsSummary> =>
    (await api.get('/analytics/quality/summary', { params: { days } })).data,
};
