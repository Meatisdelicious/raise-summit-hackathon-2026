import type {
  AgentEvent,
  HormoneResult,
  MonitoringBrief,
  Patient,
} from "../../types/contracts";

// Patient K — the "killer" demo case (docs/demo-script.md).
// Day 8, antagonist protocol, PCOS, steep E2 rise, progesterone borderline for cycle day 8.
// This case MUST trigger two computation-driven conditional retrievals (OHSS SOP, then the
// premature-luteinization rule) — that pairing is the core "not RAG" proof of the demo.

export const patientK: Patient = {
  id: "patient-k",
  label: "Patient K",
  protocol: "antagonist",
  cycle_day: 8,
  amh: 6.2,
  antral_follicle_count: 22,
  pcos_flag: true,
};

export const patientKResults: HormoneResult[] = [
  {
    id: "result-k-1",
    patient_id: "patient-k",
    cycle_day: 4,
    drawn_at: "2026-06-23T08:00:00Z",
    e2: 380,
    lh: 3.1,
    progesterone: 0.4,
    mature_follicle_count: 8,
  },
  {
    id: "result-k-2",
    patient_id: "patient-k",
    cycle_day: 6,
    drawn_at: "2026-06-25T08:00:00Z",
    e2: 950,
    lh: 2.8,
    progesterone: 0.6,
    mature_follicle_count: 14,
  },
  {
    id: "result-k-3",
    patient_id: "patient-k",
    cycle_day: 8,
    drawn_at: "2026-06-27T08:15:00Z",
    e2: 2450,
    lh: 2.6,
    progesterone: 1.3,
    mature_follicle_count: 18,
  },
];

export const patientKBrief: MonitoringBrief = {
  id: "brief-k-1",
  patient_id: "patient-k",
  result_id: "result-k-3",
  run_id: "run-k-1",
  states: ["OHSS_RISK_ESCALATE", "PREMATURE_LUTEINIZATION_FLAG"],
  interpretation:
    "Day-8 E2 rose 158%/day following a rapid antral response in a PCOS patient, crossing the " +
    "OHSS-risk composite threshold. Progesterone (1.3 ng/mL) is also borderline for cycle day 8, " +
    "raising concern for premature luteinization.",
  recommended_action:
    "Consider coasting or an agonist-trigger swap per the OHSS-prevention SOP; monitor " +
    "progesterone closely and discuss freeze-all per the premature-luteinization rule. Next draw " +
    "in 24h.",
  citations: [
    {
      doc_id: "ohss_sop",
      rule_type: "ohss",
      page: 4,
      article: "§4.2",
      quote:
        "For patients with PCOS and an E2 rate-of-rise exceeding 100%/day between consecutive " +
        "draws, consider coasting or converting to a GnRH-agonist trigger to reduce OHSS risk.",
      score: 0.93,
    },
    {
      doc_id: "luteinization_rule",
      rule_type: "luteinization",
      page: 3,
      article: "§3.1",
      quote:
        "A progesterone level at or above 1.2 ng/mL on cycle day 7-9 is considered borderline for " +
        "premature luteinization; discuss freeze-all with the prescribing clinician.",
      score: 0.89,
    },
  ],
  escalation_level: "urgent",
  validated_by: null,
  validated_at: null,
  created_at: "2026-06-27T09:00:00Z",
};

