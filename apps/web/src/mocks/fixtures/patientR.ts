import type {
  AgentEvent,
  HormoneResult,
  MonitoringBrief,
  Patient,
} from "../../types/contracts";

// Patient R — the "routine" control case (docs/demo-script.md).
// A normal trajectory: the agent computes signals but NONE of them trip, so it never fetches the
// OHSS SOP or the luteinization rule. This is the control that proves the extra retrievals shown
// for Patient K are computation-driven, not scripted for every patient.

export const patientR: Patient = {
  id: "patient-r",
  label: "Patient R",
  protocol: "long_agonist",
  cycle_day: 9,
  amh: 2.4,
  antral_follicle_count: 11,
  pcos_flag: false,
};

export const patientRResults: HormoneResult[] = [
  {
    id: "result-r-1",
    patient_id: "patient-r",
    cycle_day: 5,
    drawn_at: "2026-06-24T08:00:00Z",
    e2: 210,
    lh: 2.2,
    progesterone: 0.3,
    mature_follicle_count: 5,
  },
  {
    id: "result-r-2",
    patient_id: "patient-r",
    cycle_day: 7,
    drawn_at: "2026-06-26T08:00:00Z",
    e2: 520,
    lh: 2.0,
    progesterone: 0.4,
    mature_follicle_count: 8,
  },
  {
    id: "result-r-3",
    patient_id: "patient-r",
    cycle_day: 9,
    drawn_at: "2026-06-28T08:00:00Z",
    e2: 980,
    lh: 1.9,
    progesterone: 0.5,
    mature_follicle_count: 10,
  },
];

export const patientRBrief: MonitoringBrief = {
  id: "brief-r-1",
  patient_id: "patient-r",
  result_id: "result-r-3",
  run_id: "run-r-1",
  states: ["ROUTINE_CONTINUE"],
  interpretation:
    "Day-9 trajectory shows a steady E2 rise consistent with the expected stimulation curve; " +
    "progesterone remains well within normal range for this cycle day. No risk signals trip.",
  recommended_action: "Continue current protocol; next draw in 48h.",
  citations: [],
  escalation_level: "none",
  validated_by: null,
  validated_at: null,
  created_at: "2026-06-28T09:00:00Z",
};

export const patientREvents: AgentEvent[] = [
  {
    type: "plan",
    run_id: "run-r-1",
    step: 0,
    plan: [
      "Retrieve patient context",
      "Retrieve trajectory",
      "Compute E2 rate-of-rise",
      "Compute OHSS composite",
      "Check progesterone vs. cycle day",
      "Compute the next action",
      "Draft the monitoring brief",
    ],
  },
  {
    type: "retrieve",
    run_id: "run-r-1",
    step: 1,
    what: "patient_context",
    summary: "Long-agonist protocol, day 9, no PCOS flag, AMH 2.4 ng/mL, AFC 11.",
  },
  {
    type: "retrieve",
    run_id: "run-r-1",
    step: 2,
    what: "trajectory",
    summary: "3 prior draws retrieved (cycle day 5, 7, 9).",
  },
  {
    type: "compute",
    run_id: "run-r-1",
    step: 3,
    signal: {
      name: "e2_rate",
      value: "+88%/day",
      detail: "E2 rose from 520 to 980 pg/mL between day 7 and day 9 (+88%/day) — within curve.",
      tripped: false,
    },
  },
  {
    type: "compute",
    run_id: "run-r-1",
    step: 4,
    signal: {
      name: "ohss_composite",
      value: "low",
      detail: "OHSS composite: LOW (moderate rise, average AFC, no PCOS).",
      tripped: false,
    },
  },
  {
    type: "compute",
    run_id: "run-r-1",
    step: 5,
    signal: {
      name: "progesterone_for_day",
      value: "0.5 ng/mL",
      detail: "Progesterone 0.5 ng/mL is normal for cycle day 9 (threshold 1.2 ng/mL).",
      tripped: false,
    },
  },
  {
    type: "action",
    run_id: "run-r-1",
    step: 6,
    name: "next_draw_timing",
    detail: "Next draw in 48h — routine cadence.",
  },
  {
    type: "brief",
    run_id: "run-r-1",
    step: 7,
    brief: patientRBrief,
  },
  {
    type: "escalate",
    run_id: "run-r-1",
    step: 8,
    level: "none",
    to: "biologist",
  },
  {
    type: "done",
    run_id: "run-r-1",
    final_states: ["ROUTINE_CONTINUE"],
  },
];
