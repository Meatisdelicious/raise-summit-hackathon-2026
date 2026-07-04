# Cycle Sentinel

**An ovarian-stimulation monitoring & escalation agent — RAISE Summit Hackathon 2026 (Vultr enterprise track).**

For every new serial hormone result in an IVF stimulation cycle, Cycle Sentinel rebuilds the patient's
trajectory, computes the risk signals, pulls the exact protocol/SOP rule the computation says applies, and
hands the **lab biologist** a **cited, ready-to-validate escalation brief** — before a missed or mis-timed
value wrecks the cycle. It is **internal triage for professionals — never patient-facing advice.**

> ⚠️ **Synthetic data only.** Serial hormone data is Article-9 sensitive. No real patient data belongs in
> this repo or the demo. See [`docs/safety.md`](docs/safety.md).

## Read these
| Doc | Purpose |
|---|---|
| [`docs/PRD.md`](docs/PRD.md) | Product brief — problem, users, the "not RAG" thesis, judging fit |
| [`docs/doc.md`](docs/doc.md) | Technical spec — agent loop, tools, calculators, states, data, demo cases |
| [`docs/CONTRACTS.md`](docs/CONTRACTS.md) | API contract (REST + SSE + TS types) the React app builds against |
| [`docs/architecture.md`](docs/architecture.md) | System architecture on Vultr |
| [`docs/demo-script.md`](docs/demo-script.md) | The 2-minute "killer patient" demo |
| [`docs/safety.md`](docs/safety.md) | Safety & privacy boundary |
| [`AGENTS.md`](AGENTS.md) | Conventions + non-negotiables |

## The idea in one loop
plan → retrieve patient context → retrieve trajectory → **compute** (E2 rate, OHSS composite, P4-for-day)
→ **branch → conditionally retrieve** the governing rule (OHSS SOP / luteinization / poor-responder) →
compute next action → **cited brief + escalation** → human validates. The conditional retrievals can't be
issued up front — which is why it's an agent, not RAG.

## Stack
Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy + pgvector · React + TypeScript (Raph) · **Vultr**
Serverless Inference + EU vector store (HDS-aligned) + Object Storage + Compute.

## Dev
```
cp .env.example .env      # replay mode needs no secrets; live mode needs Vultr keys
make install
make verify               # lint + typecheck + test + privacy (replay mode)
make dev                  # run the API
```

## The four hard rules
1. Synthetic data only. 2. Internal triage — never patient-facing. 3. Every recommendation cites a
protocol article. 4. Keep it an agent (trajectory + computation-driven conditional retrieval + branching),
not RAG. Full text in [`AGENTS.md`](AGENTS.md).
