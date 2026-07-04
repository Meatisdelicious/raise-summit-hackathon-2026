# CONTRACTS.md — frozen integration seams

**This file is the single source of truth for the interfaces every module imports.** It is created in
Wave 0 and frozen. Parallel agents code *to this file*, never to each other's implementations. A seam
change requires an orchestrator-owned integration task — never an inline edit by a feature task.

Derived from `docs/doc.md` §7 (tools), §10 (data model), §11 (API), §14.3 (events), §6 (state machine).

---

## 1. Enums — `apps/api/src/loopcloser/models/enums.py`

```python
from enum import StrEnum

class DecisionState(StrEnum):
    COMPLETED = "COMPLETED"
    SCHEDULED_NOT_COMPLETED = "SCHEDULED_NOT_COMPLETED"
    OPEN_NOT_DUE = "OPEN_NOT_DUE"
    OPEN_OVERDUE = "OPEN_OVERDUE"
    AMBIGUOUS_REQUIRES_REVIEW = "AMBIGUOUS_REQUIRES_REVIEW"
    CLOSED_BY_DOCUMENTED_EXCEPTION = "CLOSED_BY_DOCUMENTED_EXCEPTION"

class DocumentType(StrEnum):
    CONSULTATION_NOTE = "consultation_note"
    DISCHARGE_SUMMARY = "discharge_summary"
    LAB_ORDER = "lab_order"
    APPOINTMENT = "appointment"
    LAB_RESULT = "lab_result"
    EXTERNAL_LAB_RESULT = "external_lab_result"
    COORDINATOR_NOTE = "coordinator_note"
    CANCELLATION_REFUSAL = "cancellation_refusal"
    POLICY = "policy"
    ALIAS_TABLE = "alias_table"

class CandidateType(StrEnum):
    ORDER = "order"
    APPOINTMENT = "appointment"
    RESULT = "result"
    EXTERNAL_RESULT = "external_result"
    EXCEPTION = "exception"

class ValidationStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    AMBIGUOUS = "ambiguous"

class TaskType(StrEnum):
    COORDINATOR_REVIEW = "coordinator_review"
    VERIFY_EXTERNAL_RESULT = "verify_external_result"
    CLINICIAN_REMINDER = "clinician_reminder"
    PATIENT_NOTIFICATION_DRAFT = "patient_notification_draft"
    OVERDUE_ESCALATION = "overdue_escalation"
    MONITOR = "monitor"

class TaskStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTION_PENDING = "action_pending"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
```

## 2. Pydantic schemas — `apps/api/src/loopcloser/models/schemas.py`

The shared value objects. Field names are frozen. (SQLAlchemy ORM models mirror these; see §10 of the
spec for column lists — owned by `backend-core`, task T11.)

```python
class Citation(BaseModel):
    document_id: str
    page_number: int
    start_offset: int
    end_offset: int

class Recommendation(BaseModel):
    id: str
    case_id: str
    action_type: str            # e.g. "repeat_laboratory_test"
    target_code: str            # normalized synthetic test code
    instruction_date: date
    deadline: date | None
    documented_urgency: str | None
    source: Citation
    source_quote: str
    extraction_confidence: float
    status: str

class Candidate(BaseModel):
    id: str
    recommendation_id: str
    document_id: str
    page_number: int
    candidate_type: CandidateType
    retrieval_score: float
    validation_status: ValidationStatus
    validation_details: dict[str, bool | str]   # per-check results
    accepted: bool
    citation: Citation

class Decision(BaseModel):
    id: str
    recommendation_id: str
    state: DecisionState
    policy_version: str
    reasoning_summary: str
    accepted_evidence_ids: list[str]
    rejected_evidence_ids: list[str]
    citations: list[Citation]
    extraction_confidence: float | None   # NOT a clinical confidence score

class ToolCall(BaseModel):
    run_id: str
    step: int
    tool_name: str              # must be one of the 8 registered tools
    arguments: dict
    result_summary: str
    error: str | None
    latency_ms: int
```

## 3. Tool protocol — `apps/api/src/loopcloser/tools/base.py`

Exactly eight tools. Each takes a validated Pydantic arg model and returns a Pydantic result. The
registry maps name → tool; the model may not call an unregistered tool (spec §7.2).

```python
class Tool(Protocol):
    name: str                       # one of the 8 canonical names
    args_model: type[BaseModel]
    result_model: type[BaseModel]
    def run(self, args: BaseModel, ctx: "ToolContext") -> BaseModel: ...

TOOL_REGISTRY: dict[str, Tool]      # populated by tools/__init__.py
```

