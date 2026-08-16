export type UserRole = "viewer" | "admin";

export interface CurrentUser {
  id: number;
  username: string;
  first_name?: string | null;
  last_name?: string | null;
  email?: string | null;
  role: UserRole;
  administered_project_keys: string[];
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in_seconds: number;
}

export interface Project {
  id: string;
  key: string;
  name: string;
}

export interface ScrumTeam {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AccessUser {
  id: number;
  username: string;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  role: UserRole;
  is_active: boolean;
}

export interface TeamMember {
  user_id: number;
  username: string;
  display_name: string;
  scrum_role: string | null;
  is_active: boolean;
}

export interface ProjectAccessSummary {
  project_key: string;
  project_name: string;
  owning_team: ScrumTeam | null;
  team_members: TeamMember[];
  project_administrator_ids: number[];
}

export interface Ticket {
  id: string | null;
  key: string;
  summary: string | null;
  description: unknown;
  status: string | null;
  status_category: string | null;
  priority: string | null;
  issue_type: string | null;
  assignee: string | null;
  reporter: string | null;
  created: string | null;
  updated: string | null;
  resolution_date: string | null;
  due_date: string | null;
  story_points: number | null;
  labels: string[];
}

export interface ProjectOverview {
  project_key: string;
  total_issues: number;
  status_counts: Record<string, number>;
  priority_counts: Record<string, number>;
  issue_type_counts: Record<string, number>;
  workload_by_assignee: Record<string, number>;
  overdue_count: number;
  unassigned_count: number;
  completed_count: number;
  open_count: number;
  completion_rate: number;
}

export interface ProjectActivity {
  project_key: string;
  average_issue_age_days: number;
  oldest_open_issues: Ticket[];
  recently_updated_issues: Ticket[];
  stale_days: number;
  stale_issues: Ticket[];
}

export interface ProjectInsights {
  project_key: string;
  weeks: number;
  created_by_week: Record<string, number>;
  label_counts: Record<string, number>;
  workload_by_assignee_status: Record<string, Record<string, number>>;
  workload_by_assignee_priority: Record<string, Record<string, number>>;
  overdue_by_assignee: Record<string, number>;
  overdue_by_priority: Record<string, number>;
  blocked_count: number;
  blocked_issues: Ticket[];
}

export interface ProjectHistory {
  project_key: string;
  weeks: number;
  completed_by_week: Record<string, number>;
  completed_count: number;
  average_lead_time_days: number | null;
  average_cycle_time_days: number | null;
  lead_time_sample_size: number;
  cycle_time_sample_size: number;
}

export interface SprintSummary {
  sprint_id: number;
  board_id: number | null;
  name: string;
  state: string;
  start_date: string | null;
  end_date: string | null;
  issue_count: number;
  completed_count: number;
  open_count: number;
  completion_rate: number;
}

export interface ProjectSprintSummary {
  project_key: string;
  total_sprints: number;
  sprints: SprintSummary[];
}

export interface AIResponse {
  answer: string;
  risks?: string[];
  recommendations?: string[];
  source_issue_keys: string[];
  limitations: string[];
  project_key: string;
  model: string;
  grounded: boolean;
  retrieved_chunks?: number;
  evidence?: RAGSearchResult[];
}

export interface RiskSignal {
  type: string;
  label: string;
  severity: "low" | "medium" | "high";
  fact: string;
  issue_keys: string[];
  recommended_action: string;
}

export interface ProjectRiskAnalysis {
  project_key: string;
  signals: RiskSignal[];
  limitations: string[];
}

export interface SyncRun {
  id: number;
  project_key: string;
  mode: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  projects_processed: number;
  issues_processed: number;
  sprints_processed: number;
  changelogs_processed: number;
  comments_processed: number;
  error_message: string | null;
}

export interface SyncChange {
  issue_key: string;
  change_type: "created" | "updated" | "unchanged";
  changed_fields: string[];
  before_values: Record<string, unknown>;
  after_values: Record<string, unknown>;
  changelogs_inspected: number;
  comments_inspected: number;
}

export interface SyncRunDetail extends SyncRun {
  changes: SyncChange[];
}

export interface SyncFreshness {
  project_key: string;
  last_completed_sync_id: number | null;
  completed_at: string | null;
  sync_required: boolean;
  jira_checked_at: string | null;
  jira_latest_issue_key: string | null;
  jira_latest_updated_at: string | null;
  update_check_error: string | null;
}

export interface ClientConfig {
  jira_base_url: string;
}

export interface RAGSearchResult {
  chunk_id: string;
  text: string;
  metadata: {
    project_key?: string;
    issue_key?: string;
    content_type?: string;
    chunk_index?: number;
    source_updated_at?: string;
    [key: string]: unknown;
  };
  similarity: number;
}

export interface RAGSearchResponse {
  project_key: string;
  query: string;
  results: RAGSearchResult[];
  returned: number;
  embedding_model: string;
}

export interface RAGIndexStatus {
  project_key: string;
  issues_indexed: number;
  chunks_indexed: number;
  last_indexed_at: string | null;
  latest_source_update: string | null;
}

export interface RAGIndexResponse {
  project_key: string;
  issues_processed: number;
  chunks_indexed: number;
  embedding_model: string;
}

export interface SprintPerformance {
  sprint_id: number;
  sprint_name: string;
  throughput: number;
  committed_issue_count: number;
  completed_story_points: number | null;
  committed_story_points: number | null;
  scope_added_issue_keys: string[];
  scope_removed_issue_keys: string[];
  carryover_issue_keys: string[];
}
