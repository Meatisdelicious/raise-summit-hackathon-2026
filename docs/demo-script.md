# Two-minute demo — the killer patient

The whole build protects this path (Demo = 50% of judging). The goal: make it **impossible** to call the
workflow a single RAG call.

**Patient K:** Day 8 of an antagonist protocol, flagged **PCOS** at baseline. Today's E2 jumped steeply
from the prior draw; progesterone is borderline for day 8.

| Time | Beat | On screen |
|---|---|---|
| 0:00–0:15 | **Problem** | "A hormone value alone means nothing. Interpreting it needs her whole trajectory and the right protocol rule — which one, you don't know yet." |
| 0:15–0:30 | **New result lands** | Day-8 E2 arrives for Patient K. Click **Run monitoring review**. The agent shows its **plan** first. |
| 0:30–0:50 | **Rebuild + compute** | Agent retrieves patient context (PCOS, day 8) → retrieves the **trajectory** → computes **E2 rate-of-rise** + **OHSS composite** (tools, live in the trace). |
| 0:50–1:15 | **Money shot #1** | Because the OHSS composite **trips**, the agent goes and fetches the **OHSS-prevention SOP** — a document it would *not* have touched for a normal patient. Cited. |
| 1:15–1:30 | **Money shot #2** | It *also* notices **progesterone borderline for day 8**, so it fetches the **premature-luteinization rule** (a second computation-triggered retrieval). Cited. |
| 1:30–1:45 | **Action + brief** | Computes **next-draw timing (24h not 48h)** → emits the brief: "High OHSS-risk trajectory; SOP §4.2 → coasting vs agonist-trigger; progesterone borderline per §3.1 → monitor for freeze-all; next draw 24h." Every clause cited. |
| 1:45–2:00 | **Escalate + close** | **Escalation flag → biologist validates** → clinician alert. Close: "Cycle Sentinel doesn't decide medicine. It makes sure the right rule reaches the right person, in time — and it proves why." |

## Why no judge can call it RAG (say this)
> One patient produced **two computation-triggered retrievals** a normal patient wouldn't have caused,
> **two tool calls**, a **branch**, an **escalation**, and a **cited outcome**. The OHSS SOP and the
> luteinization rule couldn't be fetched up front — the agent didn't know it needed them until it had
> rebuilt the curve and run the math.

## Control + backup
- Run the **routine** patient (R) first or on standby: same UI, the agent computes, nothing trips, it
  does **not** fetch the OHSS/luteinization docs → `ROUTINE_CONTINUE`. This proves the extra retrievals in
  K are computation-driven, not scripted.
- If live Vultr fails, show the last successful run **clearly labeled as a recorded run** — never faked as live.
