#!/usr/bin/env python3
"""Deterministic synthetic-data generator — the ``make seed`` target (Lane D).

Regenerates *everything* under ``data/synthetic/`` from the constants in this file:

- ``patients.json`` / ``results.json`` — the 4 demo cases (K / R / P / M) + serial trajectories.
- ``thresholds.json`` / ``dose_tables.json`` — the cited numeric thresholds & dose ranges the
  deterministic calculators read (never hardcoded in code).
- ``manifest.json`` — GROUND TRUTH per case (tripped signals, DecisionState[], expected citations,
  conditional-retrieval branches, escalation level) so tests assert against one source.
- ``corpus/<doc>/page-NN.txt`` + ``page-NN.meta.json`` + a rendered ``page-NN.png`` (the page image
  Vultron Prime-8B embeds for visual retrieval) for the 4 synthetic protocol/SOP documents. Each page
  carries the exact article text the text-only LLM cites.

ALL data is SYNTHETIC — invented patients with obviously fake labels ("Patient K/R/P/M"), no real
identifiers, no real hormone values. Keeps ``scripts/privacy_scan.py`` green.

Run via ``make seed`` (uses the venv so Pillow renders real page images). Running under a plain
interpreter without Pillow still works — it falls back to a 1x1 placeholder PNG. Idempotent + deterministic.
"""

from __future__ import annotations

import base64
import io
import json
import textwrap
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNTH = REPO_ROOT / "data" / "synthetic"
CORPUS = SYNTH / "corpus"

# A 1x1 fallback PNG (stdlib only) used if Pillow is unavailable. With Pillow (the ``dev``/``live``
# extra, so ``make seed`` runs it in the venv) each page is rendered to a real document image below —
# the page image Vultron Prime-8B embeds for visual retrieval. The text layer stays authoritative.
_PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

# Portrait page (~A4 ratio) rendered from the text layer. Bytes need not be identical across Pillow
# versions — no test asserts image bytes; the corpus loader only needs the file to exist.
_PAGE_W, _PAGE_H, _MARGIN = 1000, 1414, 72


def _page_font(size: int) -> Any:
    """The default bitmap font at ``size`` (scalable in Pillow >= 10.1; falls back otherwise)."""
    from PIL import ImageFont

    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # older Pillow: load_default() takes no size
        return ImageFont.load_default()


# The default bitmap font lacks a few glyphs; transliterate them FOR THE IMAGE ONLY so nothing
# renders as tofu. The ``.txt`` text layer keeps the originals (e.g. ``§`` for citations/grounding).
_GLYPH_FALLBACK = {"§": "Sec. ", "—": "-", "–": "-", "•": "* ", "≥": ">=", "≤": "<=", "→": "->"}


def _drawable(text: str) -> str:
    """Replace glyphs the default font can't draw (image-only; the text layer is untouched)."""
    for src, dst in _GLYPH_FALLBACK.items():
        text = text.replace(src, dst)
    return text


def _render_page_png(doc_id: str, text: str) -> bytes:
    """Render one corpus page to a real PNG (a plain SYNTHETIC protocol/SOP page), or fall back.

    Draws a letterhead, the document title, and the page's text layer (which already contains the
    article label, e.g. ``§2.1 …``) word-wrapped, plus a footer watermark. Returns PNG bytes.
    """
    try:
        from PIL import Image, ImageDraw
    except ModuleNotFoundError:
        return _PLACEHOLDER_PNG

    img = Image.new("RGB", (_PAGE_W, _PAGE_H), "white")
    draw = ImageDraw.Draw(img)
    x = _MARGIN
    y = _MARGIN

    draw.text((x, y), "CYCLE SENTINEL - SYNTHETIC PROTOCOL / SOP CORPUS", font=_page_font(19), fill=(120, 120, 120))
    y += 34
    draw.line([(x, y), (_PAGE_W - _MARGIN, y)], fill=(200, 200, 200), width=2)
    y += 28
    draw.text((x, y), doc_id.replace("_", " ").upper(), font=_page_font(34), fill=(20, 20, 20))
    y += 62

    body = _page_font(23)
    for paragraph in text.splitlines():
        stripped = _drawable(paragraph.strip())
        if not stripped:
            y += 18
            continue
        for line in textwrap.wrap(stripped, width=74):
            draw.text((x, y), line, font=body, fill=(30, 30, 30))
            y += 32
        y += 14

    draw.text(
        (x, _PAGE_H - _MARGIN),
        "SYNTHETIC - invented thresholds - internal biologist decision-support only.",
        font=_page_font(16),
        fill=(165, 165, 165),
    )
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()

