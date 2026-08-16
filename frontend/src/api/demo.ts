import type {
  AIResponse,
  ProjectActivity,
  ProjectHistory,
  ProjectInsights,
  ProjectOverview,
  ProjectRiskAnalysis,
  ProjectSprintSummary,
  RAGIndexResponse,
  RAGIndexStatus,
  RAGSearchResponse,
  SprintPerformance,
  SyncRun,
  Ticket,
} from "./types";

export const DEMO_MODE_KEY = "jira-ai-demo-mode";
export const DEMO_UNHANDLED = Symbol("demo-unhandled");

export function isDemoMode(): boolean {
  return localStorage.getItem(DEMO_MODE_KEY) === "true";
}

const tickets: Ticket[] = [
  issue("DEMO-101", "Harden authentication token refresh", "In Progress", "High", "Amina", ["security"]),
  issue("DEMO-102", "Resolve payment API timeout", "To Do", "Highest", null, ["blocked", "backend"], "2026-07-20"),
  issue("DEMO-103", "Improve sprint analytics accuracy", "In Review", "High", "Leo", ["analytics"]),
  issue("DEMO-104", "Design release readiness dashboard", "Done", "Medium", "Sara", ["frontend"]),
  issue("DEMO-105", "Fix Jira API pagination", "To Do", "Medium", "Amina", ["integration"]),
  issue("DEMO-106", "Document incident recovery procedure", "Done", "Medium", "Nadia", ["docs"]),
  issue("DEMO-107", "Add customer notification preferences", "To Do", "Low", "Leo", ["frontend"]),
  issue("DEMO-108", "Migrate legacy webhook processing", "In Progress", "High", "Amina", ["backend"], "2026-07-26"),
  issue("DEMO-109", "Validate mobile issue deep links", "To Do", "Medium", "Sara", ["mobile"]),
  issue("DEMO-110", "Review production access matrix", "Done", "High", "Nadia", ["security"]),
  issue("DEMO-111", "Prevent AI from inventing Jira tickets", "To Do", "Medium", "Amina", ["ai-safety"]),
  issue("DEMO-112", "Prepare sprint review evidence", "Done", "Low", "Leo", ["demo"]),
];

const overview: ProjectOverview = {
  project_key: "DEMO", total_issues: 12, open_count: 8, completed_count: 4,
  completion_rate: 33.33, overdue_count: 2, unassigned_count: 1,
  status_counts: { "To Do": 5, "In Progress": 2, "In Review": 1, Done: 4 },
  priority_counts: { Highest: 1, High: 4, Medium: 5, Low: 2 },
  issue_type_counts: { Task: 8, Bug: 3, Story: 1 },
  workload_by_assignee: { Amina: 4, Leo: 3, Sara: 2, Nadia: 2, Unassigned: 1 },
};

const activity: ProjectActivity = {
  project_key: "DEMO", average_issue_age_days: 12.4, stale_days: 14,
  stale_issues: [tickets[1], tickets[7]], oldest_open_issues: [tickets[1], tickets[7], tickets[0]],
  recently_updated_issues: [tickets[2], tickets[8], tickets[4]],
};

const insights: ProjectInsights = {
  project_key: "DEMO", weeks: 8,
  created_by_week: { "2026-06-15": 1, "2026-06-22": 2, "2026-06-29": 1, "2026-07-06": 3, "2026-07-13": 2, "2026-07-20": 2, "2026-07-27": 1 },
  label_counts: { security: 2, backend: 2, frontend: 2, analytics: 1, quality: 1 },
  workload_by_assignee_status: { Amina: { "To Do": 2, "In Progress": 2 }, Leo: { "To Do": 1, "In Review": 1, Done: 1 }, Sara: { "To Do": 1, Done: 1 }, Nadia: { Done: 2 }, Unassigned: { "To Do": 1 } },
  workload_by_assignee_priority: { Amina: { High: 2, Medium: 2 }, Leo: { High: 1, Medium: 1, Low: 1 }, Sara: { Medium: 2 }, Nadia: { High: 1, Medium: 1 }, Unassigned: { Highest: 1 } },
  overdue_by_assignee: { Unassigned: 1, Amina: 1 }, overdue_by_priority: { Highest: 1, High: 1 },
  blocked_count: 1, blocked_issues: [tickets[1]],
};

