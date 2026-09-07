import React from 'react';
import { AlertCircle, BrainCircuit, Github, Moon, Search, Sparkles, Sun } from 'lucide-react';
import IdeaComposer from './components/IdeaComposer';
import AgentTrace from './components/AgentTrace';
import ResultsView from './components/ResultsView';
import KnowledgeExplorer from './components/KnowledgeExplorer';
import { Badge, cx } from './components/ui/Primitives';
import { api } from './lib/api';
import type { Depth, HealthResponse, PlanPayload, StreamEvent, TraceEntry } from './types';

type View = 'plan' | 'knowledge';

const useTheme = () => {
  const [dark, setDark] = React.useState<boolean>(() => {
    const stored = window.localStorage.getItem('aipm-theme');
    if (stored) return stored === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  React.useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    window.localStorage.setItem('aipm-theme', dark ? 'dark' : 'light');
  }, [dark]);

  return { dark, toggle: () => setDark((value) => !value) };
};

const App: React.FC = () => {
  const { dark, toggle } = useTheme();
  const [view, setView] = React.useState<View>('plan');

  const [health, setHealth] = React.useState<HealthResponse | null>(null);
  const [running, setRunning] = React.useState(false);
  const [trace, setTrace] = React.useState<TraceEntry[]>([]);
  const [payload, setPayload] = React.useState<PlanPayload | null>(null);
  const [idea, setIdea] = React.useState('');
  const [error, setError] = React.useState<string | null>(null);
  const [elapsed, setElapsed] = React.useState(0);

  const abortRef = React.useRef<AbortController | null>(null);
  const startedRef = React.useRef<number>(0);

  React.useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  // Wall-clock ticker. Runs on the client so a long, paced run still shows
  // progress rather than looking hung.
  React.useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => setElapsed((Date.now() - startedRef.current) / 1000), 200);
    return () => window.clearInterval(timer);
  }, [running]);

  const applyEvent = React.useCallback((event: StreamEvent) => {
    setTrace((previous) => {
      const next = [...previous];
      const find = (node: string) => next.findIndex((entry) => entry.node === node);

      switch (event.type) {
        case 'node_start': {
          if (find(event.node) === -1) {
            next.push({ node: event.node, label: event.label, status: 'running', tools: [], repairs: 0 });
          }
          return next;
        }
        case 'node_end': {
          const index = find(event.node);
          if (index >= 0) next[index] = { ...next[index], status: 'done', duration: event.duration };
          return next;
        }
        case 'node_skipped': {
          if (find(event.node) === -1) {
            next.push({ node: event.node, label: event.label, status: 'skipped', tools: [], repairs: 0 });
          }
          return next;
        }
        case 'node_failed': {
          const index = find(event.node);
          const entry: TraceEntry = {
            node: event.node,
            label: event.label,
            status: 'failed',
            tools: index >= 0 ? next[index].tools : [],
            repairs: index >= 0 ? next[index].repairs : 0,
            error: event.critical ? event.error : `Skipped (non-critical): ${event.error}`,
          };
          if (index >= 0) next[index] = entry;
          else next.push(entry);
          return next;
        }
        case 'tool_call': {
          const index = find(event.agent);
          if (index >= 0) {
            next[index] = {
              ...next[index],
              tools: [...next[index].tools, { tool: event.tool, ok: event.ok, summary: event.summary }],
            };
          }
          return next;
        }
        case 'repair': {
          const index = find(event.agent);
          if (index >= 0) next[index] = { ...next[index], repairs: event.attempt };
          return next;
        }
        default:
          return next;
      }
    });
  }, []);

  const run = async (nextIdea: string, depth: Depth) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIdea(nextIdea);
    setPayload(null);
    setTrace([]);
    setError(null);
    setElapsed(0);
    startedRef.current = Date.now();
    setRunning(true);

    try {
      const result = await api.streamPlan(nextIdea, depth, applyEvent, controller.signal);
      setPayload(result);
    } catch (cause) {
      if (controller.signal.aborted) return;
      setError(cause instanceof Error ? cause.message : 'The run failed.');
    } finally {
      if (!controller.signal.aborted) setRunning(false);
    }
  };

  const cancel = () => {
    abortRef.current?.abort();
    setRunning(false);
    setError('Run cancelled.');
  };

  const llmReady = health?.components.llm.ready ?? true;

  return (
    <div className="min-h-screen">
      <header className="no-print sticky top-0 z-40 border-b border-zinc-200 bg-zinc-50/85 backdrop-blur-md dark:border-zinc-800 dark:bg-zinc-950/85">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent-600 text-white">
              <BrainCircuit className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <h1 className="truncate text-sm font-semibold text-zinc-900 dark:text-zinc-50">AI Product Manager</h1>
              <p className="hidden truncate text-2xs text-zinc-500 dark:text-zinc-400 sm:block">
                Multi-agent planning grounded in retrieval
              </p>
            </div>
          </div>

          <nav className="flex items-center gap-1">
            <button
              onClick={() => setView('plan')}
              className={cx('btn btn-sm', view === 'plan' ? 'btn-secondary' : 'btn-ghost')}
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Plan</span>
            </button>
            <button
              onClick={() => setView('knowledge')}
              className={cx('btn btn-sm', view === 'knowledge' ? 'btn-secondary' : 'btn-ghost')}
            >
              <Search className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Knowledge</span>
            </button>
            <a
              href="https://github.com/Anshul1734/AI-Product-Manager"
              target="_blank"
              rel="noreferrer"
              className="btn btn-ghost btn-sm"
              aria-label="Source on GitHub"
            >
              <Github className="h-3.5 w-3.5" />
            </a>
            <button onClick={toggle} className="btn btn-ghost btn-sm" aria-label="Toggle theme">
              {dark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        {!llmReady && (
          <div className="no-print mb-5 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900/60 dark:bg-red-950/30">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
            <div className="text-sm">
              <p className="font-medium text-red-800 dark:text-red-200">Language model not configured</p>
              <p className="mt-0.5 text-red-700/90 dark:text-red-300/80">
                {health?.components.llm.detail ?? 'Set GROQ_API_KEY in the backend environment.'}
              </p>
            </div>
          </div>
        )}

        {view === 'knowledge' ? (
          <KnowledgeExplorer />
        ) : (
          <div className="space-y-5">
            {!payload && (
              <section className="no-print">
                <div className="mb-6 max-w-2xl">
                  <h2 className="text-balance text-2xl font-semibold tracking-[-0.02em] text-zinc-900 dark:text-zinc-50 sm:text-3xl">
                    Turn a problem into a plan a team can build
                  </h2>
                  <p className="mt-2.5 text-pretty text-[0.9375rem] leading-relaxed text-zinc-600 dark:text-zinc-300">
                    Six specialist agents work in sequence — framing the vision, writing the PRD, scoring the roadmap
                    with RICE, designing the architecture, breaking down the backlog, then reviewing the whole thing.
                    Each one is grounded in a retrieval corpus of product-management practice, and every number you see
                    is computed rather than guessed.
                  </p>
                  {health && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      <Badge tone={health.components.retrieval.ready ? 'success' : 'warning'}>
                        {health.components.retrieval.documents} knowledge documents
                      </Badge>
                      <Badge>{health.components.retrieval.corpus_chunks} indexed passages</Badge>
                      <Badge tone="accent">
                        {health.components.retrieval.dense ? 'Hybrid retrieval' : 'BM25 retrieval'}
                      </Badge>
                    </div>
                  )}
                </div>

                <IdeaComposer
                  onSubmit={run}
                  onCancel={cancel}
                  running={running}
                  disabled={!llmReady}
                  disabledReason={!llmReady ? 'Configure GROQ_API_KEY to run the pipeline.' : undefined}
                />
              </section>
            )}

            {payload && (
              <section className="no-print flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="label mb-1">Your idea</div>
                  <p className="max-w-3xl truncate text-sm text-zinc-600 dark:text-zinc-300">{idea}</p>
                </div>
                <button
                  onClick={() => {
                    setPayload(null);
                    setTrace([]);
                    setError(null);
                  }}
                  className="btn btn-secondary btn-sm"
                >
                  New plan
                </button>
              </section>
            )}

            {error && (
              <div className="no-print flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900/60 dark:bg-red-950/30">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
                <div className="min-w-0 text-sm">
                  <p className="font-medium text-red-800 dark:text-red-200">Run did not finish</p>
                  <p className="mt-0.5 break-words text-red-700/90 dark:text-red-300/80">{error}</p>
                </div>
              </div>
            )}

            {trace.length > 0 && (
              <AgentTrace entries={trace} elapsed={elapsed} running={running} className="no-print" />
            )}

            {payload && <ResultsView payload={payload} idea={idea} />}
          </div>
        )}
      </main>

      <footer className="no-print border-t border-zinc-200 py-6 dark:border-zinc-800">
        <div className="mx-auto max-w-6xl px-4 text-xs text-zinc-400 dark:text-zinc-500 sm:px-6">
          <p>
            Agent graph with tool calling, hybrid BM25 + dense retrieval, schema-validated artifacts, and an
            independent review pass. Also exposed as an MCP server.
          </p>
          {health && (
            <p className="mt-1">
              v{health.version} · {health.components.llm.model}
            </p>
          )}
        </div>
      </footer>
    </div>
  );
};

export default App;
