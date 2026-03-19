export interface ProductVision {
  product_name: string;
  problem_statement: string;
  target_users: string[];
  core_goals: string[];
  key_features_high_level: string[];
}

export interface UserPersona {
  name: string;
  description: string;
  pain_points: string[];
}

export interface UserStory {
  title: string;
  as_a: string;
  i_want_to: string;
  so_that: string;
}

export interface SuccessMetric {
  name: string;
  description: string;
  target: string;
}

export interface PRD {
  problem_statement: string;
  target_users: string[];
  user_personas: UserPersona[];
  user_stories: UserStory[];
  success_metrics: SuccessMetric[];
}

export interface APIEndpoint {
  name: string;
  method: string;
  endpoint: string;
  description: string;
}

export interface DatabaseField {
  name: string;
  type: string;
  constraints: string;
}

export interface DatabaseTable {
  table_name: string;
  fields: DatabaseField[];
}

export interface SystemArchitecture {
  system_design: string;
  tech_stack: {
    frontend: string;
    backend: string;
    database: string;
    infrastructure: string;
  };
  architecture_components: string[];
  api_endpoints: APIEndpoint[];
  database_schema: DatabaseTable[];
}

export interface Task {
  title: string;
  description: string;
  estimated_hours: string;
}

export interface Story {
  story_title: string;
  description: string;
  acceptance_criteria: string[];
  tasks: Task[];
}

export interface Epic {
  epic_name: string;
  description: string;
  stories: Story[];
}

export interface Tickets {
  epics: Epic[];
}

export interface WorkflowOutput {
  plan: ProductVision;
  prd: PRD;
  architecture: SystemArchitecture;
  tickets: Tickets;
}

export interface WorkflowResponse {
  success: boolean;
  data?: WorkflowOutput;
  state?: any;
  error?: string;
  execution_time?: number;
  thread_id?: string;
}

export interface ProductIdeaRequest {
  idea: string;
  thread_id?: string;
  use_legacy?: boolean;
}

export interface BatchRequest {
  product_ideas: string[];
  thread_id?: string;
  use_legacy?: boolean;
}

export interface BatchResponse {
  success: boolean;
  results: Array<{
    index: number;
    product_idea: string;
    success: boolean;
    data?: any;
    error?: string;
  }>;
  errors: string[];
  total_execution_time?: number;
  processed_count: number;
  failed_count: number;
}

export interface AnalyticsResponse {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  average_execution_time: number;
  most_common_steps: Record<string, number>;
  active_threads: number;
}

export interface HealthResponse {
  status: string;
  message: string;
  workflow_engine: string;
}

export interface WebSocketMessage {
  type: string;
  data?: any;
  step?: string;
  timestamp?: number;
  message?: string;
  idea?: string;
  thread_id?: string;
  error?: string;
}
