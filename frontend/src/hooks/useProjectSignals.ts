import { useQuery } from "@tanstack/react-query";

import { apiRequest } from "../api/client";
import type { ProjectActivity, ProjectInsights, ProjectOverview } from "../api/types";

export function useProjectSignals(projectKey: string) {
  const overview = useQuery({ queryKey: ["overview", projectKey], queryFn: () => apiRequest<ProjectOverview>(`/api/stored/analytics/projects/${projectKey}/overview`), enabled: Boolean(projectKey) });
  const activity = useQuery({ queryKey: ["activity", projectKey, 14, 20], queryFn: () => apiRequest<ProjectActivity>(`/api/stored/analytics/projects/${projectKey}/activity?stale_days=14&limit=20`), enabled: Boolean(projectKey) });
  const insights = useQuery({ queryKey: ["insights", projectKey, 8], queryFn: () => apiRequest<ProjectInsights>(`/api/stored/analytics/projects/${projectKey}/insights?weeks=8`), enabled: Boolean(projectKey) });
  return { overview, activity, insights, isLoading: overview.isLoading || activity.isLoading || insights.isLoading, error: overview.error || activity.error || insights.error };
}
