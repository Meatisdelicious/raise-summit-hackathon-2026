import { useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../../api";

export function AppShell({ children }: { children: ReactNode }) {
  const [resetting, setResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const navigate = useNavigate();

  async function handleReset() {
    setResetting(true);
    setResetMessage(null);
    try {
      await api.resetDemo();
      setResetMessage("Demo state reset.");
      navigate("/app/patients/pat-K");
    } finally {
      setResetting(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <Link to="/" className="app-shell__brand">
          MILA
        </Link>
        <span className="app-shell__subtitle">
          Internal monitoring, human-validated before the clinic
        </span>
        <button
          type="button"
          className="button button--ghost app-shell__reset"
          onClick={() => void handleReset()}
          disabled={resetting}
        >
          {resetting ? "Resetting…" : "Reset demo"}
        </button>
        <span aria-live="polite" className="visually-hidden">
          {resetMessage}
        </span>
      </header>
      <main className="app-shell__main">{children}</main>
    </div>
  );
}
