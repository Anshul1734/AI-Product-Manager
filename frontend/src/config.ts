/**
 * Central configuration for AI Product Manager frontend.
 */
// Use Vercel's injected environment variable or fallback to local port
export const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

export const WS_BASE_URL = "ws://localhost:8001";

export const API_ENDPOINTS = {
  GENERATE: `${API_BASE_URL}/api/v1/generate`,
  HEALTH: `${API_BASE_URL}/api/v1/health`,
  MEMORY: `${API_BASE_URL}/api/v1/memory`,
  AGENTS: `${API_BASE_URL}/api/v1/agents`,
  OBSERVABILITY: `${API_BASE_URL}/api/v1/observability`
} as const;
