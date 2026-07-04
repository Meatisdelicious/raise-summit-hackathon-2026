import type { RunStatus } from "../../hooks/useAgentRun";

const statusText: Record<RunStatus, string> = {
  idle: "",
  starting: "Starting the monitoring review…",
  running: "Running — the agent is retrieving and computing.",
  done: "Review complete.",
  error: "The run failed.",
};

export function RunControls({
  status,
  onRun,
}: {
  status: RunStatus;
  onRun: () => void;
}) {
  const busy = status === "starting" || status === "running";

  return (
    <div className="run-controls">
      <button type="button" className="button button--primary" onClick={onRun} disabled={busy}>
        {busy ? "Running…" : "Run monitoring review"}
      </button>
      <span aria-live="polite" className="run-controls__status">
        {statusText[status]}
      </span>
    </div>
  );
}
