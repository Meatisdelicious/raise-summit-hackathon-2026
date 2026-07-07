# MILA — the pitch

**A 3-minute pitch for a non-biologist audience. Every number below is real and sourced ([Grounding & sources](#-grounding--sources)).**

> **One line:** MILA is an AI *agent* that watches IVF hormone monitoring, proves when a patient is heading
> for danger, cites the exact protocol, and flags a human — before the warning sign is lost in the records.

---

## ⏱️ The 3-minute script

**[0:00 — The hook]**

Right now, somewhere in Europe, a woman is a few days into an IVF cycle. She has spent thousands of euros
and months of hope on this one attempt. Her hormone levels are climbing a little too fast — an early
warning sign. The data to catch it already exists. **But nobody is watching the whole picture.**

**[0:20 — The problem, in plain words]**

IVF works by stimulating the ovaries to grow many eggs at once. Sometimes they over-respond — doctors call
it **OHSS**. It can put a woman in the hospital, and in rare cases, it kills. Here's the tragedy: it is
**almost entirely preventable** — *if* you catch the trend early and act in time.

But a cycle is monitored every 24 to 48 hours — across blood tests, ultrasound scans, and different
people's notes. The warning isn't in any single value; it's in the **trajectory**, spread across fragmented
records. And the one person who should connect the dots is buried under dozens of other patients.

**[1:00 — Why this matters, now]**

This is not a rare edge case. More than **2 million IVF cycles** happen every year worldwide — **nearly a
million in Europe alone**. Moderate-to-severe OHSS strikes **1 to 5%** of them. That's tens of thousands of
women a year, every year.

And the deeper failure is one medicine already known by the name: **follow-up**. Study after study shows that
**20% to 60% of abnormal test results are never properly followed up.** Every one of those is a warning that
was sitting in the system — and slipped through the cracks. On top of the human cost, each IVF attempt costs
**€3,500 to €7,500 in Europe** — and most patients need more than two. One missed signal can waste a cycle,
or end in an emergency.

**[1:30 — The solution]**

Meet **MILA**. For every new hormone result, MILA does what an overloaded team simply can't do consistently:

- it **rebuilds the patient's entire trajectory** — never the day's value in isolation;
- it **computes the risk with hard math**, not a guess;
- and the moment a number crosses a line, it **goes and pulls the exact clinical protocol rule** that
  applies, **quotes it**, and puts a **ready-to-review flag** in front of the biologist — *before the
  deadline is forgotten.*

MILA never diagnoses and never speaks to the patient. **A human validates every single conclusion.** It's
not a chatbot you ask questions — it's an **agent that watches, reasons step by step, and escalates.** You
literally watch it think.

**[2:20 — Why it *has* to exist]**

Why is this a necessity, not a nice-to-have? Because the stakes are a human life and a family's one real
chance — and the failure is an **operational** one we already know how to name. MILA doesn't replace the
doctor; it makes sure the doctor **never misses the moment that matters.**

And it earns trust by design: **every recommendation is cited** to a real protocol article — no black box.
Everything runs **sovereign, inside the EU**, on Vultr — because the most sensitive data a person owns should
never leave the region. This isn't a slide; it's **live today**: real AI reasoning, real document retrieval,
unfolding step by step.

**[2:45 — The close]**

Two million chances a year. A preventable danger hiding in plain sight. **MILA closes the loop — so no
warning sign is ever lost again.**

---

## 🎯 The idea in one sentence

> For every clinician-requested follow-up, MILA proves whether there is enough documented evidence that it
> was done — and if not, puts the exact next action, cited and ready, in front of a human before the window
> closes.

It answers an **operational** question, never a clinical one: *is the loop closed, and if not, what should
staff review next?*

---

## 📊 Grounding & sources

**The scale — IVF is huge and growing**
- **~2 million+** ART/IVF cycles performed worldwide each year; **~1 million** babies born from them.
- **960,347** ART cycles reported in **Europe** in 2022 alone, across 1,371 clinics in 39 countries.
- Each cycle costs **€3,500–€7,500** in Europe (**$20,000–$25,000** in the US), and the average patient needs
  **2.3–2.7 cycles** — so each attempt is emotionally and financially precious.

**The danger — OHSS is common, serious, and preventable**
- **Moderate-to-severe OHSS: 1–5%** of IVF cycles. Mild: 20–33%. Severe: 0.1–2%.
- OHSS is **iatrogenic** (caused by the stimulation itself) → **largely preventable** with timely monitoring
  and action. It can be **life-threatening**; mortality ~**1 in 50,000**.
- It shows up **in the numbers, early**: guidelines flag *coasting* when estradiol climbs above **~3,000
  pg/mL**, and the best predictor combines a high estradiol level with a high follicle count — exactly the
  kind of trajectory signal MILA computes. **The information is there; the problem is watching it in time.**

**The failure mode — lost follow-ups are endemic**
- Follow-up of abnormal test results fails in **20% to ~60%** of inpatient cases (up to 75% in emergency
  departments); **6.8% to 62%** of abnormal ambulatory lab results lack follow-up.
- A 2024 study found **23%** of patients who died or were moved to intensive care had a **missed or delayed
  diagnosis**; 17% of those errors caused harm. Handoffs and transitions are the most vulnerable points —
  precisely where fragmented fertility records lose the thread.

**Sources**
- ESHRE ART fact sheet (2023/2025) — global & European cycle volumes:
  https://www.eshre.eu/Europe/Factsheets-and-infographics
- OHSS incidence, severity & mortality — *Ovarian Hyperstimulation Syndrome: Current Views* (PMC2868304):
  https://pmc.ncbi.nlm.nih.gov/articles/PMC2868304/
- OHSS prevention & estradiol/coasting thresholds — ASRM guideline (2023):
  https://www.asrm.org/practice-guidance/practice-committee-documents/prevention-and-treatment-of-moderate-and-severe-ovarian-hyperstimulation-syndrome-a-guideline/
- Failure to follow up test results — systematic reviews (PMC3038104, PMC3445672):
  https://pmc.ncbi.nlm.nih.gov/articles/PMC3038104/ · https://pmc.ncbi.nlm.nih.gov/articles/PMC3445672/
- Diagnostic error & patient harm (2024 statistics overview):
  https://www.fhvlegal.com/blog/staggering-u-s-diagnostic-error-statistics-july-2024/
- IVF cost per cycle (US & Europe): https://www.advancedfertility.com/blog/what-is-the-average-cost-of-ivf-in-the-united-states

*Figures are ranges as reported in the literature; OHSS definitions vary between studies, so incidence is
given as a range. All patient data in the product and demo is 100% synthetic.*

---

## 🛡️ Why it's defensible (30-second backup answers)

- **"Isn't this just a chatbot / RAG?"** — No. MILA *computes* first, then retrieves the rule the computation
  calls for. The routine patient triggers **zero** retrieval; the at-risk patient triggers exactly the right
  one. You can't retrieve-then-answer, because *which* rule is needed is unknown until the math runs. That's
  an **agent**, not a search box.
- **"Is it safe?"** — It never diagnoses, never contacts the patient, and a biologist validates every brief.
  Every recommendation is grounded in a **cited** protocol article — reject the citation, reject the brief.
- **"Why does sovereignty matter?"** — Serial fertility hormone data is among the most sensitive data a
  person has. MILA keeps the reasoning, the retrieval, and the data **in the EU** (Vultr, HDS-aligned) — the
  sovereign alternative to shipping it overseas.
- **"Is it real?"** — Yes. Live on Vultr: real Kimi K2.6 reasoning + real Vultron document retrieval. Run the
  demo and watch the agent think, step by step.
