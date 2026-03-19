/**
 * Advanced API service for the enhanced AI Product Manager.
 */
import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  ApiResponse,
  ConversationTurn,
  AgentState,
  AgentLearning,
  MemoryStats,
  MetricPoint,
  TraceSpan,
  SystemHealth,
  MonitoringDashboard,
  AgentCapabilities,
  EnhancedWorkflowState,
  ProductIdeaRequest,
  ExportOptions,
  Notification
} from '../types/advanced';
import { API_BASE_URL, WS_BASE_URL } from '../config';

class AdvancedApiService {
  private api: AxiosInstance;
  private ws: WebSocket | null = null;
  private wsCallbacks: Map<string, Function[]> = new Map();

  constructor() {
    this.api = axios.create({
      baseURL: process.env.REACT_APP_API_URL || `${API_BASE_URL}/api/v1`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth/logging
    this.api.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response: AxiosResponse) => {
        console.log(`API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, response.status);
        return response;
      },
      (error) => {
        console.error('API Response Error:', error);
        if (error.response?.status === 401) {
          // Handle auth errors
          this.handleAuthError();
        }
        return Promise.reject(error);
      }
    );
  }

  // Workflow API
  async generateProductPlan(request: ProductIdeaRequest): Promise<ApiResponse<EnhancedWorkflowState>> {
    try {
      const response = await fetch(`${API_BASE_URL}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ idea: request.idea })
      });
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Generate product plan error:', error);
      throw error;
    }
  }

  async getWorkflowStatus(workflowId: string): Promise<ApiResponse<any>> {
    try {
      const response = await this.api.get(`/workflows/${workflowId}/status`);
      return response.data;
    } catch (error) {
      console.error('Get workflow status error:', error);
      throw error;
    }
  }

  async cancelWorkflow(workflowId: string): Promise<ApiResponse<any>> {
    try {
      const response = await this.api.post(`/workflows/${workflowId}/cancel`);
      return response.data;
    } catch (error) {
      console.error('Cancel workflow error:', error);
      throw error;
    }
  }

  // Agent Management API
  async getAgentCapabilities(): Promise<ApiResponse<Record<string, AgentCapabilities>>> {
    try {
      const response = await this.api.get('/agents/capabilities');
      return response.data;
    } catch (error) {
      console.error('Get agent capabilities error:', error);
      throw error;
    }
  }

  async getAgentPerformance(): Promise<ApiResponse<Record<string, any>>> {
    try {
      const response = await this.api.get('/agents/performance');
      return response.data;
    } catch (error) {
      console.error('Get agent performance error:', error);
      throw error;
    }
  }

  async resetAgentMetrics(agentName?: string): Promise<ApiResponse<any>> {
    try {
      const url = agentName ? `/agents/reset-metrics?agent_name=${agentName}` : '/agents/reset-metrics';
      const response = await this.api.post(url);
      return response.data;
    } catch (error) {
      console.error('Reset agent metrics error:', error);
      throw error;
    }
  }

  async getSystemStatus(): Promise<ApiResponse<any>> {
    try {
      const response = await this.api.get('/agents/system-status');
      return response.data;
    } catch (error) {
      console.error('Get system status error:', error);
      throw error;
    }
  }

  // Memory API
  async addConversationTurn(
    threadId: string,
    userInput: string,
    agentResponse: string,
    agentName: string,
    metadata?: Record<string, any>
  ): Promise<ApiResponse<{ turn_id: string }>> {
    try {
      const response = await this.api.post('/memory/conversation/add', {
        thread_id: threadId,
        user_input: userInput,
        agent_response: agentResponse,
        agent_name: agentName,
        metadata,
      });
      return response.data;
    } catch (error) {
      console.error('Add conversation turn error:', error);
      throw error;
    }
  }

  async getAgentContext(
    agentName: string,
    threadId: string,
    query: string,
    options: {
      max_conversation_turns?: number;
      max_agent_learning?: number;
      similarity_threshold?: number;
    } = {}
  ): Promise<ApiResponse<any>> {
    try {
      const params = new URLSearchParams({
        thread_id: threadId,
        query,
        max_conversation_turns: String(options.max_conversation_turns || 3),
        max_agent_learning: String(options.max_agent_learning || 2),
        similarity_threshold: String(options.similarity_threshold || 0.6),
      });
      
      const response = await this.api.get(`/memory/context/${agentName}?${params}`);
      return response.data;
    } catch (error) {
      console.error('Get agent context error:', error);
      throw error;
    }
  }

  async storeAgentState(
    agentName: string,
    stateData: Record<string, any>,
    metadata?: Record<string, any>
  ): Promise<ApiResponse<{ state_id: string }>> {
    try {
      const response = await this.api.post('/memory/agent/state', {
        agent_name: agentName,
        state_data: stateData,
        metadata,
      });
      return response.data;
    } catch (error) {
      console.error('Store agent state error:', error);
      throw error;
    }
  }

  async storeAgentLearning(
    agentName: string,
    learningType: string,
    learningData: Record<string, any>,
    confidence: number,
    source: string,
    metadata?: Record<string, any>
  ): Promise<ApiResponse<{ learning_id: string }>> {
    try {
      const response = await this.api.post('/memory/agent/learning', {
        agent_name: agentName,
        learning_type: learningType,
        learning_data: learningData,
        confidence,
        source,
        metadata,
      });
      return response.data;
    } catch (error) {
      console.error('Store agent learning error:', error);
      throw error;
    }
  }

  async searchMemory(
    query: string,
    options: {
      thread_id?: string;
      agent_name?: string;
      memory_types?: string[];
      max_results?: number;
    } = {}
  ): Promise<ApiResponse<any>> {
    try {
      const params = new URLSearchParams({
        query,
        max_results: String(options.max_results || 20),
        ...(options.thread_id && { thread_id: options.thread_id }),
        ...(options.agent_name && { agent_name: options.agent_name }),
        ...(options.memory_types && { memory_types: options.memory_types.join(',') }),
      });
      
      const response = await this.api.get(`/memory/search?${params}`);
      return response.data;
    } catch (error) {
      console.error('Search memory error:', error);
      throw error;
    }
  }

  async getMemoryStats(): Promise<ApiResponse<MemoryStats>> {
    try {
      const response = await this.api.get('/memory/stats');
      return response.data;
    } catch (error) {
      console.error('Get memory stats error:', error);
      throw error;
    }
  }

  async cleanupMemory(): Promise<ApiResponse<any>> {
    try {
      const response = await this.api.post('/memory/cleanup');
      return response.data;
    } catch (error) {
      console.error('Cleanup memory error:', error);
      throw error;
    }
  }

  async clearMemory(
    threadId?: string,
    agentName?: string,
    memoryType?: string
  ): Promise<ApiResponse<Record<string, number>>> {
    try {
      const params = new URLSearchParams();
      if (threadId) params.append('thread_id', threadId);
      if (agentName) params.append('agent_name', agentName);
      if (memoryType) params.append('memory_type', memoryType);
      
      const response = await this.api.delete(`/memory/clear?${params}`);
      return response.data;
    } catch (error) {
      console.error('Clear memory error:', error);
      throw error;
    }
  }

  // Observability API
  async getSystemHealth(): Promise<ApiResponse<SystemHealth>> {
    try {
      const response = await this.api.get('/observability/health');
      return response.data;
    } catch (error) {
      console.error('Get system health error:', error);
      throw error;
    }
  }

  async getPerformanceMetrics(): Promise<ApiResponse<MonitoringDashboard>> {
    try {
      const response = await this.api.get('/observability/performance');
      return response.data;
    } catch (error) {
      console.error('Get performance metrics error:', error);
      throw error;
    }
  }

  async getTraces(
    limit: number = 50,
    operationName?: string,
    status?: string
  ): Promise<ApiResponse<any>> {
    try {
      const params = new URLSearchParams({
        limit: String(limit),
        ...(operationName && { operation_name: operationName }),
        ...(status && { status }),
      });
      
      const response = await this.api.get(`/observability/traces?${params}`);
      return response.data;
    } catch (error) {
      console.error('Get traces error:', error);
      throw error;
    }
  }

  async getTrace(traceId: string): Promise<ApiResponse<any>> {
    try {
      const response = await this.api.get(`/observability/traces/${traceId}`);
      return response.data;
    } catch (error) {
      console.error('Get trace error:', error);
      throw error;
    }
  }

  async createAlert(
    alertType: string,
    severity: 'info' | 'warning' | 'critical',
    message: string,
    details?: Record<string, any>
  ): Promise<ApiResponse<any>> {
    try {
      const response = await this.api.post('/observability/alerts', {
        alert_type: alertType,
        severity,
        message,
        details,
      });
      return response.data;
    } catch (error) {
      console.error('Create alert error:', error);
      throw error;
    }
  }

  async getAlerts(
    severity?: string,
    limit: number = 50
  ): Promise<ApiResponse<any>> {
    try {
      const params = new URLSearchParams({
        limit: String(limit),
        ...(severity && { severity }),
      });
      
      const response = await this.api.get(`/observability/alerts?${params}`);
      return response.data;
    } catch (error) {
      console.error('Get alerts error:', error);
      throw error;
    }
  }

  async getMonitoringDashboard(): Promise<ApiResponse<MonitoringDashboard>> {
    try {
      const response = await this.api.get('/observability/dashboard');
      return response.data;
    } catch (error) {
      console.error('Get monitoring dashboard error:', error);
      throw error;
    }
  }

  async getObservabilityStats(): Promise<ApiResponse<any>> {
    try {
      const response = await this.api.get('/observability/stats');
      return response.data;
    } catch (error) {
      console.error('Get observability stats error:', error);
      throw error;
    }
  }

  // Metrics API
  async incrementCounter(
    name: string,
    value: number = 1,
    tags?: Record<string, string>
  ): Promise<ApiResponse<any>> {
    try {
      const response = await this.api.post('/observability/metrics/counter', {
        name,
        value,
        metric_type: 'counter',
        tags,
      });
      return response.data;
    } catch (error) {
      console.error('Increment counter error:', error);
      throw error;
    }
  }

  async setGauge(
    name: string,
    value: number,
    tags?: Record<string, string>
  ): Promise<ApiResponse<any>> {
    try {
      const response = await this.api.post('/observability/metrics/gauge', {
        name,
        value,
        metric_type: 'gauge',
        tags,
      });
      return response.data;
    } catch (error) {
      console.error('Set gauge error:', error);
      throw error;
    }
  }

  async recordHistogram(
    name: string,
    value: number,
    tags?: Record<string, string>
  ): Promise<ApiResponse<any>> {
    try {
      const response = await this.api.post('/observability/metrics/histogram', {
        name,
        value,
        metric_type: 'histogram',
        tags,
      });
      return response.data;
    } catch (error) {
      console.error('Record histogram error:', error);
      throw error;
    }
  }

  async getMetrics(
    name?: string,
    format: string = 'json'
  ): Promise<ApiResponse<any>> {
    try {
      const params = new URLSearchParams({
        format,
        ...(name && { name }),
      });
      
      const response = await this.api.get(`/observability/metrics?${params}`);
      return response.data;
    } catch (error) {
      console.error('Get metrics error:', error);
      throw error;
    }
  }

  async resetMetrics(name?: string): Promise<ApiResponse<any>> {
    try {
      const params = name ? `?name=${name}` : '';
      const response = await this.api.post(`/observability/metrics/reset${params}`);
      return response.data;
    } catch (error) {
      console.error('Reset metrics error:', error);
      throw error;
    }
  }

  // WebSocket for real-time updates
  connectWebSocket(clientId: string): WebSocket {
    const wsUrl = `${process.env.REACT_APP_WS_URL || `${WS_BASE_URL}`}/ws/${clientId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.emit('connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.emit(data.type, data);
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.emit('disconnected');
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', error);
    };

    return this.ws;
  }

  disconnectWebSocket(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  // Event emitter pattern for WebSocket
  on(event: string, callback: Function): void {
    if (!this.wsCallbacks.has(event)) {
      this.wsCallbacks.set(event, []);
    }
    this.wsCallbacks.get(event)!.push(callback);
  }

  off(event: string, callback: Function): void {
    const callbacks = this.wsCallbacks.get(event);
    if (callbacks) {
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  private emit(event: string, data?: any): void {
    const callbacks = this.wsCallbacks.get(event);
    if (callbacks) {
      callbacks.forEach(callback => callback(data));
    }
  }

  private handleAuthError(): void {
    // Handle authentication errors
    console.error('Authentication error - please log in again');
    // Redirect to login or refresh token
  }
}

// Create singleton instance
const advancedApiService = new AdvancedApiService();

export default advancedApiService;
