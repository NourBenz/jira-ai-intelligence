import {
  BarChart3,
  Bot,
  Gauge,
  FlaskConical,
  LogOut,
  Menu,
  RefreshCw,
  Sparkles,
  ShieldAlert,
  Tickets,
  Users,
  X,
} from "lucide-react";
import { useState } from "react";
import { Link, useLocation } from "wouter";

import { useAuth } from "../auth/AuthContext";
import { canAdministerProject, userDisplayName, userInitials, userRoleLabel } from "../auth/userDisplay";
import { useProject } from "../project/ProjectContext";
import { HeaderTools } from "./HeaderTools";
import { ProjectSwitcher } from "./ProjectSwitcher";
import { EmptyState, ErrorState } from "./States";

const links = [
  { to: "/", label: "Overview", icon: Gauge, end: true },
  { to: "/issues", label: "Issues", icon: Tickets },
  { to: "/sprints", label: "Sprints", icon: BarChart3 },
  { to: "/risks", label: "Risk center", icon: ShieldAlert },
  { to: "/team", label: "Team workload", icon: Users },
  { to: "/assistant", label: "AI assistant", icon: Bot },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [location] = useLocation();
  const { user, logout } = useAuth();
  const { projects, projectKey, loading, demoMode, error } = useProject();

  return (
    <div className="app-shell">
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
        <div className="brand-block">
          <div className="brand-mark"><Sparkles size={20} /></div>
          <div>
            <strong>Jira AI</strong>
            <span>Intelligence</span>
          </div>
          <button className="mobile-close" onClick={() => setOpen(false)} aria-label="Close menu">
            <X size={20} />
          </button>
        </div>

        <nav className="primary-nav" aria-label="Primary navigation">
          <p className="nav-label">Workspace</p>
          {links.map(({ to, label, icon: Icon, end }) => (
            <Link key={to} href={to} className={end ? (location === to ? "active" : "") : (location.startsWith(to) ? "active" : "")} onClick={() => setOpen(false)}>
              <Icon size={18} />
              {label}
            </Link>
          ))}
          {user && canAdministerProject(user, projectKey) && (
            <Link href="/admin" className={location.startsWith("/admin") ? "active" : ""} onClick={() => setOpen(false)}>
              <RefreshCw size={18} />
              Administration
            </Link>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="user-avatar">{user ? userInitials(user) : "--"}</div>
          <div className="user-summary">
            <strong>{user ? userDisplayName(user) : "Unknown user"}</strong>
            <span>{user ? userRoleLabel(user, projectKey) : ""}</span>
          </div>
          <button onClick={logout} aria-label="Sign out" title="Sign out">
            <LogOut size={18} />
          </button>
        </div>
      </aside>

      {open && <button className="mobile-overlay" onClick={() => setOpen(false)} aria-label="Close menu" />}

      <main className="main-column">
        <div className="topbar">
          <button className="menu-button" onClick={() => setOpen(true)} aria-label="Open menu">
            <Menu size={21} />
          </button>
          <ProjectSwitcher />
          <HeaderTools />
        </div>
        {demoMode && <div className="demo-workspace-banner" role="status"><FlaskConical size={16} /><div><strong>Synthetic demonstration workspace</strong><span>No company Jira data is loaded, synchronized, or changed in this mode.</span></div></div>}
        <div className="content-wrap">
          {!demoMode && error ? (
            <ErrorState error={error} />
          ) : !demoMode && !loading && !projects.length ? (
            <EmptyState message="No Jira projects are assigned to your Scrum team. Contact a company administrator." />
          ) : children}
        </div>
      </main>
    </div>
  );
}
