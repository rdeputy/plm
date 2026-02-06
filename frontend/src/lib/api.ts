import axios from 'axios';
import { supabase } from './supabase';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || '';

export const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth interceptor - prefer JWT, fall back to API key
api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();

  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  } else if (API_KEY) {
    config.headers['X-API-Key'] = API_KEY;
  }

  return config;
});

// Parts
export const partsApi = {
  list: (params?: Record<string, string>) => api.get('/parts', { params }),
  get: (id: string) => api.get(`/parts/${id}`),
  create: (data: unknown) => api.post('/parts', data),
  update: (id: string, data: unknown) => api.patch(`/parts/${id}`, data),
  release: (id: string, releasedBy: string) =>
    api.post(`/parts/${id}/release?released_by=${releasedBy}`),
};

// BOMs
export const bomsApi = {
  list: (params?: Record<string, string>) => api.get('/boms', { params }),
  get: (id: string) => api.get(`/boms/${id}`),
  create: (data: unknown) => api.post('/boms', data),
  update: (id: string, data: unknown) => api.patch(`/boms/${id}`, data),
  getItems: (id: string) => api.get(`/boms/${id}/items`),
};

// Projects
export const projectsApi = {
  list: (params?: Record<string, string>) => api.get('/projects', { params }),
  get: (id: string) => api.get(`/projects/${id}`),
  create: (data: unknown) => api.post('/projects', data),
  update: (id: string, data: unknown) => api.patch(`/projects/${id}`, data),
  getMilestones: (id: string) => api.get(`/projects/${id}/milestones`),
  getDeliverables: (id: string) => api.get(`/projects/${id}/deliverables`),
};

// Requirements
export const requirementsApi = {
  list: (params?: Record<string, string>) => api.get('/requirements', { params }),
  get: (id: string) => api.get(`/requirements/${id}`),
  create: (data: unknown) => api.post('/requirements', data),
  update: (id: string, data: unknown) => api.patch(`/requirements/${id}`, data),
};

// Suppliers
export const suppliersApi = {
  listManufacturers: (params?: Record<string, string>) =>
    api.get('/suppliers/manufacturers', { params }),
  listVendors: (params?: Record<string, string>) =>
    api.get('/suppliers/vendors', { params }),
  getPartAML: (partId: string) => api.get(`/suppliers/parts/${partId}/aml`),
  getPartAVL: (partId: string) => api.get(`/suppliers/parts/${partId}/avl`),
};

// Changes
export const changesApi = {
  list: (params?: Record<string, string>) => api.get('/changes', { params }),
  get: (id: string) => api.get(`/changes/${id}`),
  create: (data: unknown) => api.post('/changes', data),
  update: (id: string, data: unknown) => api.patch(`/changes/${id}`, data),
};

// Documents
export const documentsApi = {
  list: (params?: Record<string, string>) => api.get('/documents', { params }),
  get: (id: string) => api.get(`/documents/${id}`),
  create: (data: unknown) => api.post('/documents', data),
  update: (id: string, data: unknown) => api.patch(`/documents/${id}`, data),
};

// Compliance
export const complianceApi = {
  listRegulations: (params?: Record<string, string>) =>
    api.get('/compliance/regulations', { params }),
  listCertificates: (params?: Record<string, string>) =>
    api.get('/compliance/certificates', { params }),
};

// Costing
export const costingApi = {
  listVariances: (params?: Record<string, string>) =>
    api.get('/costing/variances', { params }),
};

// Service Bulletins
export const bulletinsApi = {
  list: (params?: Record<string, string>) => api.get('/bulletins', { params }),
  get: (id: string) => api.get(`/bulletins/${id}`),
  create: (data: unknown) => api.post('/bulletins', data),
  listMaintenanceSchedules: (params?: Record<string, string>) =>
    api.get('/bulletins/maintenance/schedules', { params }),
  listUnits: (params?: Record<string, string>) =>
    api.get('/bulletins/units', { params }),
};
