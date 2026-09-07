/** Small presentational building blocks shared across panels. */
import React from 'react';
import { Check, Copy } from 'lucide-react';

export const cx = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(' ');

/* --------------------------------------------------------------- containers */

export const Card: React.FC<{ className?: string; children: React.ReactNode }> = ({ className, children }) => (
  <section className={cx('surface p-5 sm:p-6', className)}>{children}</section>
);

export const SectionTitle: React.FC<{
  title: string;
  hint?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}> = ({ title, hint, icon, action }) => (
  <div className="mb-4 flex items-start justify-between gap-4">
    <div className="min-w-0">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
        {icon && <span className="text-zinc-400 dark:text-zinc-500">{icon}</span>}
        {title}
      </h3>
      {hint && <p className="mt-1 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">{hint}</p>}
    </div>
    {action && <div className="no-print shrink-0">{action}</div>}
  </div>
);

export const EmptyState: React.FC<{ message: string; icon?: React.ReactNode }> = ({ message, icon }) => (
  <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-zinc-300 px-6 py-10 text-center dark:border-zinc-700">
    {icon && <span className="text-zinc-300 dark:text-zinc-600">{icon}</span>}
    <p className="text-sm text-zinc-500 dark:text-zinc-400">{message}</p>
  </div>
);

/* -------------------------------------------------------------------- atoms */

type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

const TONES: Record<Tone, string> = {
  neutral: 'border-zinc-200 bg-zinc-100 text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300',
  accent: 'border-accent-200 bg-accent-50 text-accent-700 dark:border-accent-800/60 dark:bg-accent-950/50 dark:text-accent-300',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300',
  warning: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300',
  danger: 'border-red-200 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300',
  info: 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900/60 dark:bg-sky-950/40 dark:text-sky-300',
};

export const Badge: React.FC<{ tone?: Tone; children: React.ReactNode; className?: string }> = ({
  tone = 'neutral',
  children,
  className,
}) => (
  <span
    className={cx(
      'inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-2xs font-medium',
      TONES[tone],
      className,
    )}
  >
    {children}
  </span>
);

export const Bullets: React.FC<{ items?: string[]; empty?: string; className?: string }> = ({
  items,
  empty = 'Not specified.',
  className,
}) => {
  if (!items?.length) {
    return <p className="text-sm italic text-zinc-400 dark:text-zinc-500">{empty}</p>;
  }
  return (
    <ul className={cx('space-y-1.5', className)}>
      {items.map((item, index) => (
        <li key={index} className="flex gap-2.5 text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
          <span aria-hidden className="mt-[0.45rem] h-1 w-1 shrink-0 rounded-full bg-zinc-400 dark:bg-zinc-600" />
          <span className="text-pretty">{item}</span>
        </li>
      ))}
    </ul>
  );
};

export const Stat: React.FC<{ label: string; value: React.ReactNode; hint?: string }> = ({ label, value, hint }) => (
  <div className="min-w-0">
    <div className="label">{label}</div>
    <div className="tabular mt-1 truncate text-lg font-semibold text-zinc-900 dark:text-zinc-100">{value}</div>
    {hint && <div className="mt-0.5 truncate text-xs text-zinc-500 dark:text-zinc-400">{hint}</div>}
  </div>
);

/** Horizontal magnitude bar. Used for RICE scores, where relative size is the point. */
export const ScoreBar: React.FC<{ value: number; max: number; tone?: Tone }> = ({ value, max, tone = 'accent' }) => {
  const pct = max > 0 ? Math.max(2, Math.min(100, (value / max) * 100)) : 0;
  const fill =
    tone === 'success' ? 'bg-emerald-500' : tone === 'warning' ? 'bg-amber-500' : tone === 'danger' ? 'bg-red-500' : 'bg-accent-500';
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-150 dark:bg-zinc-800">
      <div className={cx('h-full rounded-full transition-[width] duration-500', fill)} style={{ width: `${pct}%` }} />
    </div>
  );
};

/** Circular 0-10 score. */
export const ScoreRing: React.FC<{ score: number; size?: number; label?: string }> = ({ score, size = 56, label }) => {
  const radius = (size - 6) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(10, score));
  const stroke = clamped >= 8 ? '#10b981' : clamped >= 7 ? '#6366f1' : clamped >= 5 ? '#f59e0b' : '#ef4444';

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={5} className="stroke-zinc-200 dark:stroke-zinc-800" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={5}
          stroke={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - clamped / 10)}
          style={{ transition: 'stroke-dashoffset 700ms cubic-bezier(0.16,1,0.3,1)' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="tabular text-sm font-semibold leading-none text-zinc-900 dark:text-zinc-100">
          {clamped.toFixed(1)}
        </span>
        {label && <span className="mt-0.5 text-[0.5rem] uppercase tracking-wide text-zinc-400">{label}</span>}
      </div>
    </div>
  );
};

export const CopyButton: React.FC<{ text: string; label?: string }> = ({ text, label = 'Copy' }) => {
  const [copied, setCopied] = React.useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard blocked (insecure context or denied permission) */
    }
  };

  return (
    <button type="button" onClick={onCopy} className="btn btn-ghost btn-sm no-print" aria-label={label}>
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
      <span className="hidden sm:inline">{copied ? 'Copied' : label}</span>
    </button>
  );
};

export const MethodBadge: React.FC<{ method: string }> = ({ method }) => {
  const tone: Tone =
    method === 'GET' ? 'info' : method === 'POST' ? 'success' : method === 'DELETE' ? 'danger' : 'warning';
  return (
    <Badge tone={tone} className="w-14 justify-center font-mono">
      {method}
    </Badge>
  );
};

export const priorityTone = (priority: string): Tone =>
  priority === 'High' ? 'danger' : priority === 'Low' ? 'neutral' : 'warning';

export const moscowTone = (moscow: string): Tone =>
  moscow === 'Must' ? 'danger' : moscow === 'Should' ? 'warning' : moscow === 'Could' ? 'info' : 'neutral';
