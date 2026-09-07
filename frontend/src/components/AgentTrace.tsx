/**
 * Live view of the agent graph executing.
 *
 * This is the difference between "a spinner ran for two minutes" and being able
 * to see which specialist is working, which tool it reached for, and where a
 * schema repair was needed.
 */
import React from 'react';
import {
  AlertCircle,
  BookOpen,
  Boxes,
  Calculator,
  Check,
  ChevronRight,
  Database,
  FileText,
  Loader2,
  MinusCircle,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Wrench,
} from 'lucide-react';
import type { TraceEntry } from '../types';
import { Badge, cx } from './ui/Primitives';

const NODE_ICONS: Record<string, React.ReactNode> = {
  retrieve: <Search className="h-3.5 w-3.5" />,
  planner: <Sparkles className="h-3.5 w-3.5" />,
  analyst: <FileText className="h-3.5 w-3.5" />,
  prioritizer: <Calculator className="h-3.5 w-3.5" />,
  architect: <Boxes className="h-3.5 w-3.5" />,
  ticket_generator: <Database className="h-3.5 w-3.5" />,
  critic: <ShieldCheck className="h-3.5 w-3.5" />,
  refine: <RefreshCw className="h-3.5 w-3.5" />,
};

const TOOL_ICONS: Record<string, React.ReactNode> = {
  search_pm_knowledge: <BookOpen className="h-3 w-3" />,
  score_features_rice: <Calculator className="h-3 w-3" />,
  recall_similar_plans: <Database className="h-3 w-3" />,
};

const TOOL_LABELS: Record<string, string> = {
  search_pm_knowledge: 'Searched knowledge base',
  score_features_rice: 'Computed RICE scores',
  recall_similar_plans: 'Recalled past plans',
};

const StatusMark: React.FC<{ status: TraceEntry['status'] }> = ({ status }) => {
  if (status === 'running') {
    return (
      <span className="relative flex h-6 w-6 items-center justify-center">
        <span className="absolute inset-0 rounded-full bg-accent-500/25 animate-pulse-ring" />
        <Loader2 className="h-3.5 w-3.5 animate-spin text-accent-600 dark:text-accent-400" />
      </span>
    );
  }
  if (status === 'done') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-950/60">
        <Check className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-red-100 dark:bg-red-950/60">
        <AlertCircle className="h-3.5 w-3.5 text-red-600 dark:text-red-400" />
      </span>
    );
  }
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800">
      <MinusCircle className="h-3.5 w-3.5 text-zinc-400 dark:text-zinc-500" />
    </span>
  );
};

interface Props {
  entries: TraceEntry[];
  elapsed: number;
  running: boolean;
  className?: string;
}

const AgentTrace: React.FC<Props> = ({ entries, elapsed, running, className }) => {
  if (!entries.length) return null;

  const done = entries.filter((entry) => entry.status === 'done').length;
  const total = entries.length;

  return (
    <div className={cx('surface overflow-hidden', className)}>
      <div className="flex items-center justify-between gap-3 border-b border-zinc-200 px-5 py-3.5 dark:border-zinc-800">
        <div className="flex items-center gap-2.5">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Agent pipeline</h3>
          {running ? (
            <Badge tone="accent">
              <Loader2 className="h-2.5 w-2.5 animate-spin" />
              Running
            </Badge>
          ) : (
            <Badge tone="success">Complete</Badge>
          )}
        </div>
        <span className="tabular text-xs text-zinc-500 dark:text-zinc-400">
          {done}/{total} · {elapsed.toFixed(0)}s
        </span>
      </div>

      <ol className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
        {entries.map((entry) => (
          <li key={entry.node} className="animate-fade-in px-5 py-3">
            <div className="flex items-start gap-3">
              <StatusMark status={entry.status} />

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className="text-zinc-400 dark:text-zinc-500">{NODE_ICONS[entry.node]}</span>
                  <span
                    className={cx(
                      'text-sm font-medium',
                      entry.status === 'skipped'
                        ? 'text-zinc-400 dark:text-zinc-500'
                        : 'text-zinc-800 dark:text-zinc-200',
                    )}
                  >
                    {entry.label}
                  </span>
                  {entry.duration !== undefined && (
                    <span className="tabular text-2xs text-zinc-400 dark:text-zinc-500">
                      {entry.duration.toFixed(1)}s
                    </span>
                  )}
                  {entry.repairs > 0 && (
                    <Badge tone="warning">
                      <RefreshCw className="h-2.5 w-2.5" />
                      {entry.repairs} schema {entry.repairs === 1 ? 'repair' : 'repairs'}
                    </Badge>
                  )}
                  {entry.status === 'skipped' && <Badge>skipped at this depth</Badge>}
                </div>

                {entry.tools.length > 0 && (
                  <ul className="mt-1.5 space-y-1">
                    {entry.tools.map((tool, index) => (
                      <li
                        key={index}
                        className="flex items-start gap-1.5 text-xs text-zinc-500 dark:text-zinc-400"
                      >
                        <ChevronRight className="mt-0.5 h-3 w-3 shrink-0 text-zinc-300 dark:text-zinc-600" />
                        <span className="shrink-0 text-zinc-400 dark:text-zinc-500">
                          {TOOL_ICONS[tool.tool] ?? <Wrench className="h-3 w-3" />}
                        </span>
                        <span className="min-w-0">
                          <span className={cx(!tool.ok && 'text-amber-600 dark:text-amber-400')}>
                            {TOOL_LABELS[tool.tool] ?? tool.tool}
                          </span>
                          {tool.summary && (
                            <span className="text-zinc-400 dark:text-zinc-500"> · “{tool.summary}”</span>
                          )}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}

                {entry.error && (
                  <p className="mt-1.5 text-xs leading-relaxed text-red-600 dark:text-red-400">{entry.error}</p>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
};

export default AgentTrace;
