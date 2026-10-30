/**
 * The user's own documents: upload, list, delete.
 *
 * Uploaded files are parsed, chunked, embedded and stored in the vector
 * database under this browser's workspace id. Every plan run and knowledge
 * search from this browser then retrieves from them alongside the curated
 * product-management corpus, and cites them as "Your document".
 */
import React from 'react';
import { AlertCircle, FileText, FolderOpen, Loader2, Trash2, Upload } from 'lucide-react';
import type { DocumentLibraryStatus, UploadedDocument } from '../types';
import { api } from '../lib/api';
import { Badge, Card, SectionTitle, cx } from './ui/Primitives';

interface PendingUpload {
  id: string;
  name: string;
  status: 'uploading' | 'failed';
  error?: string;
}

const formatBytes = (bytes: number) =>
  bytes < 1024 ? `${bytes} B` : bytes < 1_048_576 ? `${(bytes / 1024).toFixed(0)} KB` : `${(bytes / 1_048_576).toFixed(1)} MB`;

const extensionOf = (name: string) => {
  const dot = name.lastIndexOf('.');
  return dot >= 0 ? name.slice(dot).toLowerCase() : '';
};

const DocumentLibrary: React.FC<{ className?: string }> = ({ className }) => {
  const [status, setStatus] = React.useState<DocumentLibraryStatus | null>(null);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [pending, setPending] = React.useState<PendingUpload[]>([]);
  const [deleting, setDeleting] = React.useState<string | null>(null);
  const [dragging, setDragging] = React.useState(false);
  const [notice, setNotice] = React.useState<string | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const refresh = React.useCallback(async () => {
    try {
      const response = await api.listDocuments();
      setStatus(response.data);
      setLoadError(null);
    } catch (cause) {
      setLoadError(cause instanceof Error ? cause.message : 'Could not load your documents');
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const upload = async (files: FileList | File[]) => {
    if (!status?.enabled) return;
    setNotice(null);

    // Sequential, not parallel: each upload is embedded server-side, and a
    // burst of parallel embedding calls is what trips provider rate limits.
    for (const file of Array.from(files)) {
      const id = `${file.name}-${file.size}-${Date.now()}`;
      const reject = (error: string) =>
        setPending((items) => [...items.filter((item) => item.id !== id), { id, name: file.name, status: 'failed', error }]);

      if (!status.supported_extensions.includes(extensionOf(file.name))) {
        reject(`Unsupported type. Use ${status.supported_extensions.join(', ')}`);
        continue;
      }
      if (file.size > status.max_bytes) {
        reject(`Larger than the ${formatBytes(status.max_bytes)} limit`);
        continue;
      }

      setPending((items) => [...items, { id, name: file.name, status: 'uploading' }]);
      try {
        const response = await api.uploadDocument(file);
        setPending((items) => items.filter((item) => item.id !== id));
        setNotice(response.message);
        await refresh();
      } catch (cause) {
        reject(cause instanceof Error ? cause.message : 'Upload failed');
      }
    }
  };

  const remove = async (document: UploadedDocument) => {
    setDeleting(document.doc_id);
    try {
      await api.deleteDocument(document.doc_id);
      setNotice(`Removed '${document.filename}'`);
      await refresh();
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : 'Delete failed');
    } finally {
      setDeleting(null);
    }
  };

  const documents = status?.documents ?? [];
  const busy = pending.some((item) => item.status === 'uploading');
  const atLimit = status ? documents.length >= status.max_documents : false;

  return (
    <Card className={className}>
      <SectionTitle
        title="Your documents"
        icon={<FolderOpen className="h-3.5 w-3.5" />}
        hint={
          status?.enabled
            ? 'Research, interview notes, specs, constraints. Every plan and search from this browser draws on them alongside the product-management corpus, and cites them.'
            : undefined
        }
        action={documents.length > 0 ? <Badge tone="accent">{documents.length} in use</Badge> : undefined}
      />

      {loadError && (
        <p className="flex items-start gap-2 text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {loadError}
        </p>
      )}

      {!status && !loadError && (
        <p className="flex items-center gap-2 text-sm text-zinc-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </p>
      )}

      {status && !status.enabled && (
        <p className="rounded-lg border border-dashed border-zinc-300 px-4 py-3 text-sm text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">
          Document upload is not available on this server. {status.reason}
        </p>
      )}

      {status?.enabled && (
        <>
          <button
            type="button"
            disabled={atLimit}
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              if (event.dataTransfer.files.length) upload(event.dataTransfer.files);
            }}
            className={cx(
              'flex w-full flex-col items-center gap-1.5 rounded-lg border border-dashed px-4 py-6 text-center transition-colors',
              dragging
                ? 'border-accent-400 bg-accent-50 dark:border-accent-600 dark:bg-accent-950/40'
                : 'border-zinc-300 hover:border-accent-300 dark:border-zinc-700 dark:hover:border-accent-700',
              atLimit && 'cursor-not-allowed opacity-60',
            )}
          >
            {busy ? (
              <Loader2 className="h-5 w-5 animate-spin text-accent-500" />
            ) : (
              <Upload className="h-5 w-5 text-zinc-400" />
            )}
            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-200">
              {atLimit ? `Limit of ${status.max_documents} documents reached` : 'Drop files here, or click to choose'}
            </span>
            <span className="text-2xs text-zinc-500 dark:text-zinc-400">
              {status.supported_extensions.join(' ')} · up to {formatBytes(status.max_bytes)} each
            </span>
          </button>
          <input
            ref={inputRef}
            type="file"
            multiple
            hidden
            accept={status.supported_extensions.join(',')}
            onChange={(event) => {
              if (event.target.files?.length) upload(event.target.files);
              event.target.value = '';
            }}
          />

          {notice && <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">{notice}</p>}

          {(pending.length > 0 || documents.length > 0) && (
            <ul className="mt-3 divide-y divide-zinc-100 dark:divide-zinc-800/70">
              {pending.map((item) => (
                <li key={item.id} className="flex items-center gap-3 py-2">
                  {item.status === 'uploading' ? (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-accent-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm text-zinc-800 dark:text-zinc-200">{item.name}</div>
                    <div className={cx('text-2xs', item.error ? 'text-red-600 dark:text-red-400' : 'text-zinc-500')}>
                      {item.error ?? 'Reading, chunking and embedding…'}
                    </div>
                  </div>
                  {item.status === 'failed' && (
                    <button
                      type="button"
                      onClick={() => setPending((items) => items.filter((entry) => entry.id !== item.id))}
                      className="btn btn-ghost btn-sm"
                    >
                      Dismiss
                    </button>
                  )}
                </li>
              ))}
              {documents.map((document) => (
                <li key={document.doc_id} className="flex items-center gap-3 py-2">
                  <FileText className="h-4 w-4 shrink-0 text-zinc-400" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm text-zinc-800 dark:text-zinc-200">{document.filename}</div>
                    <div className="tabular text-2xs text-zinc-500 dark:text-zinc-400">
                      {document.chunk_count} passages · {formatBytes(document.size_bytes)} ·{' '}
                      {new Date(document.uploaded_at).toLocaleDateString()}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => remove(document)}
                    disabled={deleting === document.doc_id}
                    className="btn btn-ghost btn-sm"
                    aria-label={`Delete ${document.filename}`}
                  >
                    {deleting === document.doc_id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="h-3.5 w-3.5" />
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Card>
  );
};

export default DocumentLibrary;
