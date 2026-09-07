import React from 'react';
import { Calculator, ListOrdered } from 'lucide-react';
import type { ScoredFeature } from '../../types';
import { Badge, Card, EmptyState, ScoreBar, SectionTitle, moscowTone } from '../ui/Primitives';

const RoadmapPanel: React.FC<{ features: ScoredFeature[]; rationale: string }> = ({ features, rationale }) => {
  if (!features.length) {
    return (
      <EmptyState
        message="No prioritized features. RICE scoring runs at Standard depth and above."
        icon={<Calculator className="h-6 w-6" />}
      />
    );
  }

  const max = Math.max(...features.map((feature) => feature.rice.score));

  return (
    <div className="space-y-4">
      <Card>
        <SectionTitle
          title="RICE prioritization"
          icon={<Calculator className="h-3.5 w-3.5" />}
          hint="Score = (Reach × Impact × Confidence / 100) ÷ Effort. Computed server-side in Python from the estimates below, so the ranking always matches the arithmetic."
        />

        <div className="overflow-x-auto">
          <table className="w-full min-w-[46rem] text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left dark:border-zinc-800">
                <th className="label pb-2 pr-3 font-semibold">#</th>
                <th className="label pb-2 pr-3 font-semibold">Feature</th>
                <th className="label pb-2 pr-3 text-right font-semibold">Reach</th>
                <th className="label pb-2 pr-3 text-right font-semibold">Impact</th>
                <th className="label pb-2 pr-3 text-right font-semibold">Conf.</th>
                <th className="label pb-2 pr-3 text-right font-semibold">Effort</th>
                <th className="label pb-2 pr-3 font-semibold">Score</th>
                <th className="label pb-2 font-semibold">MoSCoW</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
              {features.map((feature, index) => (
                <tr key={index} className="group align-top">
                  <td className="tabular py-3 pr-3 text-zinc-400 dark:text-zinc-500">{index + 1}</td>
                  <td className="py-3 pr-3">
                    <div className="font-medium text-zinc-900 dark:text-zinc-100">{feature.name}</div>
                    {feature.description && (
                      <div className="mt-0.5 max-w-md text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">
                        {feature.description}
                      </div>
                    )}
                  </td>
                  <td className="tabular py-3 pr-3 text-right text-zinc-600 dark:text-zinc-300">
                    {feature.rice.reach.toLocaleString()}
                  </td>
                  <td className="tabular py-3 pr-3 text-right text-zinc-600 dark:text-zinc-300">
                    {feature.rice.impact}
                  </td>
                  <td className="tabular py-3 pr-3 text-right text-zinc-600 dark:text-zinc-300">
                    {feature.rice.confidence}%
                  </td>
                  <td className="tabular py-3 pr-3 text-right text-zinc-600 dark:text-zinc-300">
                    {feature.rice.effort}
                    <span className="ml-0.5 text-2xs text-zinc-400">pm</span>
                  </td>
                  <td className="py-3 pr-3" style={{ minWidth: '7rem' }}>
                    <div className="tabular mb-1 font-semibold text-zinc-900 dark:text-zinc-100">
                      {feature.rice.score.toLocaleString()}
                    </div>
                    <ScoreBar value={feature.rice.score} max={max} />
                  </td>
                  <td className="py-3">
                    <Badge tone={moscowTone(feature.moscow)}>{feature.moscow}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-3 text-2xs text-zinc-400 dark:text-zinc-500">
          Effort in person-months. Impact scale: 3 massive · 2 high · 1 medium · 0.5 low · 0.25 minimal.
        </p>
      </Card>

      <Card>
        <SectionTitle title="Why these estimates" hint="An unjustified number is noise." />
        <ul className="space-y-2.5">
          {features.map((feature, index) => (
            <li key={index} className="flex gap-3 text-sm">
              <span className="tabular mt-0.5 shrink-0 font-semibold text-zinc-400 dark:text-zinc-500">
                {index + 1}.
              </span>
              <span className="min-w-0">
                <span className="font-medium text-zinc-800 dark:text-zinc-200">{feature.name}</span>
                <span className="text-zinc-600 dark:text-zinc-400"> — {feature.justification}</span>
              </span>
            </li>
          ))}
        </ul>
      </Card>

      {rationale && (
        <Card>
          <SectionTitle
            title="Sequencing rationale"
            icon={<ListOrdered className="h-3.5 w-3.5" />}
            hint="Build order is not just score order — dependencies and risk reordering matter."
          />
          <p className="text-pretty text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">{rationale}</p>
        </Card>
      )}
    </div>
  );
};

export default RoadmapPanel;
