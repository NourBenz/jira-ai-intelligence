/** Canonical delivery-risk view backed by the shared backend rule engine. */
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Ban, Clock3, ShieldCheck, UserRoundX } from "lucide-react";

import { apiRequest } from "../api/client";
import type { ClientConfig, ProjectRiskAnalysis, RiskSignal, Ticket } from "../api/types";
import { JiraIssueLink } from "../components/JiraIssueLink";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useProject } from "../project/ProjectContext";

export function RiskCenterPage() {
  const { projectKey } = useProject();
  const risks = useQuery({ queryKey: ["risks", projectKey], queryFn: () => apiRequest<ProjectRiskAnalysis>(`/api/stored/analytics/projects/${projectKey}/risks`), enabled: Boolean(projectKey) });
  const issues = useQuery({ queryKey: ["issues", projectKey], queryFn: () => apiRequest<Ticket[]>(`/api/stored/issues/${projectKey}`), enabled: Boolean(projectKey) });
  const config = useQuery({ queryKey: ["client-config"], queryFn: () => apiRequest<ClientConfig>("/api/client-config"), staleTime: Infinity });
  if (risks.isLoading || issues.isLoading) return <LoadingState label="Evaluating delivery signals" />;
  if (risks.error || issues.error) return <ErrorState error={risks.error ?? issues.error} />;
  if (!risks.data) return <EmptyState message="No risk evidence is available." />;

  const issueMap = new Map((issues.data ?? []).map((issue) => [issue.key, issue]));
  return <div className="page-stack">
    <PageHeader eyebrow={`Project ${projectKey}`} title="Risk center" description="One authoritative view of measured delivery risks, their evidence, and the recommended next action." action={<span className="data-badge"><ShieldCheck size={14} /> Shared deterministic rules</span>} />
    {risks.data.signals.length ? <>
      <section className="risk-summary-grid">{risks.data.signals.map((signal) => <RiskSummary signal={signal} key={signal.type} />)}</section>
      <section className="risk-explanation-list">{risks.data.signals.map((signal) => {
        const Icon = iconFor(signal.type);
        const affected = signal.issue_keys.map((key) => issueMap.get(key)).filter((issue): issue is Ticket => Boolean(issue));
        return <article className={`surface-card risk-explanation risk-${toneFor(signal)}`} key={signal.type}>
          <header><span className="risk-explanation-icon"><Icon size={19} /></span><div><span className="section-kicker">{signal.severity} severity</span><h2>{signal.label}</h2></div><strong>{signal.issue_keys.length ? `${signal.issue_keys.length} cited` : "Project signal"}</strong></header>
          <div className="risk-explanation-copy"><p><b>Why:</b> {signal.fact}</p><p><b>Recommended action:</b> {signal.recommended_action}</p></div>
          {affected.length > 0 && <div className="risk-issue-list">{affected.map((issue) => <div key={issue.key}><JiraIssueLink issueKey={issue.key} jiraBaseUrl={config.data?.jira_base_url} /><p>{issue.summary ?? "Untitled issue"}</p><span>{issue.assignee ?? "Unassigned"}</span></div>)}</div>}
        </article>;
      })}</section>
    </> : <EmptyState message="No current delivery-risk threshold is exceeded." />}
    <article className="surface-card risk-explanation capacity-risk"><div className="risk-note"><strong>How this is calculated</strong><p>The API, AI risk endpoint, and this page all use the same synchronized Jira fields and the same thresholds. Missing fields are reported as limitations, never invented as risks.</p></div>{risks.data.limitations.length > 0 && <div className="risk-note"><strong>Data limitations</strong><p>{risks.data.limitations.join(" ")}</p></div>}</article>
  </div>;
}

function RiskSummary({ signal }: { signal: RiskSignal }) {
  const Icon = iconFor(signal.type);
  return <article className={`risk-summary risk-${toneFor(signal)}`}><Icon size={20} /><div><span>{signal.label}</span><strong>{signal.issue_keys.length || "!"}</strong><p>{signal.severity} severity</p></div></article>;
}

function iconFor(type: string) {
  if (type === "blocked_work") return Ban;
  if (type === "overdue_work") return Clock3;
  if (type === "unassigned_work") return UserRoundX;
  return AlertTriangle;
}

function toneFor(signal: RiskSignal): "red" | "amber" | "violet" | "blue" {
  if (signal.type === "blocked_work") return "red";
  if (signal.type === "overdue_work") return "amber";
  if (signal.type === "unassigned_work") return "violet";
  return "blue";
}
