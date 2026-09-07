import React from 'react';
import { AlertTriangle, ArrowRight, Lightbulb, Loader2, Square } from 'lucide-react';
import type { Depth, ValidationResult } from '../types';
import { api } from '../lib/api';
import { Badge, cx } from './ui/Primitives';

const DEPTHS: { value: Depth; title: string; blurb: string; agents: string }[] = [
  { value: 'quick', title: 'Quick', blurb: 'Vision, PRD, architecture, backlog.', agents: '4 agents' },
  { value: 'standard', title: 'Standard', blurb: 'Adds RICE prioritization and a quality review.', agents: '6 agents' },
  { value: 'deep', title: 'Deep', blurb: 'Regenerates any artifact that fails review.', agents: '6 agents + revision' },
];

const EXAMPLES = [
  'Small logistics operators only discover an SLA breach when the customer complains — shipment state lives in spreadsheets across three warehouses.',
  'Junior clinicians waste hours each week re-entering the same patient intake data into three separate systems that do not talk to each other.',
  'Indie game studios have no way to tell which of their Discord community requests actually correlate with player retention.',
];

interface Props {
  onSubmit: (idea: string, depth: Depth) => void;
  onCancel: () => void;
  running: boolean;
  disabled?: boolean;
  disabledReason?: string;
}

const IdeaComposer: React.FC<Props> = ({ onSubmit, onCancel, running, disabled, disabledReason }) => {
  const [idea, setIdea] = React.useState('');
  const [depth, setDepth] = React.useState<Depth>('standard');
  const [check, setCheck] = React.useState<ValidationResult | null>(null);
  const [checking, setChecking] = React.useState(false);

  // Debounced server-side sanity check, so the user can sharpen a weak idea
  // before spending a full multi-agent run on it.
  React.useEffect(() => {
    const trimmed = idea.trim();
    if (trimmed.length < 15) {
      setCheck(null);
      return;
    }
    const timer = window.setTimeout(async () => {
      setChecking(true);
      try {
        setCheck(await api.validateIdea(trimmed));
      } catch {
        setCheck(null);
      } finally {
        setChecking(false);
      }
    }, 700);
    return () => window.clearTimeout(timer);
  }, [idea]);

  const tooShort = idea.trim().length < 10;

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!tooShort && !running && !disabled) onSubmit(idea.trim(), depth);
  };

  return (
    <form onSubmit={submit} className="surface p-5 sm:p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Describe the problem</h2>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Lead with what breaks today and who it hurts. A problem produces a far better plan than a feature list.
          </p>
        </div>
      </div>

      <textarea
        value={idea}
        onChange={(event) => setIdea(event.target.value)}
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') submit(event);
        }}
        rows={5}
        maxLength={2000}
        placeholder="e.g. Support agents can't see a customer's order history during a call, so every refund takes three days and two handoffs…"
        className="field resize-y font-normal leading-relaxed"
        aria-label="Product idea"
      />

      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="mr-1 text-xs text-zinc-400 dark:text-zinc-500">Try:</span>
          {EXAMPLES.map((example, index) => (
            <button
              key={index}
              type="button"
              onClick={() => setIdea(example)}
              className="chip transition-colors hover:border-accent-300 hover:text-accent-700 dark:hover:border-accent-700 dark:hover:text-accent-300"
            >
              <Lightbulb className="h-3 w-3" />
              Example {index + 1}
            </button>
          ))}
        </div>
        <span className="tabular text-xs text-zinc-400 dark:text-zinc-500">{idea.length}/2000</span>
      </div>

      {check && !check.valid && check.issues.length > 0 && (
        <div className="mt-4 animate-fade-in rounded-lg border border-amber-200 bg-amber-50/70 p-3.5 dark:border-amber-900/50 dark:bg-amber-950/25">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
            <div className="min-w-0 text-sm">
              <p className="font-medium text-amber-900 dark:text-amber-200">
                This will still run, but the plan will be sharper if you address:
              </p>
              <ul className="mt-1.5 space-y-1 text-amber-800/90 dark:text-amber-200/80">
                {check.issues.map((issue, index) => (
                  <li key={index}>
                    · {issue}
                    {check.suggestions[index] && (
                      <span className="text-amber-700/80 dark:text-amber-300/70"> — {check.suggestions[index]}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {check?.valid && (
        <div className="mt-4 animate-fade-in">
          <Badge tone="success">Reads like a real problem statement</Badge>
        </div>
      )}

      <fieldset className="mt-5">
        <legend className="label mb-2">Depth</legend>
        <div className="grid gap-2 sm:grid-cols-3">
          {DEPTHS.map((option) => {
            const active = depth === option.value;
            return (
              <label
                key={option.value}
                className={cx(
                  'cursor-pointer rounded-lg border p-3 transition-colors',
                  active
                    ? 'border-accent-500 bg-accent-50/60 ring-1 ring-accent-500/30 dark:bg-accent-950/30'
                    : 'border-zinc-200 hover:border-zinc-300 dark:border-zinc-700 dark:hover:border-zinc-600',
                )}
              >
                <input
                  type="radio"
                  name="depth"
                  value={option.value}
                  checked={active}
                  onChange={() => setDepth(option.value)}
                  className="sr-only"
                />
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={cx(
                      'text-sm font-medium',
                      active ? 'text-accent-800 dark:text-accent-200' : 'text-zinc-800 dark:text-zinc-200',
                    )}
                  >
                    {option.title}
                  </span>
                  <span className="text-2xs text-zinc-400 dark:text-zinc-500">{option.agents}</span>
                </div>
                <p className="mt-1 text-xs leading-snug text-zinc-500 dark:text-zinc-400">{option.blurb}</p>
              </label>
            );
          })}
        </div>
      </fieldset>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        {running ? (
          <button type="button" onClick={onCancel} className="btn btn-secondary btn-md">
            <Square className="h-3.5 w-3.5" />
            Stop run
          </button>
        ) : (
          <button type="submit" disabled={tooShort || disabled} className="btn btn-primary btn-md">
            Generate plan
            <ArrowRight className="h-4 w-4" />
          </button>
        )}

        {running && (
          <span className="inline-flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Agents are working — results stream in below
          </span>
        )}
        {!running && checking && <span className="text-xs text-zinc-400">Checking idea…</span>}
        {!running && disabled && disabledReason && (
          <span className="text-sm text-red-600 dark:text-red-400">{disabledReason}</span>
        )}
        {!running && !disabled && (
          <span className="hidden text-xs text-zinc-400 dark:text-zinc-500 sm:inline">
            <kbd className="rounded border border-zinc-300 px-1 font-sans dark:border-zinc-600">⌘</kbd>
            <kbd className="ml-0.5 rounded border border-zinc-300 px-1 font-sans dark:border-zinc-600">↵</kbd> to run
          </span>
        )}
      </div>
    </form>
  );
};

export default IdeaComposer;