# --- Synthetic cycle anchor --------------------------------------------------------------------
# Cycle day 1 == 2026-06-20; a draw on cycle day D is at 08:00Z on (2026-06-20 + (D-1) days).
_CYCLE_START_YMD = (2026, 6, 20)


def _drawn_at(cycle_day: int) -> str:
    """ISO-8601 draw timestamp for a given stimulation cycle day (deterministic, all in the past)."""
    day = _CYCLE_START_YMD[2] + (cycle_day - 1)
    return f"2026-06-{day:02d}T08:00:00Z"


# ================================================================================================
# 1. PATIENTS + SERIAL RESULTS (the 4 demo cases; docs/doc.md §7)
# ================================================================================================

PATIENTS: list[dict[str, Any]] = [
    # K — killer: PCOS, high reserve, steep E2, borderline-high P4 for day 8.
    {
        "id": "pat-K",
        "label": "Patient K",
        "protocol": "antagonist",
        "cycle_day": 8,
        "amh": 5.8,
        "antral_follicle_count": 24,
        "pcos_flag": True,
    },
    # R — routine control: normal curve, normal P4, no PCOS. Must NOT trigger conditional retrieval.
    {
        "id": "pat-R",
        "label": "Patient R",
        "protocol": "antagonist",
        "cycle_day": 8,
        "amh": 2.1,
        "antral_follicle_count": 12,
        "pcos_flag": False,
    },
    # P — poor responder: low reserve, flat E2 vs the expected curve.
    {
        "id": "pat-P",
        "label": "Patient P",
        "protocol": "antagonist",
        "cycle_day": 8,
        "amh": 0.6,
        "antral_follicle_count": 5,
        "pcos_flag": False,
    },
    # M — missing timepoint: expected day-7 draw absent (gap day 5 -> day 8).
    {
        "id": "pat-M",
        "label": "Patient M",
        "protocol": "antagonist",
        "cycle_day": 8,
        "amh": 2.4,
        "antral_follicle_count": 14,
        "pcos_flag": False,
    },
]


def _result(
    rid: str,
    patient_id: str,
    cycle_day: int,
    e2: float | None,
    lh: float | None,
    progesterone: float | None,
    mature_follicle_count: int | None = None,
) -> dict[str, Any]:
    return {
        "id": rid,
        "patient_id": patient_id,
        "cycle_day": cycle_day,
        "drawn_at": _drawn_at(cycle_day),
        "e2": e2,
        "lh": lh,
        "progesterone": progesterone,
        "fsh": None,
        "hcg": None,
        "mature_follicle_count": mature_follicle_count,
    }


# Serial trajectories, ordered by cycle_day. The newest draw (day 8, except M whose current is day 8
# with the day-7 draw absent) is the result the agent run interprets.
RESULTS: list[dict[str, Any]] = [
    # K — steep E2 rise: day7 2600 -> day8 4200 = +61.5%/day; 19 mature follicles; P4 1.6 > 1.5.
    _result("res-K-d3", "pat-K", 3, 210.0, 3.1, 0.4),
    _result("res-K-d5", "pat-K", 5, 920.0, 2.6, 0.7),
    _result("res-K-d7", "pat-K", 7, 2600.0, 2.2, 1.2, mature_follicle_count=15),
    _result("res-K-d8", "pat-K", 8, 4200.0, 2.0, 1.6, mature_follicle_count=19),
    # R — normal curve: day7 980 -> day8 1350 = +37.8%/day; 8 follicles; P4 0.9 < 1.5.
    _result("res-R-d3", "pat-R", 3, 140.0, 4.2, 0.3),
    _result("res-R-d5", "pat-R", 5, 420.0, 3.8, 0.5),
    _result("res-R-d7", "pat-R", 7, 980.0, 3.3, 0.7, mature_follicle_count=6),
    _result("res-R-d8", "pat-R", 8, 1350.0, 3.0, 0.9, mature_follicle_count=8),
    # P — flat E2: day8 380 vs expected ~1200 (ratio 0.32 < 0.5); 4 follicles; P4 normal.
    _result("res-P-d3", "pat-P", 3, 90.0, 5.1, 0.3),
    _result("res-P-d5", "pat-P", 5, 180.0, 4.6, 0.4),
    _result("res-P-d7", "pat-P", 7, 320.0, 4.1, 0.6, mature_follicle_count=3),
    _result("res-P-d8", "pat-P", 8, 380.0, 3.9, 0.7, mature_follicle_count=4),
    # M — day-7 draw ABSENT: draws land on day 3, day 5, day 8 (gap of 3 days > 48h cadence).
    _result("res-M-d3", "pat-M", 3, 140.0, 4.0, 0.3),
    _result("res-M-d5", "pat-M", 5, 430.0, 3.6, 0.5),
    _result("res-M-d8", "pat-M", 8, 720.0, 3.2, 1.0, mature_follicle_count=8),
]


