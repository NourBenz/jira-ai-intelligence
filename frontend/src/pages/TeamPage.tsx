import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useProjectSignals } from "../hooks/useProjectSignals";
import { useProject } from "../project/ProjectContext";

const COLORS = ["#f4a640", "#3976e8", "#8b5cf6", "#20a879", "#ef6575"];

export function TeamPage() {
  const { projectKey } = useProject();
  const { insights, isLoading, error } = useProjectSignals(projectKey);
  const statuses = useMemo(() => [...new Set(Object.values(insights.data?.workload_by_assignee_status ?? {}).flatMap(Object.keys))], [insights.data]);
  const rows = useMemo(() => Object.entries(insights.data?.workload_by_assignee_status ?? {}).map(([assignee, counts]) => ({ assignee, total: Object.values(counts).reduce((sum, count) => sum + count, 0), ...counts })).sort((a, b) => b.total - a.total), [insights.data]);
  if (isLoading) return <LoadingState label="Loading team workload" />;
  if (error) return <ErrorState error={error} />;
  if (!rows.length) return <EmptyState message="No assignee workload is available." />;
  return <div className="page-stack">
    <PageHeader eyebrow={`Project ${projectKey}`} title="Team workload" description="Compare ownership and workflow state before sprint planning or stand-up." />
    <section className="surface-card workload-chart-card"><div className="card-heading"><div><span className="section-kicker">Open and completed work</span><h2>Issues by assignee and status</h2></div></div><div className="team-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={rows} margin={{ top: 20, right: 20, left: 0, bottom: 10 }}><CartesianGrid stroke="#e5ebf3" vertical={false} /><XAxis dataKey="assignee" axisLine={false} tickLine={false} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} /><Tooltip /><Legend />{statuses.map((status, index) => <Bar key={status} dataKey={status} stackId="work" fill={COLORS[index % COLORS.length]} radius={index === statuses.length - 1 ? [5, 5, 0, 0] : 0} />)}</BarChart></ResponsiveContainer></div></section>
    <section className="team-grid">{rows.map((row) => <article className="surface-card teammate-card" key={row.assignee}><div className="teammate-avatar">{row.assignee === "Unassigned" ? "?" : row.assignee.slice(0, 2).toUpperCase()}</div><div className="teammate-main"><h2>{row.assignee}</h2><p>{row.total} total issues</p><div className="status-breakdown">{statuses.filter((status) => Number(row[status as keyof typeof row] ?? 0) > 0).map((status) => <span key={status}>{status} <strong>{Number(row[status as keyof typeof row])}</strong></span>)}</div></div></article>)}</section>
  </div>;
}
