/**
 * API base URL.
 *
 * In production the frontend and API are served from the same origin (or the
 * host is supplied at build time), so the default is a relative path. Locally
 * the backend runs on 8001 while CRA serves 3000.
 *
 * Trailing slashes are stripped: `${API_BASE}/api/v1/...` would otherwise
 * produce a double slash and a 404 on some hosts.
 */
const raw = process.env.REACT_APP_API_URL ?? (process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8001');

export const API_BASE = raw.replace(/\/+$/, '');
export const API_V1 = `${API_BASE}/api/v1`;
