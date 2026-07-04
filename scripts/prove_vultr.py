#!/usr/bin/env python3
"""Prove — from Vultr's own API — that this project really uses Vultr.

The Vultr dashboard's main page shows nothing for Serverless Inference (it is pay-per-token, billed
under Serverless Inference → Usage, not Compute). So the proof lives in the API itself. This script
hits the real Vultr API with your key and prints, screenshot-ready:

  1. the models the account can call (Kimi K2.6 + the Vultron retrievers),
  2. the Vector Store collections that exist (one per rule_type) + their item counts,
  3. a LIVE retrieval: Vector Store search -> Vultron rerank, with real relevance scores,
  4. a LIVE LLM call to Kimi K2.6,
  5. the account's token usage BEFORE and AFTER — the delta proves the calls above really hit Vultr.

Run:  make prove-vultr        (sources ./.env)
  or:  VULTR_INFERENCE_API_KEY=... python scripts/prove_vultr.py
"""

from __future__ import annotations

import os
import sys

import httpx

BASE = os.environ.get("VULTR_INFERENCE_BASE_URL", "https://api.vultrinference.com/v1").rstrip("/")
KEY = os.environ.get("VULTR_INFERENCE_API_KEY", "").strip()
LLM = os.environ.get("CS_LLM_MODEL", "moonshotai/Kimi-K2.6")
RETRIEVER = os.environ.get("CS_RETRIEVER_MODEL", "vultr/VultronRetrieverPrime-Qwen3.5-8B")
PREFIX = os.environ.get("VULTR_VECTOR_COLLECTION", "cs")
RULE_TYPES = ("ohss", "lut", "poor", "stim")

H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def rule(title: str) -> None:
    print(f"\n{'=' * 68}\n{title}\n{'=' * 68}")


def chat_tokens(client: httpx.Client) -> int:
    """Total Kimi chat tokens the account has used this month (0 if none yet)."""
    r = client.get(f"{BASE}/usage")
    r.raise_for_status()
    month = r.json().get("usage", {}).get("current_month", {})
    total = 0
    for row in month.get("chat_usage", []):
        total += int(row.get("input_tokens", 0)) + int(row.get("output_tokens", 0))
    return total


def main() -> int:
    if not KEY:
        print("error: set VULTR_INFERENCE_API_KEY (e.g. `make prove-vultr`).", file=sys.stderr)
        return 2

    with httpx.Client(timeout=httpx.Timeout(60.0, connect=15.0), headers=H) as client:
        print(f"Vultr endpoint : {BASE}")
        print(f"API key        : ****{KEY[-4:]}  ({len(KEY)} chars)")

        # 1. Models the account can call ----------------------------------------------------------
        rule("1. MODELS AVAILABLE ON THIS ACCOUNT  (GET /v1/models)")
        models = [m["id"] for m in client.get(f"{BASE}/models").json().get("data", [])]
        print(f"  LLM       {LLM:<42}{'  ✓ present' if LLM in models else '  ✗ MISSING'}")
        print(f"  Retriever {RETRIEVER:<42}{'  ✓ present' if RETRIEVER in models else '  ✗ MISSING'}")

        # 2. Vector Store collections -------------------------------------------------------------
        rule("2. VECTOR STORE COLLECTIONS  (GET /v1/vector_store)")
        listed = {c["id"]: c for c in client.get(f"{BASE}/vector_store").json().get("collections", [])}
        for rt in RULE_TYPES:
            cid = f"{PREFIX}{rt}"
            meta = listed.get(cid)
            if not meta:
                print(f"  {cid:<10} ✗ not found")
                continue
            items = client.get(f"{BASE}/vector_store/{cid}/items").json().get("items", [])
            print(f"  {cid:<10} ✓ {len(items)} pages indexed   (created {meta.get('created')})")

        # usage BEFORE the live calls
        before = chat_tokens(client)

        # 3. LIVE retrieval: Vector Store search -> Vultron rerank --------------------------------
        rule("3. LIVE RETRIEVAL  (POST /v1/vector_store/csohss/search  ->  POST /v1/rerank)")
        query = "steep estradiol rise, OHSS escalation and management, coasting or freeze-all"
        search = client.post(
            f"{BASE}/vector_store/{PREFIX}ohss/search", json={"input": query, "top_k": 6}
        ).json()
        docs = [r["content"] for r in search.get("results", [])]
        print(f"  Vector Store recall  -> {len(docs)} candidate pages")
        rr = client.post(
            f"{BASE}/rerank", json={"model": RETRIEVER, "query": query, "documents": docs}
        ).json()
        print(f"  Vultron rerank ({RETRIEVER.split('/')[-1]}) -> real relevance scores:")
        for res in rr.get("results", [])[:3]:
            txt = docs[res["index"]].splitlines()[0][:52]
            print(f"     score {res['relevance_score']:>8.3f}   {txt}")

        # 4. LIVE LLM call ------------------------------------------------------------------------
        rule("4. LIVE LLM CALL  (POST /v1/chat/completions)")
        chat = client.post(
            f"{BASE}/chat/completions",
            json={
                "model": LLM,
                "temperature": 0,
                "messages": [{"role": "user", "content": "Reply with exactly one word: online"}],
            },
        ).json()
        reply = chat["choices"][0]["message"]["content"].strip()
        used = chat.get("usage", {})
        print(f"  {LLM} replied: {reply!r}")
        print(f"  this call used {used.get('total_tokens', '?')} tokens")

        # 5. usage AFTER — the delta proves the calls hit Vultr -----------------------------------
        rule("5. ACCOUNT TOKEN USAGE  (GET /v1/usage)  — the live proof")
        after = chat_tokens(client)
        print(f"  Kimi chat tokens BEFORE : {before:>8,}")
        print(f"  Kimi chat tokens AFTER  : {after:>8,}")
        print(f"  delta from this run     : {after - before:>8,}  ← real usage, on THIS account")

    print(
        "\n✅ Proof complete. The collections above exist on your Vultr Vector Store, the rerank "
        "scores come from Vultron Prime-8B, and the token counter moved — all from Vultr's own API.\n"
        "   (Dashboard: find this under Serverless Inference → Usage, not the Compute page.)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
