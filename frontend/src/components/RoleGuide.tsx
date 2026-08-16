/** Permission-aware guidance that explains what the signed-in user can do. */
import { CheckCircle2, ExternalLink, Info, ShieldCheck, X } from "lucide-react";
import { useEffect } from "react";

import type { CurrentUser } from "../api/types";
import { effectiveInterfaceRole, userRoleLabel } from "../auth/userDisplay";

interface RoleGuideProps {
  open: boolean;
  projectKey: string;
  user: CurrentUser;
  welcome?: boolean;
  onClose: () => void;
}

const guidance = {
  company_administrator: {
    title: "Manage the company workspace",
    description: "You can view every synchronized project and manage platform access.",
    actions: [
      "View dashboards, analytics, risks, sprints, and grounded AI evidence.",
      "Synchronize and rebuild the AI knowledge index for any project.",
      "Create Scrum teams and manage project access and administrators.",
    ],
  },
  project_administrator: {
    title: "Keep this project current",
    description: "You can administer synchronized data for this project without managing the whole company workspace.",
    actions: [
      "View the project dashboards, analytics, risks, sprints, and AI evidence.",
      "Check Jira for updates and run full or incremental synchronization.",
      "Rebuild this project's AI knowledge index and inspect synchronization details.",
    ],
  },
  team_member: {
    title: "Explore your team's project intelligence",
    description: "You have secure, read-only access to the projects assigned to your Scrum team.",
    actions: [
      "Review synchronized issues, sprints, delivery risks, and team workload.",
      "Ask grounded questions about Jira issue summaries, descriptions, and comments.",
      "See data-freshness notifications after a project administrator synchronizes.",
    ],
  },
} as const;

export function RoleGuide({ open, projectKey, user, welcome = false, onClose }: RoleGuideProps) {
  const role = effectiveInterfaceRole(user, projectKey);
  const content = guidance[role];

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose, open]);

  if (!open) return null;

  return (
    <div className="role-guide-backdrop" onMouseDown={onClose}>
      <section aria-labelledby="role-guide-title" aria-modal="true" className="role-guide-card" onMouseDown={(event) => event.stopPropagation()} role="dialog">
        <div className="role-guide-heading">
          <span className="role-guide-icon"><ShieldCheck size={23} /></span>
          <div>
            <span className="section-kicker">{welcome ? "Welcome to your workspace" : "Your access guide"}</span>
            <h2 id="role-guide-title">{content.title}</h2>
          </div>
          <button aria-label="Close role guide" onClick={onClose} type="button"><X size={18} /></button>
        </div>
        <div className="role-guide-role">
          <span>{userRoleLabel(user, projectKey)}</span>
          <small>{projectKey ? `Current project: ${projectKey}` : "No project selected"}</small>
        </div>
        <p className="role-guide-description">{content.description}</p>
        <div className="role-guide-actions">
          {content.actions.map((action) => <p key={action}><CheckCircle2 size={16} /> {action}</p>)}
        </div>
        <div className="role-guide-boundary">
          <Info size={17} />
          <p><strong>This platform is read-only.</strong> Create, assign, transition, or edit issues in Jira; synchronized changes are then displayed here.</p>
        </div>
        <button className="primary-button role-guide-confirm" onClick={onClose} type="button">
          {welcome ? "Open my workspace" : "Got it"} <ExternalLink size={15} />
        </button>
      </section>
    </div>
  );
}
