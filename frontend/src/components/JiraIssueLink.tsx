import { ExternalLink } from "lucide-react";

export function JiraIssueLink({ issueKey, jiraBaseUrl, compact = false }: { issueKey: string; jiraBaseUrl?: string; compact?: boolean }) {
  if (!jiraBaseUrl || jiraBaseUrl.includes("example.atlassian.net")) return <span className="issue-key-label">{issueKey}</span>;
  return <a className="jira-link" href={`${jiraBaseUrl}/browse/${encodeURIComponent(issueKey)}`} target="_blank" rel="noreferrer">{issueKey}{!compact && <ExternalLink size={11} />}</a>;
}
