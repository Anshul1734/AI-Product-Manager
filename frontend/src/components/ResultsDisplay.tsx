import React, { useState } from 'react';
import { 
  Lightbulb, 
  Users, 
  Cpu, 
  CheckSquare,
  Clock,
  Target,
  Code,
  Database,
  Globe,
  Shield,
  Zap,
  ChevronRight,
  FileText,
  Layers,
  Rocket,
  Download,
  FileDown,
  FileSpreadsheet,
  FileJson
} from 'lucide-react';
import { WorkflowOutput } from '../types';
import { ProductIdeaRequest } from '../types';
import apiService from '../services/api';
import { downloadFile, generateFilename } from '../utils/exportUtils';

interface ResultsDisplayProps {
  results: WorkflowOutput;
  executionTime?: number;
  isLoading?: boolean;
  originalIdea?: string;
  threadId?: string;
}

const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ 
  results, 
  executionTime,
  isLoading = false,
  originalIdea = '',
  threadId = ''
}) => {
  const [activeTab, setActiveTab] = useState<'plan' | 'prd' | 'architecture' | 'tickets'>('plan');
  const [exporting, setExporting] = useState<string | null>(null);

  const tabs = [
    { 
      id: 'plan' as const, 
      label: 'Product Vision', 
      icon: <Lightbulb className="w-4 h-4" />,
      color: 'blue'
    },
    { 
      id: 'prd' as const, 
      label: 'PRD', 
      icon: <Users className="w-4 h-4" />,
      color: 'green'
    },
    { 
      id: 'architecture' as const, 
      label: 'Architecture', 
      icon: <Cpu className="w-4 h-4" />,
      color: 'purple'
    },
    { 
      id: 'tickets' as const, 
      label: 'Tickets', 
      icon: <CheckSquare className="w-4 h-4" />,
      color: 'orange'
    }
  ];

  const TabButton: React.FC<{ tab: typeof tabs[0]; isActive: boolean }> = ({ tab, isActive }) => (
    <button
      onClick={() => setActiveTab(tab.id)}
      className={`
        flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all duration-200
        ${isActive 
          ? `bg-${tab.color}-100 text-${tab.color}-700 border-${tab.color}-200 border` 
          : `text-gray-600 hover:text-gray-800 hover:bg-gray-100`
        }
      `}
    >
      {tab.icon}
      <span className="hidden sm:inline">{tab.label}</span>
      <span className="sm:hidden">{tab.label.split(' ')[0]}</span>
    </button>
  );

  const StatCard: React.FC<{ icon: React.ReactNode; label: string; value: string | number; color?: string }> = ({ 
    icon, label, value, color = 'blue' 
  }) => (
    <div className={`bg-${color}-50 rounded-lg p-4 border border-${color}-200`}>
      <div className="flex items-center space-x-3">
        <div className={`text-${color}-600`}>{icon}</div>
        <div>
          <p className={`text-sm text-${color}-600 font-medium`}>{label}</p>
          <p className={`text-lg font-semibold text-${color}-900`}>{value}</p>
        </div>
      </div>
    </div>
  );

  const handleExportPRD = async () => {
    if (!originalIdea) return;
    
    setExporting('prd');
    try {
      const request: ProductIdeaRequest = {
        idea: originalIdea,
        thread_id: threadId || undefined,
        use_legacy: false
      };
      
      const blob = await apiService.exportPRDAsPDF(request);
      const filename = generateFilename(results.plan.product_name, 'PRD', 'pdf');
      downloadFile(blob, filename);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setExporting(null);
    }
  };

  const handleExportTickets = async () => {
    if (!originalIdea) return;
    
    setExporting('tickets');
    try {
      const request: ProductIdeaRequest = {
        idea: originalIdea,
        thread_id: threadId || undefined,
        use_legacy: false
      };
      
      const blob = await apiService.exportTicketsAsCSV(request);
      const filename = generateFilename(results.plan.product_name, 'tickets', 'csv');
      downloadFile(blob, filename);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setExporting(null);
    }
  };

  const handleExportJSON = async () => {
    if (!originalIdea) return;
    
    setExporting('json');
    try {
      const request: ProductIdeaRequest = {
        idea: originalIdea,
        thread_id: threadId || undefined,
        use_legacy: false
      };
      
      const blob = await apiService.exportFullJSON(request);
      const filename = generateFilename(results.plan.product_name, 'workflow', 'json');
      downloadFile(blob, filename);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setExporting(null);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Loading Header */}
        <div className="text-center py-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
            <Rocket className="w-8 h-8 text-blue-600 animate-pulse" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">Generating Your Product Plan</h3>
          <p className="text-gray-600 mb-6">Our AI agents are working together to create a comprehensive product plan...</p>
          
          {/* Loading Steps */}
          <div className="max-w-md mx-auto space-y-3">
            <div className="flex items-center space-x-3 text-left">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <Lightbulb className="w-4 h-4 text-blue-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Planner Agent</p>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-blue-600 h-2 rounded-full w-3/4 animate-pulse"></div>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-3 text-left">
              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                <Users className="w-4 h-4 text-green-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Analyst Agent</p>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-green-600 h-2 rounded-full w-1/2 animate-pulse"></div>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-3 text-left">
              <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                <Cpu className="w-4 h-4 text-purple-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Architect Agent</p>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-purple-600 h-2 rounded-full w-1/4 animate-pulse"></div>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-3 text-left">
              <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
                <CheckSquare className="w-4 h-4 text-orange-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Ticket Generator</p>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-orange-600 h-2 rounded-full w-1/8 animate-pulse"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Success Header */}
      {executionTime && (
        <div className="bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <Rocket className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Product Plan Generated Successfully!</h3>
                <p className="text-gray-600">Your comprehensive product plan is ready for review and export</p>
              </div>
            </div>
            <div className="text-right">
              <div className="flex items-center space-x-2 text-green-600 mb-2">
                <Clock className="w-4 h-4" />
                <span className="font-medium">{executionTime.toFixed(2)}s</span>
              </div>
            </div>
          </div>
          
          {/* Export Buttons */}
          <div className="flex flex-wrap gap-3 pt-4 border-t border-green-200">
            <button
              onClick={handleExportPRD}
              disabled={exporting === 'prd' || !originalIdea}
              className="flex items-center space-x-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FileDown className="w-4 h-4" />
              <span>{exporting === 'prd' ? 'Exporting...' : 'Export PRD (PDF)'}</span>
            </button>
            
            <button
              onClick={handleExportTickets}
              disabled={exporting === 'tickets' || !originalIdea}
              className="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FileSpreadsheet className="w-4 h-4" />
              <span>{exporting === 'tickets' ? 'Exporting...' : 'Export Tickets (CSV)'}</span>
            </button>
            
            <button
              onClick={handleExportJSON}
              disabled={exporting === 'json' || !originalIdea}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FileJson className="w-4 h-4" />
              <span>{exporting === 'json' ? 'Exporting...' : 'Export Full (JSON)'}</span>
            </button>
          </div>
        </div>
      )}

{/* Agent Processing Steps (Optional) */}
      {results.agent_steps && results.agent_steps.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h4 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-indigo-600" />
            AI Agent Processing Steps
          </h4>
          <div className="flex flex-wrap gap-2">
            {results.agent_steps.map((step, index) => (
              <div key={index} className="flex items-center space-x-2 bg-indigo-50 text-indigo-700 rounded-full px-4 py-1.5 text-sm font-medium border border-indigo-100">
                <span>{index + 1}. {step}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          icon={<Target className="w-5 h-5" />}
          label="Target Users"
          value={results.plan.target_users.length}
          color="blue"
        />
        <StatCard
          icon={<Users className="w-5 h-5" />}
          label="User Personas"
          value={results.prd.user_personas.length}
          color="green"
        />
        <StatCard
          icon={<Code className="w-5 h-5" />}
          label="API Endpoints"
          value={results.architecture.api_endpoints.length}
          color="purple"
        />
        <StatCard
          icon={<CheckSquare className="w-5 h-5" />}
          label="Development Epics"
          value={results.tickets.epics.length}
          color="orange"
        />
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-1 p-2" aria-label="Tabs">
            {tabs.map((tab) => (
              <TabButton key={tab.id} tab={tab} isActive={activeTab === tab.id} />
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {/* Product Vision Tab */}
          {activeTab === 'plan' && (
            <div className="space-y-6">
              <div className="flex items-center space-x-3 mb-6">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Lightbulb className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Product Vision</h3>
                  <p className="text-gray-600">The foundation of your product strategy</p>
                </div>
              </div>

              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-200">
                <h4 className="text-lg font-bold text-gray-900 mb-2">{results.plan.product_name}</h4>
                <p className="text-gray-700 leading-relaxed">{results.plan.problem_statement}</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <div className="flex items-center space-x-2 mb-4">
                    <Users className="w-5 h-5 text-blue-600" />
                    <h4 className="font-semibold text-gray-900">Target Users</h4>
                  </div>
                  <ul className="space-y-2">
                    {results.plan.target_users.map((user, index) => (
                      <li key={index} className="flex items-center space-x-2">
                        <ChevronRight className="w-4 h-4 text-blue-500" />
                        <span className="text-gray-700">{user}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <div className="flex items-center space-x-2 mb-4">
                    <Target className="w-5 h-5 text-blue-600" />
                    <h4 className="font-semibold text-gray-900">Core Goals</h4>
                  </div>
                  <ul className="space-y-2">
                    {results.plan.core_goals.map((goal, index) => (
                      <li key={index} className="flex items-center space-x-2">
                        <ChevronRight className="w-4 h-4 text-blue-500" />
                        <span className="text-gray-700">{goal}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex items-center space-x-2 mb-4">
                  <Zap className="w-5 h-5 text-blue-600" />
                  <h4 className="font-semibold text-gray-900">Key Features</h4>
                </div>
                {results.features_detailed && results.features_detailed.length > 0 ? (
                  <div className="space-y-4">
                    {results.features_detailed.map((feature, index) => (
                      <div key={index} className="bg-blue-50 rounded-lg p-4 border border-blue-100">
                        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start mb-2 gap-2">
                          <h5 className="font-semibold text-blue-900">{feature.name}</h5>
                          {feature.rice && (
                            <div className="bg-white px-3 py-1 rounded-full text-xs font-bold text-blue-700 border border-blue-200 flex items-center gap-1 shrink-0">
                              <Target className="w-3 h-3" />
                              RICE: {feature.rice.score.toFixed(1)}
                            </div>
                          )}
                        </div>
                        <p className="text-sm text-blue-800 mb-3">{feature.description}</p>
                        {feature.justification && (
                          <div className="bg-white bg-opacity-60 p-3 rounded text-sm text-gray-700 border border-blue-50">
                            <span className="font-semibold text-blue-900 mb-1 block">Justification:</span>
                            {feature.justification}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {results.plan.key_features_high_level.map((feature, index) => (
                      <div key={index} className="flex items-center space-x-2 bg-blue-50 rounded-lg p-3">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        <span className="text-gray-700 text-sm">{feature}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* PRD Tab */}
          {activeTab === 'prd' && (
            <div className="space-y-6">
              <div className="flex items-center space-x-3 mb-6">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                  <Users className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Product Requirements Document</h3>
                  <p className="text-gray-600">Detailed specifications for your product</p>
                </div>
              </div>

              <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border border-green-200">
                <h4 className="text-lg font-bold text-gray-900 mb-3">Problem Statement</h4>
                <p className="text-gray-700 leading-relaxed">{results.prd.problem_statement}</p>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex items-center space-x-2 mb-4">
                  <Users className="w-5 h-5 text-green-600" />
                  <h4 className="font-semibold text-gray-900">User Personas</h4>
                </div>
                <div className="space-y-4">
                  {results.prd.user_personas.map((persona, index) => (
                    <div key={index} className="bg-green-50 rounded-lg p-4 border border-green-200">
                      <h5 className="font-semibold text-gray-900 mb-2">{persona.name}</h5>
                      <p className="text-gray-700 text-sm mb-3">{persona.description}</p>
                      <div>
                        <h6 className="font-medium text-gray-800 mb-2 text-sm">Pain Points:</h6>
                        <ul className="space-y-1">
                          {persona.pain_points.map((point, pointIndex) => (
                            <li key={pointIndex} className="flex items-center space-x-2 text-sm">
                              <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
                              <span className="text-gray-700">{point}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex items-center space-x-2 mb-4">
                  <FileText className="w-5 h-5 text-green-600" />
                  <h4 className="font-semibold text-gray-900">User Stories</h4>
                </div>
                <div className="space-y-3">
                  {results.prd.user_stories.map((story, index) => (
                    <div key={index} className="bg-gray-50 rounded-lg p-4 border-l-4 border-green-500">
                      <h5 className="font-medium text-gray-900 mb-2">{story.title}</h5>
                      <p className="text-gray-700 text-sm leading-relaxed">
                        As a <span className="font-medium text-green-700">{story.as_a}</span>, I want to 
                        <span className="font-medium text-green-700"> {story.i_want_to}</span> so that 
                        <span className="font-medium text-green-700"> {story.so_that}</span>
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex items-center space-x-2 mb-4">
                  <Target className="w-5 h-5 text-green-600" />
                  <h4 className="font-semibold text-gray-900">Success Metrics</h4>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {results.prd.success_metrics.map((metric, index) => (
                    <div key={index} className="bg-green-50 rounded-lg p-4 border border-green-200">
                      <h5 className="font-medium text-gray-900 mb-1">{metric.name}</h5>
                      <p className="text-gray-600 text-sm mb-2">{metric.description}</p>
                      <div className="flex items-center space-x-2">
                        <Target className="w-4 h-4 text-green-600" />
                        <span className="text-sm font-medium text-green-700">Target: {metric.target}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Architecture Tab */}
          {activeTab === 'architecture' && (
            <div className="space-y-6">
              <div className="flex items-center space-x-3 mb-6">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Cpu className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">System Architecture</h3>
                  <p className="text-gray-600">Technical foundation and infrastructure</p>
                </div>
              </div>

              <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-xl p-6 border border-purple-200">
                <h4 className="text-lg font-bold text-gray-900 mb-3">System Design</h4>
                <p className="text-gray-700 leading-relaxed">{results.architecture.system_design}</p>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex items-center space-x-2 mb-4">
                  <Layers className="w-5 h-5 text-purple-600" />
                  <h4 className="font-semibold text-gray-900">Tech Stack</h4>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(results.architecture.tech_stack).map(([key, value]) => (
                    <div key={key} className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                      <div className="flex items-center space-x-2 mb-2">
                        <Code className="w-4 h-4 text-purple-600" />
                        <h5 className="font-medium text-gray-900 capitalize">{key}</h5>
                      </div>
                      <p className="text-gray-700 text-sm">{value}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex items-center space-x-2 mb-4">
                  <Globe className="w-5 h-5 text-purple-600" />
                  <h4 className="font-semibold text-gray-900">Architecture Components</h4>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {results.architecture.architecture_components.map((component, index) => (
                    <div key={index} className="flex items-center space-x-2 bg-purple-50 rounded-lg p-3">
                      <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                      <span className="text-gray-700 text-sm">{component}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex items-center space-x-2 mb-4">
                  <Database className="w-5 h-5 text-purple-600" />
                  <h4 className="font-semibold text-gray-900">Database Schema</h4>
                </div>
                <div className="space-y-4">
                  {results.architecture.database_schema.map((table, index) => (
                    <div key={index} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <h5 className="font-medium text-gray-900 mb-3 font-mono">{table.table_name}</h5>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-gray-200">
                              <th className="text-left py-2 font-medium text-gray-700">Field</th>
                              <th className="text-left py-2 font-medium text-gray-700">Type</th>
                              <th className="text-left py-2 font-medium text-gray-700">Constraints</th>
                            </tr>
                          </thead>
                          <tbody>
                            {table.fields.map((field, fieldIndex) => (
                              <tr key={fieldIndex} className="border-b border-gray-100">
                                <td className="py-2 font-mono text-gray-900">{field.name}</td>
                                <td className="py-2">
                                  <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded text-xs font-medium">
                                    {field.type}
                                  </span>
                                </td>
                                <td className="py-2">
                                  <span className="bg-gray-100 text-gray-800 px-2 py-1 rounded text-xs">
                                    {field.constraints}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Tickets Tab */}
          {activeTab === 'tickets' && (
            <div className="space-y-6">
              <div className="flex items-center space-x-3 mb-6">
                <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                  <CheckSquare className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Development Tickets</h3>
                  <p className="text-gray-600">Implementation roadmap and tasks</p>
                </div>
              </div>

              <div className="space-y-6">
                {results.tickets.epics.map((epic, epicIndex) => (
                  <div key={epicIndex} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                    <div className="bg-gradient-to-r from-orange-50 to-amber-50 p-6 border-b border-orange-200">
                      <div className="flex items-center space-x-3 mb-2">
                        <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center">
                          <Layers className="w-4 h-4 text-orange-600" />
                        </div>
                        <h4 className="text-lg font-bold text-gray-900">{epic.epic_name}</h4>
                      </div>
                      <p className="text-gray-700">{epic.description}</p>
                    </div>
                    
                    <div className="p-6 space-y-4">
                      {epic.stories.map((story, storyIndex) => (
                        <div key={storyIndex} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                          <div className="flex items-center space-x-2 mb-3">
                            <FileText className="w-4 h-4 text-orange-600" />
                            <h5 className="font-semibold text-gray-900">{story.story_title}</h5>
                          </div>
                          <p className="text-gray-700 text-sm mb-4">{story.description}</p>
                          
                          {story.acceptance_criteria.length > 0 && (
                            <div className="mb-4">
                              <h6 className="font-medium text-gray-800 mb-2 text-sm">Acceptance Criteria:</h6>
                              <ul className="space-y-1">
                                {story.acceptance_criteria.map((criteria, criteriaIndex) => (
                                  <li key={criteriaIndex} className="flex items-center space-x-2 text-sm">
                                    <Shield className="w-3 h-3 text-green-600" />
                                    <span className="text-gray-700">{criteria}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          
                          {story.tasks.length > 0 && (
                            <div>
                              <h6 className="font-medium text-gray-800 mb-2 text-sm">Tasks:</h6>
                              <div className="space-y-2">
                                {story.tasks.map((task, taskIndex) => (
                                  <div key={taskIndex} className="flex items-center justify-between bg-white rounded p-3 border border-gray-200">
                                    <div className="flex items-center space-x-2">
                                      <CheckSquare className="w-4 h-4 text-orange-600" />
                                      <span className="text-sm text-gray-700">{task.title}</span>
                                    </div>
                                    {task.estimated_hours && (
                                      <span className="bg-orange-100 text-orange-800 px-2 py-1 rounded text-xs font-medium">
                                        {task.estimated_hours}h
                                      </span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResultsDisplay;
