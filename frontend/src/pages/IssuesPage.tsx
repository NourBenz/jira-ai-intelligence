/** Read-only stored Jira issue explorer with operational quick filters. */
import { useQuery } from "@tanstack/react-query";
import { FilterX, Info, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { apiRequest } from "../api/client";
import type { ClientConfig, Ticket } from "../api/types";
import { JiraIssueLink } from "../components/JiraIssueLink";
import { PageHeader } from "../components/PageHeader";
import { PriorityBadge } from "../components/PriorityBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useProject } from "../project/ProjectContext";

type QuickFilter = "all" | "overdue" | "unassigned" | "stale" | "blocked";

export function IssuesPage() {
  const { projectKey } = useProject();
  const initialQuick = new URLSearchParams(window.location.search).get("quick") as QuickFilter | null;
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("All");
  const [priority, setPriority] = useState("All");
  const [assignee, setAssignee] = useState("All");
  const [issueType, setIssueType] = useState("All");
  const [quick, setQuick] = useState<QuickFilter>(["overdue", "unassigned", "stale", "blocked"].includes(initialQuick ?? "") ? initialQuick! : "all");
  const query = useQuery({ queryKey: ["issues", projectKey], queryFn: () => apiRequest<Ticket[]>(`/api/stored/issues/${projectKey}`), enabled: Boolean(projectKey) });
  const config = useQuery({ queryKey: ["client-config"], queryFn: () => apiRequest<ClientConfig>("/api/client-config"), staleTime: Infinity });

  const source = query.data ?? [];
  const options = useMemo(() => ({
    statuses: unique(source.map((issue) => issue.status ?? "Unknown")),
    priorities: unique(source.map((issue) => issue.priority ?? "None")),
    assignees: unique(source.map((issue) => issue.assignee ?? "Unassigned")),
    types: unique(source.map((issue) => issue.issue_type ?? "Issue")),
  }), [source]);
  const issues = useMemo(() => {
    const term = search.trim().toLowerCase();
    return source.filter((issue) => {
      if (status !== "All" && (issue.status ?? "Unknown") !== status) return false;
      if (priority !== "All" && (issue.priority ?? "None") !== priority) return false;
      if (assignee !== "All" && (issue.assignee ?? "Unassigned") !== assignee) return false;
      if (issueType !== "All" && (issue.issue_type ?? "Issue") !== issueType) return false;
      if (term && !`${issue.key} ${issue.summary ?? ""}`.toLowerCase().includes(term)) return false;
      return matchesQuickFilter(issue, quick);
    });
  }, [assignee, issueType, priority, quick, search, source, status]);

  const resetFilters = () => { setSearch(""); setStatus("All"); setPriority("All"); setAssignee("All"); setIssueType("All"); setQuick("all"); };
  if (query.isLoading) return <LoadingState label="Loading stored issues" />;
  if (query.error) return <ErrorState error={query.error} />;

  return <div className="page-stack">
    <PageHeader eyebrow={`Project ${projectKey}`} title="Issue explorer" description="Find synchronized Jira work by ownership, workflow state, priority, type, or delivery warning." />
    <div className="context-guidance"><Info size={17} /><div><strong>Read-only Jira snapshot</strong><p>Use these filters to find work quickly. Open the issue key to assign, transition, comment, or edit it in Jira.</p></div></div>
    <section className="issue-quick-filters" aria-label="Issue quick filters">
      {(["all", "overdue", "unassigned", "stale", "blocked"] as QuickFilter[]).map((item) => <button className={quick === item ? "active" : ""} key={item} onClick={() => setQuick(item)} type="button">{quickLabel(item)}</button>)}
    </section>
    <section className="filter-bar advanced-filter-bar">
      <label className="compact-filter issue-search-filter"><span>Search</span><div className="search-field"><Search size={17} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search key or summary" /></div></label>
      <FilterSelect label="Status" value={status} values={options.statuses} onChange={setStatus} />
      <FilterSelect label="Priority" value={priority} values={options.priorities} onChange={setPriority} />
      <FilterSelect label="Assignee" value={assignee} values={options.assignees} onChange={setAssignee} />
      <FilterSelect label="Issue type" value={issueType} values={options.types} onChange={setIssueType} />
      <button className="filter-reset" onClick={resetFilters} type="button"><FilterX size={15} /> Reset</button>
      <span>{issues.length} of {source.length} issues</span>
    </section>
    {!issues.length ? <EmptyState message="No issues match these filters." /> : <section className="table-panel">
      <div className="issue-table-header"><span>Issue</span><span>Status</span><span>Priority</span><span>Assignee</span><span>Updated</span></div>
      {issues.map((issue) => <article className="issue-row" key={issue.key}>
        <div className="issue-title"><JiraIssueLink issueKey={issue.key} jiraBaseUrl={config.data?.jira_base_url} /><p>{issue.summary || "Untitled issue"}</p><small>{issue.issue_type ?? "Issue"}</small></div>
        <div><span className={`status-pill status-${(issue.status_category ?? "unknown").toLowerCase().replaceAll(" ", "-")}`}>{issue.status ?? "Unknown"}</span></div>
        <div><PriorityBadge priority={issue.priority} /></div><div>{issue.assignee ?? <span className="muted">Unassigned</span>}</div><div>{issue.updated ? new Date(issue.updated).toLocaleDateString() : "—"}</div>
      </article>)}
    </section>}
  </div>;
}

function FilterSelect({ label, value, values, onChange }: { label: string; value: string; values: string[]; onChange: (value: string) => void }) {
  return <label className="compact-filter"><span>{label}</span><select aria-label={`Filter by ${label.toLowerCase()}`} value={value} onChange={(event) => onChange(event.target.value)}><option>All</option>{values.map((item) => <option key={item}>{item}</option>)}</select></label>;
}

function unique(values: string[]): string[] { return [...new Set(values)].sort((a, b) => a.localeCompare(b)); }
function isDone(issue: Ticket): boolean { return issue.status_category?.toLowerCase() === "done"; }
function matchesQuickFilter(issue: Ticket, filter: QuickFilter): boolean {
  if (filter === "all") return true;
  if (filter === "unassigned") return !isDone(issue) && !issue.assignee;
  if (filter === "overdue") return !isDone(issue) && Boolean(issue.due_date) && new Date(`${issue.due_date}T23:59:59`).getTime() < Date.now();
  if (filter === "stale") return !isDone(issue) && Boolean(issue.updated) && Date.now() - new Date(issue.updated!).getTime() >= 14 * 86_400_000;
  return !isDone(issue) && ([...(issue.labels ?? []), issue.status ?? ""].some((value) => value.toLowerCase().includes("block")));
}
function quickLabel(filter: QuickFilter): string { return ({ all: "All issues", overdue: "Overdue", unassigned: "Unassigned", stale: "Stale 14+ days", blocked: "Blocked" })[filter]; }