# ================================================================================================
# 2. THRESHOLDS (cited numeric cutoffs the calculators read; each carries its grounding citation)
# ================================================================================================

THRESHOLDS: dict[str, Any] = {
    "_note": "Cited numeric thresholds for the deterministic calculators, in the exact `Thresholds` "
    "TypedDict shape (cyclesentinel.calculators.Thresholds) the calculators consume. Loaded live via "
    "cyclesentinel.calculators.load_thresholds. Never hardcode these in code — read them here so "
    "every escalation grounds to a protocol/SOP article. Each block carries an optional `citation` "
    "(provenance only; ignored by the loader).",
    "units": {
        "e2": "pg/mL",
        "progesterone": "ng/mL",
        "e2_rate": "percent_per_day",
        "interval": "hours",
    },
    "ohss": {
        "e2_high": 3000.0,
        "rate_pct_per_day_high": 50.0,
        "mature_follicle_count_high": 18,
        "pcos_threshold_multiplier": 0.9,
        "citation": {"doc_id": "ohss_sop", "rule_type": "ohss", "page": 3, "article": "§3.1"},
    },
    "luteinization": {
        "progesterone_by_cycle_day": [
            {"max_cycle_day": 6, "threshold": 1.0},
            {"max_cycle_day": 8, "threshold": 1.5},
            {"max_cycle_day": 10, "threshold": 1.75},
        ],
        "default_threshold": 2.0,
        "citation": {
            "doc_id": "luteinization",
            "rule_type": "luteinization",
            "page": 2,
            "article": "§2.3",
        },
    },
    "poor_responder": {
        "flat_rate_pct_per_day": 70.0,
        "min_e2_on_trajectory": 500.0,
        "citation": {
            "doc_id": "poor_responder",
            "rule_type": "poor_responder",
            "page": 2,
            "article": "§3.1",
        },
    },
}


# ================================================================================================
# 3. DOSE TABLES (gonadotropin dose-adjustment ranges by situation; each cited)
# ================================================================================================

DOSE_TABLES: dict[str, Any] = {
    "_note": "Gonadotropin dose-adjustment ranges (IU) by computed situation. Read by "
    "lookup_dose_adjustment; deltas are advisory ranges a human validates.",
    "units": {"dose": "IU"},
    "gonadotropin_adjustments": [
        {
            "situation": "routine",
            "action": "maintain",
            "delta_iu_range": [0, 0],
            "citation": {
                "doc_id": "stimulation",
                "rule_type": "stimulation",
                "page": 3,
                "article": "§1.3",
            },
        },
        {
            "situation": "poor_response",
            "action": "increase",
            "delta_iu_range": [75, 150],
            "citation": {
                "doc_id": "poor_responder",
                "rule_type": "poor_responder",
                "page": 3,
                "article": "§3.2",
            },
        },
        {
            "situation": "ohss_risk",
            "action": "reduce_or_coast",
            "delta_iu_range": [-150, -75],
            "citation": {
                "doc_id": "ohss_sop",
                "rule_type": "ohss",
                "page": 4,
                "article": "§4.2",
            },
        },
        {
            "situation": "premature_luteinization",
            "action": "freeze_all_consider",
            "delta_iu_range": None,
            "citation": {
                "doc_id": "luteinization",
                "rule_type": "luteinization",
                "page": 3,
                "article": "§2.4",
            },
        },
    ],
}


# ================================================================================================
# 4. SYNTHETIC PROTOCOL/SOP CORPUS (page text layer + meta; the exact articles the LLM cites)
# ================================================================================================
# Each entry: (doc_id, rule_type, page, article, text). The `text` contains, verbatim, the quote
# used in the manifest citations so citations RESOLVE to a real page.

CorpusPageSpec = tuple[str, str, int, str, str]

