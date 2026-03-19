import { useEffect, useRef, useState, useCallback } from 'react';
import WebSocketService from '../services/websocket';
import { WebSocketMessage } from '../types';

export const useWebSocket = (clientId: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const wsRef = useRef<WebSocketService | null>(null);

  const connect = useCallback(async () => {
    try {
      if (!wsRef.current) {
        wsRef.current = new WebSocketService(clientId);
        
        // Set up event handlers
        wsRef.current.onConnection((connected) => {
          setIsConnected(connected);
        });

        wsRef.current.onMessage('workflow_step', (message) => {
          setMessages(prev => [...prev, message]);
        });

        wsRef.current.onMessage('workflow_completed', (message) => {
          setMessages(prev => [...prev, message]);
        });

        wsRef.current.onMessage('workflow_error', (message) => {
          setMessages(prev => [...prev, message]);
        });

        wsRef.current.onMessage('error', (message) => {
          setMessages(prev => [...prev, message]);
        });

        await wsRef.current.connect();
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setIsConnected(false);
    }
  }, [clientId]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
      setIsConnected(false);
    }
  }, []);

  const sendMessage = useCallback((message: Partial<WebSocketMessage>) => {
    if (wsRef.current) {
      wsRef.current.sendMessage(message);
    }
  }, []);

  const executeWorkflow = useCallback((productIdea: string, threadId?: string) => {
    if (wsRef.current) {
      wsRef.current.executeWorkflow(productIdea, threadId);
    }
  }, []);

  const ping = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.ping();
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    messages,
    connect,
    disconnect,
    sendMessage,
    executeWorkflow,
    ping,
    clearMessages,
  };
};
