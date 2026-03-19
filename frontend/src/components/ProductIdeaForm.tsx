import React, { useState } from 'react';
import { Send, Sparkles, MessageSquare, Settings, Users } from 'lucide-react';
import { ProductIdeaRequest } from '../types';
import ErrorAlert from './ErrorAlert';

interface ProductIdeaFormProps {
  onSubmit: (request: ProductIdeaRequest) => void;
  loading?: boolean;
  error?: string;
  onClearError?: () => void;
}

const ProductIdeaForm: React.FC<ProductIdeaFormProps> = ({
  onSubmit,
  loading = false,
  error,
  onClearError,
}) => {
  const [productIdea, setProductIdea] = useState('');
  const [threadId, setThreadId] = useState('');
  const [useLegacy, setUseLegacy] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!productIdea.trim()) return;

    const request: ProductIdeaRequest = {
      idea: productIdea.trim(),
      thread_id: threadId.trim() || undefined,
      use_legacy: useLegacy,
    };

    onSubmit(request);
  };

  const handleClearError = () => {
    if (onClearError) {
      onClearError();
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8">
          <div className="mb-6">
            <label htmlFor="product-idea" className="flex items-center space-x-2 text-lg font-semibold text-gray-900 mb-3">
              <MessageSquare className="w-5 h-5 text-blue-600" />
              <span>Product Idea</span>
            </label>
            <textarea
              id="product-idea"
              value={productIdea}
              onChange={(e) => setProductIdea(e.target.value)}
              placeholder="Describe your product idea in detail. What problem does it solve? Who is it for? What makes it unique?"
              className="textarea w-full h-32 resize-none"
              disabled={loading}
            />
            <p className="mt-2 text-sm text-gray-500">
              Be specific about the problem, target users, and key features for better results.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="thread-id" className="flex items-center space-x-2 text-sm font-semibold text-gray-900 mb-3">
                <Users className="w-4 h-4 text-green-600" />
                <span>Thread ID (Optional)</span>
              </label>
              <input
                id="thread-id"
                type="text"
                value={threadId}
                onChange={(e) => setThreadId(e.target.value)}
                placeholder="conversation-id-123"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
              <p className="mt-2 text-sm text-gray-500">
                Use for conversation memory across requests
              </p>
            </div>

            <div className="flex items-center space-x-3 pt-6">
              <input
                id="use-legacy"
                type="checkbox"
                checked={useLegacy}
                onChange={(e) => setUseLegacy(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={loading}
              />
              <label htmlFor="use-legacy" className="text-sm font-medium text-gray-700">
                Use Legacy Mode
              </label>
            </div>
          </div>
        </div>

        {error && (
          <ErrorAlert
            message={error}
            onDismiss={handleClearError}
          />
        )}

        <div className="flex justify-center">
          <button
            type="submit"
            disabled={loading || !productIdea.trim()}
            className="flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium px-8 py-3 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
          >
            {loading ? (
              <>
                <Sparkles className="w-5 h-5 animate-spin" />
                <span>Generating...</span>
              </>
            ) : (
              <>
                <Send className="w-5 h-5" />
                <span>Generate Product Plan</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ProductIdeaForm;
