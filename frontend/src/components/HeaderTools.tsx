import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CircleHelp, Database, FlaskConical, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "wouter";

import { apiRequest } from "../api/client";
import type { SyncFreshness } from "../api/types";
import { useProjectSignals } from "../hooks/useProjectSignals";
import { useProject } from "../project/ProjectContext";
import { useAuth } from "../auth/AuthContext";
import { canAdministerProject, userRoleLabel } from "../auth/userDisplay";
import { hasNewCompletedSync } from "../utils/syncFreshness";
import { RoleGuide } from "./RoleGuide";

export function HeaderTools() {
  const [open, setOpen] = useState(false);
  const [dataUpdated, setDataUpdated] = useState(false);
  const [guideMode, setGuideMode] = useState<"welcome" | "guide" | null>(null);
  const previousSyncId = useRef<number | null | undefined>(undefined);
  const queryClient = useQueryClient();
  const { user, logout } = useAuth();
  const { projectKey, demoMode, setDemoMode } = useProject();
  const { overview, activity, insights } = useProjectSignals(projectKey);
  const canAdminister = Boolean(user && canAdministerProject(user, projectKey));
  const freshness = useQuery({
    queryKey: ["sync-freshness", projectKey],
    queryFn: () => apiRequest<SyncFreshness>(`/api/sync/projects/${projectKey}/freshness`),
    enabled: Boolean(projectKey) && !demoMode,
    refetchInterval: 15_000,
    refetchIntervalInBackground: true,
  });

  useEffect(() => {
    previousSyncId.current = undefined;
    setDataUpdated(false);
  }, [projectKey]);

  useEffect(() => {
    if (!user || (!projectKey && user.role !== "admin")) return;
    const key = `jira-ai-role-guide-seen:${user.id}:v1`;
    if (localStorage.getItem(key) !== "true") setGuideMode("welcome");
  }, [projectKey, user]);

  useEffect(() => {
    if (!freshness.data) return;
    const currentId = freshness.data.last_completed_sync_id;
    if (hasNewCompletedSync(previousSyncId.current, currentId)) {
      void queryClient.invalidateQueries({
        predicate: (query) =>
          query.queryKey[0] !== "sync-freshness" && query.queryKey.includes(projectKey),
      });
      setDataUpdated(true);
      const timer = window.setTimeout(() => setDataUpdated(false), 6_000);
      previousSyncId.current = currentId;
      return () => window.clearTimeout(timer);
    }
    previousSyncId.current = currentId;
  }, [freshness.data, projectKey, queryClient]);
  const notifications = useMemo(() => {
    const items: { label: string; tone: string; href?: string }[] = [];
    if (insights.data?.blocked_count) items.push({ label: `${insights.data.blocked_count} blocked issue${insights.data.blocked_count === 1 ? "" : "s"}`, tone: "danger", href: "/issues?quick=blocked" });
    if (overview.data?.overdue_count) items.push({ label: `${overview.data.overdue_count} overdue issue${overview.data.overdue_count === 1 ? "" : "s"}`, tone: "warning", href: "/issues?quick=overdue" });
    if (overview.data?.unassigned_count) items.push({ label: `${overview.data.unassigned_count} issue${overview.data.unassigned_count === 1 ? "" : "s"} without an owner`, tone: "warning", href: "/issues?quick=unassigned" });
    if (activity.data?.stale_issues.length) items.push({ label: `${activity.data.stale_issues.length} stale issue${activity.data.stale_issues.length === 1 ? "" : "s"}`, tone: "neutral", href: "/issues?quick=stale" });
    if (freshness.data?.sync_required) items.unshift({ label: canAdminister ? "Jira updates available — synchronization required" : "Jira updates are available — ask a project administrator to synchronize", tone: "warning" });
    if (freshness.data?.update_check_error) items.push({ label: freshness.data.update_check_error, tone: "neutral" });
    for (const item of items) if (!item.href) item.href = canAdminister ? "/admin" : "/";
    return items;
  }, [activity.data, canAdminister, freshness.data, insights.data, overview.data]);

  const closeGuide = () => {
    if (user) localStorage.setItem(`jira-ai-role-guide-seen:${user.id}:v1`, "true");
    setGuideMode(null);
  };

  const toggleDemo = () => {
    if (user?.id === 0) { logout(); return; }
    setDemoMode(!demoMode);
    queryClient.removeQueries();
  };

  return <div className="header-tools">
    {user && <button className="role-guide-trigger" onClick={() => setGuideMode("guide")} type="button"><CircleHelp size={15} /><span>{userRoleLabel(user, projectKey)}</span></button>}
    {demoMode && <button className="demo-toggle active" onClick={toggleDemo} type="button"><FlaskConical size={15} /> Exit demo</button>}
    <div className={`freshness ${dataUpdated ? "freshness-updated" : ""}`} role="status"><Database size={14} /><span>{demoMode ? "Safe demo snapshot" : freshness.data?.sync_required ? "Updates available — sync required" : dataUpdated ? "Project data updated" : freshness.data?.completed_at ? `Synced ${relativeTime(freshness.data.completed_at)}` : freshness.isLoading ? "Checking for updates" : "Not synchronized"}</span></div>
    <div className="notification-wrap">
      <button className="notification-button" onClick={() => setOpen(!open)} aria-label={`${notifications.length} delivery notifications`} type="button"><Bell size={18} />{notifications.length > 0 && <span>{notifications.length}</span>}</button>
      {open && <div className="notification-popover"><div className="notification-heading"><strong>Delivery notifications</strong><button onClick={() => setOpen(false)} aria-label="Close notifications"><X size={16} /></button></div>{notifications.length ? notifications.map((item) => item.href ? <Link className="notification-item" href={item.href} key={item.label} onClick={() => setOpen(false)}><span className={item.tone} /><span>{item.label}</span><small>View →</small></Link> : <div className="notification-item" key={item.label}><span className={item.tone} />{item.label}</div>) : <p>No active delivery warnings.</p>}</div>}
    </div>
    {user && <RoleGuide open={guideMode !== null} projectKey={projectKey} user={user} welcome={guideMode === "welcome"} onClose={closeGuide} />}
  </div>;
}

function relativeTime(value: string): string {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
