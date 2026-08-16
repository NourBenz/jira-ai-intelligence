import type { CurrentUser } from "../api/types";

export type InterfaceRole = "company_administrator" | "project_administrator" | "team_member";

export function userDisplayName(user: CurrentUser): string {
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ").trim();
  return name || user.username;
}

export function userInitials(user: CurrentUser): string {
  const parts = [user.first_name, user.last_name].filter(Boolean) as string[];
  if (parts.length) return parts.map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  return user.username.slice(0, 2).toUpperCase();
}

export function effectiveInterfaceRole(user: CurrentUser, projectKey: string): InterfaceRole {
  if (user.role === "admin") return "company_administrator";
  if (projectKey && user.administered_project_keys.includes(projectKey)) return "project_administrator";
  return "team_member";
}

export function userRoleLabel(user: CurrentUser, projectKey: string): string {
  const role = effectiveInterfaceRole(user, projectKey);
  if (role === "company_administrator") return "Company Administrator";
  if (role === "project_administrator") return "Project Administrator";
  return "Team Member";
}

export function canAdministerProject(user: CurrentUser, projectKey: string): boolean {
  return effectiveInterfaceRole(user, projectKey) !== "team_member";
}
