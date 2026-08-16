import { Link } from "wouter";

export function NotFoundPage() {
  return <div className="not-found"><span>404</span><h1>Page not found</h1><p>The dashboard route you requested does not exist.</p><Link className="primary-button" href="/">Return to overview</Link></div>;
}
