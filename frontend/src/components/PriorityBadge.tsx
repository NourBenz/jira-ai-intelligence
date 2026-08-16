/** Consistent, accessible Jira-priority badge used across issue lists. */
export function PriorityBadge({ priority }: { priority: string | null | undefined }) {
  const label = priority || "None";
  return <span className={`priority-pill priority-${priorityClass(label)}`}>{label}</span>;
}

function priorityClass(priority: string): string {
  const normalized = priority.trim().toLowerCase();
  if (["highest", "critical", "blocker"].includes(normalized)) return "critical";
  if (normalized === "high") return "high";
  if (normalized === "medium") return "medium";
  if (normalized === "low") return "low";
  if (normalized === "lowest") return "lowest";
  return "unknown";
}
