# cyclesentinel — MILA backend

Python/FastAPI backend for **MILA**, the ovarian-stimulation monitoring & escalation agent
(RAISE Summit Hackathon 2026, Vultr enterprise-agent track). Package: `cyclesentinel` (src layout).

The seam with the React frontend is frozen in [`../../docs/CONTRACTS.md`](../../docs/CONTRACTS.md);
the technical spec is [`../../docs/doc.md`](../../docs/doc.md).

## Install

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev          # dev toolchain (ruff, mypy, pytest)
uv sync --extra dev --extra live   # + live deps (psycopg, pgvector, boto3, pillow)
```

## Run

```bash
make dev     # uvicorn cyclesentinel.main:app --reload  (replay mode, from repo root)
```

## Test

```bash
make test    # pytest -m 'not live'  (replay mode)
# or, from apps/api:
uv run ruff check . && uv run mypy --strict src && uv run pytest -q -m 'not live'
```

## Inference modes (`CS_INFERENCE_MODE`)

- **`replay`** — recorded cassettes for both the LLM and the retriever. Deterministic; used by CI/tests
  and `make dev`. **Default** — needs zero infra (SQLite, `VECTOR_STORE=local`), never calls the network.
- **`stub`** — canned outputs for fast unit tests.
- **`live`** — calls Vultr Serverless Inference (EU). Used only for the demo (`make demo`); set the
  `VULTR_*` env vars in `.env` (see `../../.env.example`).
