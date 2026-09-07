import React from 'react';
import {
  Boxes,
  Calculator,
  Download,
  FileJson,
  FileText,
  KanbanSquare,
  Library,
  Printer,
  ShieldCheck,
  Sparkles,
  Table,
} from 'lucide-react';
import type { PlanPayload } from '../types';
import { api } from '../lib/api';
import ArchitecturePanel from './panels/ArchitecturePanel';
import BacklogPanel from './panels/BacklogPanel';
import OverviewPanel from './panels/OverviewPanel';
import PrdPanel from './panels/PrdPanel';
import QualityPanel from './panels/QualityPanel';
import RoadmapPanel from './panels/RoadmapPanel';
import SourcesPanel from './panels/SourcesPanel';
import { Badge, cx } from './ui/Primitives';

type TabId = 'overview' | 'prd' | 'roadmap' | 'architecture' | 'backlog' | 'quality' | 'sources';

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <Sparkles className="h-3.5 w-3.5" /> },
  { id: 'prd', label: 'PRD', icon: <FileText className="h-3.5 w-3.5" /> },
  { id: 'roadmap', label: 'Roadmap', icon: <Calculator className="h-3.5 w-3.5" /> },
  { id: 'architecture', label: 'Architecture', icon: <Boxes className="h-3.5 w-3.5" /> },
  { id: 'backlog', label: 'Backlog', icon: <KanbanSquare className="h-3.5 w-3.5" /> },
  { id: 'quality', label: 'Review', icon: <ShieldCheck className="h-3.5 w-3.5" /> },
  { id: 'sources', label: 'Provenance', icon: <Library className="h-3.5 w-3.5" /> },
];

const ResultsView: React.FC<{ payload: PlanPayload; idea: string }> = ({ payload, idea }) => {
  const [tab, setTab] = React.useState<TabId>('overview');
  const [busy, setBusy] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const counts: Partial<Record<TabId, number>> = {
    prd: payload.prd?.user_stories.length,
    roadmap: payload.features_detailed.length,
    architecture: payload.architecture?.api_endpoints.length,
    backlog: payload.tickets?.epics.length,
    sources: payload.citations.length,
  };

  const download = async (kind: 'markdown' | 'csv' | 'json') => {
    setBusy(kind);
    setError(null);
    try {
      await api.download(kind, payload, idea);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Export failed');
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="animate-slide-up">
      <div className="no-print mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {payload.quality && (
            <Badge tone={payload.quality.overall >= payload.quality.threshold ? 'success' : 'warning'}>
              Reviewed {payload.quality.overall.toFixed(1)}/10 · {payload.quality.grade}
            </Badge>
          )}
          <Badge>{payload.meta.execution_time.toFixed(1)}s</Badge>
          <Badge>{payload.meta.total_tokens.toLocaleString()} tokens</Badge>
          {payload.meta.refined_artifacts.length > 0 && (
            <Badge tone="accent">{payload.meta.refined_artifacts.length} artifact revised</Badge>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <button onClick={() => download('markdown')} disabled={busy !== null} className="btn btn-secondary btn-sm">
            <FileText className="h-3.5 w-3.5" />
            PRD.md
          </button>
          <button onClick={() => download('csv')} disabled={busy !== null} className="btn btn-secondary btn-sm">
            <Table className="h-3.5 w-3.5" />
            Jira CSV
          </button>
          <button onClick={() => download('json')} disabled={busy !== null} className="btn btn-secondary btn-sm">
            <FileJson className="h-3.5 w-3.5" />
            JSON
          </button>
          {/* PDF is the browser's own print pipeline against the print stylesheet,
              which avoids shipping a PDF engine server-side. */}
          <button onClick={() => window.print()} className="btn btn-secondary btn-sm" title="Print or save as PDF">
            <Printer className="h-3.5 w-3.5" />
            PDF
          </button>
        </div>
      </div>

      {error && (
        <div className="no-print mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-300">
          <Download className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <div
        role="tablist"
        aria-label="Plan sections"
        className="no-print mb-4 flex gap-1 overflow-x-auto border-b border-zinc-200 dark:border-zinc-800"
      >
        {TABS.map((entry) => {
          const active = tab === entry.id;
          const count = counts[entry.id];
          return (
            <button
              key={entry.id}
              role="tab"
              aria-selected={active}
              onClick={() => setTab(entry.id)}
              className={cx(
                'flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors',
                active
                  ? 'border-accent-600 text-accent-700 dark:border-accent-400 dark:text-accent-300'
                  : 'border-transparent text-zinc-500 hover:border-zinc-300 hover:text-zinc-800 dark:text-zinc-400 dark:hover:border-zinc-600 dark:hover:text-zinc-200',
              )}
            >
              {entry.icon}
              {entry.label}
              {count !== undefined && count > 0 && (
                <span className="tabular rounded bg-zinc-100 px-1 text-2xs text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Only the active tab renders on screen; print shows every panel so the
          exported PDF is the whole document, not one section. */}
      <div className={cx(tab === 'overview' ? 'block' : 'hidden', 'print-all-panels print:mb-8')}>
        <OverviewPanel payload={payload} />
      </div>
      <div className={cx(tab === 'prd' ? 'block' : 'hidden', 'print-all-panels print:mb-8')}>
        <PrdPanel prd={payload.prd} />
      </div>
      <div className={cx(tab === 'roadmap' ? 'block' : 'hidden', 'print-all-panels print:mb-8')}>
        <RoadmapPanel features={payload.features_detailed} rationale={payload.sequencing_rationale} />
      </div>
      <div className={cx(tab === 'architecture' ? 'block' : 'hidden', 'print-all-panels print:mb-8')}>
        <ArchitecturePanel architecture={payload.architecture} />
      </div>
      <div className={cx(tab === 'backlog' ? 'block' : 'hidden', 'print-all-panels print:mb-8')}>
        <BacklogPanel tickets={payload.tickets} />
      </div>
      <div className={cx(tab === 'quality' ? 'block' : 'hidden', 'print-all-panels print:mb-8')}>
        <QualityPanel quality={payload.quality} />
      </div>
      <div className={cx(tab === 'sources' ? 'block' : 'hidden', 'print-all-panels')}>
        <SourcesPanel payload={payload} />
      </div>
    </div>
  );
};

export default ResultsView;
