/** Interactive project menu that remains useful while safe demo mode is active. */

import { Check, ChevronDown, FlaskConical, FolderKanban } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useProject } from "../project/ProjectContext";

export function ProjectSwitcher() {
  const { projects, projectKey, setProjectKey, loading, demoMode, setDemoMode } = useProject();
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);
  const currentProject = projects.find((project) => project.key === projectKey);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const chooseDemo = () => {
    setDemoMode(true);
    setOpen(false);
  };

  const chooseProject = (key: string) => {
    setProjectKey(key);
    setDemoMode(false);
    setOpen(false);
  };

  return (
    <div className="project-picker" ref={container}>
      <span>Project</span>
      <button className="project-switcher-trigger" onClick={() => setOpen((value) => !value)} type="button" aria-haspopup="listbox" aria-expanded={open}>
        <span className={`project-switcher-icon ${demoMode ? "demo" : ""}`}>{demoMode ? <FlaskConical size={15} /> : <FolderKanban size={15} />}</span>
        <span className="project-switcher-copy">
          <strong>{demoMode ? "Safe Demo Project" : currentProject?.name ?? (loading ? "Loading projects" : "No project")}</strong>
          <small>{demoMode ? "DEMO · synthetic data" : currentProject?.key ?? "No access"}</small>
        </span>
        <ChevronDown className={open ? "rotate" : ""} size={16} />
      </button>

      {open && (
        <div className="project-switcher-menu" role="listbox" aria-label="Available projects">
          <div className="project-switcher-heading"><strong>Select workspace</strong><small>Only authorized projects are listed.</small></div>
          <button className={demoMode ? "selected" : ""} onClick={chooseDemo} type="button" role="option" aria-selected={demoMode}>
            <span className="project-option-icon demo"><FlaskConical size={16} /></span>
            <span><strong>Safe Demo Project</strong><small>Synthetic presentation data</small></span>
            {demoMode && <Check size={16} />}
          </button>
          {projects.filter((project) => project.key !== "DEMO").map((project) => (
            <button className={!demoMode && project.key === projectKey ? "selected" : ""} key={project.id} onClick={() => chooseProject(project.key)} type="button" role="option" aria-selected={!demoMode && project.key === projectKey}>
              <span className="project-option-icon"><FolderKanban size={16} /></span>
              <span><strong>{project.name}</strong><small>{project.key} · synchronized Jira project</small></span>
              {!demoMode && project.key === projectKey && <Check size={16} />}
            </button>
          ))}
          {!projects.length && <p className="project-switcher-empty">No company projects are assigned to this account.</p>}
        </div>
      )}
    </div>
  );
}
