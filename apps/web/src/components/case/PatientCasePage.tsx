import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { usePatientCase } from "../../hooks/usePatientCase";
import { useAgentRun } from "../../hooks/useAgentRun";
import type { MonitoringBrief } from "../../types/contracts";
import { TrajectoryChart } from "./TrajectoryChart";
import { RunControls } from "./RunControls";
import { AgentTracePanel } from "../trace/AgentTracePanel";
import { BriefPanel } from "../brief/BriefPanel";
import { formatProtocol } from "../../lib/format";

export function PatientCasePage() {
  const { patientId = "" } = useParams<{ patientId: string }>();
  const { patient, results, latestBrief, loading, error } = usePatientCase(patientId);
  const { status, events, brief: runBrief, errorMessage, start } = useAgentRun(patientId);

  const [displayedBrief, setDisplayedBrief] = useState<MonitoringBrief | null>(null);

  useEffect(() => setDisplayedBrief(latestBrief), [latestBrief]);
  useEffect(() => {
    if (runBrief) setDisplayedBrief(runBrief);
  }, [runBrief]);

  if (loading) return <p>Loading case…</p>;
  if (error || !patient) return <p role="alert">{error ?? "Patient not found."}</p>;

  return (
    <section aria-labelledby="case-heading">
      <p>
        <Link to="/app">&larr; Back to patient list</Link>
      </p>
      <h1 id="case-heading">{patient.label}</h1>
      <p className="case-page__meta">
        {formatProtocol(patient.protocol)} · Day {patient.cycle_day} · AMH {patient.amh} ng/mL · AFC{" "}
        {patient.antral_follicle_count}
        {patient.pcos_flag ? " · PCOS" : ""}
      </p>

      <h2>Hormone trajectory</h2>
      <TrajectoryChart results={results} />

      <RunControls status={status} onRun={() => void start()} />
      {errorMessage && <p role="alert">{errorMessage}</p>}

      <div className="case-page__grid">
        <div>
          <h2>Live agent trace</h2>
          <AgentTracePanel events={events} />
        </div>
        <div>
          <h2>Monitoring brief</h2>
          <BriefPanel brief={displayedBrief} onValidated={setDisplayedBrief} />
        </div>
      </div>
    </section>
  );
}
