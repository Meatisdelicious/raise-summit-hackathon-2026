import {
  patientK,
  patientKBrief,
  patientKEvents,
  patientKResults,
} from "./patientK";
import {
  patientR,
  patientRBrief,
  patientREvents,
  patientRResults,
} from "./patientR";
import type { AgentEvent, HormoneResult, MonitoringBrief, Patient } from "../../types/contracts";

export interface CaseFixture {
  patient: Patient;
  results: HormoneResult[];
  events: AgentEvent[];
  brief: MonitoringBrief;
  runId: string;
}

// The two ground-truth demo cases (docs/doc.md §7, docs/demo-script.md).
// Add POOR_RESPONSE_FLAG / MISSING_TIMEPOINT cases here later as additional fixtures.
export const caseFixtures: CaseFixture[] = [
  {
    patient: patientK,
    results: patientKResults,
    events: patientKEvents,
    brief: patientKBrief,
    runId: "run-k-1",
  },
  {
    patient: patientR,
    results: patientRResults,
    events: patientREvents,
    brief: patientRBrief,
    runId: "run-r-1",
  },
];