CORPUS_PAGES: list[CorpusPageSpec] = [
    # ---- stimulation protocol (rule_type: stimulation) ----
    (
        "stimulation",
        "stimulation",
        1,
        "Cover",
        "SYNTHETIC — Ovarian Stimulation Protocol (Antagonist Cycle)\n"
        "Cycle Sentinel demo corpus. For internal biologist decision-support only; not medical "
        "advice. All values are invented for the RAISE Summit hackathon.\n",
    ),
    (
        "stimulation",
        "stimulation",
        2,
        "§1.2",
        "§1.2 Monitoring cadence and next-draw timing\n"
        "Schedule monitoring draws no more than 48 hours apart; if a scheduled draw is missing, flag "
        "the gap and request the delayed draw before adjusting the plan. When estradiol accelerates, "
        "shorten the interval to 24 hours.\n"
        "The standard monitoring interval is 48 hours; a gap wider than one cadence step is treated "
        "as a missing timepoint and must be surfaced for review.\n",
    ),
    (
        "stimulation",
        "stimulation",
        3,
        "§1.3",
        "§1.3 Gonadotropin dosing\n"
        "Maintain the current gonadotropin dose when the response tracks the expected curve; adjust "
        "in 75 IU increments only when a calculator or rule indicates. Dose changes are advisory and "
        "require biologist validation before they reach the clinic.\n",
    ),
    # ---- OHSS prevention SOP (rule_type: ohss) ----
    (
        "ohss_sop",
        "ohss",
        1,
        "Cover",
        "SYNTHETIC — Ovarian Hyperstimulation Syndrome (OHSS) Prevention SOP\n"
        "Cycle Sentinel demo corpus. Internal triage support only. Invented thresholds.\n",
    ),
    (
        "ohss_sop",
        "ohss",
        2,
        "§2.1",
        "§2.1 Early precursors of hyperstimulation\n"
        "A rise in estradiol of 50% or more per day is an early precursor of ovarian "
        "hyperstimulation and must be scored. Estradiol per mature follicle above 250 pg/mL, or "
        "below 100 pg/mL, is noted as context for the composite score.\n",
    ),
    (
        "ohss_sop",
        "ohss",
        3,
        "§3.1",
        "§3.1 OHSS composite score\n"
        "Score one point each for estradiol >= 3000 pg/mL, >= 18 mature follicles, an estradiol rise "
        ">= 50% per day, and PCOS; a total >= 3 is a HIGH composite tier. A total of 2 is MODERATE; "
        "below 2 is LOW.\n",
    ),
    (
        "ohss_sop",
        "ohss",
        4,
        "§4.2",
        "§4.2 Escalation and management\n"
        "If the OHSS composite tier is HIGH, withhold the standard trigger and consider coasting, a "
        "GnRH-agonist trigger swap, or a freeze-all strategy, and escalate to the biologist. Reduce "
        "the gonadotropin dose by 75 to 150 IU where continued stimulation is indicated.\n",
    ),
    # ---- premature luteinization rule (rule_type: luteinization) ----
    (
        "luteinization",
        "luteinization",
        1,
        "Cover",
        "SYNTHETIC — Premature Luteinization Monitoring Rule\n"
        "Cycle Sentinel demo corpus. Internal triage support only. Invented thresholds.\n",
    ),
    (
        "luteinization",
        "luteinization",
        2,
        "§2.3",
        "§2.3 Cycle-day-dependent progesterone thresholds\n"
        "Progesterone thresholds are cycle-day dependent: 1.0 ng/mL through day 6, 1.5 ng/mL on days "
        "7-8, and 1.75 ng/mL from day 9. A value at or above the day threshold flags premature "
        "luteinization.\n",
    ),
    (
        "luteinization",
        "luteinization",
        3,
        "§2.4",
        "§2.4 Action on elevated progesterone\n"
        "When serum progesterone exceeds the cycle-day threshold, consider a freeze-all strategy and "
        "escalate for biologist review before trigger.\n",
    ),
    # ---- poor responder management (rule_type: poor_responder) ----
    (
        "poor_responder",
        "poor_responder",
        1,
        "Cover",
        "SYNTHETIC — Poor Responder Management\n"
        "Cycle Sentinel demo corpus. Internal triage support only. Invented thresholds.\n",
    ),
    (
        "poor_responder",
        "poor_responder",
        2,
        "§3.1",
        "§3.1 Poor-response criteria\n"
        "A poor response is defined as a day-8 estradiol below 50% of the expected curve (expected "
        "about 1200 pg/mL by day 8) in a patient with diminished ovarian reserve (low AMH or low "
        "antral follicle count).\n",
    ),
    (
        "poor_responder",
        "poor_responder",
        3,
        "§3.2",
        "§3.2 Dose and plan review\n"
        "For a confirmed poor response, review the gonadotropin dose (increase by 75-150 IU) or "
        "reconsider the stimulation plan, and escalate for biologist review.\n",
    ),
]


