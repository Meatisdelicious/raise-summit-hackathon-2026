import type {
  AgentEvent,
  HormoneResult,
  MonitoringBrief,
  Patient,
  RunSummary,
} from "../../types/contracts";
import { caseFixtures } from "../fixtures";

// A small in-memory "backend" so the whole demo can run without a real API. Reseeded by
// POST /demo/reset. Not persisted across a page reload (matches the "synthetic demo state" scope).

interface Store {
  patients: Patient[];
  resultsByPatient: Map<string, HormoneResult[]>;
  latestBriefByPatient: Map<string, MonitoringBrief | null>;
  briefsById: Map<string, MonitoringBrief>;
  eventsByRun: Map<string, AgentEvent[]>;
  runsById: Map<string, RunSummary>;
  runToPatient: Map<string, string>;
}

function seed(): Store {
  const store: Store = {
    patients: [],
    resultsByPatient: new Map(),
    latestBriefByPatient: new Map(),
    briefsById: new Map(),
    eventsByRun: new Map(),
    runsById: new Map(),
    runToPatient: new Map(),
  };

  for (const fixture of caseFixtures) {
    store.patients.push(fixture.patient);
    store.resultsByPatient.set(fixture.patient.id, fixture.results);
    store.latestBriefByPatient.set(fixture.patient.id, fixture.brief);
    store.briefsById.set(fixture.brief.id, fixture.brief);
    store.eventsByRun.set(fixture.runId, fixture.events);
    store.runToPatient.set(fixture.runId, fixture.patient.id);

    const lastResult = fixture.results[fixture.results.length - 1];
    store.runsById.set(fixture.runId, {
      run_id: fixture.runId,
      patient_id: fixture.patient.id,
      result_id: lastResult.id,
      final_states: fixture.brief.states,
      brief_id: fixture.brief.id,
      started_at: fixture.brief.created_at,
      finished_at: fixture.brief.created_at,
      step_count: fixture.events.length,
    });
  }

  return store;
}

let store = seed();

export function resetStore(): void {
  store = seed();
}

export function getStore(): Store {
  return store;
}