const history: ProjectHistory = {
  project_key: "DEMO", weeks: 8, completed_count: 4,
  completed_by_week: { "2026-06-15": 0, "2026-06-22": 1, "2026-06-29": 0, "2026-07-06": 1, "2026-07-13": 0, "2026-07-20": 1, "2026-07-27": 1 },
  average_lead_time_days: 8.6, average_cycle_time_days: 3.2, lead_time_sample_size: 4, cycle_time_sample_size: 4,
};

const sprints: ProjectSprintSummary = {
  project_key: "DEMO", total_sprints: 3, sprints: [
    { sprint_id: 901, board_id: 90, name: "Platform Sprint 14", state: "active", start_date: "2026-07-20T08:00:00Z", end_date: "2026-08-03T17:00:00Z", issue_count: 5, completed_count: 2, open_count: 3, completion_rate: 40 },
    { sprint_id: 900, board_id: 90, name: "Platform Sprint 13", state: "closed", start_date: "2026-07-06T08:00:00Z", end_date: "2026-07-20T17:00:00Z", issue_count: 4, completed_count: 3, open_count: 1, completion_rate: 75 },
    { sprint_id: 902, board_id: 90, name: "Platform Sprint 15", state: "future", start_date: "2026-08-03T08:00:00Z", end_date: "2026-08-17T17:00:00Z", issue_count: 3, completed_count: 0, open_count: 3, completion_rate: 0 },
  ],
};

const syncRuns: SyncRun[] = [{ id: 42, project_key: "DEMO", mode: "incremental", status: "completed", started_at: "2026-08-01T08:41:00Z", completed_at: "2026-08-01T08:41:07Z", projects_processed: 1, issues_processed: 3, sprints_processed: 3, changelogs_processed: 11, comments_processed: 4, error_message: null }];

export async function getDemoResponse(path: string, options: RequestInit): Promise<unknown | typeof DEMO_UNHANDLED> {
  if (!isDemoMode() || path.startsWith("/api/auth/")) return DEMO_UNHANDLED;
  await new Promise((resolve) => setTimeout(resolve, 180));
  if (path === "/api/projects") return [{ id: "demo-project", key: "DEMO", name: "Safe Demo Project" }];
  if (path === "/api/client-config") return { jira_base_url: "https://example.atlassian.net" };
  if (path.startsWith("/api/stored/issues/")) return tickets;
  if (path.includes("/overview")) return overview;
  if (path.includes("/activity")) return activity;
  if (path.includes("/insights")) return insights;
  if (path.includes("/history")) return history;
  if (path.includes("/risks")) return demoRisks;
  if (path.endsWith("/sprints")) return sprints;
  if (/\/api\/(?:stored\/)?sprints\/\d+\/issues/.test(path)) {
    const parts = path.split("/");
    const sprintIndex = parts.indexOf("sprints") + 1;
    return sprintIssues(Number(parts[sprintIndex]));
  }
  if (path.includes("/analytics/sprints/") && path.endsWith("/performance")) return sprintPerformance(Number(path.split("/")[5]));
  if (path === "/api/sync/runs?limit=20") return syncRuns;
  if (path.includes("/rag/projects/") && path.endsWith("/status")) return { project_key: "DEMO", issues_indexed: 12, chunks_indexed: 28, last_indexed_at: "2026-08-01T08:42:12Z", latest_source_update: "2026-08-01T08:40:31Z" } satisfies RAGIndexStatus;
  if (path.includes("/rag/projects/") && path.endsWith("/index")) return { project_key: "DEMO", issues_processed: 12, chunks_indexed: 28, embedding_model: "nomic-embed-text" } satisfies RAGIndexResponse;
  if (path.includes("/rag/projects/") && path.endsWith("/search")) return demoSearch(options);
  if (path.includes("/rag/projects/") && path.endsWith("/ask")) return demoAnswer(options, false);
  if (path.includes("/ai/projects/") && path.endsWith("/ask")) return demoAnswer(options, true);
  if (path.startsWith("/api/sync/projects/")) return { ...syncRuns[0], id: 43, started_at: new Date().toISOString(), completed_at: new Date().toISOString() };
  return DEMO_UNHANDLED;
}

function issue(key: string, summary: string, status: string, priority: string, assignee: string | null, labels: string[], dueDate: string | null = null): Ticket {
  const done = status === "Done";
  return { id: key.replace("DEMO-", "20"), key, summary, description: `${summary}. This safe demonstration issue contains no company information.`, status, status_category: done ? "Done" : status === "To Do" ? "To Do" : "In Progress", priority, issue_type: key === "DEMO-102" ? "Bug" : "Task", assignee, reporter: "Demo Product Owner", created: "2026-07-10T09:00:00Z", updated: "2026-07-30T14:30:00Z", resolution_date: done ? "2026-07-29T16:00:00Z" : null, due_date: dueDate, story_points: 3, labels };
}

