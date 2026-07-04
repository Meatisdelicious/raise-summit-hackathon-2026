import type { RunStatus } from "../../hooks/useAgentRun";

const statusText: Record<RunStatus, string> = {
  idle: "",
  starting: "Connecting to the models…",
  running: "MILA is thinking — reading the trajectory, computing the risk, and citing the protocol. Watch the trace →",
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
        {busy ? "Reviewing…" : status === "done" ? "Run again" : "Run the review"}
      </button>
      <span aria-live="polite" className="run-controls__status">
        {busy && <span className="run-controls__pulse" aria-hidden="true" />}
        {statusText[status]}
      </span>
    </div>
  );
}
