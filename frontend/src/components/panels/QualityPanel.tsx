import React from 'react';
import { AlertOctagon, RefreshCw, ShieldCheck, Wrench } from 'lucide-react';
import type { Quality } from '../../types';
import { Badge, Bullets, Card, EmptyState, ScoreBar, ScoreRing, SectionTitle } from '../ui/Primitives';

const ARTIFACT_LABELS: Record<string, string> = {
  plan: 'Product vision',
  prd: 'Requirements (PRD)',
  features_detailed: 'Prioritization',
  architecture: 'Architecture',
  tickets: 'Backlog',
};

const AXES: { key: keyof Quality['artifacts'][number]; label: string }[] = [
  { key: 'completeness', label: 'Completeness' },
  { key: 'consistency', label: 'Consistency' },
  { key: 'specificity', label: 'Specificity' },
  { key: 'feasibility', label: 'Feasibility' },
];

const QualityPanel: React.FC<{ quality: Quality | null }> = ({ quality }) => {
  if (!quality) {
    return (
      <EmptyState
        message="No quality review. Reviewing runs at Standard depth and above."
        icon={<ShieldCheck className="h-6 w-6" />}
      />
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-start gap-5">
          <ScoreRing score={quality.overall} size={72} />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Independent review</h3>
              <Badge tone={quality.overall >= quality.threshold ? 'success' : 'warning'}>
                Grade {quality.grade}
              </Badge>
            </div>
            <p className="mt-2 text-pretty text-sm leading-relaxed text-zinc-600 dark:text-zinc-300">
              {quality.assessment}
            </p>
            <p className="mt-2 text-xs text-zinc-400 dark:text-zinc-500">
              Reviewed by a different model family from the one that wrote the plan, so this is not the author
              grading itself. Anything below {quality.threshold}/10 is regenerated on a Deep run.
            </p>
          </div>
        </div>
      </Card>

      {quality.blocking_issues.length > 0 && (
        <Card className="!border-red-200 dark:!border-red-900/60">
          <SectionTitle
            title="Blocking issues"
            icon={<AlertOctagon className="h-3.5 w-3.5 text-red-500" />}
            hint="Defects that make the plan unsafe to build from as written."
          />
          <Bullets items={quality.blocking_issues} />
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {quality.artifacts.map((artifact) => (
          <Card key={artifact.artifact}>
            <div className="mb-4 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h4 className="flex flex-wrap items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                  {ARTIFACT_LABELS[artifact.artifact] ?? artifact.artifact}
                  {artifact.revised && (
                    <Badge tone="accent">
                      <RefreshCw className="h-2.5 w-2.5" />
                      revised
                    </Badge>
                  )}
                </h4>
              </div>
              <ScoreRing score={artifact.overall} size={48} />
            </div>

            <dl className="space-y-2.5">
              {AXES.map(({ key, label }) => {
                const value = artifact[key] as number;
                return (
                  <div key={key}>
                    <div className="mb-1 flex items-baseline justify-between gap-2">
                      <dt className="text-xs text-zinc-600 dark:text-zinc-400">{label}</dt>
                      <dd className="tabular text-xs font-medium text-zinc-800 dark:text-zinc-200">
                        {value.toFixed(1)}
                      </dd>
                    </div>
                    <ScoreBar
                      value={value}
                      max={10}
                      tone={value >= 8 ? 'success' : value >= 7 ? 'accent' : value >= 5 ? 'warning' : 'danger'}
                    />
                  </div>
                );
              })}
            </dl>

            {artifact.issues.length > 0 && (
              <div className="mt-4 border-t border-zinc-100 pt-3 dark:border-zinc-800">
                <div className="label mb-1.5">Issues found</div>
                <Bullets items={artifact.issues} />
              </div>
            )}

            {artifact.fix_instructions.length > 0 && (
              <div className="mt-3 rounded-md bg-zinc-50 p-3 dark:bg-zinc-800/50">
                <div className="label mb-1.5 flex items-center gap-1.5">
                  <Wrench className="h-3 w-3" />
                  {artifact.revised ? 'Applied on the revision pass' : 'Would be applied on a Deep run'}
                </div>
                <Bullets items={artifact.fix_instructions} />
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
};

export default QualityPanel;