export const patientKEvents: AgentEvent[] = [
  {
    type: "plan",
    run_id: "run-k-1",
    step: 0,
    plan: [
      "Retrieve patient context",
      "Retrieve trajectory",
      "Compute E2 rate-of-rise",
      "Compute OHSS composite",
      "Check progesterone vs. cycle day",
      "Conditionally retrieve any governing protocol rule",
      "Compute the next action",
      "Draft the monitoring brief",
    ],
  },
  {
    type: "retrieve",
    run_id: "run-k-1",
    step: 1,
    what: "patient_context",
    summary: "Antagonist protocol, day 8, PCOS flag set, AMH 6.2 ng/mL, AFC 22.",
  },
  {
    type: "retrieve",
    run_id: "run-k-1",
    step: 2,
    what: "trajectory",
    summary: "3 prior draws retrieved (cycle day 4, 6, 8).",
  },
  {
    type: "compute",
    run_id: "run-k-1",
    step: 3,
    signal: {
      name: "e2_rate",
      value: "+158%/day",
      detail: "E2 rose from 950 to 2450 pg/mL between day 6 and day 8 (+158%/day).",
      tripped: true,
    },
  },
  {
    type: "compute",
    run_id: "run-k-1",
    step: 4,
    signal: {
      name: "ohss_composite",
      value: "high",
      detail: "OHSS composite: HIGH (steep E2 rise + AFC 22 + PCOS flag).",
      tripped: true,
    },
  },
  {
    type: "branch",
    run_id: "run-k-1",
    step: 5,
    reason: "OHSS composite crossed the risk threshold.",
    rule_type: "ohss",
  },
  {
    type: "retrieve_rule",
    run_id: "run-k-1",
    step: 6,
    rule_type: "ohss",
    hits: [
      {
        doc_id: "ohss_sop",
        rule_type: "ohss",
        page: 4,
        score: 0.93,
        text:
          "Section 4 - OHSS prevention. 4.2: For patients with PCOS and an E2 rate-of-rise " +
          "exceeding 100%/day between consecutive draws, consider coasting or converting to a " +
          "GnRH-agonist trigger to reduce OHSS risk.",
        article: "§4.2",
      },
      {
        doc_id: "ohss_sop",
        rule_type: "ohss",
        page: 5,
        score: 0.41,
        text: "Section 5 - Freeze-all criteria for confirmed moderate-to-severe OHSS.",
        article: "§5.1",
      },
    ],
    citation: {
      doc_id: "ohss_sop",
      rule_type: "ohss",
      page: 4,
      article: "§4.2",
      quote:
        "For patients with PCOS and an E2 rate-of-rise exceeding 100%/day between consecutive " +
        "draws, consider coasting or converting to a GnRH-agonist trigger to reduce OHSS risk.",
      score: 0.93,
    },
  },
  {
    type: "compute",
    run_id: "run-k-1",
    step: 7,
    signal: {
      name: "progesterone_for_day",
      value: "1.3 ng/mL",
      detail: "Progesterone 1.3 ng/mL is borderline for cycle day 8 (threshold 1.2 ng/mL).",
      tripped: true,
    },
  },
  {
    type: "branch",
    run_id: "run-k-1",
    step: 8,
    reason: "Progesterone is borderline for this cycle day.",
    rule_type: "luteinization",
  },
  {
    type: "retrieve_rule",
    run_id: "run-k-1",
    step: 9,
    rule_type: "luteinization",
    hits: [
      {
        doc_id: "luteinization_rule",
        rule_type: "luteinization",
        page: 3,
        score: 0.89,
        text:
          "Section 3 - Premature luteinization. 3.1: A progesterone level at or above 1.2 ng/mL " +
          "on cycle day 7-9 is considered borderline for premature luteinization; discuss " +
          "freeze-all with the prescribing clinician.",
        article: "§3.1",
      },
    ],
    citation: {
      doc_id: "luteinization_rule",
      rule_type: "luteinization",
      page: 3,
      article: "§3.1",
      quote:
        "A progesterone level at or above 1.2 ng/mL on cycle day 7-9 is considered borderline " +
        "for premature luteinization; discuss freeze-all with the prescribing clinician.",
      score: 0.89,
    },
  },
  {
    type: "action",
    run_id: "run-k-1",
    step: 10,
    name: "next_draw_timing",
    detail: "Next draw in 24h given the accelerating trajectory.",
  },
  {
    type: "brief",
    run_id: "run-k-1",
    step: 11,
    brief: patientKBrief,
  },
  {
    type: "escalate",
    run_id: "run-k-1",
    step: 12,
    level: "urgent",
    to: "biologist",
  },
  {
    type: "done",
    run_id: "run-k-1",
    final_states: ["OHSS_RISK_ESCALATE", "PREMATURE_LUTEINIZATION_FLAG"],
  },
];
