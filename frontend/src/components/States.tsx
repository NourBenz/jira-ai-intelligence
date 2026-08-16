import { AlertTriangle, LoaderCircle } from "lucide-react";

export function LoadingState({ label = "Loading project intelligence" }: { label?: string }) {
  return (
    <div className="state-panel" role="status">
      <LoaderCircle className="spin" size={22} />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div className="state-panel state-error" role="alert">
      <AlertTriangle size={22} />
      <div>
        <strong>Unable to load this view</strong>
        <p>{message}</p>
      </div>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <div className="state-panel">{message}</div>;
}
