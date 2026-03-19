/**
 * Advanced hooks for the enhanced AI Product Manager API.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import advancedApiService from '../services/advancedApi';
import axios from 'axios';
import {
  ApiResponse,
  ConversationTurn,
  AgentState,
  AgentLearning,
  MemoryStats,
  SystemHealth,
  MonitoringDashboard,
  AgentCapabilities,
  EnhancedWorkflowState,
  ProductIdeaRequest,
  Notification,
  RealtimeUpdate
} from '../types/advanced';

// Workflow hooks
export const useWorkflow = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<EnhancedWorkflowState | null>(null);
  const [executionTime, setExecutionTime] = useState<number | null>(null);

  const generateProductPlan = useCallback(async (request: ProductIdeaRequest) => {
    setLoading(true);
    setError(null);
    setResults(null);
    setExecutionTime(null);

    try {
      const response = await advancedApiService.generateProductPlan(request);
      
      if (response.success && response.data) {
        setResults(response.data);
        setExecutionTime(response.data.execution_summary?.total_execution_time || null);
      } else {
        setError(response.error || 'Failed to generate product plan');
      }
    } catch (err) {
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        setError('Cannot reach backend at http://localhost:8001. Make sure FastAPI is running and CORS is enabled.');
      } else {
        setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const cancelWorkflow = useCallback(async (workflowId: string) => {
    try {
      await advancedApiService.cancelWorkflow(workflowId);
    } catch (err) {
      console.error('Failed to cancel workflow:', err);
    }
  }, []);

  return {
    loading,
    error,
    results,
    executionTime,
    generateProductPlan,
    cancelWorkflow,
  };
};

// Agent management hooks
export const useAgentManagement = () => {
  const [capabilities, setCapabilities] = useState<Record<string, AgentCapabilities> | null>(null);
  const [performance, setPerformance] = useState<Record<string, any> | null>(null);
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadAgentData = useCallback(async () => {
    setLoading(true);
    try {
      const [capabilitiesRes, performanceRes, statusRes] = await Promise.all([
        advancedApiService.getAgentCapabilities(),
        advancedApiService.getAgentPerformance(),
        advancedApiService.getSystemStatus(),
      ]);

      if (capabilitiesRes.success && capabilitiesRes.data) {
        setCapabilities(capabilitiesRes.data);
      } else {
        setCapabilities(null);
      }
      if (performanceRes.success && performanceRes.data) {
        setPerformance(performanceRes.data);
      } else {
        setPerformance(null);
      }
      if (statusRes.success && statusRes.data) {
        setSystemStatus(statusRes.data);
      } else {
        setSystemStatus(null);
      }
    } catch (err) {
      console.error('Failed to load agent data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const resetMetrics = useCallback(async (agentName?: string) => {
    try {
      await advancedApiService.resetAgentMetrics(agentName);
      // Reload data
      await loadAgentData();
    } catch (err) {
      console.error('Failed to reset metrics:', err);
    }
  }, [loadAgentData]);

  useEffect(() => {
    loadAgentData();
  }, [loadAgentData]);

  return {
    capabilities,
    performance,
    systemStatus,
    loading,
    loadAgentData,
    resetMetrics,
  };
};

// Memory hooks
export const useMemory = () => {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [context, setContext] = useState<any>(null);
  const [searchResults, setSearchResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const addConversationTurn = useCallback(async (
    threadId: string,
    userInput: string,
    agentResponse: string,
    agentName: string,
    metadata?: Record<string, any>
  ) => {
    try {
      const response = await advancedApiService.addConversationTurn(
        threadId,
        userInput,
        agentResponse,
        agentName,
        metadata
      );
      return (response.success && response.data) ? response.data.turn_id : null;
    } catch (err) {
      console.error('Failed to add conversation turn:', err);
      return null;
    }
  }, []);

  const getAgentContext = useCallback(async (
    agentName: string,
    threadId: string,
    query: string,
    options?: any
  ) => {
    setLoading(true);
    try {
      const response = await advancedApiService.getAgentContext(agentName, threadId, query, options);
      if (response.success && response.data) {
        setContext(response.data);
      } else {
        setContext(null);
      }
    } catch (err) {
      console.error('Failed to get agent context:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const searchMemory = useCallback(async (
    query: string,
    options?: any
  ) => {
    setLoading(true);
    try {
      const response = await advancedApiService.searchMemory(query, options);
      if (response.success && response.data) {
        setSearchResults(response.data);
      } else {
        setSearchResults(null);
      }
    } catch (err) {
      console.error('Failed to search memory:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMemoryStats = useCallback(async () => {
    try {
      const response = await advancedApiService.getMemoryStats();
      if (response.success && response.data) {
        setStats(response.data);
      } else {
        setStats(null);
      }
    } catch (err) {
      console.error('Failed to load memory stats:', err);
    }
  }, []);

  const cleanupMemory = useCallback(async () => {
    try {
      const response = await advancedApiService.cleanupMemory();
      if (response.success) {
        await loadMemoryStats();
      }
    } catch (err) {
      console.error('Failed to cleanup memory:', err);
    }
  }, [loadMemoryStats]);

  const clearMemory = useCallback(async (options?: {
    threadId?: string;
    agentName?: string;
    memoryType?: string;
  }) => {
    try {
      const response = await advancedApiService.clearMemory(
        options?.threadId,
        options?.agentName,
        options?.memoryType
      );
      if (response.success) {
        await loadMemoryStats();
      }
    } catch (err) {
      console.error('Failed to clear memory:', err);
    }
  }, [loadMemoryStats]);

  useEffect(() => {
    loadMemoryStats();
  }, [loadMemoryStats]);

  return {
    stats,
    context,
    searchResults,
    loading,
    addConversationTurn,
    getAgentContext,
    searchMemory,
    loadMemoryStats,
    cleanupMemory,
    clearMemory,
  };
};

// Observability hooks
export const useObservability = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [performance, setPerformance] = useState<MonitoringDashboard | null>(null);
  const [traces, setTraces] = useState<any>(null);
  const [alerts, setAlerts] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadSystemHealth = useCallback(async () => {
    try {
      const response = await advancedApiService.getSystemHealth();
      if (response.success && response.data) {
        setHealth(response.data);
      } else {
        setHealth(null);
      }
    } catch (err) {
      console.error('Failed to load system health:', err);
    }
  }, []);

  const loadPerformanceMetrics = useCallback(async () => {
    try {
      const response = await advancedApiService.getPerformanceMetrics();
      if (response.success && response.data) {
        setPerformance(response.data);
      } else {
        setPerformance(null);
      }
    } catch (err) {
      console.error('Failed to load performance metrics:', err);
    }
  }, []);

  const loadTraces = useCallback(async (options?: any) => {
    try {
      const response = await advancedApiService.getTraces(options?.limit, options?.operationName, options?.status);
      if (response.success) {
        setTraces(response.data);
      }
    } catch (err) {
      console.error('Failed to load traces:', err);
    }
  }, []);

  const loadAlerts = useCallback(async (options?: any) => {
    try {
      const response = await advancedApiService.getAlerts(options?.severity, options?.limit);
      if (response.success) {
        setAlerts(response.data);
      }
    } catch (err) {
      console.error('Failed to load alerts:', err);
    }
  }, []);

  const loadMetrics = useCallback(async (options?: any) => {
    try {
      const response = await advancedApiService.getMetrics(options?.name, options?.format);
      if (response.success) {
        setMetrics(response.data);
      }
    } catch (err) {
      console.error('Failed to load metrics:', err);
    }
  }, []);

  const createAlert = useCallback(async (
    alertType: string,
    severity: 'info' | 'warning' | 'critical',
    message: string,
    details?: Record<string, any>
  ) => {
    try {
      await advancedApiService.createAlert(alertType, severity, message, details);
      // Reload alerts
      await loadAlerts();
    } catch (err) {
      console.error('Failed to create alert:', err);
    }
  }, [loadAlerts]);

  const resetMetrics = useCallback(async (name?: string) => {
    try {
      await advancedApiService.resetMetrics(name);
      // Reload metrics
      await loadMetrics();
    } catch (err) {
      console.error('Failed to reset metrics:', err);
    }
  }, [loadMetrics]);

  // Load initial data
  useEffect(() => {
    loadSystemHealth();
    loadPerformanceMetrics();
    loadTraces({ limit: 50 });
    loadAlerts({ limit: 20 });
    loadMetrics();
  }, [loadSystemHealth, loadPerformanceMetrics, loadTraces, loadAlerts, loadMetrics]);

  return {
    health,
    performance,
    traces,
    alerts,
    metrics,
    loading,
    loadSystemHealth,
    loadPerformanceMetrics,
    loadTraces,
    loadAlerts,
    loadMetrics,
    createAlert,
    resetMetrics,
  };
};

// WebSocket hooks for real-time updates
export const useRealtimeUpdates = (clientId: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const [updates, setUpdates] = useState<RealtimeUpdate[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = advancedApiService.connectWebSocket(clientId);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    // Handle different types of updates
    advancedApiService.on('workflow_progress', (data: any) => {
      setUpdates(prev => [...prev, {
        type: 'workflow_progress',
        timestamp: new Date().toISOString(),
        data,
      }]);
    });

    advancedApiService.on('agent_status', (data: any) => {
      setUpdates(prev => [...prev, {
        type: 'agent_status',
        timestamp: new Date().toISOString(),
        data,
      }]);
    });

    advancedApiService.on('memory_update', (data: any) => {
      setUpdates(prev => [...prev, {
        type: 'memory_update',
        timestamp: new Date().toISOString(),
        data,
      }]);
    });

    advancedApiService.on('system_alert', (data: any) => {
      setUpdates(prev => [...prev, {
        type: 'system_alert',
        timestamp: new Date().toISOString(),
        data,
      }]);
    });

    return () => {
      advancedApiService.disconnectWebSocket();
      setIsConnected(false);
    };
  }, [clientId]);

  return {
    isConnected,
    updates,
    clearUpdates: () => setUpdates([]),
  };
};

// Notifications hook
export const useNotifications = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = useCallback((notification: Omit<Notification, 'id'>) => {
    const newNotification: Notification = {
      ...notification,
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
    };
    
    setNotifications(prev => [...prev, newNotification]);

    // Auto-dismiss if enabled
    if (notification.auto_dismiss !== false) {
      setTimeout(() => {
        removeNotification(newNotification.id);
      }, 5000);
    }
  }, []);

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  return {
    notifications,
    addNotification,
    removeNotification,
    clearNotifications,
  };
};

// Settings hook
export const useSettings = () => {
  const [settings, setSettings] = useState(() => {
    const saved = localStorage.getItem('ai-pm-settings');
    return saved ? JSON.parse(saved) : {
      theme: 'light',
      language: 'en',
      auto_save: true,
      notifications: {
        enabled: true,
        position: 'top-right',
        duration: 5000,
      },
      api: {
        timeout: 30000,
        retry_attempts: 3,
        use_streaming: true,
      },
      ui: {
        sidebar_collapsed: false,
        compact_mode: false,
        show_advanced_options: true,
      },
    };
  });

  const updateSettings = useCallback((newSettings: Partial<typeof settings>) => {
    const updated = { ...settings, ...newSettings };
    setSettings(updated);
    localStorage.setItem('ai-pm-settings', JSON.stringify(updated));
  }, [settings]);

  return {
    settings,
    updateSettings,
  };
};