# ================================================================================================
# 5. MANIFEST — GROUND TRUTH per case (one source of truth for tests + downstream lanes)
# ================================================================================================

MANIFEST: dict[str, Any] = {
    "_note": "Ground truth per demo case. Tests assert calculator signals, DecisionState[], "
    "conditional-retrieval branches, citations and escalation against this. Keeping it here means "
    "ground truth lives in one place.",
    "cases": {
        "K": {
            "patient_id": "pat-K",
            "result_id": "res-K-d8",
            "summary": "Steep E2 rise + PCOS -> OHSS composite HIGH; P4 borderline-high for day 8 "
            "-> premature luteinization. Dual flag, urgent.",
            "computed_signals": [
                {
                    "name": "e2_rate",
                    "value": 61.5,
                    "detail": "E2 +61.5%/day (2600 -> 4200 over 1 day)",
                    "tripped": True,
                },
                {
                    "name": "e2_per_follicle",
                    "value": 221.1,
                    "detail": "E2 221 pg/mL per mature follicle (4200 / 19)",
                    "tripped": False,
                },
                {
                    "name": "ohss_composite",
                    "value": "HIGH",
                    "detail": "score 4/4: E2>=3000, follicles>=18, rate>=50%/day, PCOS",
                    "tripped": True,
                },
                {
                    "name": "progesterone_for_day",
                    "value": 1.6,
                    "detail": "P4 1.6 ng/mL >= 1.5 threshold for day 8",
                    "tripped": True,
                },
                {
                    "name": "response_curve",
                    "value": 3.5,
                    "detail": "E2 4200 vs expected 1200 (ratio 3.5) — not a poor response",
                    "tripped": False,
                },
            ],
            "expected_states": ["OHSS_RISK_ESCALATE", "PREMATURE_LUTEINIZATION_FLAG"],
            "retrieve_rule_branches": ["ohss", "luteinization"],
            "expected_citations": [
                {"doc_id": "ohss_sop", "rule_type": "ohss", "page": 4, "article": "§4.2"},
                {
                    "doc_id": "luteinization",
                    "rule_type": "luteinization",
                    "page": 3,
                    "article": "§2.4",
                },
            ],
            "action": {"name": "next_draw_timing", "detail": "24h — accelerating E2"},
            "escalation_level": "urgent",
        },
        "R": {
            "patient_id": "pat-R",
            "result_id": "res-R-d8",
            "summary": "Normal curve, normal P4, no PCOS. The CONTROL: computes but does NOT branch "
            "into conditional rule retrieval.",
            "computed_signals": [
                {
                    "name": "e2_rate",
                    "value": 37.8,
                    "detail": "E2 +37.8%/day (980 -> 1350 over 1 day)",
                    "tripped": False,
                },
                {
                    "name": "e2_per_follicle",
                    "value": 168.8,
                    "detail": "E2 169 pg/mL per mature follicle (1350 / 8)",
                    "tripped": False,
                },
                {
                    "name": "ohss_composite",
                    "value": "LOW",
                    "detail": "score 0/4",
                    "tripped": False,
                },
                {
                    "name": "progesterone_for_day",
                    "value": 0.9,
                    "detail": "P4 0.9 ng/mL < 1.5 threshold for day 8",
                    "tripped": False,
                },
                {
                    "name": "response_curve",
                    "value": 1.13,
                    "detail": "E2 1350 vs expected 1200 (ratio 1.13) — on curve",
                    "tripped": False,
                },
            ],
            "expected_states": ["ROUTINE_CONTINUE"],
            "retrieve_rule_branches": [],
            "expected_citations": [
                {
                    "doc_id": "stimulation",
                    "rule_type": "stimulation",
                    "page": 2,
                    "article": "§1.2",
                }
            ],
            "action": {"name": "next_draw_timing", "detail": "48h — standard cadence"},
            "escalation_level": "none",
        },
        "P": {
            "patient_id": "pat-P",
            "result_id": "res-P-d8",
            "summary": "Flat E2 vs expected curve -> poor response. Retrieves poor-responder "
            "criteria; dose/plan review; info escalation.",
            "computed_signals": [
                {
                    "name": "e2_rate",
                    "value": 18.8,
                    "detail": "E2 +18.8%/day (320 -> 380 over 1 day)",
                    "tripped": False,
                },
                {
                    "name": "e2_per_follicle",
                    "value": 95.0,
                    "detail": "E2 95 pg/mL per mature follicle (380 / 4)",
                    "tripped": False,
                },
                {
                    "name": "ohss_composite",
                    "value": "LOW",
                    "detail": "score 0/4",
                    "tripped": False,
                },
                {
                    "name": "progesterone_for_day",
                    "value": 0.7,
                    "detail": "P4 0.7 ng/mL < 1.5 threshold for day 8",
                    "tripped": False,
                },
                {
                    "name": "response_curve",
                    "value": 0.32,
                    "detail": "E2 380 vs expected 1200 (ratio 0.32 < 0.5) — poor response",
                    "tripped": True,
                },
            ],
            "expected_states": ["POOR_RESPONSE_FLAG"],
            "retrieve_rule_branches": ["poor_responder"],
            "expected_citations": [
                {
                    "doc_id": "poor_responder",
                    "rule_type": "poor_responder",
                    "page": 3,
                    "article": "§3.2",
                }
            ],
            "action": {"name": "dose_adjustment", "detail": "increase 75-150 IU — poor response"},
            "escalation_level": "info",
        },
        "M": {
            "patient_id": "pat-M",
            "result_id": "res-M-d8",
            "summary": "Expected day-7 draw absent (gap day 5 -> day 8). Flags the gap, requests "
            "the missing draw. No conditional rule retrieval.",
            "computed_signals": [
                {
                    "name": "monitoring_gap",
                    "value": 3,
                    "detail": "3-day gap (day 5 -> day 8) exceeds the 48h monitoring cadence",
                    "tripped": True,
                },
                {
                    "name": "e2_rate",
                    "value": 22.5,
                    "detail": "E2 +22.5%/day (430 -> 720 over 3 days) — computed over a wide gap",
                    "tripped": False,
                },
                {
                    "name": "ohss_composite",
                    "value": "LOW",
                    "detail": "score 0/4",
                    "tripped": False,
                },
                {
                    "name": "progesterone_for_day",
                    "value": 1.0,
                    "detail": "P4 1.0 ng/mL < 1.5 threshold for day 8",
                    "tripped": False,
                },
                {
                    "name": "response_curve",
                    "value": 0.6,
                    "detail": "E2 720 vs expected 1200 (ratio 0.6) — on curve, not poor",
                    "tripped": False,
                },
            ],
            "expected_states": ["MISSING_TIMEPOINT"],
            "retrieve_rule_branches": [],
            "expected_citations": [
                {
                    "doc_id": "stimulation",
                    "rule_type": "stimulation",
                    "page": 2,
                    "article": "§1.2",
                }
            ],
            "action": {"name": "next_draw_timing", "detail": "request the missing day-7 draw (24h)"},
            "escalation_level": "info",
        },
    },
}


