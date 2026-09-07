/**
 * Direct window onto the retrieval layer.
 *
 * The same corpus and the same hybrid query path the agents use, exposed so the
 * grounding is inspectable rather than a claim: you can see which passages a
 * question returns and which retriever found each one.
 */
import React from 'react';
import { Loader2, Search } from 'lucide-react';
import type { KnowledgeResult } from '../types';
import { api } from '../lib/api';
import { Badge, Card, EmptyState, SectionTitle, cx } from './ui/Primitives';

const DOMAINS = [
  'discovery',
  'prioritization',
  'requirements',
  'metrics',
  'architecture',
  'data',
  'delivery',
];

const SUGGESTIONS = [
  'How is RICE impact scored?',
  'When should I choose a modular monolith over microservices?',
  'How do I write acceptance criteria that are testable?',
  'What makes a good north star metric?',
  'How do I split a story that is too large?',
];

const KnowledgeExplorer: React.FC = () => {
  const [query, setQuery] = React.useState('');
  const [domain, setDomain] = React.useState<string>('');
  const [results, setResults] = React.useState<KnowledgeResult[] | null>(null);
  const [retrievers, setRetrievers] = React.useState<string[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [corpus, setCorpus] = React.useState<{ documents: number; chunks: number; dense: boolean } | null>(null);

  React.useEffect(() => {
    api
      .knowledgeDocuments()
      .then((response) =>
        setCorpus({
          documents: response.data.documents.length,
          chunks: response.data.chunk_count,
          dense: response.data.dense_enabled,
        }),
      )
      .catch(() => setCorpus(null));
  }, []);

  const search = async (event: React.FormEvent) => {
    event.preventDefault();
    if (query.trim().length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.searchKnowledge(query.trim(), 5, domain || undefined);
      setResults(response.results);
      setRetrievers(response.retrievers);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Search failed');
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <SectionTitle
          title="Knowledge base"
          icon={<Search className="h-3.5 w-3.5" />}
          hint={
            corpus
              ? `${corpus.documents} documents · ${corpus.chunks} indexed passages · ${
                  corpus.dense ? 'hybrid BM25 + dense retrieval' : 'BM25 lexical retrieval'
                }`
              : 'Loading corpus…'
          }
        />

        <form onSubmit={search} className="flex flex-col gap-2 sm:flex-row">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ask the same corpus the agents consult…"
            className="field flex-1"
            aria-label="Knowledge query"
          />
          <select
            value={domain}
            onChange={(event) => setDomain(event.target.value)}
            className="field sm:w-44"
            aria-label="Domain filter"
          >
            <option value="">All domains</option>
            {DOMAINS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <button type="submit" disabled={loading || query.trim().length < 2} className="btn btn-primary btn-md">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Search
          </button>
        </form>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => setQuery(suggestion)}
              className="chip transition-colors hover:border-accent-300 hover:text-accent-700 dark:hover:border-accent-700 dark:hover:text-accent-300"
            >
              {suggestion}
            </button>
          ))}
        </div>

        {retrievers.length > 0 && (
          <div className="mt-3 flex items-center gap-1.5">
            <span className="label">Matched by</span>
            {retrievers.map((name) => (
              <Badge key={name} tone="accent">
                {name}
              </Badge>
            ))}
          </div>
        )}
      </Card>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-300">
          {error}
        </div>
      )}

      {results !== null &&
        (results.length ? (
          <div className="space-y-3">
            {results.map((result) => (
              <Card key={result.marker}>
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-2xs font-semibold text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
                    {result.marker}
                  </span>
                  <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{result.title}</h4>
                  <span className="text-xs text-zinc-400">›</span>
                  <span className="text-xs text-zinc-600 dark:text-zinc-300">{result.heading}</span>
                </div>

                <div className="mb-3 flex flex-wrap gap-1.5">
                  <Badge>{result.domain}</Badge>
                  <Badge tone="info">{result.authority}</Badge>
                  {result.matched_by.map((by) => (
                    <Badge key={by} tone="accent">
                      {by}
                      {by === 'bm25' && result.lexical_rank ? ` #${result.lexical_rank}` : ''}
                      {by === 'dense' && result.dense_rank ? ` #${result.dense_rank}` : ''}
                    </Badge>
                  ))}
                  <span className="tabular ml-auto text-2xs text-zinc-400" title="Reciprocal-rank-fusion score">
                    RRF {result.fused_score.toFixed(4)}
                  </span>
                </div>

                <p className={cx('whitespace-pre-line text-sm leading-relaxed text-zinc-700 dark:text-zinc-300')}>
                  {result.text}
                </p>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState message="No passages matched that query." />
        ))}
    </div>
  );
};

export default KnowledgeExplorer;
