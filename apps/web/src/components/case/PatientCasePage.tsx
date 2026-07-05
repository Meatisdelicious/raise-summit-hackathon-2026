import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { usePatientCase } from "../../hooks/usePatientCase";
import { useTracePlayer } from "../../hooks/useTracePlayer";
import type { MonitoringBrief } from "../../types/contracts";
import { TrajectoryChart } from "./TrajectoryChart";
import { RunControls } from "./RunControls";
import { AgentTracePanel } from "../trace/AgentTracePanel";
import { BriefPanel } from "../brief/BriefPanel";
import { Term } from "../shared/Term";
import { friendlyProtocol } from "../../lib/glossary";

// Plain-language patient switcher — "same agent, different outcomes" in one click. Never the raw
// DecisionState enums; these are the words a non-biologist reads.
const PATIENT_TABS: { id: string; label: string }[] = [
  { id: "pat-K", label: "Needs attention" },
  { id: "pat-R", label: "On track" },
  { id: "pat-P", label: "Slow response" },
  { id: "pat-M", label: "Missing check" },
];

export function PatientCasePage() {
  const { patientId = "" } = useParams<{ patientId: string }>();
  const { patient, results, loading, error } = usePatientCase(patientId);
  const player = useTracePlayer(patientId);

  // The brief is shown ONLY when the player reveals it (the finale) — never a pre-loaded brief.
  // Local state so a validation result (updated brief) replaces it in place.
  const [brief, setBrief] = useState<MonitoringBrief | null>(null);
  useEffect(() => setBrief(null), [patientId]);
  useEffect(() => {
    if (player.brief) setBrief(player.brief);
  }, [player.brief]);

  if (loading) return <p className="loading-state">Loading case…</p>;
  if (error || !patient)
    return (
      <p role="alert" className="alert">
        {error ?? "Patient not found."}
      </p>
    );

  const started = player.status !== "idle";

  return (
    <section aria-labelledby="case-heading" className="case">
      <Link to="/app" className="backlink">
        &larr; All patients
      </Link>

      {/* --- Plain-language patient switcher --- */}
      <nav className="case-switch" aria-label="Choose a case">
        {PATIENT_TABS.map((tab) => (
          <Link
            key={tab.id}
            to={`/app/patients/${tab.id}`}
            className={`case-switch__chip${tab.id === patientId ? " case-switch__chip--active" : ""}`}
            aria-current={tab.id === patientId ? "page" : undefined}
          >
            {tab.label}
          </Link>
        ))}
      </nav>

      {/* --- Intro: one plain line + secondary clinical detail --- */}
      <div className="case-head">
        <p className="eyebrow">Monitoring case</p>
        <h1 id="case-heading" className="page-head__title">
          {patient.label}
        </h1>
        <p className="page-head__lede">
          Day {patient.cycle_day} of stimulation. Watch MILA review the hormone response and decide
          whether a doctor is needed.
        </p>
        <details className="case-detail">
          <summary>Clinical detail</summary>
          <div className="meta-chips">
            <span className="chip">
              <span className="chip__key">Protocol</span> {friendlyProtocol(patient.protocol)}
            </span>
            <span className="chip">
              <span className="chip__key">
                <Term name="AMH">Ovarian reserve</Term>
              </span>{" "}
              AMH {patient.amh}
            </span>
            <span className="chip">
              <span className="chip__key">
                <Term name="AFC">Follicle count</Term>
              </span>{" "}
              {patient.antral_follicle_count}
            </span>
            {patient.pcos_flag && (
              <span className="chip">
                <Term name="PCOS">PCOS</Term>: higher over-response risk
              </span>
            )}
          </div>
        </details>
      </div>

      {/* --- The hormone chart (context) --- */}
      <div className="case-chart">
        <TrajectoryChart results={results} />
      </div>

      {/* --- One primary action --- */}
      <RunControls status={player.status} onRun={() => void player.start()} />
      {player.errorMessage && (
        <p role="alert" className="alert">
          {player.errorMessage}
        </p>
      )}

      {/* --- DURING: the trace is the star, revealed one step at a time --- */}
      {started && (
        <div className="case-trace">
          <div className="section__head">
            <h2 className="section__title">How MILA is thinking</h2>
            <p className="section__hint">
              Each step is a measurement or a decision. Watch for where it goes back for a specific
              protocol rule. That's the agent at work.
            </p>
          </div>
          <div className="trace-card">
            <AgentTracePanel
              events={player.visibleEvents}
              thinking={player.thinking}
              running={player.status === "starting" || player.status === "playing"}
            />
          </div>
        </div>
      )}

      {/* --- FINALE: MILA's read appears only when the brief step is revealed --- */}
      {brief && (
        <div className="case-brief">
          <div className="section__head">
            <h2 className="section__title">MILA's read</h2>
            <p className="section__hint">
              A biologist confirms before anything reaches the clinic.
            </p>
          </div>
          <BriefPanel brief={brief} onValidated={setBrief} />
        </div>
      )}
    </section>
  );
}
