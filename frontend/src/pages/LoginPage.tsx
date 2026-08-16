import { ArrowRight, BarChart3, BrainCircuit, ShieldCheck, Sparkles } from "lucide-react";
import { FormEvent, useState } from "react";
import { Redirect, useLocation } from "wouter";

import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { user, login, enterDemo } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [, navigate] = useLocation();

  if (user) return <Redirect to="/" />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Login failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-story">
        <div className="login-brand"><Sparkles size={20} /> Jira AI Intelligence</div>
        <div className="login-copy">
          <p className="eyebrow">Delivery intelligence, grounded in Jira</p>
          <h1>See the work.<br />Understand the risk.<br /><em>Act with evidence.</em></h1>
          <p>
            A secure project cockpit that turns synchronized Jira activity into
            clear metrics, sprint signals, and explainable AI guidance.
          </p>
        </div>
        <div className="login-features">
          <span><BarChart3 size={17} /> Deterministic analytics</span>
          <span><BrainCircuit size={17} /> Grounded local AI</span>
          <span><ShieldCheck size={17} /> Role-protected access</span>
        </div>
      </section>

      <section className="login-panel">
        <form className="login-card" onSubmit={submit}>
          <div className="login-card-heading">
            <p className="eyebrow">Protected workspace</p>
            <h2>Welcome back</h2>
            <p>Sign in with your Jira AI Intelligence account.</p>
          </div>
          <label>
            Username
            <input
              required
              minLength={3}
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="username"
            />
          </label>
          <label>
            Password
            <input
              required
              minLength={8}
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
            />
          </label>
          {error && <div className="form-error" role="alert">{error}</div>}
          <button className="primary-button" disabled={submitting}>
            {submitting ? "Signing in…" : "Enter workspace"}
            {!submitting && <ArrowRight size={18} />}
          </button>
          <div className="login-divider"><span>or</span></div>
          <button className="demo-entry-button" onClick={() => { enterDemo(); navigate("/"); }} type="button"><Sparkles size={17} /> Explore safe demo</button>
          <p className="demo-entry-note">Uses synthetic project data only. No company Jira information is loaded.</p>
          <p className="security-note"><ShieldCheck size={15} /> Credentials are verified by your local FastAPI backend.</p>
        </form>
      </section>
    </main>
  );
}
