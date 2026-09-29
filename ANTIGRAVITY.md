# ANTIGRAVITY.md — SatyaBid build bootstrap

> **If you are an AI coding agent, start here.** Read this file fully, then
> `docs/UI_UX_SPEC.md`, then `docs/ARCHITECTURE.md`. Do not write code until
> you have read all three. When the human says "start developing", begin with
> Phase 1 of `docs/ROADMAP.md`.

## 1. Mission

Build **SatyaBid** — an Intelligent Bid Scrutiny & Cross-Bidder Cartel Detection
Platform — into a demo-winning web application for **Smart India Hackathon 2026**,
problem statement **SIH26100** (CPCL tender/bid compliance platform, Software
category). National-level submission deadline: **30 September 2026**.

The human (Prathamesh, B.Tech CSE 2nd year) demos this to judges. **The UI is
what judges see first and remember.** It must look government-grade,
trustworthy, and polished — not like a student Streamlit sketch.

## 2. What already exists (verified working)

`mvp/` contains a **tested, working Python engine**. Do not rewrite it from
scratch — rebuild the UI on top of it, then extend it.

| Module | Does | Status |
|---|---|---|
| `mvp/satyabid/ingest.py` | PDF text extraction (PyMuPDF) + OCR adapter seam | ✅ working |
| `mvp/satyabid/blueprint.py` | Tender → structured requirements (turnover, EMD, past performance, Make-in-India %, GFR 144(xi), delivery) | ✅ working, 8 requirements |
| `mvp/satyabid/checks.py` | 7 compliance rules per bidder, evidence-linked | ✅ working |
| `mvp/satyabid/collusion.py` | networkx collusion graph: shared directors/phones/addresses, cover-bidding price proximity, shared PDF author metadata | ✅ working |
| `mvp/satyabid/evidence.py` | PASS/FAIL/REVIEW verdicts as "speaking orders" | ✅ working |
| `mvp/satyabid/audit.py` | SHA-256 hash-chained tamper-evident ledger | ✅ working |
| `mvp/gen_data.py` | Synthetic demo dataset: 1 tender + 5 bidders, planted fraud | ✅ working |
| `mvp/run_mvp.py` | Headless CLI pipeline | ✅ working |
| `mvp/diagnose.py` | 8-stage backend diagnostic, all PASS | ✅ working |
| `mvp/tests/test_mvp.py` | Ground-truth tests, all PASS | ✅ working |
| `mvp/streamlit_legacy.py` | Old Streamlit UI | ⚠️ **retired** — replaced by Phase 1 S1–S7 web app |

Verify before you build: `cd mvp && pip install -r requirements.txt &&
python diagnose.py` — all 8 stages must PASS. If any fail, fix the engine
first; do not build UI on a broken backend.

**Ground truth of the demo dataset** (your UI must reproduce exactly this):
- A Apex Computing Solutions → PASS, L1 (₹4.32 Cr), clean
- B Brightline Technologies → FAIL (R1 turnover shortfall, R2 claim-vs-cert
  mismatch 118%, R3 invalid CA number `FCA-0987X4`)
- C Crestline Systems → REVIEW, HIGH collusion
- D Deltaforce IT Services → FAIL (R5 missing GFR 144(xi) declaration),
  HIGH collusion
- C+D form a **suspected cartel ring** (2 shared directors, same phone,
  same address, prices within 0.7%, same PDF author `Crestline-PC-03`)
- E Everest Digital → FAIL (R4 Class-I claim at 28% local content,
  R6 past performance ₹40L < ₹75L required)

## 3. What to build (priority order)

1. **New UI exactly per `docs/UI_UX_SPEC.md`** — this is the current task and
   the highest priority. Follow the spec screen by screen; do not improvise
   the design system.
2. Wire the UI to the existing engine (keep the engine's module boundaries).
3. Then follow `docs/ROADMAP.md` Phase 2+ (PDF report export, OCR adapter,
   demo assets).

## 4. Engineering conventions (non-negotiable)

- **Honesty over impressiveness.** Never invent metrics, recall figures, or
  "AI accuracy" claims. Simulated registries (GSTN/Udyam/MCA) must be labeled
  *simulated* in the UI. The engine is deterministic and rule-based — present
  that as a strength (auditable, explainable), not a weakness.
- **Every verdict must show its evidence.** A PASS/FAIL pill with no
  clause+document citation is a bug.
- **Two-cover isolation.** Only PASS bidders are ranked for L1. Never rank a
  FAIL/REVIEW bidder.
- **No mock data in the demo path.** The UI runs the real engine on the real
  PDFs. Loading spinners must reflect actual pipeline stages.
- Keep engine/UI decoupled: UI calls engine functions, never reimplements
  parsing.
- Python backend; you may choose the frontend stack, but the spec's look and
  information architecture are fixed. A polished single-page app (React/Vite
  or equivalent) is preferred over Streamlit for judge-facing polish.

## 5. Definition of done (Phase 1)

- [x] All 6 screens from the UI spec implemented and navigable
- [x] Demo dataset loads in ≤ 3 clicks to the verdict dashboard
- [x] `diagnose.py` still all-PASS (engine untouched or improved)
- [x] Every verdict pill links to its evidence view
- [x] Collusion graph renders the C+D ring with all 5 signals explorable
- [x] Audit ledger verifies with one click
- [x] Works from a fresh `pip install -r requirements.txt` with no manual steps

## 6. First task

Read `docs/UI_UX_SPEC.md` and `docs/ARCHITECTURE.md`, then present a build
plan (screens in order, component breakdown) and wait for approval before
writing code.
