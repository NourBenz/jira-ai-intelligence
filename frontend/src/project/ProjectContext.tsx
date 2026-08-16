import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { apiRequest } from "../api/client";
import { DEMO_MODE_KEY } from "../api/demo";
import type { Project } from "../api/types";

interface ProjectState {
  projects: Project[];
  projectKey: string;
  setProjectKey: (key: string) => void;
  demoMode: boolean;
  setDemoMode: (enabled: boolean) => void;
  loading: boolean;
  error: Error | null;
}

const ProjectContext = createContext<ProjectState | null>(null);

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const [selectedProjectKey, setSelectedProjectKey] = useState(
    () => localStorage.getItem("jira-ai-project") ?? "",
  );
  const [demoMode, setDemoModeState] = useState(
    () => localStorage.getItem(DEMO_MODE_KEY) === "true",
  );
  const projectKey = demoMode ? "DEMO" : selectedProjectKey;
  const query = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiRequest<Project[]>("/api/projects"),
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (!query.data) return;
    const remainsAuthorized = query.data.some((project) => project.key === selectedProjectKey);
    if (!remainsAuthorized) setSelectedProjectKey(query.data[0]?.key ?? "");
  }, [selectedProjectKey, query.data]);

  useEffect(() => {
    if (selectedProjectKey) localStorage.setItem("jira-ai-project", selectedProjectKey);
    else localStorage.removeItem("jira-ai-project");
  }, [selectedProjectKey]);

  const setDemoMode = (enabled: boolean) => {
    localStorage.setItem(DEMO_MODE_KEY, String(enabled));
    setDemoModeState(enabled);
  };

  const value = useMemo(
    () => ({
      projects: query.data ?? [],
      projectKey,
      setProjectKey: setSelectedProjectKey,
      demoMode,
      setDemoMode,
      loading: query.isLoading,
      error: query.error,
    }),
    [demoMode, projectKey, query.data, query.error, query.isLoading],
  );
  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProject(): ProjectState {
  const context = useContext(ProjectContext);
  if (!context) throw new Error("useProject must be used inside ProjectProvider");
  return context;
}
