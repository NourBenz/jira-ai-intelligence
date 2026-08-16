import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BrainCircuit, DatabaseBackup, Eye, Info, LoaderCircle, RefreshCw, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { apiRequest } from "../api/client";
import type { RAGIndexResponse, RAGIndexStatus, SyncFreshness, SyncRun, SyncRunDetail } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { AccessManagement } from "../components/AccessManagement";
import { Modal } from "../components/Modal";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useProject } from "../project/ProjectContext";
import { useElapsed } from "../hooks/useElapsed";
import { useAuth } from "../auth/AuthContext";

export function AdminPage() {
  const [section, setSection] = useState<"operations" | "history" | "access">("operations");
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const { user } = useAuth();
  const { projectKey } = useProject();
  const queryClient = useQueryClient();
  const runs = useQuery({ queryKey: ["sync-runs", projectKey], queryFn: () => apiRequest<SyncRun[]>("/api/sync/runs?limit=20") });
  const freshness = useQuery({ queryKey: ["sync-freshness", projectKey], queryFn: () => apiRequest<SyncFreshness>(`/api/sync/projects/${projectKey}/freshness`), enabled: Boolean(projectKey) });
  const selectedRun = useQuery({ queryKey: ["sync-run-detail", selectedRunId], queryFn: () => apiRequest<SyncRunDetail>(`/api/sync/runs/${selectedRunId}`), enabled: selectedRunId !== null });
  const indexStatus = useQuery({ queryKey: ["rag-status", projectKey], queryFn: () => apiRequest<RAGIndexStatus>(`/api/rag/projects/${projectKey}/status`), enabled: Boolean(projectKey) });
  const sync = useMutation({
    mutationFn: (mode: "full" | "incremental") => apiRequest<SyncRun>(`/api/sync/projects/${projectKey}${mode === "incremental" ? "/incremental" : ""}`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sync-runs", projectKey] });
      queryClient.invalidateQueries({ queryKey: ["sync-freshness", projectKey] });
      queryClient.invalidateQueries({ queryKey: ["overview", projectKey] });
      queryClient.invalidateQueries({ queryKey: ["issues", projectKey] });
    },
  });
  const index = useMutation({
    mutationFn: () => apiRequest<RAGIndexResponse>(`/api/rag/projects/${projectKey}/index`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rag-status", projectKey] }),
  });
  const checkUpdates = useMutation({
    mutationFn: () => apiRequest<SyncFreshness>(`/api/sync/projects/${projectKey}/check`, { method: "POST" }),
    onSuccess: (result) => queryClient.setQueryData(["sync-freshness", projectKey], result),
  });
  const elapsed = useElapsed(sync.isPending || index.isPending || checkUpdates.isPending);
  const projectRuns = runs.data?.filter((run) => run.project_key === projectKey) ?? [];

  return (
    <div className="page-stack">
      <PageHeader eyebrow="Administrator" title="Project administration" description="Keep synchronized data current, inspect operational history, and manage authorized access." action={<span className="data-badge secure"><ShieldCheck size={14} /> Project administrators</span>} />
      <div className="context-guidance admin-guidance"><Info size={17} /><div><strong>Administration affects the shared project snapshot</strong><p>Only company or project administrators can synchronize and index this project. Every authorized team member sees the refreshed data; Jira issues remain editable only in Jira.</p></div></div>
      {freshness.data?.sync_required && <div className="warning-banner"><strong>Jira updates are available.</strong><span>{freshness.data.jira_latest_issue_key ? `${freshness.data.jira_latest_issue_key} is newer than the synchronized snapshot.` : "Run an incremental sync to refresh the shared dashboard."}</span></div>}
      <nav className="admin-section-tabs" aria-label="Administration sections">
        <button className={section === "operations" ? "active" : ""} onClick={() => setSection("operations")} type="button">Data operations</button>
        <button className={section === "history" ? "active" : ""} onClick={() => setSection("history")} type="button">Sync history</button>
        {user?.role === "admin" && <button className={section === "access" ? "active" : ""} onClick={() => setSection("access")} type="button">Access management</button>}
      </nav>
      {section === "operations" && <>
      <section className="sync-grid">
        <article className="surface-card sync-action-card">
          <span className="icon-tile"><RefreshCw size={22} /></span>
          <h2>Incremental sync</h2>
          <p>Fetch only issues updated since the last successful run. Use this for regular refreshes.</p>
          <button className="primary-button" disabled={sync.isPending} onClick={() => sync.mutate("incremental")} type="button">Run incremental sync</button>
        </article>
        <article className="surface-card sync-action-card">
          <span className="icon-tile"><DatabaseBackup size={22} /></span>
          <h2>Full sync</h2>
          <p>Rebuild the project snapshot, sprint membership, changelogs, and comments from Jira.</p>
          <button className="secondary-button" disabled={sync.isPending} onClick={() => sync.mutate("full")} type="button">Run full sync</button>
        </article>
        <article className="surface-card sync-action-card knowledge-card">
          <span className="icon-tile"><BrainCircuit size={22} /></span>
          <h2>AI knowledge index</h2>
          <p>{indexStatus.data?.chunks_indexed ? `AI knowledge includes ${indexStatus.data.issues_indexed} Jira issues. Last updated ${formatDate(indexStatus.data.last_indexed_at)}.` : "No searchable Jira knowledge is currently available."}</p>
          <button className="secondary-button" disabled={index.isPending || sync.isPending} onClick={() => index.mutate()} type="button">Rebuild knowledge index</button>
        </article>
        <article className="surface-card sync-action-card knowledge-card">
          <span className="icon-tile"><Eye size={22} /></span>
          <h2>Check Jira freshness</h2>
          <p>{freshness.data?.jira_checked_at ? `Last checked ${formatDate(freshness.data.jira_checked_at)}.` : "Jira has not yet been checked for newer issue changes."}</p>
          <button className="secondary-button" disabled={checkUpdates.isPending || sync.isPending} onClick={() => checkUpdates.mutate()} type="button">Check Jira for updates</button>
        </article>
      </section>
      {(sync.isPending || index.isPending) && <div className="operation-progress" role="status"><LoaderCircle className="spin" size={20} /><div><strong>{sync.isPending ? "Synchronizing Jira project data" : "Embedding project knowledge"}</strong><p>{elapsed}s elapsed. Keep this page open; local AI operations can take a little longer.</p></div><span className="progress-shimmer" /></div>}
      {sync.error && <ErrorState error={sync.error} />}
      {index.error && <ErrorState error={index.error} />}
      {checkUpdates.error && <ErrorState error={checkUpdates.error} />}
      {sync.data && <div className="success-banner">Sync #{sync.data.id} completed: {sync.data.issues_processed} issues, {sync.data.sprints_processed} sprints, and {sync.data.comments_processed} comments processed.</div>}
      {index.data && <div className="success-banner">AI knowledge rebuilt from {index.data.issues_processed} Jira issues.</div>}
      </>}
      {section === "history" && <>
      <section className="surface-card table-card">
        <div className="card-heading"><div><span className="section-kicker">Audit trail</span><h2>Recent sync runs</h2></div></div>
        {runs.isLoading ? <LoadingState label="Loading synchronization history" /> : runs.error ? <ErrorState error={runs.error} /> : !projectRuns.length ? <EmptyState message="No synchronization runs have been recorded for this project." /> : (
          <div className="table-scroll"><table><thead><tr><th>Run</th><th>Project</th><th>Mode</th><th>Status</th><th>Issues</th><th>Sprints</th><th>Started</th><th>Details</th></tr></thead><tbody>{projectRuns.map((run) => <tr key={run.id}><td>#{run.id}</td><td>{run.project_key}</td><td>{run.mode}</td><td><span className={`status-pill ${run.status}`}>{run.status}</span></td><td>{run.issues_processed}</td><td>{run.sprints_processed}</td><td>{new Date(run.started_at).toLocaleString()}</td><td><button className="text-button" onClick={() => setSelectedRunId(run.id)}><Eye size={13} /> View</button></td></tr>)}</tbody></table></div>
        )}
      </section>
      <Modal
        open={selectedRunId !== null}
        onClose={() => setSelectedRunId(null)}
        eyebrow={selectedRunId !== null ? `Sync #${selectedRunId}` : undefined}
        title="Synchronization details"
        description="Review exactly what the selected Jira synchronization inspected or changed."
        size="large"
        footer={<button className="secondary-button" onClick={() => setSelectedRunId(null)} type="button">Close details</button>}
      >
        {selectedRun.isLoading ? <LoadingState label="Loading synchronization details" /> : selectedRun.error ? <ErrorState error={selectedRun.error} /> : selectedRun.data?.changes.length ? <div className="sync-change-list">{selectedRun.data.changes.map((change) => <article key={change.issue_key}><div><strong>{change.issue_key}</strong><span className={`status-pill ${change.change_type}`}>{change.change_type}</span></div><p>{change.changed_fields.length ? `Changed: ${change.changed_fields.join(", ")}` : "Snapshot inspected; no Jira field differences detected."}</p>{change.changed_fields.map((field) => <small key={field}>{field}: {formatChangeValue(change.before_values[field])} → {formatChangeValue(change.after_values[field])}</small>)}<footer>{change.changelogs_inspected} histories inspected · {change.comments_inspected} comments inspected</footer></article>)}</div> : <EmptyState message="This older synchronization run has no issue-level details." />}
      </Modal>
      </>}
      {section === "access" && user?.role === "admin" && <AccessManagement projectKey={projectKey} />}
    </div>
  );
}

function formatDate(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString() : "never";
}

function formatChangeValue(value: unknown): string {
  if (value === undefined || value === null || value === "") return "—";
  return typeof value === "string" ? value : JSON.stringify(value);
}
