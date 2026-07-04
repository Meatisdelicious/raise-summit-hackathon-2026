import type { PlayerStatus } from "../../hooks/useTracePlayer";

const statusText: Record<PlayerStatus, string> = {
  idle: "",
  starting: "Connecting to the models…",
  playing: "MILA is reviewing — watch it think, step by step.",
  done: "Review complete.",
  error: "The run failed.",
};

export function RunControls({
  status,
  onRun,
}: {
  status: PlayerStatus;
  onRun: () => void;
}) {
  const busy = status === "starting" || status === "playing";
  const label = busy ? "Reviewing…" : status === "done" ? "Run again" : "Run the review";

  return (
    <div className="run-controls">
      <button type="button" className="button button--primary button--lg" onClick={onRun} disabled={busy}>
        {label}
      </button>
      {status === "idle" && (
        <span className="run-controls__hint" aria-hidden="true">
          Rebuild <span className="run-controls__arrow">→</span> Check{" "}
          <span className="run-controls__arrow">→</span> Escalate
        </span>
      )}
      <span aria-live="polite" role="status" className="run-controls__status">
        {busy && <span className="run-controls__pulse" aria-hidden="true" />}
        {statusText[status]}
      </span>
    </div>
  );
}
