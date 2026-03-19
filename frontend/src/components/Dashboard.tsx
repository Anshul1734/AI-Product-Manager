/**
 * Advanced Dashboard component with real-time monitoring and analytics.
 */
import React, { useState, useEffect } from 'react';
import {
  Activity,
  Brain,
  Database,
  AlertTriangle,
  CheckCircle,
  Zap,
  BarChart3,
  Briefcase,
} from 'lucide-react';
import { useObservability, useAgentManagement } from '../hooks/useAdvancedApi';
import { SystemHealth, MonitoringDashboard, AgentCapabilities } from '../types/advanced';

interface DashboardProps {
  className?: string;
}

const Dashboard: React.FC<DashboardProps> = ({ className = '' }) => {
  const { health, performance, alerts, loading } = useObservability();
  const { capabilities, systemStatus } = useAgentManagement();
  const [selectedTimeRange, setSelectedTimeRange] = useState('1h');

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 bg-green-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      case 'critical':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5" />;
      case 'critical':
        return <AlertTriangle className="w-5 h-5" />;
      default:
        return <Activity className="w-5 h-5" />;
    }
  };

  if (loading) {
    return (
      <div className={`p-6 ${className}`}>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* System Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Brain className="h-8 w-8 text-primary-600" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-medium text-gray-900">System Status</h3>
              <div className={`mt-1 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(health?.status || 'unknown')}`}>
                {getStatusIcon(health?.status || 'unknown')}
                <span className="ml-1">{health?.status || 'Unknown'}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Activity className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-medium text-gray-900">Active Agents</h3>
              <p className="mt-1 text-3xl font-semibold text-gray-900">
                {systemStatus?.agents?.length || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Database className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-medium text-gray-900">Memory Usage</h3>
              <p className="mt-1 text-3xl font-semibold text-gray-900">
                {performance?.metrics?.health?.total_points || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Zap className="h-8 w-8 text-yellow-600" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-medium text-gray-900">Response Time</h3>
              <p className="mt-1 text-3xl font-semibold text-gray-900">
                {'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Health Checks */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">System Health Checks</h3>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {health?.checks?.map((check: any, index: number) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className={`w-3 h-3 rounded-full mr-3 ${
                    check.status === 'healthy' ? 'bg-green-400' :
                    check.status === 'warning' ? 'bg-yellow-400' :
                    'bg-red-400'
                  }`} />
                  <span className="text-sm font-medium text-gray-900">{check.name}</span>
                </div>
                <div className="flex items-center">
                  <span className={`text-sm ${getStatusColor(check.status)}`}>
                    {check.status}
                  </span>
                  <span className="ml-2 text-sm text-gray-500">
                    {check.duration_ms}ms
                  </span>
                </div>
              </div>
            )) || (
              <div className="text-center text-gray-500 py-8">
                No health checks available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Agent Capabilities */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Agent Capabilities</h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Object.entries(capabilities || {}).map(([agentName, agentCaps]: [string, AgentCapabilities]) => (
              <div key={agentName} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center mb-3">
                  <Brain className="h-6 w-6 text-primary-600 mr-2" />
                  <h4 className="text-base font-medium text-gray-900 capitalize">{agentName}</h4>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Specialization:</span>
                    <span className="font-medium">{agentCaps.specialization}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Context Aware:</span>
                    <span className={`font-medium ${agentCaps.context_aware ? 'text-green-600' : 'text-gray-400'}`}>
                      {agentCaps.context_aware ? 'Yes' : 'No'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Structured Output:</span>
                    <span className={`font-medium ${agentCaps.structured_output ? 'text-green-600' : 'text-gray-400'}`}>
                      {agentCaps.structured_output ? 'Yes' : 'No'}
                    </span>
                  </div>
                  {agentCaps.performance && (
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Success Rate:</span>
                      <span className="font-medium">
                        {agentCaps.performance.execution_count > 0 ? 
                          `${Math.round((agentCaps.performance.success_count / agentCaps.performance.execution_count) * 100)}%` :
                          'N/A'
                        }
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )) || (
              <div className="col-span-full text-center text-gray-500 py-8">
                No agent capabilities available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Alerts */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">Recent Alerts</h3>
            <div className="flex items-center space-x-2">
              <select
                value={selectedTimeRange}
                onChange={(e) => setSelectedTimeRange(e.target.value)}
                className="text-sm border-gray-300 rounded-md"
              >
                <option value="1h">Last Hour</option>
                <option value="24h">Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
              </select>
            </div>
          </div>
        </div>
        <div className="p-6">
          <div className="space-y-3">
            {alerts?.slice(0, 10).map((alert: any, index: number) => (
              <div key={alert.id || index} className="flex items-start space-x-3 p-3 rounded-lg border">
                <div className="flex-shrink-0">
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-900">{alert.message}</p>
                    <span className="text-xs px-2 py-1 rounded-full">
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(alert.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            )) || (
              <div className="text-center text-gray-500 py-8">
                No recent alerts
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Performance Metrics</h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-base font-medium text-gray-900 mb-4">Response Times</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Average:</span>
                  <span className="font-medium">
                    {'N/A'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Total Traces:</span>
                  <span className="font-medium">
                    0
                  </span>
                </div>
              </div>
            </div>
            
            <div>
              <h4 className="text-base font-medium text-gray-900 mb-4">System Health</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Error Rate:</span>
                  <span className="font-medium">
                    0
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Total Errors:</span>
                  <span className="font-medium">
                    0
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
