/**
 * Per-browser workspace id.
 *
 * Uploaded documents are scoped to this id on the server, so one visitor's
 * documents never ground another visitor's plans. There are no accounts: the
 * id is the only key to the workspace, so it lives in localStorage and is
 * generated with a cryptographic RNG. If storage is unavailable (private mode,
 * blocked site data) the id lasts for the page session instead.
 */
const STORAGE_KEY = 'aipm-workspace-id';

let cached: string | null = null;

const generate = (): string => {
  const bytes = new Uint8Array(16);
  window.crypto.getRandomValues(bytes);
  return 'ws_' + Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
};

export const getWorkspaceId = (): string => {
  if (cached) return cached;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && /^[A-Za-z0-9_-]{6,64}$/.test(stored)) {
      cached = stored;
      return stored;
    }
  } catch {
    /* storage blocked; fall through to a session-only id */
  }
  cached = generate();
  try {
    window.localStorage.setItem(STORAGE_KEY, cached);
  } catch {
    /* keep the in-memory id */
  }
  return cached;
};
