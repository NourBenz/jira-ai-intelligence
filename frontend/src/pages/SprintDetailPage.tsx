import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "wouter";

import { apiRequest } from "../api/client";
import type { ClientConfig, SprintPerformance, Ticket } from "../api/types";
import { JiraIssueLink } from "../components/JiraIssueLink";
import { PageHeader } from "../components/PageHeader";
import { PriorityBadge } from "../components/PriorityBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/States";

export function SprintDetailPage() {
  const { id = "" } = useParams<{ id: string }>();
  const sprintId = Number(id);
  const issues = useQuery({ queryKey: ["sprint-issues", sprintId], queryFn: () => apiRequest<Ticket[]>(`/api/stored/sprints/${sprintId}/issues`), enabled: Number.isInteger(sprintId) });
  const performance = useQuery({ queryKey: ["sprint-performance", sprintId], queryFn: () => apiRequest<SprintPerformance>(`/api/stored/analytics/sprints/${sprintId}/performance`), enabled: Number.isInteger(sprintId) });
  const config = useQuery({ queryKey: ["client-config"], queryFn: () => apiRequest<ClientConfig>("/api/client-config"), staleTime: Infinity });
  if (issues.isLoading) return <LoadingState label="Loading sprint issues" />;
  if (issues.error) return <ErrorState error={issues.error} />;
  const data = issues.data ?? [];
  return <div className="page-stack print-report">
    <Link className="back-link no-print" href="/sprints"><ArrowLeft size={15} /> Back to sprints</Link>
    <PageHeader eyebrow={`Sprint #${sprintId}`} title={performance.data?.sprint_name ?? "Sprint detail"} description="Issue membership, delivery outcome, scope changes, and carryover." />
    {performance.data && <section className="sprint-performance-grid"><article><span>Throughput</span><strong>{performance.data.throughput}</strong></article><article><span>Committed issues</span><strong>{performance.data.committed_issue_count}</strong></article><article><span>Scope added</span><strong>{performance.data.scope_added_issue_keys.length}</strong></article><article><span>Carryover</span><strong>{performance.data.carryover_issue_keys.length}</strong></article></section>}
    {!data.length ? <EmptyState message="No issues belong to this sprint." /> : <section className="table-panel"><div className="issue-table-header sprint-detail-header"><span>Issue</span><span>Status</span><span>Priority</span><span>Assignee</span></div>{data.map((issue) => <article className="issue-row sprint-detail-row" key={issue.key}><div className="issue-title"><JiraIssueLink issueKey={issue.key} jiraBaseUrl={config.data?.jira_base_url} /><p>{issue.summary}</p><small>{issue.issue_type}</small></div><div><span className={`status-pill status-${(issue.status_category ?? "unknown").toLowerCase().replaceAll(" ", "-")}`}>{issue.status}</span></div><div><PriorityBadge priority={issue.priority} /></div><div>{issue.assignee ?? <span className="muted">Unassigned</span>}</div></article>)}</section>}
  </div>;
}
