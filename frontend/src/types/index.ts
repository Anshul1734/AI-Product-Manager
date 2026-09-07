/**
 * Mirrors backend/app/schemas/artifacts.py and the /generate payload shape.
 * Fields the pipeline may omit (a skipped agent, a failed non-critical node)
 * are optional here rather than assumed present.
 */

export type Depth = 'quick' | 'standard' | 'deep';

export interface JobToBeDone {
  situation: string;
  motivation: string;
  outcome: string;
}

export interface ProductVision {
  product_name: string;
  problem_statement: string;
  value_proposition: string;
  target_users: string[];
  core_goals: string[];
  key_features_high_level: string[];
  non_goals: string[];
  jobs_to_be_done: JobToBeDone[];
  assumptions: string[];
}

export interface UserPersona {
  name: string;
  description: string;
  pain_points: string[];
  current_workaround?: string | null;
}

export interface UserStory {
  title: string;
  as_a: string;
  i_want_to: string;
  so_that: string;
  acceptance_criteria: string[];
}

export interface SuccessMetric {
  name: string;
  description: string;
  target: string;
  metric_type: 'leading' | 'lagging' | 'guardrail' | string;
}

export interface PRD {
  problem_statement: string;
  target_users: string[];
  non_goals: string[];
  user_personas: UserPersona[];
  user_stories: UserStory[];
  success_metrics: SuccessMetric[];
  risks: string[];
  open_questions: string[];
}

export interface RiceInputs {
  reach: number;
  impact: number;
  confidence: number;
  effort: number;
  score: number;
}

export interface ScoredFeature {
  name: string;
  description: string;
  rice: RiceInputs;
  justification: string;
  moscow: 'Must' | 'Should' | 'Could' | "Won't" | string;
}

export interface ApiEndpoint {
  name: string;
  method: string;
  endpoint: string;
  description: string;
}

export interface SchemaField {
  name: string;
  type: string;
  constraints: string;
}

export interface DatabaseTable {
  table_name: string;
  fields: SchemaField[];
}

export interface ArchitectureDecision {
  decision: string;
  rationale: string;
  alternatives_considered: string[];
  tradeoffs: string;
}

export interface SystemArchitecture {
  system_design: string;
  architecture_pattern: string;
  tech_stack: Record<string, string>;
  architecture_components: string[];
  api_endpoints: ApiEndpoint[];
  database_schema: DatabaseTable[];
  non_functional_requirements: string[];
  key_decisions: ArchitectureDecision[];
}

export interface Task {
  title: string;
  description: string;
  estimated_hours: number;
}

export interface Story {
  story_title: string;
  description: string;
  acceptance_criteria: string[];
  tasks: Task[];
  story_points: number;
}

export interface Epic {
  epic_name: string;
  description: string;
  priority: 'High' | 'Medium' | 'Low' | string;
  stories: Story[];
}

export interface Tickets {
  epics: Epic[];
  delivery_sequence: string[];
}

export interface Citation {
  marker: string;
  doc_id: string;
  title: string;
  heading: string;
  score: number;
}

export interface AgentStep {
  agent: string;
  label: string;
  status: string;
  model: string;
  duration_seconds: number;
  tool_calls: string[];
  citations: Citation[];
  tokens: number;
  repairs: number;
  note: string;
}

export interface ArtifactQuality {
  artifact: string;
  overall: number;
  completeness: number;
  consistency: number;
  specificity: number;
  feasibility: number;
  issues: string[];
  fix_instructions: string[];
  revised: boolean;
}

export interface Quality {
  overall: number;
  grade: string;
  assessment: string;
  blocking_issues: string[];
  threshold: number;
  artifacts: ArtifactQuality[];
}

export interface RunMeta {
  thread_id: string;
  depth: Depth;
  execution_time: number;
  models: Record<string, string>;
  agent_models: Record<string, string>;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  retrieval: {
    enabled: boolean;
    retrievers: string[];
    corpus_chunks: number;
    dense: boolean;
    sources_cited: number;
  };
  refined_artifacts: string[];
  agents_run: string[];
  errors: Record<string, string>;
}

export interface PlanPayload {
  plan: ProductVision | null;
  prd: PRD | null;
  architecture: SystemArchitecture | null;
  tickets: Tickets | null;
  features_detailed: ScoredFeature[];
  sequencing_rationale: string;
  agent_steps: AgentStep[];
  citations: Citation[];
  quality: Quality | null;
  meta: RunMeta;
}

export interface WorkflowResponse {
  success: boolean;
  message?: string;
  data?: PlanPayload;
  execution_time?: number;
  thread_id?: string;
  error_type?: string;
}

/** Server-Sent Events emitted while the graph runs. */
export type StreamEvent =
  | { type: 'start'; depth: Depth; idea: string }
  | { type: 'node_start'; node: string; label: string }
  | { type: 'node_end'; node: string; label: string; duration: number }
  | { type: 'node_skipped'; node: string; label: string }
  | { type: 'node_failed'; node: string; label: string; critical: boolean; error: string }
  | { type: 'tool_call'; agent: string; tool: string; ok: boolean; round: number; summary: string }
  | { type: 'tool_failed'; agent: string; error: string }
  | { type: 'repair'; agent: string; attempt: number; errors: string }
  | { type: 'complete'; data: PlanPayload }
  | { type: 'error'; message: string; error_type: string };

export interface ValidationResult {
  success: boolean;
  valid: boolean;
  issues: string[];
  suggestions: string[];
  confidence_score: number;
  message?: string;
}

export interface KnowledgeResult {
  marker: string;
  doc_id: string;
  title: string;
  heading: string;
  domain: string;
  authority: string;
  text: string;
  fused_score: number;
  matched_by: string[];
  lexical_rank: number | null;
  dense_rank: number | null;
}

export interface KnowledgeSearchResponse {
  success: boolean;
  query: string;
  results: KnowledgeResult[];
  retrievers: string[];
  message?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  serverless: boolean;
  components: {
    llm: { ready: boolean; provider: string; model: string; fast_model: string; detail?: string | null };
    retrieval: {
      ready: boolean;
      corpus_chunks: number;
      documents: number;
      dense: boolean;
      provider: string;
      detail?: string | null;
    };
    memory: { ready: boolean; stats?: Record<string, unknown> };
  };
}

/** One row in the live agent trace, assembled from stream events. */
export interface TraceEntry {
  node: string;
  label: string;
  status: 'running' | 'done' | 'skipped' | 'failed';
  duration?: number;
  tools: { tool: string; ok: boolean; summary: string }[];
  repairs: number;
  error?: string;
}
