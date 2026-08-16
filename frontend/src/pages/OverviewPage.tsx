import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, CheckCircle2, Clock3, Layers3, RefreshCw } from "lucide-react";
import { Link } from "wouter";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiRequest } from "../api/client";
import type { ProjectActivity, ProjectHistory, ProjectOverview, ProjectSprintSummary } from "../api/types";
import { ErrorState, LoadingState } from "../components/States";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { useProject } from "../project/ProjectContext";

const COLORS = ["#4f8cff", "#8b5cf6", "#f59e0b", "#20c997", "#f05d6f"];

export function OverviewPage() {
  const { projectKey } = useProject();
  const overview = useQuery({
    queryKey: ["overview", projectKey],
    queryFn: () => apiRequest<ProjectOverview>(`/api/stored/analytics/projects/${projectKey}/overview`),
    enabled: Boolean(projectKey),
  });
  const history = useQuery({
    queryKey: ["history", projectKey, 8],
    queryFn: () => apiRequest<ProjectHistory>(`/api/stored/analytics/projects/${projectKey}/history?weeks=8`),
    enabled: Boolean(projectKey),
  });
  const activity = useQuery({ queryKey: ["activity", projectKey, 14, 5], queryFn: () => apiRequest<ProjectActivity>(`/api/stored/analytics/projects/${projectKey}/activity?stale_days=14&limit=5`), enabled: Boolean(projectKey) });
  const sprints = useQuery({ queryKey: ["sprints", projectKey], queryFn: () => apiRequest<ProjectSprintSummary>(`/api/stored/analytics/projects/${projectKey}/sprints`), enabled: Boolean(projectKey), retry: false });

  if (overview.isLoading) return <LoadingState />;
  if (overview.error) return <ErrorState error={overview.error} />;
  if (!overview.data) return null;

  const data = overview.data;
  const statusData = Object.entries(data.status_counts).map(([name, value]) => ({ name, value }));
  const workloadData = Object.entries(data.workload_by_assignee)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 7);
  const historyData = Object.entries(history.data?.completed_by_week ?? {}).map(([week, completed]) => ({
    week: new Date(`${week}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    completed,
  }));
  const activeSprint = sprints.data?.sprints.find((sprint) => sprint.state.toLowerCase() === "active");

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow={`Project ${projectKey}`}
        title="Delivery overview"
        description="A reliable current-state view built from synchronized Jira data."
      />

      <section className="metric-grid">
        <MetricCard label="Total issues" value={data.total_issues} detail={`${data.open_count} currently open`} icon={Layers3} />
        <MetricCard label="Completion" value={`${data.completion_rate}%`} detail={`${data.completed_count} issues delivered`} icon={CheckCircle2} tone="green" />
        <MetricCard label="Overdue" value={data.overdue_count} detail="Open issues past due date" icon={Clock3} tone="amber" />
        <MetricCard label="Unassigned" value={data.unassigned_count} detail="Issues without an owner" icon={AlertTriangle} tone="violet" />
      </section>

      <section className="overview-action-grid">
        <article className="surface-card active-sprint-overview">
          <div className="card-heading"><div><span className="section-kicker">Current sprint</span><h2>{activeSprint?.name ?? "No active sprint"}</h2></div>{activeSprint && <span>{activeSprint.completion_rate}% complete</span>}</div>
          {activeSprint ? <><div className="progress-track"><span style={{ width: `${Math.min(activeSprint.completion_rate, 100)}%` }} /></div><div className="overview-sprint-stats"><span><strong>{activeSprint.completed_count}</strong> done</span><span><strong>{activeSprint.open_count}</strong> remaining</span><span><strong>{formatDaysRemaining(activeSprint.end_date)}</strong></span></div><Link href={`/sprints/${activeSprint.sprint_id}`}>Open sprint details <ArrowRight size={15} /></Link></> : <p className="muted-copy">Start a Jira sprint and synchronize the project to display its current delivery state.</p>}
        </article>
        <article className="surface-card overview-priorities">
          <div className="card-heading"><div><span className="section-kicker">Needs attention</span><h2>Priority signals</h2></div><Link href="/risks">Open Risk center <ArrowRight size={14} /></Link></div>
          <Link href="/issues?quick=overdue"><Clock3 size={17} /><span><strong>{data.overdue_count} overdue</strong><small>Past due and still open</small></span></Link>
          <Link href="/issues?quick=unassigned"><AlertTriangle size={17} /><span><strong>{data.unassigned_count} unassigned</strong><small>Open work without ownership</small></span></Link>
          <Link href="/issues?quick=stale"><RefreshCw size={17} /><span><strong>{activity.data?.stale_issues.length ?? 0} stale</strong><small>Not updated for 14+ days</small></span></Link>
        </article>
        <article className="surface-card overview-recent">
          <div className="card-heading"><div><span className="section-kicker">Since the snapshot</span><h2>Recently updated</h2></div><Link href="/issues">All issues <ArrowRight size={14} /></Link></div>
          {activity.data?.recently_updated_issues.length ? activity.data.recently_updated_issues.slice(0, 3).map((issue) => <div key={issue.key}><strong>{issue.key}</strong><span>{issue.summary ?? "Untitled issue"}</span><small>{issue.updated ? new Date(issue.updated).toLocaleDateString() : "No update date"}</small></div>) : <p className="muted-copy">No recent issue activity is available.</p>}
        </article>
      </section>

      <section className="dashboard-grid">
        <article className="panel panel-span-2">
          <div className="panel-heading">
            <div><p className="panel-kicker">Flow</p><h2>Completed work</h2></div>
            <span>Last 8 weeks</span>
          </div>
          <div className="chart-area">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historyData} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
                <CartesianGrid stroke="#dbe5f1" vertical={false} />
                <XAxis dataKey="week" axisLine={false} tickLine={false} tick={{ fill: "#718096", fontSize: 12 }} />
                <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: "#718096", fontSize: 12 }} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #dbe5f1" }} />
                <Line type="monotone" dataKey="completed" stroke="#4f8cff" strokeWidth={3} dot={{ fill: "#4f8cff", r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading"><div><p className="panel-kicker">Current state</p><h2>Status mix</h2></div></div>
          <div className="donut-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={statusData} dataKey="value" nameKey="name" innerRadius={62} outerRadius={88} paddingAngle={3}>
                  {statusData.map((entry, index) => <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="donut-label"><strong>{data.total_issues}</strong><span>issues</span></div>
          </div>
          <div className="legend-list">
            {statusData.map((item, index) => (
              <div key={item.name}><span style={{ background: COLORS[index % COLORS.length] }} /><p>{item.name}</p><strong>{item.value}</strong></div>
            ))}
          </div>
        </article>

        <article className="panel panel-span-2">
          <div className="panel-heading"><div><p className="panel-kicker">Capacity</p><h2>Workload by assignee</h2></div><span>Issue count</span></div>
          <div className="chart-area chart-short">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={workloadData} layout="vertical" margin={{ left: 10, right: 16 }}>
                <CartesianGrid stroke="#dbe5f1" horizontal={false} />
                <XAxis type="number" allowDecimals={false} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" width={105} axisLine={false} tickLine={false} tick={{ fontSize: 12 }} />
                <Tooltip cursor={{ fill: "#edf3fa" }} />
                <Bar dataKey="value" fill="#8b5cf6" radius={[0, 7, 7, 0]} barSize={18} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel attention-panel">
          <p className="panel-kicker">Attention</p>
          <h2>Delivery signals</h2>
          <div className="signal-list">
            <div><span className={data.overdue_count ? "signal-warn" : "signal-good"} /><p><strong>{data.overdue_count} overdue</strong><small>Needs date review</small></p></div>
            <div><span className={data.unassigned_count ? "signal-warn" : "signal-good"} /><p><strong>{data.unassigned_count} unassigned</strong><small>Needs ownership</small></p></div>
            <div><span className={data.completion_rate < 25 ? "signal-warn" : "signal-good"} /><p><strong>{data.completion_rate}% complete</strong><small>Overall delivery rate</small></p></div>
          </div>
        </article>
      </section>
    </div>
  );
}

function formatDaysRemaining(value: string | null): string {
  if (!value) return "No end date";
  const days = Math.ceil((new Date(value).getTime() - Date.now()) / 86_400_000);
  if (days < 0) return `${Math.abs(days)}d overdue`;
  if (days === 0) return "Ends today";
  return `${days}d remaining`;
}
