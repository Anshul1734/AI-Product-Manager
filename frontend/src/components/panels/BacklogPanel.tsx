import React from 'react';
import { ChevronDown, ChevronRight, Clock, KanbanSquare, Route } from 'lucide-react';
import type { Tickets } from '../../types';
import { Badge, Bullets, Card, EmptyState, SectionTitle, cx, priorityTone } from '../ui/Primitives';

const BacklogPanel: React.FC<{ tickets: Tickets | null }> = ({ tickets }) => {
  const [open, setOpen] = React.useState<Record<string, boolean>>({});

  if (!tickets?.epics.length) {
    return <EmptyState message="No backlog was produced." icon={<KanbanSquare className="h-6 w-6" />} />;
  }

  const totalPoints = tickets.epics.reduce(
    (sum, epic) => sum + epic.stories.reduce((inner, story) => inner + story.story_points, 0),
    0,
  );
  const totalHours = tickets.epics.reduce(
    (sum, epic) =>
      sum +
      epic.stories.reduce(
        (inner, story) => inner + story.tasks.reduce((taskSum, task) => taskSum + task.estimated_hours, 0),
        0,
      ),
    0,
  );
  const storyCount = tickets.epics.reduce((sum, epic) => sum + epic.stories.length, 0);

  return (
    <div className="space-y-4">
      <Card>
        <SectionTitle
          title="Delivery summary"
          icon={<KanbanSquare className="h-3.5 w-3.5" />}
          hint="Story points are relative complexity, not hours. Task hours are the bottom-up estimate."
        />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            ['Epics', tickets.epics.length],
            ['Stories', storyCount],
            ['Story points', totalPoints],
            ['Task hours', Math.round(totalHours)],
          ].map(([label, value]) => (
            <div key={label as string}>
              <div className="label">{label}</div>
              <div className="tabular mt-1 text-2xl font-semibold text-zinc-900 dark:text-zinc-100">{value}</div>
            </div>
          ))}
        </div>

        {tickets.delivery_sequence.length > 0 && (
          <div className="mt-5 border-t border-zinc-100 pt-4 dark:border-zinc-800">
            <div className="label mb-2 flex items-center gap-1.5">
              <Route className="h-3 w-3" />
              Build order
            </div>
            <ol className="flex flex-wrap items-center gap-1.5">
              {tickets.delivery_sequence.map((name, index) => (
                <li key={index} className="flex items-center gap-1.5">
                  <span className="chip py-1 text-xs">
                    <span className="tabular text-zinc-400">{index + 1}</span>
                    {name}
                  </span>
                  {index < tickets.delivery_sequence.length - 1 && (
                    <ChevronRight className="h-3 w-3 text-zinc-300 dark:text-zinc-600" />
                  )}
                </li>
              ))}
            </ol>
          </div>
        )}
      </Card>

      {tickets.epics.map((epic, epicIndex) => {
        const points = epic.stories.reduce((sum, story) => sum + story.story_points, 0);
        return (
          <Card key={epicIndex} className="!p-0 overflow-hidden">
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-200 p-5 dark:border-zinc-800">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{epic.epic_name}</h3>
                  <Badge tone={priorityTone(epic.priority)}>{epic.priority}</Badge>
                </div>
                {epic.description && (
                  <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-zinc-600 dark:text-zinc-300">
                    {epic.description}
                  </p>
                )}
              </div>
              <div className="tabular shrink-0 text-right">
                <div className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">{points}</div>
                <div className="label">points</div>
              </div>
            </div>

            <ul className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
              {epic.stories.map((story, storyIndex) => {
                const key = `${epicIndex}-${storyIndex}`;
                const expanded = open[key] ?? false;
                const hours = story.tasks.reduce((sum, task) => sum + task.estimated_hours, 0);

                return (
                  <li key={storyIndex}>
                    <button
                      type="button"
                      onClick={() => setOpen((prev) => ({ ...prev, [key]: !expanded }))}
                      className="flex w-full items-start gap-2.5 px-5 py-3 text-left transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/40"
                      aria-expanded={expanded}
                    >
                      {expanded ? (
                        <ChevronDown className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400" />
                      ) : (
                        <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400" />
                      )}
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-medium text-zinc-800 dark:text-zinc-200">
                          {story.story_title}
                        </span>
                        <span className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-2xs text-zinc-500 dark:text-zinc-400">
                          <span className="tabular">{story.story_points} pts</span>
                          <span>
                            {story.tasks.length} {story.tasks.length === 1 ? 'task' : 'tasks'}
                          </span>
                          <span className="tabular inline-flex items-center gap-1">
                            <Clock className="h-2.5 w-2.5" />
                            {hours}h
                          </span>
                          <span>
                            {story.acceptance_criteria.length} acceptance{' '}
                            {story.acceptance_criteria.length === 1 ? 'criterion' : 'criteria'}
                          </span>
                        </span>
                      </span>
                    </button>

                    <div className={cx('px-5 pb-4 pl-12', expanded ? 'block' : 'hidden print:block')}>
                      {story.description && (
                        <p className="mb-3 text-sm leading-relaxed text-zinc-600 dark:text-zinc-300">
                          {story.description}
                        </p>
                      )}
                      {story.acceptance_criteria.length > 0 && (
                        <div className="mb-3 rounded-md bg-zinc-50 p-3 dark:bg-zinc-800/50">
                          <div className="label mb-1.5">Acceptance criteria</div>
                          <Bullets items={story.acceptance_criteria} />
                        </div>
                      )}
                      {story.tasks.length > 0 && (
                        <div>
                          <div className="label mb-1.5">Tasks</div>
                          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
                            {story.tasks.map((task, taskIndex) => (
                              <li key={taskIndex} className="flex items-start justify-between gap-3 py-2">
                                <div className="min-w-0">
                                  <div className="text-sm text-zinc-800 dark:text-zinc-200">{task.title}</div>
                                  {task.description && (
                                    <div className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
                                      {task.description}
                                    </div>
                                  )}
                                </div>
                                <span className="tabular shrink-0 text-xs text-zinc-400 dark:text-zinc-500">
                                  {task.estimated_hours}h
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </Card>
        );
      })}
    </div>
  );
};

export default BacklogPanel;
