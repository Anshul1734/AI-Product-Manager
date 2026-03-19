import axios, { AxiosResponse } from 'axios';
import {
  ProductIdeaRequest,
  WorkflowResponse,
  HealthResponse,
  BatchRequest,
  BatchResponse,
  AnalyticsResponse,
} from '../types';
import { API_BASE_URL } from '../config';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 300000, // 5 minutes timeout for long workflows
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for logging
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error);
    return Promise.reject(error);
  }
);

export const apiService = {
  // Health check
  async getHealth(): Promise<HealthResponse> {
    const response: AxiosResponse<HealthResponse> = await api.get('/api/v1/health');
    return response.data;
  },

  // Generate product plan
  async generateProductPlan(request: ProductIdeaRequest): Promise<WorkflowResponse> {
    const response = await fetch(`${API_BASE_URL}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea: request.idea })
    });
    return await response.json();
  },

  // Stream workflow execution
  async streamWorkflow(request: ProductIdeaRequest): Promise<ReadableStream> {
    const response = await fetch(`${API_BASE_URL}/api/v1/generate/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.body) {
      throw new Error('Response body is null');
    }

    return response.body;
  },

  // Batch processing
  async batchGenerateProductPlans(request: BatchRequest): Promise<BatchResponse> {
    const response: AxiosResponse<BatchResponse> = await api.post('/api/v1/batch', request);
    return response.data;
  },

  // Get analytics
  async getAnalytics(): Promise<AnalyticsResponse> {
    const response: AxiosResponse<AnalyticsResponse> = await api.get('/api/v1/analytics');
    return response.data;
  },

  // Get workflow state
  async getWorkflowState(threadId: string): Promise<any> {
    const response = await api.get(`/api/v1/state/${threadId}`);
    return response.data;
  },

  // Validate product idea
  async validateProductIdea(request: ProductIdeaRequest): Promise<any> {
    const response = await api.post('/api/v1/validate', request);
    return response.data;
  },

  // Get active threads
  async getActiveThreads(): Promise<any> {
    const response = await api.get('/api/v1/threads');
    return response.data;
  },

  // Reset analytics
  async resetAnalytics(): Promise<any> {
    const response = await api.post('/api/v1/reset-analytics');
    return response.data;
  },

  // Export PRD as PDF
  async exportPRDAsPDF(request: ProductIdeaRequest): Promise<Blob> {
    const response = await api.post('/api/v1/export/prd/pdf', request, {
      responseType: 'blob'
    });
    return response.data;
  },

  // Export tickets as CSV
  async exportTicketsAsCSV(request: ProductIdeaRequest): Promise<Blob> {
    const response = await api.post('/api/v1/export/tickets/csv', request, {
      responseType: 'blob'
    });
    return response.data;
  },

  // Export full workflow as JSON
  async exportFullJSON(request: ProductIdeaRequest): Promise<Blob> {
    const response = await api.post('/api/v1/export/full/json', request, {
      responseType: 'blob'
    });
    return response.data;
  },
};

export default apiService;
