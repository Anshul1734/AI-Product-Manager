/**
 * Backend client.
 *
 * `streamPlan` reads the Server-Sent Events endpoint with fetch + a stream
 * reader rather than `EventSource`, because EventSource cannot issue a POST and
 * the idea has to travel in the request body.
 */
import { API_V1 } from '../config';
import { getWorkspaceId } from './workspace';
import type {
  Depth,
  DocumentLibraryStatus,
  HealthResponse,
  KnowledgeSearchResponse,
  PlanPayload,
  StreamEvent,
  UploadedDocument,
  ValidationResult,
  WorkflowResponse,
} from '../types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_V1}${path}`, {
    // A FormData body must set its own multipart boundary header.
    headers: init?.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
    ...init,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      // FastAPI request-validation errors carry a list of {msg} objects.
      detail = Array.isArray(body.detail)
        ? body.detail.map((item: { msg?: string }) => item.msg).join('; ')
        : body.detail || body.message || detail;
    } catch {
      /* non-JSON error body; keep the status line */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>('/health'),

  pipeline: () => request<{ success: boolean; data: Record<string, unknown> }>('/pipeline'),

  validateIdea: (idea: string) =>
    request<ValidationResult>('/validate', { method: 'POST', body: JSON.stringify({ idea }) }),

  searchKnowledge: (query: string, k = 5, domain?: string) =>
    request<KnowledgeSearchResponse>('/knowledge/search', {
      method: 'POST',
      body: JSON.stringify({ query, k, domain: domain || null, workspace_id: getWorkspaceId() }),
    }),

  knowledgeDocuments: () =>
    request<{ success: boolean; data: { documents: { doc_id: string; title: string; domain: string }[]; domains: string[]; chunk_count: number; dense_enabled: boolean } }>(
      '/knowledge/documents',
    ),

  /** Documents this browser has uploaded, or why uploads are unavailable. */
  listDocuments: () =>
    request<{ success: boolean; data: DocumentLibraryStatus }>(
      `/documents?workspace_id=${encodeURIComponent(getWorkspaceId())}`,
    ),

  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    form.append('workspace_id', getWorkspaceId());
    return request<{ success: boolean; message: string; data: { document: UploadedDocument } }>('/documents', {
      method: 'POST',
      body: form,
    });
  },

  deleteDocument: (docId: string) =>
    request<{ success: boolean }>(
      `/documents/${encodeURIComponent(docId)}?workspace_id=${encodeURIComponent(getWorkspaceId())}`,
      { method: 'DELETE' },
    ),

  generate: (idea: string, depth: Depth, threadId?: string) =>
    request<WorkflowResponse>('/generate', {
      method: 'POST',
      body: JSON.stringify({ idea, depth, thread_id: threadId ?? null, workspace_id: getWorkspaceId() }),
    }),

  /** Stream a run, invoking `onEvent` for each server event. */
  async streamPlan(
    idea: string,
    depth: Depth,
    onEvent: (event: StreamEvent) => void,
    signal?: AbortSignal,
    threadId?: string,
  ): Promise<PlanPayload> {
    const response = await fetch(`${API_V1}/generate/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify({ idea, depth, thread_id: threadId ?? null, workspace_id: getWorkspaceId() }),
      signal,
    });

    if (!response.ok || !response.body) {
      throw new Error(`Stream failed: ${response.status} ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let result: PlanPayload | null = null;
    let failure: string | null = null;

    // SSE frames are separated by a blank line and can be split across chunks,
    // so the tail of the buffer is carried forward until a separator arrives.
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      buffer = frames.pop() ?? '';

      for (const frame of frames) {
        const line = frame.split('\n').find((candidate) => candidate.startsWith('data:'));
        if (!line) continue; // comment frame, e.g. the keep-alive

        try {
          const event = JSON.parse(line.slice(5).trim()) as StreamEvent;
          onEvent(event);
          if (event.type === 'complete') result = event.data;
          if (event.type === 'error') failure = event.message;
        } catch {
          /* ignore a malformed frame rather than aborting the run */
        }
      }
    }

    if (failure) throw new Error(failure);
    if (!result) throw new Error('The run ended without returning a plan.');
    return result;
  },

  /** Download an export. The plan travels in the body; nothing is regenerated. */
  async download(kind: 'markdown' | 'csv' | 'json', plan: PlanPayload, idea?: string): Promise<void> {
    const path = {
      markdown: '/export/prd/markdown',
      csv: '/export/tickets/csv',
      json: '/export/full/json',
    }[kind];

    const response = await fetch(`${API_V1}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan, idea: idea ?? null }),
    });

    if (!response.ok) {
      let detail = `Export failed (${response.status})`;
      try {
        detail = (await response.json()).detail || detail;
      } catch {
        /* keep the status line */
      }
      throw new Error(detail);
    }

    const blob = await response.blob();
    const filename =
      response.headers.get('content-disposition')?.match(/filename="?([^"]+)"?/)?.[1] ??
      `product-plan.${kind === 'markdown' ? 'md' : kind}`;

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  },
};
