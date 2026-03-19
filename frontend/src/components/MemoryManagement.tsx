/**
 * Memory Management component for advanced memory operations.
 */
import React, { useState, useEffect } from 'react';
import {
  Database,
  Search,
  Trash2,
  Download,
  Plus,
  Filter,
  Clock,
  User,
  Brain,
  BarChart3,
} from 'lucide-react';
import { useMemory } from '../hooks/useAdvancedApi';
import { ConversationTurn, AgentState, AgentLearning, MemoryStats } from '../types/advanced';

interface MemoryManagementProps {
  className?: string;
}

const MemoryManagement: React.FC<MemoryManagementProps> = ({ className = '' }) => {
  const {
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
  } = useMemory();

  const [activeTab, setActiveTab] = useState<'overview' | 'conversations' | 'search' | 'analytics'>('overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedThread, setSelectedThread] = useState<string>('');
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newConversation, setNewConversation] = useState({
    threadId: '',
    userInput: '',
    agentResponse: '',
    agentName: '',
  });

  useEffect(() => {
    loadMemoryStats();
  }, [loadMemoryStats]);

  const handleSearch = () => {
    if (searchQuery.trim()) {
      searchMemory(searchQuery, {
        thread_id: selectedThread || undefined,
        agent_name: selectedAgent || undefined,
      });
    }
  };

  const handleAddConversation = async () => {
    if (newConversation.threadId && newConversation.userInput && newConversation.agentResponse && newConversation.agentName) {
      await addConversationTurn(
        newConversation.threadId,
        newConversation.userInput,
        newConversation.agentResponse,
        newConversation.agentName
      );
      setNewConversation({ threadId: '', userInput: '', agentResponse: '', agentName: '' });
      setShowAddDialog(false);
      loadMemoryStats();
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (loading && !stats) {
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
      {/* Header */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Memory Management</h2>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setShowAddDialog(true)}
                className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Conversation
              </button>
              <button
                onClick={cleanupMemory}
                className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Cleanup
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow mt-6">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            {[
              { key: 'overview', label: 'Overview', icon: Database },
              { key: 'conversations', label: 'Conversations', icon: User },
              { key: 'search', label: 'Search', icon: Search },
              { key: 'analytics', label: 'Analytics', icon: BarChart3 },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.key
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <tab.icon className="h-5 w-5 mr-2" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && stats && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div className="bg-gray-50 rounded-lg p-6">
                  <div className="flex items-center">
                    <Database className="h-8 w-8 text-primary-600" />
                    <div className="ml-4">
                      <h3 className="text-lg font-medium text-gray-900">Total Documents</h3>
                      <p className="mt-2 text-3xl font-semibold text-gray-900">
                        {stats.vector_store?.total_documents || 0}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-6">
                  <div className="flex items-center">
                    <User className="h-8 w-8 text-blue-600" />
                    <div className="ml-4">
                      <h3 className="text-lg font-medium text-gray-900">Active Threads</h3>
                      <p className="mt-2 text-3xl font-semibold text-gray-900">
                        {stats.conversation_memory?.thread_count || 0}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-6">
                  <div className="flex items-center">
                    <Brain className="h-8 w-8 text-green-600" />
                    <div className="ml-4">
                      <h3 className="text-lg font-medium text-gray-900">Agent States</h3>
                      <p className="mt-2 text-3xl font-semibold text-gray-900">
                        {stats.agent_memory?.total_agents || 0}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Memory Statistics</h3>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <h4 className="text-base font-medium text-gray-900">Vector Store</h4>
                      <div className="mt-2 space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Dimension:</span>
                          <span className="font-medium">{stats.vector_store?.dimension || 0}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Index Size:</span>
                          <span className="font-medium">{stats.vector_store?.index_size || 0}</span>
                        </div>
                      </div>
                    </div>

                    <div>
                      <h4 className="text-base font-medium text-gray-900">Conversation Memory</h4>
                      <div className="mt-2 space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Total Turns:</span>
                          <span className="font-medium">{stats.conversation_memory?.total_conversation_turns || 0}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Max Age (days):</span>
                          <span className="font-medium">{stats.conversation_memory?.max_age_days || 0}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Conversations Tab */}
          {activeTab === 'conversations' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">Conversation Threads</h3>
                <div className="flex items-center space-x-3">
                  <select
                    value={selectedThread}
                    onChange={(e) => setSelectedThread(e.target.value)}
                    className="text-sm border-gray-300 rounded-md"
                  >
                    <option value="">All Threads</option>
                    {Object.entries((stats?.conversation_memory?.vector_store_stats?.threads) || {}).map(([threadId, count]: [string, any]) => (
                      <option key={threadId} value={threadId}>
                        Thread {threadId} ({count} items)
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => loadMemoryStats()}
                    className="text-sm text-primary-600 hover:text-primary-800"
                  >
                    Refresh
                  </button>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-center text-gray-500 py-8">
                  <Database className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                  <p>Conversation details will be displayed here</p>
                  <p className="text-sm mt-2">Thread-based conversation history and context management</p>
                </div>
              </div>
            </div>
          )}

          {/* Search Tab */}
          {activeTab === 'search' && (
            <div className="space-y-4">
              <div className="flex items-center space-x-4 mb-6">
                <div className="flex-1">
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Search className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                      placeholder="Search memory..."
                      className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    />
                  </div>
                </div>
                <button
                  onClick={handleSearch}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  Search
                </button>
              </div>

              <div className="flex items-center space-x-4 mb-4">
                <select
                  value={selectedThread}
                  onChange={(e) => setSelectedThread(e.target.value)}
                  className="text-sm border-gray-300 rounded-md"
                >
                  <option value="">All Threads</option>
                  <option value="planner">Planner</option>
                  <option value="analyst">Analyst</option>
                  <option value="architect">Architect</option>
                  <option value="ticket_generator">Ticket Generator</option>
                </select>
                <select
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value)}
                  className="text-sm border-gray-300 rounded-md"
                >
                  <option value="">All Agents</option>
                  <option value="planner">Planner</option>
                  <option value="analyst">Analyst</option>
                  <option value="architect">Architect</option>
                  <option value="ticket_generator">Ticket Generator</option>
                </select>
              </div>

              {searchResults && (
                <div className="bg-white rounded-lg border border-gray-200">
                  <div className="px-4 py-3 border-b border-gray-200">
                    <h4 className="text-base font-medium text-gray-900">Search Results</h4>
                  </div>
                  <div className="p-4">
                    <div className="space-y-3">
                      {searchResults.conversations && searchResults.conversations.length > 0 && (
                        <div>
                          <h5 className="text-sm font-medium text-gray-900 mb-2">Conversations</h5>
                          {searchResults.conversations.map((conv: ConversationTurn, index: number) => (
                            <div key={index} className="p-3 bg-gray-50 rounded-lg">
                              <div className="flex items-start space-x-3">
                                <User className="h-5 w-5 text-blue-500 mt-1" />
                                <div className="flex-1">
                                  <p className="text-sm text-gray-900">
                                    <strong>User:</strong> {conv.user_input}
                                  </p>
                                  <p className="text-sm text-gray-600 mt-1">
                                    <strong>{conv.agent_name}:</strong> {conv.agent_response}
                                  </p>
                                  <p className="text-xs text-gray-500 mt-1">
                                    {formatDate(conv.timestamp)} • Similarity: {conv.similarity?.toFixed(2) || 'N/A'}
                                  </p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {searchResults.agent_memory && searchResults.agent_memory.length > 0 && (
                        <div className="mt-4">
                          <h5 className="text-sm font-medium text-gray-900 mb-2">Agent Memory</h5>
                          {searchResults.agent_memory.map((mem: any, index: number) => (
                            <div key={index} className="p-3 bg-blue-50 rounded-lg">
                              <div className="flex items-start space-x-3">
                                <Brain className="h-5 w-5 text-blue-500 mt-1" />
                                <div className="flex-1">
                                  <p className="text-sm text-gray-900">
                                    <strong>Type:</strong> {mem.type}
                                  </p>
                                  <p className="text-sm text-gray-600 mt-1">
                                    {mem.content?.substring(0, 200)}...
                                  </p>
                                  <p className="text-xs text-gray-500 mt-1">
                                    Similarity: {mem.similarity?.toFixed(2) || 'N/A'}
                                  </p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Analytics Tab */}
          {activeTab === 'analytics' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Memory Usage</h3>
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-base font-medium text-gray-900">Storage Breakdown</h4>
                      <div className="mt-2">
                        <div className="space-y-2">
                          {Object.entries((stats?.conversation_memory?.vector_store_stats?.threads) || {}).map(([threadId, count]: [string, any]) => (
                            <div key={threadId} className="flex justify-between items-center">
                              <span className="text-sm text-gray-600">Thread {threadId}:</span>
                              <span className="text-sm font-medium">{count} items</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Agent Performance</h3>
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-base font-medium text-gray-900">Agent States</h4>
                      <div className="mt-2">
                        <div className="space-y-2">
                          {Object.entries(stats?.agent_memory?.agent_stats || {}).map(([agentName, stats]: [string, any]) => (
                            <div key={agentName} className="flex justify-between items-center">
                              <span className="text-sm text-gray-600 capitalize">{agentName}:</span>
                              <div className="text-sm text-gray-900">
                                <span className="font-medium">{stats.state_count} states</span> • 
                                <span className="text-blue-600">{stats.learning_count} learning items</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add Conversation Dialog */}
      {showAddDialog && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full z-50">
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">Add Conversation Turn</h3>
                <button
                  onClick={() => setShowAddDialog(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ×
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Thread ID</label>
                  <input
                    type="text"
                    value={newConversation.threadId}
                    onChange={(e) => setNewConversation({...newConversation, threadId: e.target.value})}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    placeholder="thread-123"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">User Input</label>
                  <textarea
                    value={newConversation.userInput}
                    onChange={(e) => setNewConversation({...newConversation, userInput: e.target.value})}
                    rows={3}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    placeholder="User's input or question..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Agent Response</label>
                  <textarea
                    value={newConversation.agentResponse}
                    onChange={(e) => setNewConversation({...newConversation, agentResponse: e.target.value})}
                    rows={3}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    placeholder="Agent's response..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Agent Name</label>
                  <select
                    value={newConversation.agentName}
                    onChange={(e) => setNewConversation({...newConversation, agentName: e.target.value})}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  >
                    <option value="">Select Agent</option>
                    <option value="planner">Planner</option>
                    <option value="analyst">Analyst</option>
                    <option value="architect">Architect</option>
                    <option value="ticket_generator">Ticket Generator</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowAddDialog(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddConversation}
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  Add Conversation
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MemoryManagement;
