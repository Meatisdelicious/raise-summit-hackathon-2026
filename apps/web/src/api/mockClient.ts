import type { Api } from "./types";
import * as handlers from "../mocks/server/handlers";
import { subscribeToRunEvents } from "../mocks/server/eventStream";

export const mockClient: Api = {
  listPatients: () => handlers.listPatients(),
  getPatient: (id) => handlers.getPatient(id),
  getPatientResults: (id) => handlers.getPatientResults(id),
  getLatestBrief: (id) => handlers.getLatestBrief(id),
  startRun: (patientId, resultId) => handlers.startRun(patientId, resultId),
  getRun: (runId) => handlers.getRun(runId),
  subscribeToRunEvents: (runId, callbacks) => subscribeToRunEvents(runId, callbacks),
  validateBrief: (briefId, validatedBy, edits) =>
    handlers.validateBrief(briefId, validatedBy, edits),
  rejectBrief: (briefId, validatedBy, reason) => handlers.rejectBrief(briefId, validatedBy, reason),
  resetDemo: () => handlers.resetDemo(),
};