Tool arg shapes (frozen):

| Tool | Args (key fields) | Returns |
|---|---|---|
| `search_documents` | `case_id, document_types[], query, after?, before?, aliases[]?, limit` | ranked `Candidate`-shaped hits with citations |
| `get_document_context` | `document_id, page_number` | cited page text + adjacent context |
| `resolve_deadline` | `expression, instruction_date` | `date` or `needs_review` |
| `normalize_target` | `expression` | approved alias code (versioned, deterministic) |
| `validate_completion` | `recommendation_id, candidate_id` | `ValidationStatus` + per-check dict |
| `create_task_draft` | `decision_id, task_type, assigned_team, draft_body` | task draft (idempotent) |
| `approve_task` | `task_id, approver` | task with new state (authenticated human action) |
| `schedule_monitor` | `case_id, check_at` | scheduled monitor record |

## 4. Inference protocol — `apps/api/src/loopcloser/agent/inference/base.py`

```python
class InferenceClient(Protocol):
    def extract_recommendation(self, doc_text: str, meta: dict) -> Recommendation: ...
    def create_plan(self, rec: Recommendation, policy: dict) -> list[str]: ...
    def generate_query(self, rec: Recommendation, evidence_class: str) -> dict: ...
    def select_next_tool(self, state: dict) -> ToolCall: ...
    def explain_decision(self, decision: Decision, evidence: list[Candidate]) -> str: ...
```

Implementations (selected by `LOOPCLOSER_INFERENCE_MODE`): `VultrInferenceClient` (`live`),
`ReplayInferenceClient` (`replay`), `StubInferenceClient` (`stub`), `RecordingInferenceClient`
(`make record`). All structured outputs are validated against the schemas above; invalid output is
retried once with the validation error (spec §7.2, §18).

## 5. API surface — `apps/api/src/loopcloser/api/` (frozen routes, spec §11)

```
GET  /api/cases
GET  /api/cases/{case_id}
GET  /api/cases/{case_id}/documents
GET  /api/documents/{document_id}/pages/{page_number}
POST /api/cases/{case_id}/runs
GET  /api/runs/{run_id}
GET  /api/runs/{run_id}/events          # Server-Sent Events (see §6)
GET  /api/cases/{case_id}/recommendations
GET  /api/recommendations/{recommendation_id}
POST /api/tasks/{task_id}/approve
POST /api/tasks/{task_id}/reject
POST /api/tasks/{task_id}/request-review
POST /api/demo/reset                    # protected; restores synthetic state only
GET  /api/health
GET  /api/ready
```

## 6. SSE event contract — `GET /api/runs/{run_id}/events` (spec §14.3)

Each event is `data: <json>\n\n` with a discriminated `type`. Frozen event types (the frontend and
orchestrator both depend on these):

```jsonc
{ "type": "plan_created",      "run_id": "...", "step": 0, "plan": ["...", "..."] }
{ "type": "tool_call",         "run_id": "...", "step": 1, "tool_name": "search_documents", "arguments": {...} }
{ "type": "tool_result",       "run_id": "...", "step": 1, "summary": "Retrieved 3 candidates", "citations": [...] }
{ "type": "candidate_rejected","run_id": "...", "step": 2, "candidate_id": "...", "reason": "event predates instruction" }
{ "type": "retrieval_expanded","run_id": "...", "step": 3, "evidence_class": "external_result" }
{ "type": "decision",          "run_id": "...", "step": 4, "state": "OPEN_OVERDUE", "reasoning": "...", "citations": [...] }
{ "type": "task_drafted",      "run_id": "...", "step": 5, "task_id": "...", "task_type": "coordinator_review" }
{ "type": "run_error",         "run_id": "...", "message": "..." }
{ "type": "run_complete",      "run_id": "...", "final_state": "OPEN_OVERDUE" }
```

## 7. TypeScript mirror — `apps/web/src/types/`

`apps/web/src/types/` re-declares the enums (§1), the value objects (§2), the SSE event union (§6),
and the API response shapes (§5) in TypeScript. Keep names identical to the Python side. The frontend
builds against this + a mock client (task T13) before the real API exists.

---

**Rule:** if your task needs a field or type not defined here, that is a seam change — **escalate**
(AGENTS.md §12), do not add it inline.
