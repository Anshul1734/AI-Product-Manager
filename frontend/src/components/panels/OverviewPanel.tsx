import React from 'react';
import { Ban, Compass, FlaskConical, Target, Users } from 'lucide-react';
import type { PlanPayload } from '../../types';
import { Badge, Bullets, Card, EmptyState, SectionTitle } from '../ui/Primitives';

const OverviewPanel: React.FC<{ payload: PlanPayload }> = ({ payload }) => {
  const plan = payload.plan;
  if (!plan) return <EmptyState message="No product vision was produced." />;

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-balance text-xl font-semibold tracking-[-0.015em] text-zinc-900 dark:text-zinc-50">
              {plan.product_name}
            </h2>
            <p className="mt-2 max-w-3xl text-pretty text-[0.9375rem] leading-relaxed text-zinc-600 dark:text-zinc-300">
              {plan.value_proposition}
            </p>
          </div>
          <Badge tone="accent">{payload.meta.depth} run</Badge>
        </div>

        <div className="mt-5 rounded-lg border-l-2 border-accent-400 bg-zinc-50 p-4 dark:bg-zinc-800/40">
          <div className="label mb-1.5">The problem</div>
          <p className="text-pretty text-sm leading-relaxed text-zinc-700 dark:text-zinc-200">
            {plan.problem_statement}
          </p>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle title="Target users" icon={<Users className="h-3.5 w-3.5" />} />
          <div className="flex flex-wrap gap-1.5">
            {plan.target_users.length ? (
              plan.target_users.map((user, index) => (
                <span key={index} className="chip py-1 text-xs">
                  {user}
                </span>
              ))
            ) : (
              <p className="text-sm italic text-zinc-400">Not specified.</p>
            )}
          </div>
        </Card>

        <Card>
          <SectionTitle title="Goals" icon={<Target className="h-3.5 w-3.5" />} />
          <Bullets items={plan.core_goals} />
        </Card>
      </div>

      {plan.jobs_to_be_done.length > 0 && (
        <Card>
          <SectionTitle
            title="Jobs to be done"
            icon={<Compass className="h-3.5 w-3.5" />}
            hint="What users are trying to accomplish, independent of any solution."
          />
          <ul className="space-y-2.5">
            {plan.jobs_to_be_done.map((job, index) => (
              <li key={index} className="rounded-lg border border-zinc-200 p-3.5 dark:border-zinc-800">
                <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
                  <span className="font-medium text-zinc-500 dark:text-zinc-400">When</span> {job.situation}
                  <span className="font-medium text-zinc-500 dark:text-zinc-400">, I want to</span> {job.motivation}
                  <span className="font-medium text-zinc-500 dark:text-zinc-400">, so I can</span> {job.outcome}.
                </p>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle
            title="Non-goals"
            icon={<Ban className="h-3.5 w-3.5" />}
            hint="Deliberately out of scope. A plan that excludes nothing has not made a choice."
          />
          <Bullets items={plan.non_goals} empty="No non-goals declared — worth pushing on." />
        </Card>

        <Card>
          <SectionTitle
            title="Assumptions to validate"
            icon={<FlaskConical className="h-3.5 w-3.5" />}
            hint="If one of these is wrong, the plan changes. Test them early."
          />
          <Bullets items={plan.assumptions} empty="No assumptions surfaced." />
        </Card>
      </div>

      <Card>
        <SectionTitle title="Candidate features" hint="Expanded and scored on the Roadmap tab." />
        <Bullets items={plan.key_features_high_level} />
      </Card>
    </div>
  );
};

export default OverviewPanel;
