import React from 'react';
import { Boxes, GitBranch, Layers, Network, ShieldAlert, Table2 } from 'lucide-react';
import type { SystemArchitecture } from '../../types';
import { Badge, Bullets, Card, EmptyState, MethodBadge, SectionTitle } from '../ui/Primitives';

const ArchitecturePanel: React.FC<{ architecture: SystemArchitecture | null }> = ({ architecture }) => {
  if (!architecture) return <EmptyState message="No architecture was produced." icon={<Boxes className="h-6 w-6" />} />;

  return (
    <div className="space-y-4">
      <Card>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <SectionTitle title="System design" icon={<Layers className="h-3.5 w-3.5" />} />
        </div>
        <Badge tone="accent" className="mb-3">
          {architecture.architecture_pattern}
        </Badge>
        <p className="text-pretty text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
          {architecture.system_design}
        </p>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle title="Tech stack" />
          <dl className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
            {Object.entries(architecture.tech_stack).map(([layer, choice]) => (
              <div key={layer} className="flex items-baseline justify-between gap-4 py-2 first:pt-0 last:pb-0">
                <dt className="label">{layer.replace(/_/g, ' ')}</dt>
                <dd className="text-right text-sm font-medium text-zinc-800 dark:text-zinc-200">{choice}</dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card>
          <SectionTitle title="Components" icon={<Boxes className="h-3.5 w-3.5" />} />
          <div className="flex flex-wrap gap-1.5">
            {architecture.architecture_components.map((component, index) => (
              <span key={index} className="chip py-1 text-xs">
                {component}
              </span>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <SectionTitle
          title={`API endpoints (${architecture.api_endpoints.length})`}
          icon={<Network className="h-3.5 w-3.5" />}
        />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[34rem] text-sm">
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
              {architecture.api_endpoints.map((endpoint, index) => (
                <tr key={index} className="align-top">
                  <td className="w-16 py-2.5 pr-3">
                    <MethodBadge method={endpoint.method} />
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-xs text-zinc-800 dark:text-zinc-200">
                    {endpoint.endpoint}
                  </td>
                  <td className="py-2.5 text-zinc-600 dark:text-zinc-400">{endpoint.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <SectionTitle
          title={`Data model (${architecture.database_schema.length} tables)`}
          icon={<Table2 className="h-3.5 w-3.5" />}
        />
        <div className="grid gap-3 md:grid-cols-2">
          {architecture.database_schema.map((table, index) => (
            <div key={index} className="overflow-hidden rounded-lg border border-zinc-200 dark:border-zinc-800">
              <div className="border-b border-zinc-200 bg-zinc-50 px-3 py-2 font-mono text-xs font-semibold text-zinc-800 dark:border-zinc-800 dark:bg-zinc-800/60 dark:text-zinc-200">
                {table.table_name}
              </div>
              <table className="w-full text-xs">
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
                  {table.fields.map((field, fieldIndex) => (
                    <tr key={fieldIndex}>
                      <td className="py-1.5 pl-3 pr-2 font-mono text-zinc-800 dark:text-zinc-200">{field.name}</td>
                      <td className="py-1.5 pr-2 font-mono text-zinc-500 dark:text-zinc-400">{field.type}</td>
                      <td className="py-1.5 pr-3 text-2xs text-zinc-400 dark:text-zinc-500">{field.constraints}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </Card>

      {architecture.key_decisions.length > 0 && (
        <Card>
          <SectionTitle
            title="Key decisions"
            icon={<GitBranch className="h-3.5 w-3.5" />}
            hint="Each records what was given up, not just what was chosen."
          />
          <div className="space-y-3">
            {architecture.key_decisions.map((decision, index) => (
              <article key={index} className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
                <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{decision.decision}</h4>
                <p className="mt-1.5 text-sm leading-relaxed text-zinc-600 dark:text-zinc-300">{decision.rationale}</p>
                {decision.alternatives_considered.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                    <span className="label">Considered</span>
                    {decision.alternatives_considered.map((alternative, altIndex) => (
                      <span key={altIndex} className="chip">
                        {alternative}
                      </span>
                    ))}
                  </div>
                )}
                {decision.tradeoffs && (
                  <p className="mt-2.5 rounded-md bg-amber-50 px-2.5 py-1.5 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
                    <span className="font-medium">Tradeoff accepted:</span> {decision.tradeoffs}
                  </p>
                )}
              </article>
            ))}
          </div>
        </Card>
      )}

      {architecture.non_functional_requirements.length > 0 && (
        <Card>
          <SectionTitle
            title="Non-functional requirements"
            icon={<ShieldAlert className="h-3.5 w-3.5" />}
            hint="Concrete budgets and targets, not adjectives."
          />
          <Bullets items={architecture.non_functional_requirements} />
        </Card>
      )}
    </div>
  );
};

export default ArchitecturePanel;
