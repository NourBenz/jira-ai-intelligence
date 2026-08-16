/** Stored-first sprint portfolio focused on the active iteration. */
import { useQuery } from "@tanstack/react-query";
import { CalendarDays, CheckCircle2, CircleDot, Clock3, Flag, Layers3 } from "lucide-react";
import { Link } from "wouter";

import { apiRequest } from "../api/client";
import type { ProjectSprintSummary, SprintSummary } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useProject } from "../project/ProjectContext";

export function SprintsPage() {
  const { projectKey } = useProject();
  const query = useQuery({
    queryKey: ["sprints", projectKey],
    queryFn: () => apiRequest<ProjectSprintSummary>(`/api/stored/analytics/projects/${projectKey}/sprints`),
    enabled: Boolean(projectKey),
  });

  if (query.isLoading) return <LoadingState label="Loading synchronized sprints" />;
  if (query.error) return <ErrorState error={query.error} />;

  const sprints = query.data?.sprints ?? [];
  const active = sprints.filter((sprint) => sprint.state.toLowerCase() === "active");
  const future = sprints.filter((sprint) => sprint.state.toLowerCase() === "future");
  const past = sprints.filter((sprint) => !["active", "future"].includes(sprint.state.toLowerCase())).reverse();

  return (
    <div className="page-stack">
      <PageHeader eyebrow={`Project ${projectKey}`} title="Sprint workspace" description="Focus on the active sprint while keeping planned and completed iterations available." action={<span className="data-badge">Synchronized data</span>} />
      {!sprints.length ? <EmptyState message="No synchronized sprints were found for this project." /> : (
        <>
          <SprintSection className="active-sprint-section" eyebrow="Current delivery" title="Active sprint" empty="No sprint is currently active." sprints={active} featured />
          <SprintSection eyebrow="Planning" title="Future sprints" empty="No future sprints are currently planned." sprints={future} />
          <SprintSection eyebrow="History" title="Completed sprints" empty="No completed sprints are synchronized yet." sprints={past} compact />
        </>
      )}
    </div>
  );
}

function SprintSection({ className = "", eyebrow, title, empty, sprints, featured = false, compact = false }: { className?: string; eyebrow: string; title: string; empty: string; sprints: SprintSummary[]; featured?: boolean; compact?: boolean }) {
  return <section className={`sprint-section ${className}`}>
    <div className="card-heading"><div><span className="section-kicker">{eyebrow}</span><h2>{title}</h2></div><span>{sprints.length} sprint{sprints.length === 1 ? "" : "s"}</span></div>
    {!sprints.length ? <div className="sprint-empty">{empty}</div> : <div className={`sprint-grid ${featured ? "sprint-grid-featured" : ""} ${compact ? "sprint-grid-compact" : ""}`}>{sprints.map((sprint) => <SprintCard sprint={sprint} featured={featured} key={sprint.sprint_id} />)}</div>}
  </section>;
}

function SprintCard({ sprint, featured = false }: { sprint: SprintSummary; featured?: boolean }) {
  const remaining = daysRemaining(sprint.end_date);
  return <Link className={`sprint-card sprint-link ${featured ? "featured-sprint-card" : ""}`} href={`/sprints/${sprint.sprint_id}`}>
    <div className="sprint-topline"><span className={`sprint-state state-${sprint.state.toLowerCase()}`}>{sprint.state}</span><small>#{sprint.sprint_id}</small></div>
    <h2>{sprint.name}</h2>
    <p className="sprint-date"><CalendarDays size={15} /> {formatDate(sprint.start_date)} — {formatDate(sprint.end_date)}</p>
    {featured && <div className="active-sprint-context"><span><Flag size={15} /> Current iteration</span><strong><Clock3 size={15} /> {remaining}</strong></div>}
    <div className="progress-label"><span>Completion</span><strong>{sprint.completion_rate}%</strong></div>
    <div className="progress-track"><span style={{ width: `${Math.min(sprint.completion_rate, 100)}%` }} /></div>
    <div className="sprint-stats">
      <div><Layers3 size={16} /><p><strong>{sprint.issue_count}</strong><span>Committed</span></p></div>
      <div><CheckCircle2 size={16} /><p><strong>{sprint.completed_count}</strong><span>Done</span></p></div>
      <div><CircleDot size={16} /><p><strong>{sprint.open_count}</strong><span>Remaining</span></p></div>
    </div>
    <span className="sprint-open-label">Open sprint details →</span>
  </Link>;
}

function formatDate(value: string | null): string {
  if (!value) return "Not scheduled";
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function daysRemaining(value: string | null): string {
  if (!value) return "No end date";
  const days = Math.ceil((new Date(value).getTime() - Date.now()) / 86_400_000);
  if (days < 0) return `${Math.abs(days)}d overdue`;
  if (days === 0) return "Ends today";
  return `${days}d remaining`;
}
