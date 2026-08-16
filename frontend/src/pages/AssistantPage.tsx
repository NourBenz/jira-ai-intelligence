/** Project-scoped Jira knowledge assistant with response-bound supporting evidence. */
import { useMutation, useQuery } from "@tanstack/react-query";
import { Bot, Database, Info, Send, ShieldCheck, Sparkles } from "lucide-react";
import { FormEvent, useState } from "react";
import { Link } from "wouter";

import { apiRequest } from "../api/client";
import type { AIResponse, ClientConfig, RAGIndexStatus, RAGSearchResult } from "../api/types";
import { JiraIssueLink } from "../components/JiraIssueLink";
import { PageHeader } from "../components/PageHeader";
import { ErrorState } from "../components/States";
import { useProject } from "../project/ProjectContext";

export function AssistantPage() {
  const { projectKey } = useProject();
  const [question, setQuestion] = useState("");
  const config = useQuery({ queryKey: ["client-config"], queryFn: () => apiRequest<ClientConfig>("/api/client-config"), staleTime: Infinity });
  const indexStatus = useQuery({ queryKey: ["rag-status", projectKey], queryFn: () => apiRequest<RAGIndexStatus>(`/api/rag/projects/${projectKey}/status`), enabled: Boolean(projectKey) });
  const mutation = useMutation({
    mutationFn: (prompt: string) => apiRequest<AIResponse>(`/api/rag/projects/${projectKey}/ask`, {
      method: "POST",
      body: JSON.stringify({ question: prompt }),
    }),
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const prompt = question.trim();
    if (prompt.length >= 3) mutation.mutate(prompt);
  };

  return (
    <div className="page-stack assistant-page">
      <PageHeader
        eyebrow={`Project ${projectKey}`}
        title="Jira knowledge assistant"
        description="Ask grounded questions about synchronized Jira summaries, descriptions, comments, and issue fields."
        action={<div className="assistant-status"><span className="data-badge grounded"><ShieldCheck size={14} /> Grounded output</span><span>{indexStatus.data ? `AI knowledge: ${indexStatus.data.issues_indexed} Jira issues` : "Checking AI knowledge…"}</span></div>}
      />
      <div className="context-guidance ai-guidance"><Info size={17} /><div><strong>Evidence-backed assistance</strong><p>The answer and the information displayed beside it come from the same retrieval operation. Review cited Jira keys and limitations before acting.</p></div></div>

      <section className="assistant-layout">
        <div className="assistant-composer surface-card">
          <div className="assistant-intro">
            <span className="assistant-orb"><Bot size={28} /></span>
            <div><h2>Search project knowledge</h2><p>Answers search synchronized Jira summaries, descriptions, comments, and structured issue fields.</p></div>
          </div>
          <div className="assistant-purpose knowledge-purpose">
            <Info size={18} />
            <div><strong>Use this for issue content and meaning</strong><p>Find or explain Jira information, or filter issues by priority, status, assignee, or type. For sprint totals use Sprints; for measured delivery warnings use <Link href="/risks">Risk Center</Link>.</p></div>
          </div>
          <form onSubmit={submit} className="prompt-form">
            <textarea aria-label="Question" maxLength={1000} minLength={3} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask what Jira issues or comments say…" rows={5} value={question} />
            <div className="prompt-footer"><span>{question.length}/1000</span><button className="primary-button" disabled={mutation.isPending || question.trim().length < 3} type="submit">{mutation.isPending ? "Searching…" : "Search Jira knowledge"} <Send size={16} /></button></div>
          </form>
          <p className="mode-direction"><ShieldCheck size={14} /> Delivery risks have one authoritative home: <Link href="/risks">open Risk Center</Link>.</p>
        </div>

        <div className="assistant-result surface-card" aria-live="polite">
          {!mutation.data && !mutation.error && !mutation.isPending && <div className="result-placeholder"><Sparkles size={30} /><h2>Evidence-backed answers appear here</h2><p>The assistant cites only synchronized Jira issues that support its answer.</p></div>}
          {mutation.isPending && <div className="result-placeholder pulse"><Bot size={30} /><h2>Reviewing project evidence…</h2><p>The local model can take a few seconds to respond.</p></div>}
          {mutation.error && <div className="assistant-error"><ErrorState error={mutation.error} /><div><p>The local model can be temporarily busy while loading embeddings. Your synchronized project data is unaffected.</p><button className="secondary-button" disabled={!mutation.variables} onClick={() => mutation.variables && mutation.mutate(mutation.variables)} type="button">Retry AI request</button></div></div>}
          {mutation.data && <AssistantResult result={mutation.data} evidence={mutation.data.evidence ?? []} jiraBaseUrl={config.data?.jira_base_url} />}
        </div>
      </section>
    </div>
  );
}

function AssistantResult({ result, evidence, jiraBaseUrl }: { result: AIResponse; evidence: RAGSearchResult[]; jiraBaseUrl?: string }) {
  return <div className="answer-stack">
    <div className="answer-meta"><span className={`data-badge ${result.grounded ? "grounded" : "secure"}`}><ShieldCheck size={14} /> {result.grounded ? "Evidence grounded" : "Insufficient evidence"}</span><span className="answer-scope">Project {result.project_key}</span></div>
    <section className="answer-hero"><span className="section-kicker">Answer</span><p className="answer-copy">{result.answer}</p></section>
    {Boolean(result.source_issue_keys.length) && <section className="ai-section source-section"><div className="ai-section-title"><Database size={17} /><div><span className="section-kicker">Jira sources</span><p>Open the authoritative issues behind this response</p></div></div><div className="source-chips">{result.source_issue_keys.map((key) => <JiraIssueLink compact issueKey={key} jiraBaseUrl={jiraBaseUrl} key={key} />)}</div></section>}
    {Boolean(evidence.length) && <section className="evidence-panel ai-section"><div className="ai-section-title"><Sparkles size={17} /><div><span className="section-kicker">Jira information used</span><p>The exact retrieved content used for this same answer</p></div></div>{evidence.map((item) => <details key={item.chunk_id}><summary><span><JiraIssueLink compact issueKey={String(item.metadata.issue_key ?? "Jira issue")} jiraBaseUrl={jiraBaseUrl} /><small>{String(item.metadata.content_type ?? "issue information").replaceAll("_", " ")}</small></span><strong>{relevanceLabel(item.similarity)}</strong></summary><p>{item.text}</p></details>)}</section>}
    {Boolean(result.limitations.length) && <ResultList title="Limitations and missing evidence" items={result.limitations} />}
    <details className="ai-technical-details"><summary>Technical details</summary><p>Engine: {result.model}</p><p>{result.retrieved_chunks ?? evidence.length} Jira information passages reviewed</p><p>{result.grounded ? "Every displayed source is bound to this response." : "The available Jira data did not support a grounded answer."}</p></details>
  </div>;
}

function relevanceLabel(similarity: number): string {
  if (similarity >= 0.75) return "High relevance";
  if (similarity >= 0.55) return "Moderate relevance";
  return "Supporting context";
}

function ResultList({ title, items }: { title: string; items: string[] }) {
  return <div className="result-list muted"><span className="section-kicker">{title}</span><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></div>;
}
