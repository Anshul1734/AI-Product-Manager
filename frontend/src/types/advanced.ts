/**
 * Advanced types for the enhanced AI Product Manager frontend.
 */

// Base types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp?: string;
  execution_time?: number;
  thread_id?: string;
  request_id?: string;
}

// Memory System Types
export interface ConversationTurn {
  turn_id: string;
  thread_id: string;
  user_input: string;
  agent_response: string;
  agent_name: string;
  timestamp: string;
  similarity?: number;
}

export interface AgentState {
  agent_name: string;
  state_data: Record<string, any>;
  timestamp: string;
  version: number;
}

export interface AgentLearning {
  agent_name: string;
  learning_type: string;
  learning_data: Record<string, any>;
  confidence: number;
  timestamp: string;
  source: string;
}

export interface MemoryStats {
  timestamp: string;
  conversation_memory: {
    total_conversation_turns: number;
    thread_count: number;
    max_age_days: number;
    vector_store_stats: {
      total_documents: number;
      dimension: number;
      thread_count: number;
      threads: Record<string, number>;
      index_size: number;
    };
  };
  agent_memory: {
    total_agents: number;
    agent_stats: Record<string, {
      state_count: number;
      learning_count: number;
      total_memory_items: number;
    }>;
    vector_store_stats: any;
  };
  vector_store: any;
  last_cleanup: string;
  cleanup_interval_hours: number;
}

// Observability Types
export interface MetricPoint {
  timestamp: string;
  value: number;
  tags?: Record<string, string>;
  metadata?: Record<string, any>;
}

export interface MetricSummary {
  name: string;
  count: number;
  min_value: number;
  max_value: number;
  avg_value: number;
  sum_value: number;
  last_updated: string;
}

export interface TraceSpan {
  span_id: string;
  parent_span_id?: string;
  operation_name: string;
  start_time: string;
  end_time?: string;
  duration_ms?: number;
  status: string;
  tags: Record<string, any>;
  logs: Array<{
    timestamp: string;
    level: string;
    message: string;
    fields?: Record<string, any>;
  }>;
}

export interface HealthCheck {
  name: string;
  status: 'healthy' | 'warning' | 'critical';
  message: string;
  duration_ms: number;
  timestamp: string;
  details?: Record<string, any>;
}

export interface SystemHealth {
  status: 'healthy' | 'warning' | 'critical';
  timestamp: string;
  checks: HealthCheck[];
  summary: {
    total_checks: number;
    healthy: number;
    warnings: number;
    critical: number;
  };
}

export interface MonitoringDashboard {
  timestamp: string;
  health: SystemHealth;
  performance: {
    timestamp: string;
    metrics: Record<string, MetricSummary>;
    tracing: {
      enabled: boolean;
      total_traces: number;
      active_spans: number;
      error_spans: number;
      error_rate: number;
      avg_duration_ms: number;
      max_traces: number;
    };
    health: SystemHealth;
  };
  alerts: Array<{
    id: string;
    type: string;
    severity: 'info' | 'warning' | 'critical';
    message: string;
    timestamp: string;
    details: Record<string, any>;
  }>;
  metrics: {
    health: {
      status: string;
      metrics_count: number;
      counters_count: number;
      gauges_count: number;
      histograms_count: number;
      max_points: number;
      total_points: number;
    };
    tracing: {
      status: string;
      enabled: boolean;
      trace_count: number;
      active_span_count: number;
      max_traces: number;
    };
  };
}

// Agent Capabilities
export interface AgentCapabilities {
  name: string;
  specialization: string;
  input_types: string[];
  output_types: string[];
  expertise: string[];
  llm_model: string;
  context_aware: boolean;
  structured_output: boolean;
  performance?: {
    execution_count: number;
    success_count: number;
    failure_count: number;
    total_execution_time: number;
    average_execution_time: number;
    retry_count: number;
    timeout_count: number;
  };
}

// Enhanced Workflow Types
export interface AgentContext {
  request_id: string;
  thread_id?: string;
  agent_name: string;
  execution_id: string;
  start_time: string;
  metadata: Record<string, any>;
}

export interface AgentResult {
  success: boolean;
  data: any;
  execution_time: number;
  metadata: Record<string, any>;
  error?: string;
}

export interface EnhancedWorkflowState {
  plan?: any;
  prd?: any;
  architecture?: any;
  tickets?: any;
  features_detailed?: any[];
  agent_steps?: string[];
  metadata?: {
    start_time: string;
    thread_id?: string;
    idea: string;
    execution_id: string;
  };
  execution_summary?: {
    total_execution_time: number;
    completed_at: string;
    agents_executed: string[];
    workflow_id: string;
  };
  quality_metrics?: any;
}

// UI State Types
export interface UIState {
  loading: boolean;
  error: string | null;
  results: EnhancedWorkflowState | null;
  executionTime: number | null;
  lastRequest: ProductIdeaRequest | null;
  useStreaming: boolean;
  isConnected: boolean;
  messages: any[];
  currentView: 'main' | 'memory' | 'observability' | 'analytics';
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
}

export interface ProductIdeaRequest {
  idea: string;
  thread_id?: string;
  context?: {
    conversation_context: ConversationTurn[];
    agent_learning: AgentLearning[];
    agent_state: AgentState;
  };
  advanced_options?: {
    enable_memory: boolean;
    enable_learning: boolean;
    enable_tracing: boolean;
    quality_threshold: number;
    max_retries: number;
  };
}

// Chart and Analytics Types
export interface ChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    backgroundColor?: string;
    borderColor?: string;
    tension?: number;
  }>;
}

export interface PerformanceMetrics {
  timestamp: string;
  response_times: number[];
  success_rates: number[];
  error_rates: number[];
  agent_counts: Record<string, number>;
}

// Export and Import Types
export interface ExportOptions {
  format: 'json' | 'pdf' | 'markdown' | 'csv';
  include_sections: {
    plan: boolean;
    prd: boolean;
    architecture: boolean;
    tickets: boolean;
    metrics: boolean;
    memory: boolean;
  };
  include_metadata: boolean;
}

// Notification Types
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: string;
  auto_dismiss?: boolean;
  actions?: Array<{
    label: string;
    action: () => void;
  }>;
}

// Settings and Configuration
export interface UserSettings {
  theme: 'light' | 'dark' | 'auto';
  language: string;
  auto_save: boolean;
  notifications: {
    enabled: boolean;
    position: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
    duration: number;
  };
  api: {
    timeout: number;
    retry_attempts: number;
    use_streaming: boolean;
  };
  ui: {
    sidebar_collapsed: boolean;
    compact_mode: boolean;
    show_advanced_options: boolean;
  };
}

// Real-time Updates
export interface RealtimeUpdate {
  type: 'workflow_progress' | 'agent_status' | 'memory_update' | 'system_alert';
  timestamp: string;
  data: any;
  metadata?: Record<string, any>;
}