# ================================================================================================
# Writers
# ================================================================================================


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_corpus() -> list[dict[str, Any]]:
    """Write page-NN.txt + page-NN.meta.json (+ page-NN.png) per doc. Returns the page index."""
    index: list[dict[str, Any]] = []
    for doc_id, rule_type, page, article, text in CORPUS_PAGES:
        doc_dir = CORPUS / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        stem = f"page-{page:02d}"
        (doc_dir / f"{stem}.txt").write_text(text, encoding="utf-8")
        meta = {"doc_id": doc_id, "rule_type": rule_type, "page": page, "article": article}
        _write_json(doc_dir / f"{stem}.meta.json", meta)
        (doc_dir / f"{stem}.png").write_bytes(_render_page_png(doc_id, text))
        index.append(meta)
    return index


def main() -> int:
    SYNTH.mkdir(parents=True, exist_ok=True)
    _write_json(SYNTH / "patients.json", PATIENTS)
    _write_json(SYNTH / "results.json", RESULTS)
    _write_json(SYNTH / "thresholds.json", THRESHOLDS)
    _write_json(SYNTH / "dose_tables.json", DOSE_TABLES)
    _write_json(SYNTH / "manifest.json", MANIFEST)
    index = _write_corpus()

    print(f"seed: {len(PATIENTS)} patients, {len(RESULTS)} results -> {SYNTH}")
    print(f"seed: {len(index)} corpus pages across 4 docs -> {CORPUS}")
    print("seed: thresholds.json, dose_tables.json, manifest.json written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
