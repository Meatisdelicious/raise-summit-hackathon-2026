# LoopCloser

## Product and implementation specification

**Track:** Statement Two — Vultr enterprise agent  
**Industry:** Healthcare operations and diagnostic safety  
**Product type:** Web-based, document-grounded enterprise agent  
**Status:** Hackathon build specification  
**Data policy:** Synthetic data only in the public repository and hosted demo

---

## 1. Executive summary

LoopCloser is a healthcare-operations agent that turns explicit, clinician-authored follow-up instructions into tracked obligations.

The agent reads longitudinal case documents, identifies an instruction such as “repeat this test within six months,” plans which records could prove that the instruction was completed, searches the record more than once when necessary, validates candidate evidence with deterministic tools, assigns an operational status, and prepares the next staff action. Every conclusion includes document and page citations. External communication or escalation requires human approval.

LoopCloser does **not** diagnose, interpret whether a laboratory value is medically abnormal, recommend treatment, apply clinical guidelines autonomously, or prescribe anything. It answers an operational question:

> Is there sufficient documented evidence that an explicitly requested follow-up action was completed, and if not, what workflow task should staff review next?

### One-sentence pitch

> LoopCloser finds clinician-requested follow-ups that disappeared across fragmented records, proves whether each loop is closed, and creates the next auditable staff action before the deadline is forgotten.

### Enterprise outcome

For every detected recommendation, the system produces one of the following usable outcomes:

- a cited proof that the requested follow-up was completed;
- a cited explanation that the action is scheduled but not completed;
- an open-loop task with a responsible team and deadline;
- an overdue escalation draft;
- a human-review case when the evidence is ambiguous.

---

## 2. Problem

Follow-up instructions are often buried in narrative reports, consultation notes, discharge summaries, and correspondence. Evidence that the action was completed may appear later in a different document, system, facility, or format.

Existing systems commonly notify staff when a result first arrives, but the harder operational problem is longitudinal:

1. a recommendation is written;
2. an order may or may not be created;
3. an appointment may or may not be scheduled;
4. the requested action may occur elsewhere;
5. the result may return under a different naming convention;
6. no single record explicitly states whether the loop is truly closed.

