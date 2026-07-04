import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { usePatientCase } from "../../hooks/usePatientCase";
import { useAgentRun } from "../../hooks/useAgentRun";
import type { MonitoringBrief } from "../../types/contracts";
import { TrajectoryChart } from "./TrajectoryChart";
import { RunControls } from "./RunControls";
import { AgentTracePanel } from "../trace/AgentTracePanel";
import { BriefPanel } from "../brief/BriefPanel";
import { Term } from "../shared/Term";
import { friendlyProtocol, reserveHint } from "../../lib/glossary";

export function PatientCasePage() {
  const { patientId = "" } = useParams<{ patientId: string }>();
  const { patient, results, latestBrief, loading, error } = usePatientCase(patientId);
  const { status, events, brief: runBrief, errorMessage, start } = useAgentRun(patientId);

  const [displayedBrief, setDisplayedBrief] = useState<MonitoringBrief | null>(null);

  useEffect(() => setDisplayedBrief(latestBrief), [latestBrief]);
  useEffect(() => {
    if (runBrief) setDisplayedBrief(runBrief);
  }, [runBrief]);

  if (loading) return <p className="loading-state">Loading case…</p>;
  if (error || !patient)
    return <p role="alert" className="alert">{error ?? "Patient not found."}</p>;

  return (
    <section aria-labelledby="case-heading">
      <Link to="/app" className="backlink">
        &larr; All patients
      </Link>

      <div className="case-head">
        <p className="eyebrow">Monitoring case</p>
        <h1 id="case-heading" className="page-head__title">
          {patient.label}
        </h1>
        <p className="page-head__lede">
          Day {patient.cycle_day} of stimulation. MILA checks whether this hormone response is on
          track — or needs a doctor now.
        </p>
        <div className="meta-chips">
          <span className="chip">
            <span className="chip__key">Treatment</span> Day {patient.cycle_day}
          </span>
          <span className="chip">
            <span className="chip__key">Protocol</span> {friendlyProtocol(patient.protocol)}
          </span>
          <span className="chip">
            <span className="chip__key">
              <Term name="AMH">Ovarian reserve</Term>
            </span>{" "}
            {reserveHint(patient.amh)} (AMH {patient.amh})
          </span>
          <span className="chip">
            <span className="chip__key">
              <Term name="AFC">Follicle count</Term>
            </span>{" "}
            {patient.antral_follicle_count}
          </span>
          {patient.pcos_flag && (
            <span className="chip">
              <Term name="PCOS">PCOS</Term> — higher over-response risk
            </span>
          )}
        </div>
      </div>

      <div className="case-chart section">
        <div className="section__head">
          <h2 className="section__title">Hormone trajectory</h2>
          <p className="section__hint">
            <Term name="E2">Estrogen</Term>, <Term name="LH">LH</Term> and{" "}
            <Term name="progesterone">progesterone</Term> across the treatment days.
          </p>
        </div>
        <TrajectoryChart results={results} />
      </div>

      <RunControls status={status} onRun={() => void start()} />
      {errorMessage && (
        <p role="alert" className="alert">
          {errorMessage}
        </p>
      )}

      <div className="case-page__grid">
        <div className="section">
          <div className="section__head">
            <h2 className="section__title">How MILA is thinking</h2>
            <p className="section__hint">
              Each step is a measurement or a decision. Watch for where it goes back for a specific
              protocol rule — that's the agent at work.
            </p>
          </div>
          <div className="trace-card">
            <AgentTracePanel events={events} />
          </div>
        </div>
        <div className="section">
          <div className="section__head">
            <h2 className="section__title">MILA's read</h2>
            <p className="section__hint">A draft for the team — a biologist confirms before anything reaches the clinic.</p>
          </div>
          <BriefPanel brief={displayedBrief} onValidated={setDisplayedBrief} />
        </div>
      </div>
    </section>
  );
}