function sprintIssues(id: number): Ticket[] { return id === 901 ? tickets.slice(0, 5) : id === 900 ? tickets.slice(5, 9) : tickets.slice(9, 12); }
function sprintPerformance(id: number): SprintPerformance { const sprint = sprints.sprints.find((item) => item.sprint_id === id) ?? sprints.sprints[0]; return { sprint_id: id, sprint_name: sprint.name, throughput: sprint.completed_count, committed_issue_count: sprint.issue_count, completed_story_points: sprint.completed_count * 3, committed_story_points: sprint.issue_count * 3, scope_added_issue_keys: id === 901 ? ["DEMO-105"] : [], scope_removed_issue_keys: [], carryover_issue_keys: id === 900 ? ["DEMO-108"] : [] }; }

function bodyQuestion(options: RequestInit): string { try { return JSON.parse(String(options.body ?? "{}")).question ?? JSON.parse(String(options.body ?? "{}")).query ?? "project evidence"; } catch { return "project evidence"; } }
function rankedDemoTickets(query: string): Ticket[] {
  const normalized = query.toLowerCase();
  if (normalized.includes("pagination")) return [tickets[4], tickets[2], tickets[0]];
  if (normalized.includes("invent") || normalized.includes("hallucin") || normalized.includes("ai reliability")) return [tickets[10], tickets[2], tickets[0]];
  if (normalized.includes("auth") || normalized.includes("token")) return [tickets[0], tickets[9], tickets[1]];
  return [tickets[1], tickets[0], tickets[2]];
}

function demoSearch(options: RequestInit): RAGSearchResponse {
  const query = bodyQuestion(options);
  return { project_key: "DEMO", query, returned: 3, embedding_model: "nomic-embed-text", results: rankedDemoTickets(query).map((item, index) => ({ chunk_id: `demo-chunk-${item.key}`, text: `${item.summary}. ${String(item.description)}`, metadata: { project_key: "DEMO", issue_key: item.key, content_type: "summary_and_description", chunk_index: 0, source_updated_at: item.updated ?? undefined }, similarity: 0.92 - index * 0.07 })) };
}

function demoAnswer(options: RequestInit, risk: boolean): AIResponse {
  if (risk) return { answer: "The main delivery risks are one blocked unassigned issue, two overdue items, and workload concentration around Amina.", risks: ["Blocked and unassigned work", "Overdue delivery", "Workload concentration"], recommendations: ["Assign DEMO-102 and remove its blocker.", "Review the two overdue items during the next stand-up.", "Redistribute one open issue from Amina to a teammate with capacity."], source_issue_keys: ["DEMO-102", "DEMO-108"], limitations: ["This is safe demonstration data, not company Jira data."], project_key: "DEMO", model: "deterministic-risk-engine", grounded: true };
  const question = bodyQuestion(options);
  const bestMatch = rankedDemoTickets(question)[0];
  const search = demoSearch(options);
  return { answer: `${bestMatch.key} is the strongest indexed match: ${bestMatch.summary}.`, source_issue_keys: [bestMatch.key], limitations: ["This answer uses safe demonstration evidence."], project_key: "DEMO", model: "llama3.2", retrieved_chunks: search.returned, grounded: true, evidence: search.results.filter((result) => result.metadata.issue_key === bestMatch.key) };
}

const demoRisks: ProjectRiskAnalysis = {
  project_key: "DEMO",
  signals: [
    { type: "blocked_work", label: "Blocked work", severity: "high", fact: "1 open issue(s) are blocked.", issue_keys: ["DEMO-102"], recommended_action: "Review DEMO-102, identify the blocker owner, and agree on the next unblock action." },
    { type: "overdue_work", label: "Overdue work", severity: "high", fact: "2 open issue(s) are overdue.", issue_keys: ["DEMO-102", "DEMO-108"], recommended_action: "Review the overdue issues with their owners and replan them in Jira." },
    { type: "unassigned_work", label: "Unassigned work", severity: "medium", fact: "1 open issue(s) are unassigned.", issue_keys: ["DEMO-102"], recommended_action: "Assign an accountable owner to DEMO-102." },
  ],
  limitations: [],
};
