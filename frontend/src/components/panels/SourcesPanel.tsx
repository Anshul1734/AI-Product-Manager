import React from 'react';
import { BookOpen, Cpu, Database, Library, Zap } from 'lucide-react';
import type { PlanPayload } from '../../types';
import { Badge, Card, EmptyState, SectionTitle, Stat } from '../ui/Primitives';

const SourcesPanel: React.FC<{ payload: PlanPayload }> = ({ payload }) => {
  const { citations, agent_steps: steps, meta } = payload;
  const retrieval = meta.retrieval;

  return (
    <div className="space-y-4">
      <Card>
        <SectionTitle
          title="Run provenance"
          icon={<Cpu className="h-3.5 w-3.5" />}
          hint="Which models ran, what they cost, and how much of the plan was grounded in retrieved sources."
        />
        <div className="grid grid-cols-2 gap-5 sm:grid-cols-4">
          <Stat label="Wall clock" value={`${meta.execution_time.toFixed(1)}s`} />
          <Stat
            label="Tokens"
            value={meta.total_tokens.toLocaleString()}
            hint={`${meta.prompt_tokens.toLocaleString()} in / ${meta.completion_tokens.toLocaleString()} out`}
          />
          <Stat label="Agents" value={meta.agents_run.length} hint={meta.depth + ' depth'} />
          <Stat
            label="Sources cited"
            value={retrieval.sources_cited}
            hint={`of ${retrieval.corpus_chunks} indexed passages`}
          />
        </div>

        <div className="mt-5 flex flex-wrap gap-1.5 border-t border-zinc-100 pt-4 dark:border-zinc-800">
          <Badge tone={retrieval.enabled ? 'success' : 'neutral'}>
            <Database className="h-2.5 w-2.5" />
            Retrieval {retrieval.enabled ? 'on' : 'off'}
          </Badge>
          <Badge tone={retrieval.dense ? 'accent' : 'neutral'}>
            {retrieval.dense ? 'Hybrid: BM25 + dense vectors' : 'BM25 lexical only'}
          </Badge>
          {retrieval.retrievers.map((name) => (
            <Badge key={name}>{name}</Badge>
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle title="Agent execution" icon={<Zap className="h-3.5 w-3.5" />} />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[38rem] text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left dark:border-zinc-800">
                <th className="label pb-2 pr-3 font-semibold">Agent</th>
                <th className="label pb-2 pr-3 font-semibold">Model</th>
                <th className="label pb-2 pr-3 text-right font-semibold">Time</th>
                <th className="label pb-2 pr-3 text-right font-semibold">Tokens</th>
                <th className="label pb-2 font-semibold">Tools used</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
              {steps.map((step, index) => (
                <tr key={index} className="align-top">
                  <td className="py-2.5 pr-3">
                    <div className="font-medium text-zinc-800 dark:text-zinc-200">{step.label}</div>
                    {step.note && <div className="text-2xs text-zinc-400">{step.note}</div>}
                  </td>
                  <td className="py-2.5 pr-3 font-mono text-2xs text-zinc-500 dark:text-zinc-400">
                    {step.model || '—'}
                  </td>
                  <td className="tabular py-2.5 pr-3 text-right text-zinc-600 dark:text-zinc-300">
                    {step.duration_seconds ? `${step.duration_seconds.toFixed(1)}s` : '—'}
                  </td>
                  <td className="tabular py-2.5 pr-3 text-right text-zinc-600 dark:text-zinc-300">
                    {step.tokens ? step.tokens.toLocaleString() : '—'}
                  </td>
                  <td className="py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {step.tool_calls.length ? (
                        step.tool_calls.map((tool, toolIndex) => (
                          <Badge key={toolIndex} className="font-mono">
                            {tool}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-2xs text-zinc-400">—</span>
                      )}
                      {step.repairs > 0 && <Badge tone="warning">{step.repairs} repair</Badge>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {Object.keys(meta.errors).length > 0 && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50/70 p-3 dark:border-amber-900/50 dark:bg-amber-950/25">
            <div className="label mb-1.5 text-amber-800 dark:text-amber-300">Non-fatal issues</div>
            <ul className="space-y-1 text-xs text-amber-800/90 dark:text-amber-200/80">
              {Object.entries(meta.errors).map(([node, message]) => (
                <li key={node}>
                  <span className="font-medium">{node}:</span> {message}
                </li>
              ))}
            </ul>
            <p className="mt-2 text-2xs text-amber-700/80 dark:text-amber-300/70">
              These steps are non-critical, so the run continued and produced the plan without them.
            </p>
          </div>
        )}
      </Card>

      <Card>
        <SectionTitle
          title={`Knowledge sources (${citations.length})`}
          icon={<Library className="h-3.5 w-3.5" />}
          hint="Passages retrieved from the product-management corpus and supplied to the agents as grounding."
        />
        {citations.length ? (
          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
            {citations.map((citation) => (
              <li key={citation.marker} className="flex items-start gap-3 py-2.5">
                <span className="mt-0.5 shrink-0 rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-2xs font-semibold text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
                  {citation.marker}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-zinc-800 dark:text-zinc-200">{citation.title}</div>
                  {citation.heading && (
                    <div className="text-xs text-zinc-500 dark:text-zinc-400">{citation.heading}</div>
                  )}
                </div>
                <span className="tabular shrink-0 text-2xs text-zinc-400" title="Reciprocal-rank-fusion score">
                  {citation.score.toFixed(4)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState message="No sources were retrieved for this run." icon={<BookOpen className="h-6 w-6" />} />
        )}
      </Card>
    </div>
  );
};

export default SourcesPanel;
