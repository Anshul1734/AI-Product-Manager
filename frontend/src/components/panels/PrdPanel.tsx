import React from 'react';
import { AlertTriangle, HelpCircle, Gauge, ScrollText, UserRound } from 'lucide-react';
import type { PRD } from '../../types';
import { Badge, Bullets, Card, EmptyState, SectionTitle } from '../ui/Primitives';

const metricTone = (type: string) =>
  type === 'guardrail' ? ('warning' as const) : type === 'lagging' ? ('info' as const) : ('success' as const);

const PrdPanel: React.FC<{ prd: PRD | null }> = ({ prd }) => {
  if (!prd) return <EmptyState message="No PRD was produced." />;

  return (
    <div className="space-y-4">
      <Card>
        <SectionTitle title="Problem" />
        <p className="text-pretty text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">{prd.problem_statement}</p>
        {prd.non_goals.length > 0 && (
          <div className="mt-4 border-t border-zinc-100 pt-4 dark:border-zinc-800">
            <div className="label mb-2">Non-goals</div>
            <Bullets items={prd.non_goals} />
          </div>
        )}
      </Card>

      <Card>
        <SectionTitle
          title={`Personas (${prd.user_personas.length})`}
          icon={<UserRound className="h-3.5 w-3.5" />}
          hint="Capped deliberately — persona bloat hides the real user."
        />
        <div className="grid gap-3 md:grid-cols-2">
          {prd.user_personas.map((persona, index) => (
            <article key={index} className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
              <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{persona.name}</h4>
              <p className="mt-1 text-sm leading-relaxed text-zinc-600 dark:text-zinc-300">{persona.description}</p>
              {persona.current_workaround && (
                <p className="mt-2.5 rounded-md bg-zinc-50 px-2.5 py-1.5 text-xs text-zinc-600 dark:bg-zinc-800/60 dark:text-zinc-300">
                  <span className="font-medium">Today they:</span> {persona.current_workaround}
                </p>
              )}
              <div className="mt-3">
                <div className="label mb-1.5">Pain points</div>
                <Bullets items={persona.pain_points} />
              </div>
            </article>
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle
          title={`User stories (${prd.user_stories.length})`}
          icon={<ScrollText className="h-3.5 w-3.5" />}
          hint="Acceptance criteria are written to be falsifiable — each one is a test you could run."
        />
        <ol className="space-y-3">
          {prd.user_stories.map((story, index) => (
            <li key={index} className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
              <div className="flex items-start gap-2.5">
                <span className="tabular mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded bg-zinc-100 text-2xs font-semibold text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{story.title}</h4>
                  <p className="mt-1.5 text-sm leading-relaxed text-zinc-600 dark:text-zinc-300">
                    As <span className="font-medium text-zinc-800 dark:text-zinc-200">{story.as_a}</span>, I want to{' '}
                    <span className="font-medium text-zinc-800 dark:text-zinc-200">{story.i_want_to}</span> so that{' '}
                    <span className="font-medium text-zinc-800 dark:text-zinc-200">{story.so_that}</span>.
                  </p>
                  {story.acceptance_criteria.length > 0 && (
                    <div className="mt-3 rounded-md bg-zinc-50 p-3 dark:bg-zinc-800/50">
                      <div className="label mb-1.5">Acceptance criteria</div>
                      <Bullets items={story.acceptance_criteria} />
                    </div>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </Card>

      <Card>
        <SectionTitle
          title="Success metrics"
          icon={<Gauge className="h-3.5 w-3.5" />}
          hint="Guardrail metrics exist to catch the primary metric being gamed."
        />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left dark:border-zinc-800">
                <th className="label pb-2 pr-4 font-semibold">Metric</th>
                <th className="label pb-2 pr-4 font-semibold">Type</th>
                <th className="label pb-2 pr-4 font-semibold">Target</th>
                <th className="label pb-2 font-semibold">Definition</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
              {prd.success_metrics.map((metric, index) => (
                <tr key={index}>
                  <td className="py-2.5 pr-4 font-medium text-zinc-800 dark:text-zinc-200">{metric.name}</td>
                  <td className="py-2.5 pr-4">
                    <Badge tone={metricTone(metric.metric_type)}>{metric.metric_type}</Badge>
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-xs text-zinc-700 dark:text-zinc-300">{metric.target}</td>
                  <td className="py-2.5 text-zinc-600 dark:text-zinc-400">{metric.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {(prd.risks.length > 0 || prd.open_questions.length > 0) && (
        <div className="grid gap-4 lg:grid-cols-2">
          {prd.risks.length > 0 && (
            <Card>
              <SectionTitle title="Risks" icon={<AlertTriangle className="h-3.5 w-3.5" />} />
              <Bullets items={prd.risks} />
            </Card>
          )}
          {prd.open_questions.length > 0 && (
            <Card>
              <SectionTitle
                title="Open questions"
                icon={<HelpCircle className="h-3.5 w-3.5" />}
                hint="Recorded rather than guessed at."
              />
              <Bullets items={prd.open_questions} />
            </Card>
          )}
        </div>
      )}
    </div>
  );
};

export default PrdPanel;