This is a document-grounded workflow problem, not a medical-knowledge chatbot problem. AHRQ has specifically supported closed-loop systems for diagnostic tests and referrals, and the Joint Commission has published guidance on closed-loop communication and escalation of unaddressed results. See [AHRQ Closed Loop Diagnostics](https://www.ahrq.gov/diagnostic-safety/research/closed-loop.html) and [Joint Commission Quick Safety](https://digitalassets.jointcommission.org/api/public/content/77c6421712dc463eae4b2398f9bf01a5?v=e9bc1e0f).

### Target users

- clinical operations coordinators;
- quality and patient-safety teams;
- referral and diagnostic follow-up teams;
- medical secretaries and care coordinators;
- clinicians who approve the final action.

### User need

The user needs a defensible answer supported by documents, not an opaque risk score:

- What follow-up was explicitly requested?
- When was it due?
- What evidence was searched?
- Does a later document actually satisfy the request?
- Why was a tempting candidate rejected?
- What staff action should happen next?
- Who approved the action, and when?

---

## 3. Statement Two fit

Statement Two requires a web-based enterprise agent that plans, retrieves repeatedly, calls tools, makes decisions, and produces an operational outcome.

LoopCloser satisfies each requirement:

| Requirement | LoopCloser implementation |
|---|---|
| Web-based | Browser case workbench backed by a web API |
| Enterprise workflow | Diagnostic and referral follow-up operations |
| Grounded in documents | Every extracted instruction, candidate, decision, and action carries source citations |
| Plans | The agent creates an evidence-search plan from the recommendation and policy |
| Retrieves more than once | It first retrieves the instruction, then searches for orders, appointments, results, external records, and exceptions; ambiguous candidates trigger targeted retrieval |
| Calls tools | Document search, date resolution, terminology matching, evidence validation, task creation, and escalation tools |
| Makes decisions | Assigns a constrained operational state using evidence and policy |
| Produces an outcome | Creates a cited closure record, staff task, or escalation draft |
| Agent rather than RAG | The system maintains state, branches on tool results, retries retrieval, rejects insufficient evidence, and changes workflow state |

The final demo must visibly show this loop. Merely uploading a PDF and returning an answer is not sufficient.

---

## 4. Product boundary

### 4.1 In scope

- Extract explicit follow-up instructions from synthetic clinical documents.
- Resolve explicit or relative deadlines from the source text.
- Search a longitudinal synthetic record for completion evidence.
- Match document identity, requested action, dates, and completion status.
- Reject evidence that predates the instruction or does not match the requested action.
- Recognize a scheduled action as different from a completed action.
- Recognize explicitly documented exceptions such as cancellation or refusal.
- Assign a constrained operational state.
- Create staff tasks and communication drafts.
- Require human approval for external action.
- Preserve an audit log of plans, retrievals, tool calls, decisions, citations, and approvals.

### 4.2 Out of scope

- Diagnosing a condition.
- Interpreting a result for a patient.
- Deciding that a result medically requires follow-up when no clinician wrote that instruction.
- Applying Fleischner or other clinical guidelines autonomously.
- Inferring clinical severity from laboratory values or imaging findings.
- Recommending medication, treatment, supplements, or lifestyle changes.
- Generating or signing prescriptions.
- Automatically contacting a patient without approval.
- Replacing clinician judgment.
- Training a medical model or claiming clinical efficacy from the small demo corpus.

### 4.3 Authority model

The agent may autonomously search, extract, compare, classify within the defined state machine, and draft an action. It may not perform an external action until an authorized user approves it.

Priority is calculated from documented urgency and overdue duration. It is never an LLM-generated clinical-risk score.

---

## 5. Core user journey

### 5.1 Case inbox

The user opens an inbox of synthetic cases requiring review. This is a workflow inbox, not a metrics dashboard.

Each row shows:

- synthetic case identifier;
- number of open recommendations;
- nearest documented deadline;
- operational state;
- assigned team;
- last agent run.

### 5.2 Case workbench

The user selects one case and sees:

- a chronological document timeline;
- the source recommendation highlighted in context;
- the agent’s current plan;
- live retrieval and tool-call events;
- candidate completion evidence;
- accepted and rejected evidence with reasons;
- the resulting operational state;
- a proposed task or communication;
- approve, reject, and request-review controls.

### 5.3 Human action

The clinician or coordinator reviews the citations and approves the draft. The system records the approver, changes the task state, and schedules monitoring.

---

## 6. Agent workflow

### 6.1 High-level state flow

```text
INGESTED
   |
   v
RECOMMENDATION_DETECTED
   |
   v
PLAN_CREATED
   |
   v
EVIDENCE_SEARCH
   |
   +--> candidate found --> VALIDATE_CANDIDATE
   |                           |
   |                           +--> insufficient --> TARGETED_RETRIEVAL
   |                           |
   |                           +--> sufficient ----> DECIDE
   |
   +--> no candidate ------------------------------> DECIDE
                                                       |
                                                       v
                                              DRAFT_OPERATIONAL_ACTION
                                                       |
                                                       v
                                                HUMAN_APPROVAL
                                                       |
                                                       v
                                                   MONITOR
```

### 6.2 Detailed steps

#### Step 1 — Sweep

Search the case corpus for explicit clinician-authored follow-up instructions.

The extractor returns structured data:

```json
{
  "action_requested": "repeat laboratory test",
  "target": "synthetic test code",
  "instruction_date": "2026-01-10",
  "deadline_expression": "within 6 months",
  "document_id": "doc-001",
  "page": 2,
  "source_quote": "...",
  "extraction_confidence": 0.96
}
```

Only explicit instructions enter the registry automatically. Vague text, missing targets, or missing authorship is sent to human review.

#### Step 2 — Plan

The agent converts the instruction into an evidence plan. For a repeated laboratory test, the plan may be:

1. resolve the deadline;
2. search later orders for the requested test;
3. search appointments to determine whether it is merely scheduled;
4. search finalized laboratory reports for completion evidence;
5. search external documents for equivalent test names;
6. search cancellation or refusal notes if no result exists;
7. validate every candidate before deciding.

The plan is stored and displayed before execution.

#### Step 3 — Hunt

The retrieval tool is called separately for different evidence classes. One broad semantic search is not enough.

Example retrieval sequence:

```text
search_documents(type="order", target="synthetic-test", after="2026-01-10")
search_documents(type="appointment", target="synthetic-test", after="2026-01-10")
search_documents(type="result", aliases=[...], after="2026-01-10")
search_documents(type="external_result", aliases=[...], after="2026-01-10")
```

When a candidate is incomplete or contradictory, the agent requests the exact page and surrounding context rather than guessing.

#### Step 4 — Validate

Deterministic validators enforce hard requirements:

- the document belongs to the same synthetic case;
- the evidence date is after the instruction date;
- the evidence matches the requested action or an approved alias;
- the document is final rather than draft or cancelled;
- a booked appointment is not treated as completion;
- the evidence falls within the relevant operational window;
- a closure exception is accepted only when explicitly documented;
- every accepted fact has a resolvable document and page citation.

The language model may propose a match. It cannot override a failed hard validator.

#### Step 5 — Decide

The decision engine selects exactly one state:

| State | Meaning |
|---|---|
| `COMPLETED` | Valid final evidence satisfies the explicit request |
| `SCHEDULED_NOT_COMPLETED` | An order or appointment exists, but no final completion evidence exists |
| `OPEN_NOT_DUE` | No completion evidence exists, but the explicit deadline has not passed |
| `OPEN_OVERDUE` | No valid completion evidence exists and the explicit deadline has passed |
| `AMBIGUOUS_REQUIRES_REVIEW` | Evidence is conflicting, incomplete, or below the acceptance threshold |
| `CLOSED_BY_DOCUMENTED_EXCEPTION` | An authorized source explicitly documents refusal, cancellation, supersession, or another approved exception |

Every decision contains:

- state;
- policy version;
- accepted evidence;
- rejected evidence and rejection reasons;
- source citations;
- deterministic validation results;
- model confidence for extracted fields, not a clinical confidence score;
- recommended operational action.

#### Step 6 — Act

Allowed draft actions include:

- create a coordinator review task;
- request verification of an external result;
- prepare a reminder for clinician review;
- prepare a synthetic patient-notification draft;
- assign an overdue case to a configured team;
- schedule the next monitoring check.

No draft is sent externally until a user approves it.

#### Step 7 — Guard

A scheduled monitor rechecks open cases. If an approved task remains unresolved beyond the institution’s synthetic policy window, the agent drafts an escalation to the configured team.

---

## 7. Tool design

The project uses one orchestrating agent with a constrained tool registry. Multiple agents are unnecessary for the MVP and would add failure modes without improving the judging criteria.

### 7.1 Required tools

#### `search_documents`

Searches document chunks using case, document type, date range, target aliases, and semantic query.

```json
{
  "case_id": "case-001",
  "document_types": ["lab_result", "external_lab_result"],
  "query": "repeat synthetic test",
  "after": "2026-01-10",
  "before": "2026-07-10",
  "limit": 10
}
```

#### `get_document_context`

Returns a cited page and adjacent context for a candidate document.

#### `resolve_deadline`

Converts an explicit date or relative expression into a date using the instruction date. Ambiguous expressions return `needs_review`.

#### `normalize_target`

Maps a source expression to an approved synthetic terminology alias. The mapping table is versioned and deterministic.

#### `validate_completion`

Evaluates hard matching rules and returns pass, fail, or ambiguous with individual checks.

#### `create_task_draft`

Creates an internal action draft linked to the recommendation, evidence, and decision.

#### `approve_task`

Requires an authenticated human action. It records the approver and changes task state.

#### `schedule_monitor`

Schedules a future workflow check for open or scheduled cases.

### 7.2 Agent constraints

- Maximum number of steps per run: 12.
- Maximum retrieval retries per evidence class: 2.
- Structured model outputs validated with Pydantic or JSON Schema.
- Invalid output is retried once with the validation error.
- Tool arguments are validated before execution.
- The model cannot call unregistered tools.
- The model cannot directly modify a final decision or approved task.
- A run that exceeds its limits ends in `AMBIGUOUS_REQUIRES_REVIEW`.

---

## 8. Vultr architecture

Vultr must be part of the agent’s critical execution path. Hosting only the frontend on Vultr would be a weak sponsor-track integration.

### 8.1 Architecture

```text
Browser
  |
  v
React case workbench
  |
  v
FastAPI orchestration API on Vultr Compute
  |             |                 |
  |             |                 +--> Vultr Managed PostgreSQL
  |             |                       cases, state, audit, actions
  |             |
  |             +--> Vultr Object Storage
  |                     synthetic PDFs and extracted artifacts
  |
  +--> Vultr Serverless Inference
          planning, structured extraction,
          query generation, cited explanation
```

Relevant services:

- [Vultr Serverless Inference](https://docs.vultr.com/products/compute/serverless-inference)
- [Vultr Object Storage](https://docs.vultr.com/products/storage/object-storage)
- [Vultr Managed PostgreSQL](https://docs.vultr.com/products/storage/databases/postgresql)

### 8.2 Service responsibilities

#### Vultr Serverless Inference

- extract explicit recommendations into a schema;
- create the evidence-search plan;
- generate targeted retrieval queries;
- decide which registered tool to call next;
- explain the operational decision using validated evidence and citations.

The final status is constrained by deterministic validation and the state machine.

#### Vultr Object Storage

- store synthetic PDF source documents;
- store extracted text and page images only when needed;
- expose objects through private, time-limited access from the backend;
- never enable public-read access for the document bucket.

#### Vultr Managed PostgreSQL

- persist cases and document metadata;
- store recommendations, candidate evidence, decisions, tasks, and policies;
- store agent-run and tool-call audit events;
- support idempotent task creation and demo reset.

#### Vultr Compute

- host the FastAPI application and background monitor;
- serve the frontend or route to the static frontend deployment;
- keep Vultr and storage credentials server-side.

### 8.3 Minimum credible Vultr integration

If time is limited, the non-negotiable integration is:

1. the orchestration backend is deployed on Vultr;
2. planning and extraction call Vultr Serverless Inference live;
3. the demo shows the resulting model and tool events;
4. at least one persistent state change is stored by the deployed backend.

Object Storage and Managed PostgreSQL should be included when stable, but a reliable agent demo is more important than adding unused services.

### 8.4 Secrets and environment

Expected server-side variables:

```text
VULTR_INFERENCE_API_KEY=
VULTR_INFERENCE_BASE_URL=
VULTR_MODEL=
DATABASE_URL=
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_BUCKET=
APP_SECRET_KEY=
```

No secret belongs in the repository, frontend bundle, screenshots, or recorded demo.

---

## 9. Proposed technical stack

### Frontend

- React;
- TypeScript;
- Vite;
- TanStack Query for server state;
- Server-Sent Events for the live agent trace;
- a small component library or plain accessible CSS;
- Playwright for the critical demo path.

### Backend

- Python 3.12;
- FastAPI;
- Pydantic models and strict structured outputs;
- SQLAlchemy and Alembic;
- PostgreSQL;
- S3-compatible client for Vultr Object Storage;
- direct orchestration state machine rather than a large multi-agent framework;
- PyMuPDF or pypdf for text-based synthetic PDFs;
- pytest for unit and integration tests.

### Retrieval

- page-aware chunking;
- document-type and date filters before semantic ranking;
- exact alias matching for deterministic targets;
- semantic retrieval for narrative instructions and external terminology;
- citations stored as `document_id`, page number, and character offsets.

### Why not Streamlit

Streamlit projects are explicitly disallowed. The product must be a real web application with a case workflow, not a notebook-style interface.

---

## 10. Data model

### `cases`

- `id`
- `synthetic_patient_id`
- `status`
- `assigned_team`
- `created_at`
- `updated_at`

### `documents`

- `id`
- `case_id`
- `document_type`
- `event_date`
- `author_role`
- `source_organization`
- `object_key`
- `sha256`
- `is_synthetic`
- `processing_status`

### `document_chunks`

- `id`
- `document_id`
- `page_number`
- `text`
- `start_offset`
- `end_offset`
- `embedding_reference`

### `recommendations`

- `id`
- `case_id`
- `source_document_id`
- `source_page`
- `source_quote`
- `action_type`
- `target_code`
- `instruction_date`
- `deadline`
- `documented_urgency`
- `extraction_confidence`
- `status`

### `evidence_candidates`

- `id`
- `recommendation_id`
- `document_id`
- `page_number`
- `candidate_type`
- `retrieval_score`
- `validation_status`
- `validation_details`
- `accepted`

### `decisions`

- `id`
- `recommendation_id`
- `state`
- `policy_version`
- `reasoning_summary`
- `accepted_evidence_ids`
- `rejected_evidence_ids`
- `created_at`

### `tasks`

- `id`
- `decision_id`
- `task_type`
- `assigned_team`
- `draft_body`
- `status`
- `approved_by`
- `approved_at`
- `due_at`

### `agent_runs` and `tool_calls`

- run identifier and case identifier;
- model and prompt version;
- plan;
- ordered tool calls and sanitized arguments;
- results and errors;
- token and latency metadata;
- final status;
- timestamps.

---

## 11. API surface

### Cases and documents

```text
GET  /api/cases
GET  /api/cases/{case_id}
GET  /api/cases/{case_id}/documents
GET  /api/documents/{document_id}/pages/{page_number}
```

### Agent execution

```text
POST /api/cases/{case_id}/runs
GET  /api/runs/{run_id}
GET  /api/runs/{run_id}/events
```

`GET /events` uses Server-Sent Events so the demo can show the plan, retrievals, validation, and decision as they occur.

### Recommendations and actions

```text
GET  /api/cases/{case_id}/recommendations
GET  /api/recommendations/{recommendation_id}
POST /api/tasks/{task_id}/approve
POST /api/tasks/{task_id}/reject
POST /api/tasks/{task_id}/request-review
```

### Demo operations

```text
POST /api/demo/reset
GET  /api/health
GET  /api/ready
```

The reset endpoint is protected and restores only the synthetic demo state.

---

## 12. Synthetic dataset

### 12.1 Current local files

The current `docs/*.PDF` files are real laboratory reports containing direct identifiers and sensitive health information. They must not be committed, published, uploaded to Vultr, passed to a hosted model, used in screenshots, or shown during the demo.

Before repository initialization:

1. move the real PDFs outside the project directory;
2. add `data/private/` and all original-report patterns to `.gitignore`;
3. verify the public tree contains no patient identifiers or original report metadata;
4. generate all demo documents independently.

Health data is sensitive personal data, and pseudonymization does not make it anonymous. See [CNIL health data guidance](https://www.cnil.fr/fr/thematiques/sante) and [CNIL anonymization guidance](https://www.cnil.fr/fr/technologies/lanonymisation-de-donnees-personnelles).

### 12.2 Synthetic-generation rules

- Use entirely fictional names, addresses, organizations, identifiers, and clinicians.
- Change all dates and numeric values.
- Do not copy logos, branding, access identifiers, dossier numbers, or exact visual layouts.
- Clear PDF metadata.
- Mark every page `SYNTHETIC DATA — NOT FOR CLINICAL USE`.
- Use a deterministic generator seed so the corpus can be recreated.
- Store the generator and templates in the repository.
- Store generated documents under `data/synthetic/`.
- Include a manifest mapping every document to its intended ground truth.
- Do not train a model on the six source reports.

### 12.3 Recommended corpus

Build 8–10 synthetic cases with approximately 30–40 documents total. Quality and controlled branches matter more than volume.

| Case | Intended behavior | Key reasoning moment |
|---|---|---|
| A | `COMPLETED` | A later final result matches an explicit repeat-test instruction |
| B | `OPEN_OVERDUE` | A later panel exists but does not contain the requested test |
| C | `SCHEDULED_NOT_COMPLETED` | An appointment exists without a final result |
| D | `AMBIGUOUS_REQUIRES_REVIEW` | A candidate uses an unknown alias or has conflicting identity data |
| E | `OPEN_OVERDUE` | A matching result exists but predates the instruction |
| F | `COMPLETED` | A valid external result closes the loop |
| G | `CLOSED_BY_DOCUMENTED_EXCEPTION` | A synthetic refusal or authorized cancellation is documented |
| H | `OPEN_NOT_DUE` | No completion evidence exists, but the deadline is in the future |

### 12.4 Required document types

- consultation notes;
- discharge or follow-up summaries;
- laboratory orders;
- appointment confirmations;
- finalized laboratory reports;
- external laboratory reports;
- coordinator notes;
- documented cancellation or refusal;
- institutional follow-up policy;
- terminology alias table.

### 12.5 Policy document

The demo policy is operational and fictional. It defines:

- which team owns each task type;
- how explicit deadlines are interpreted;
- when reminders and escalations occur;
- which documents qualify as completion evidence;
- which exception documents may close a loop;
- required human approvals.

It must not pretend to be a clinical guideline.

---

## 13. Decision policy

### 13.1 Completion

A recommendation can be marked `COMPLETED` only when:

1. the source recommendation is explicit;
2. the requested target is known;
3. the candidate belongs to the same synthetic case;
4. the candidate date is after the recommendation date;
5. the candidate matches the target using an approved alias;
6. the candidate is final;
7. its citation is resolvable;
8. every hard validator passes.

### 13.2 Scheduled is not completed

An order, referral, or appointment proves workflow progress but not completion. It produces `SCHEDULED_NOT_COMPLETED` unless final evidence is also present.

### 13.3 No proof is not proof of failure

When retrieval coverage is incomplete or contradictory, the result is `AMBIGUOUS_REQUIRES_REVIEW`, not `OPEN_OVERDUE`.

### 13.4 Fail-safe behavior

False closure is the most dangerous system error. When uncertain, the agent must keep the loop open and request human review.

---

## 14. User interface specification

### 14.1 Case inbox

- filters for state, deadline, and assigned team;
- concise case rows rather than KPI-heavy charts;
- one primary action: open case;
- demo case labels for the presenter, hidden in normal mode.

### 14.2 Case timeline

- chronological documents;
- distinct icons for note, order, appointment, internal result, and external result;
- click to open the cited page;
- visible synthetic-data watermark.

### 14.3 Agent trace

Show events in plain language:

```text
Plan created: search for order, appointment, and final result.
Retrieved clinician note, page 2.
Extracted deadline: 2026-07-10.
Retrieved 3 candidate result documents.
Rejected candidate doc-004: event predates instruction.
Expanded search to external results.
No valid completion evidence found.
Decision: OPEN_OVERDUE.
Drafted coordinator review task.
```

The trace must expose actual tool events, not a fabricated animation.

### 14.4 Evidence panel

- source recommendation;
- accepted evidence;
- rejected candidates;
- individual validator outcomes;
- filename-safe document label and page number;
- direct page preview.

### 14.5 Action panel

- operational state;
- draft task;
- assigned team;
- deadline;
- approve, reject, and request-review controls;
- approval audit information.

### 14.6 Design constraints

- The primary experience is a case-resolution workflow, not a dashboard.
- There is no patient-facing chat interface.
- The document preview supports the workflow but is not marketed as an image analyzer.
- Accessibility: keyboard controls, labeled buttons, sufficient contrast, and no status conveyed by color alone.

---

## 15. Two-minute demo script

### 0:00–0:15 — Problem

Show a synthetic clinician note with one highlighted sentence requesting a repeat test by a defined deadline.

Say:

> The instruction exists, but proof that it was completed may be scattered across orders, appointments, and reports. LoopCloser owns that operational search.

### 0:15–0:30 — Start the agent

Open the case and click **Run follow-up review**.

The agent displays its evidence plan before calling tools.

### 0:30–0:55 — Multiple retrievals

Show separate retrievals for:

1. the source instruction;
2. later internal results;
3. external results or appointment records.

### 0:55–1:20 — Signature reasoning moment

The agent finds a result that appears to match, then rejects it because it predates the instruction. This proves it is not doing keyword matching.

It performs another targeted retrieval and finds no valid final evidence.

### 1:20–1:40 — Decision

Show:

```text
OPEN_OVERDUE
Reason: no final matching evidence after the instruction date.
Rejected evidence: result predates instruction.
```

Open the citations to prove grounding.

### 1:40–1:55 — Enterprise action

The agent drafts a coordinator task. The clinician clicks **Approve**. The database state changes to `ACTION_PENDING`, and an audit event appears.

### 1:55–2:00 — Close

> LoopCloser does not decide medicine. It makes sure an explicit clinical decision does not disappear between documents.

### Backup demo

Keep a second preloaded case in which a valid external report closes the loop. If live inference fails, the application should preserve the last successful run and clearly label it as a recorded run rather than pretending it is live.

---

## 16. Judging strategy

### 16.1 Impact — 25%

Strengths:

- clear patient-safety and operational problem;
- identifiable enterprise buyers and users;
- applicable to laboratory tests, imaging, referrals, pathology, and specialist follow-up;
- creates an auditable work product rather than advice.

Evidence should be precise. Avoid repeating a universal “30–60%” failure rate without a source and defined population. One systematic review, for example, reported condition-specific follow-up rates for incidental adrenal masses; it should not be generalized to all medicine. See [PubMed PMID 34508918](https://pubmed.ncbi.nlm.nih.gov/34508918/).

### 16.2 Demo — 50%

This is the dominant criterion. The demo must reliably show:

- a live Vultr inference call;
- an explicit plan;
- at least two retrieval calls;
- a deterministic tool validation;
- a branch caused by insufficient evidence;
- a cited decision;
- a real task-state mutation;
- human approval;
- an audit event.

Do not trade this path for additional features.

### 16.3 Creativity — 15%

The differentiating moment is not recommendation extraction. It is the agent refusing to close a loop when a plausible document fails temporal or semantic validation, then planning another search.

### 16.4 Pitch — 10%

Keep the pitch concrete and credible:

- lead with the lost follow-up workflow;
- show the hidden sentence;
- demonstrate the false-positive rejection;
- finish on the approved enterprise action;
- avoid sensational or unsupported mortality, revenue, and malpractice claims.

### Expected potential

If the complete path is reliable, the concept can credibly target:

| Criterion | Target |
|---|---:|
| Impact | 22–24 / 25 |
| Demo | 42–47 / 50 |
| Creativity | 12–14 / 15 |
| Pitch | 8–9 / 10 |
| Total | 84–94 / 100 |

These are planning targets, not guaranteed scores.

---

## 17. Evaluation plan

### 17.1 Ground truth

The synthetic manifest defines for every case:

- source recommendation and citation;
- expected deadline;
- expected retrieval classes;
- valid and invalid candidate evidence;
- expected state;
- expected action;
- required citations.

### 17.2 Metrics

- recommendation extraction precision and recall;
- deadline-resolution accuracy;
- evidence-candidate recall;
- closure-state accuracy;
- false-closure rate;
- citation correctness;
- task idempotency;
- median end-to-end latency;
- percentage of runs completed within the step limit.

### 17.3 Release gates

- **False closure:** 0 on the controlled demo corpus.
- **Decision accuracy:** at least 90% on all synthetic recommendations.
- **Citation validity:** 100% of displayed citations resolve to the expected page.
- **Demo cases:** both primary cases pass five consecutive end-to-end runs.
- **Task creation:** repeated runs do not create duplicate tasks.
- **Privacy scan:** no real identifier or original PDF is present in the repository or deployment.

### 17.4 Tests

#### Unit tests

- relative deadline resolution;
- target alias normalization;
- temporal validation;
- final-versus-draft document status;
- appointment-versus-completion distinction;
- state transition rules;
- task idempotency.

#### Integration tests

- Vultr inference structured output;
- object storage upload and retrieval;
- database migrations;
- multi-retrieval agent run;
- model failure and retry behavior;
- ambiguous evidence fallback.

#### End-to-end tests

- open case;
- run agent;
- inspect citations;
- approve action;
- verify state mutation;
- reset demo.

---

## 18. Reliability and observability

- Use low model temperature for extraction and planning.
- Validate every model response against a strict schema.
- Use request timeouts and bounded retries.
- Make tool calls idempotent.
- Record each state transition.
- Attach a correlation identifier to every run.
- Store prompt and policy versions.
- Never log full document text or secrets in production logs.
- Display a clear error state rather than inventing a decision.
- Provide `/health` and `/ready` endpoints.
- Capture latency per inference and tool call.
- Preserve the last successful synthetic run for transparent fallback.

---

## 19. Privacy, safety, and compliance

### Hackathon policy

- Public repository contains synthetic data only.
- Hosted demo processes synthetic data only.
- No real report is sent to Vultr or another external service.
- No real identifier appears in commits, issues, screenshots, logs, prompts, or presentation material.
- Synthetic files use neutral templates and assets the team owns.

### Product safety

- Explicit recommendation required.
- Deterministic hard validation before closure.
- Human review for ambiguity.
- Human approval before external action.
- No diagnosis, treatment, clinical-risk score, or guideline adjudication.
- Complete audit trail.
- Fail open to review: uncertainty keeps the workflow visible rather than silently closing it.

### Future real-world deployment

A real deployment would require a formal legal, privacy, security, clinical-safety, and procurement assessment. Relevant considerations may include a lawful processing basis, an Article 9 condition, processor agreements, access control, retention, security testing, a data-protection impact assessment, and appropriate health-data hosting arrangements.

French digital hosting of real personal health data can fall under the HDS framework. The hackathon must not claim production compliance or HDS eligibility. See [Agence du Numérique en Santé — HDS](https://esante.gouv.fr/ens/offre/hds).

This specification is an engineering boundary, not legal or medical advice.

---

## 20. Security baseline

- Private object-storage bucket.
- TLS for every network path.
- Server-side secrets only.
- Least-privilege service credentials.
- Separate development and demo credentials.
- Authenticated approval endpoint.
- Role distinction between reviewer and administrator.
- Short-lived signed document URLs.
- File type, size, and checksum validation.
- No executable file uploads.
- Dependency and secret scanning in CI.
- Structured audit events without full document contents.
- Database backups only for synthetic demo data.
- Credential rotation after the event.

---

## 21. Proposed repository structure

```text
.
├── README.md
├── doc.md
├── .env.example
├── .gitignore
├── Makefile
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── src/loopcloser/
│   │   │   ├── api/
│   │   │   ├── agent/
│   │   │   ├── models/
│   │   │   ├── retrieval/
│   │   │   ├── tools/
│   │   │   ├── policies/
│   │   │   └── storage/
│   │   └── tests/
│   └── web/
│       ├── package.json
│       ├── src/
│       └── tests/
├── data/
│   ├── synthetic/
│   ├── manifests/
│   └── private/              # ignored; should be empty in the public project
├── scripts/
│   ├── generate_synthetic_data.py
│   ├── seed_demo.py
│   ├── reset_demo.py
│   └── privacy_scan.py
├── infra/
│   ├── docker/
│   └── terraform/
└── docs/
    ├── architecture.md
    ├── demo-script.md
    └── safety.md
```

The current real PDFs must be removed from the future public project before this structure is created.

---

## 22. Implementation plan

### Phase 0 — Privacy and scope

- Move real PDFs out of the project.
- Add ignore rules and a privacy scanner.
- Freeze the clinical boundary.
- Define the synthetic operational policy.

**Exit condition:** no real data remains in the intended repository tree.

### Phase 1 — Controlled corpus

- Define the eight ground-truth cases.
- Build neutral document templates.
- Generate deterministic synthetic PDFs.
- Write the manifest and expected decisions.

**Exit condition:** every demo branch has documents and ground truth.

### Phase 2 — Deterministic core

- Implement data models.
- Implement deadline, alias, temporal, and completion validators.
- Implement the decision state machine.
- Add unit tests.

**Exit condition:** ground-truth cases can be decided from pre-extracted fixtures without an LLM.

### Phase 3 — Document ingestion and retrieval

- Extract page-aware text.
- Store source artifacts and metadata.
- Implement filtered and semantic search.
- Make all citations resolvable.

**Exit condition:** valid and invalid evidence candidates are retrieved for the signature cases.

### Phase 4 — Agent orchestration

- Connect Vultr Serverless Inference.
- Implement structured extraction and planning.
- Register constrained tools.
- Add branching, step limits, retries, and event logging.

**Exit condition:** one run visibly performs multiple retrievals and reaches the correct constrained state.

### Phase 5 — Web workflow

- Build case inbox and workbench.
- Stream the real agent trace.
- Add document citations and preview.
- Add task approval and state mutation.

**Exit condition:** the complete two-minute path works from the browser.

### Phase 6 — Vultr deployment

- Deploy backend.
- Configure inference, storage, and database credentials.
- Seed the synthetic corpus.
- Run health checks and smoke tests.

**Exit condition:** the public URL executes the live agent path on synthetic data.

### Phase 7 — Demo hardening

- Run repeated end-to-end tests.
- Measure latency.
- Prepare a transparent fallback run.
- Freeze the demo dataset.
- Rehearse the pitch.

**Exit condition:** both primary demo cases pass five consecutive runs.

---

## 23. Suggested 48-hour allocation

| Time | Deliverable |
|---|---|
| Hours 0–4 | Scope, privacy cleanup, architecture, synthetic case definitions |
| Hours 4–10 | Synthetic generator, policy, manifest, and core case documents |
| Hours 10–18 | Database, ingestion, retrieval, and deterministic validators |
| Hours 18–26 | Vultr inference integration and agent orchestration |
| Hours 26–34 | Case workbench, live trace, citations, approval flow |
| Hours 34–40 | Vultr deployment and synthetic-data seeding |
| Hours 40–45 | End-to-end testing, reliability fixes, privacy scan |
| Hours 45–48 | Demo rehearsal, pitch, README, submission evidence |

### Five-person ownership model

1. Agent orchestration and Vultr inference.
2. Backend, data model, and tools.
3. Retrieval, synthetic data, and evaluation.
4. Frontend workflow and document evidence UX.
5. Deployment, QA, demo, and pitch integration.

All work shown to judges must be clearly attributable to the hackathon period.

---

## 24. Risks and mitigations

| Risk | Consequence | Mitigation |
|---|---|---|
| Real PDFs enter the repository | Privacy breach and disqualification risk | Move originals out before Git initialization; synthetic-only policy; automated privacy scan |
| Product looks like medical advice | Banned-project or safety concern | Track only explicit instructions; enforce out-of-scope language; no patient chatbot |
| Product looks like basic RAG | Weak Statement Two fit | Show plan, repeated retrieval, deterministic validation, branching, action, and monitoring |
| Product looks like an image analyzer | Banned-project concern | Use text-based PDFs; make document parsing subordinate to the operational workflow |
| Main feature looks like a dashboard | Banned-project concern | Use an interactive case workbench and approval workflow |
| Agent falsely closes a loop | Unsafe and destroys trust | Hard validators; false-closure release gate of zero; human review on uncertainty |
| LLM returns invalid structure | Failed run | Strict schema, bounded retry, deterministic fallback to review |
| Retrieval misses external evidence | Incorrect open state | Search by evidence class; alias table; incomplete coverage produces ambiguous review |
| Demo depends on too many services | Reliability failure | Keep one critical path; prepare health checks and transparent recorded-run fallback |
| Vultr appears incidental | Weak sponsor fit | Use Vultr inference for live planning/tool selection and show it in the trace |
| Unsupported statistics weaken pitch | Judge skepticism | Use specific sources and defined populations; avoid universal claims |
| Multi-agent architecture consumes time | Integration instability | One orchestrator with bounded tools and explicit state |

---

## 25. Acceptance criteria

The MVP is complete only when all of the following are true:

- [ ] Public project contains no real health data or direct identifiers.
- [ ] All demo documents are visibly synthetic and generated from owned templates.
- [ ] The web application is not Streamlit.
- [ ] A case can be opened from the browser.
- [ ] A live agent run creates and displays a plan.
- [ ] The run calls document retrieval at least twice for distinct evidence needs.
- [ ] The run calls at least one deterministic validation tool.
- [ ] A candidate is rejected for a concrete reason in the signature demo.
- [ ] The agent performs a targeted retrieval after that rejection.
- [ ] The final state is constrained to the defined state machine.
- [ ] Every displayed conclusion has a working page citation.
- [ ] The agent creates a real draft task.
- [ ] Human approval changes persistent state.
- [ ] The audit trace records the plan, tool calls, decision, and approval.
- [ ] Vultr Serverless Inference is on the live execution path.
- [ ] The backend is deployed on Vultr.
- [ ] The primary and backup cases pass five consecutive runs.
- [ ] No diagnosis, medical interpretation, treatment, or autonomous prescription is presented.

---

## 26. Pitch outline

### Opening

> The instruction is already in the record. The problem is that no system proves whether anyone acted on it.

### Product

> LoopCloser converts every explicit follow-up instruction into an auditable operational obligation.

### Agent differentiation

> It plans where evidence should exist, searches each source, rejects false matches, searches again when evidence is insufficient, and creates the next staff action.

### Safety

> It does not decide medicine. Clinicians author the recommendation and approve the action. The agent makes the workflow accountable.

### Closing

> A recommendation should not disappear merely because its proof lives in another document.

---

## 27. Final product principles

1. **Documents are evidence, not decoration.** Every conclusion must resolve to a source page.
2. **The agent owns the search, not the medicine.** Clinical intent comes from the clinician-authored record.
3. **Scheduled is not completed.** Workflow progress must not be mistaken for closure.
4. **No evidence is not always evidence of failure.** Incomplete coverage must produce human review.
5. **False closure is worse than an open review.** Uncertainty keeps the loop visible.
6. **Actions require accountability.** External consequences require explicit human approval.
7. **The demo must change state.** A useful enterprise agent does more than answer a question.
8. **Synthetic means synthetic.** No real identity, value set, metadata, branding, or source document belongs in the public build.

