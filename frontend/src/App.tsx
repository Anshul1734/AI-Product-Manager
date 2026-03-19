/**
 * Enhanced App component with advanced UI and features.
 */
import React, { useState, useEffect } from 'react';
import {
  Brain,
  Menu,
  X,
  Settings,
  BarChart3,
  Database,
  Bell,
  Moon,
  Sun,
} from 'lucide-react';
import ProductIdeaForm from './components/ProductIdeaForm';
import ResultsDisplay from './components/ResultsDisplay';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorAlert from './components/ErrorAlert';
import Dashboard from './components/Dashboard';
import MemoryManagement from './components/MemoryManagement';
import { useWorkflow } from './hooks/useAdvancedApi';
import { useNotifications, useSettings } from './hooks/useAdvancedApi';
import { ProductIdeaRequest, EnhancedWorkflowState, Notification } from './types/advanced';
import { WorkflowOutput } from './types';

// Helper function to convert EnhancedWorkflowState to WorkflowOutput
const convertToWorkflowOutput = (enhanced: EnhancedWorkflowState): WorkflowOutput => {
  const plan = enhanced.plan || {} as any;
  const prd = enhanced.prd || {} as any;
  const architecture = enhanced.architecture || {} as any;
  const tickets = enhanced.tickets || {} as any;

  return {
    plan: {
      ...plan,
      target_users: plan.target_users || [],
      core_goals: plan.core_goals || [],
      key_features_high_level: plan.key_features_high_level || []
    },
    prd: {
      ...prd,
      user_personas: (prd.user_personas || []).map((p: any) => ({...p, pain_points: p.pain_points || []})),
      user_stories: prd.user_stories || [],
      success_metrics: prd.success_metrics || []
    },
    architecture: {
      ...architecture,
      tech_stack: architecture.tech_stack || {},
      api_endpoints: architecture.api_endpoints || [],
      architecture_components: architecture.architecture_components || [],
      database_schema: (architecture.database_schema || []).map((s: any) => ({...s, fields: s.fields || []}))
    },
    tickets: {
      ...tickets,
      epics: (tickets.epics || []).map((e: any) => ({
        ...e, 
        stories: (e.stories || []).map((s: any) => ({...s, acceptance_criteria: s.acceptance_criteria || [], tasks: s.tasks || []}))
      }))
    },
  };
};

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<'main' | 'dashboard' | 'memory' | 'settings'>('main');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  
  const {
    loading,
    error,
    results,
    executionTime,
    generateProductPlan,
  } = useWorkflow();
  
  const { notifications, addNotification, removeNotification, clearNotifications } = useNotifications();
  const { settings, updateSettings } = useSettings();
  
  const [clientId] = useState(`client-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);
  const [lastRequest, setLastRequest] = useState<ProductIdeaRequest | null>(null);

  // Auto-dismiss notifications
  useEffect(() => {
    const timer = setTimeout(() => {
      if (notifications.length > 0) {
        clearNotifications();
      }
    }, 5000);
    
    return () => clearTimeout(timer);
  }, [notifications, clearNotifications]);

  const handleSubmit = async (request: ProductIdeaRequest) => {
    setLastRequest(request);
    addNotification({
      type: 'info',
      title: 'Workflow Started',
      message: `Processing: ${request.idea.substring(0, 100)}${request.idea.length > 100 ? '...' : ''}`,
      auto_dismiss: true,
      timestamp: new Date().toISOString(),
    });
    
    try {
      await generateProductPlan(request);
      
      addNotification({
        type: 'success',
        title: 'Workflow Completed',
        message: 'Product plan generated successfully!',
        auto_dismiss: true,
        timestamp: new Date().toISOString(),
        actions: [
          {
            label: 'View Results',
            action: () => setCurrentView('main'),
          },
          {
            label: 'View Dashboard',
            action: () => setCurrentView('dashboard'),
          },
        ],
      });
    } catch (err) {
      addNotification({
        type: 'error',
        title: 'Workflow Failed',
        message: err instanceof Error ? err.message : 'An unexpected error occurred',
        auto_dismiss: false,
        timestamp: new Date().toISOString(),
        actions: [
          {
            label: 'Retry',
            action: () => handleSubmit(request),
          },
        ],
      });
    }
  };

  const handleClearError = () => {
    // Error clearing is handled by the hook
  };

  const toggleTheme = () => {
    const newTheme = settings.theme === 'light' ? 'dark' : 'light';
    updateSettings({ theme: newTheme });
  };

  const navigationItems = [
    {
      id: 'main',
      label: 'Product Planning',
      icon: Brain,
      description: 'Generate comprehensive product plans',
    },
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: BarChart3,
      description: 'System monitoring and analytics',
    },
    {
      id: 'memory',
      label: 'Memory Management',
      icon: Database,
      description: 'Manage conversation and agent memory',
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: Settings,
      description: 'Application preferences',
    },
  ];

  const renderCurrentView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard className="max-w-7xl mx-auto" />;
      case 'memory':
        return <MemoryManagement className="max-w-7xl mx-auto" />;
      case 'settings':
        return (
          <div className="max-w-4xl mx-auto p-6">
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-xl font-semibold text-gray-900">Settings</h2>
              </div>
              <div className="p-6 space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Appearance</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <span className="text-sm font-medium text-gray-700">Theme</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => updateSettings({ theme: 'light' })}
                          className={`p-2 rounded-md ${
                            settings.theme === 'light'
                              ? 'bg-primary-100 text-primary-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          <Sun className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => updateSettings({ theme: 'dark' })}
                          className={`p-2 rounded-md ${
                            settings.theme === 'dark'
                              ? 'bg-primary-100 text-primary-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          <Moon className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Notifications</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <span className="text-sm font-medium text-gray-700">Enable Notifications</span>
                      </div>
                      <button
                        onClick={() => updateSettings({ 
                          notifications: { ...settings.notifications, enabled: !settings.notifications.enabled }
                        })}
                        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ease-in-out duration-200 focus:outline-none ${
                          settings.notifications.enabled
                            ? 'bg-primary-600'
                            : 'bg-gray-200'
                        }`}
                      >
                        <span className={`translate-x-0 inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200 ${
                          settings.notifications.enabled ? 'translate-x-5' : 'translate-x-0'
                        }`} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      default:
        return (
          <div className="max-w-7xl mx-auto">
            {/* Product Idea Form */}
            <section>
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-gray-900 mb-4">
                  Transform Your Ideas into Reality
                </h2>
                <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                  Our AI-powered system analyzes your product idea and generates comprehensive plans, 
                  requirements, architecture, and development tickets with advanced memory and observability.
                </p>
              </div>
              
              <ProductIdeaForm
                onSubmit={handleSubmit}
                loading={loading}
                error={error || undefined}
                onClearError={handleClearError}
              />
            </section>

            {/* Loading State */}
            {loading && (
              <section>
                <ResultsDisplay 
                  results={convertToWorkflowOutput({} as EnhancedWorkflowState)} 
                  isLoading={true}
                />
              </section>
            )}

            {/* Results Display */}
            {results && !loading && (
              <section>
                <div className="text-center mb-8">
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">
                    Your Product Plan is Ready!
                  </h2>
                  <p className="text-gray-600">
                    Explore the comprehensive analysis below, organized into clear sections.
                  </p>
                </div>
                
                <ResultsDisplay 
                  results={convertToWorkflowOutput(results)} 
                  executionTime={executionTime || undefined}
                  originalIdea={lastRequest?.idea || undefined}
                  threadId={lastRequest?.thread_id || undefined}
                />
              </section>
            )}
          </div>
        );
    }
  };

  return (
    <div className={`min-h-screen ${settings.theme === 'dark' ? 'bg-gray-900' : 'bg-gradient-to-br from-blue-50 to-indigo-100'}`}>
      {/* Header */}
      <header className={`${settings.theme === 'dark' ? 'bg-gray-800' : 'bg-white'} shadow-sm border-b ${settings.theme === 'dark' ? 'border-gray-700' : 'border-gray-200'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo and Title */}
            <div className="flex items-center space-x-3">
              <Brain className={`w-8 h-8 ${settings.theme === 'dark' ? 'text-primary-400' : 'text-primary-600'}`} />
              <h1 className={`text-xl font-bold ${settings.theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
                AI Product Manager
              </h1>
            </div>
            
            {/* Navigation */}
            <nav className="hidden md:flex space-x-8">
              {navigationItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setCurrentView(item.id as any)}
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    currentView === item.id
                      ? `border-primary-500 ${settings.theme === 'dark' ? 'text-primary-400' : 'text-primary-600'}`
                      : `border-transparent ${settings.theme === 'dark' ? 'text-gray-300 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'} hover:border-gray-300`
                  }`}
                >
                  <item.icon className="h-5 w-5" />
                  <span className="ml-2">{item.label}</span>
                </button>
              ))}
            </nav>

            {/* Right side actions */}
            <div className="flex items-center space-x-4">
              {/* Notifications */}
              <div className="relative">
                <button
                  onClick={() => setShowNotifications(!showNotifications)}
                  className={`p-1 rounded-full ${settings.theme === 'dark' ? 'text-gray-300 hover:text-gray-200' : 'text-gray-400 hover:text-gray-600'}`}
                >
                  <Bell className="h-6 w-6" />
                  {notifications.length > 0 && (
                    <span className="absolute top-0 right-0 block h-2 w-2 rounded-full bg-red-500 ring-2 ring-white"></span>
                  )}
                </button>
                
                {/* Notifications Dropdown */}
                {showNotifications && notifications.length > 0 && (
                  <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg ring-1 ring-black ring-opacity-5 z-50">
                    <div className="py-1">
                      <div className="px-4 py-2 border-b border-gray-200">
                        <h3 className="text-sm font-medium text-gray-900">Notifications</h3>
                      </div>
                      <div className="max-h-64 overflow-y-auto">
                        {notifications.map((notification: Notification) => (
                          <div key={notification.id} className="px-4 py-3 hover:bg-gray-50">
                            <div className="flex items-start space-x-3">
                              <div className="flex-shrink-0">
                                {notification.type === 'success' && <div className="w-2 h-2 rounded-full bg-green-400"></div>}
                                {notification.type === 'error' && <div className="w-2 h-2 rounded-full bg-red-400"></div>}
                                {notification.type === 'warning' && <div className="w-2 h-2 rounded-full bg-yellow-400"></div>}
                                {notification.type === 'info' && <div className="w-2 h-2 rounded-full bg-blue-400"></div>}
                              </div>
                              <div className="flex-1">
                                <p className="text-sm text-gray-900">{notification.message}</p>
                                <p className="text-xs text-gray-500 mt-1">{notification.timestamp}</p>
                              </div>
                              <button
                                onClick={() => removeNotification(notification.id)}
                                className="flex-shrink-0 ml-2 text-gray-400 hover:text-gray-600"
                              >
                                <X className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Theme Toggle */}
              <button
                onClick={toggleTheme}
                className={`p-2 rounded-md ${settings.theme === 'dark' ? 'bg-gray-700 text-yellow-400' : 'bg-gray-100 text-gray-800'}`}
              >
                {settings.theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </button>

              {/* Mobile Menu */}
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className={`md:hidden p-2 rounded-md ${settings.theme === 'dark' ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-800'}`}
              >
                {sidebarOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile Sidebar */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)}></div>
          <div className={`relative flex-1 flex flex-col max-w-xs w-full ${settings.theme === 'dark' ? 'bg-gray-800' : 'bg-white'}`}>
            <div className="absolute top-0 right-0 pt-5 pb-4 sm:pt-6 sm:pb-6">
              <button
                onClick={() => setSidebarOpen(false)}
                className={`absolute top-5 right-5 -m-2.5 p-2 rounded-md ${settings.theme === 'dark' ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-800'}`}
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <div className="mt-6 space-y-1 px-2">
              {navigationItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    setCurrentView(item.id as any);
                    setSidebarOpen(false);
                  }}
                  className={`block w-full text-left px-3 py-2 rounded-md text-base font-medium ${
                    currentView === item.id
                      ? `bg-primary-100 ${settings.theme === 'dark' ? 'text-primary-400' : 'text-primary-600'}`
                      : `text-gray-700 hover:bg-gray-100 ${settings.theme === 'dark' ? 'hover:bg-gray-700' : ''}`
                  }`}
                >
                  <item.icon className="h-6 w-6 mr-3" />
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className={`${settings.theme === 'dark' ? 'text-white' : ''}`}>
        {renderCurrentView()}
      </main>

      {/* Footer */}
      <footer className={`${settings.theme === 'dark' ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} mt-16`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className={`text-center text-sm ${settings.theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
            <p>Powered by AI Product Manager Agent</p>
            <p className="mt-1">Advanced memory & observability enabled</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
