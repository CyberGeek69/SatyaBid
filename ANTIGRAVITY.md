# ANTIGRAVITY.md — SatyaBid build bootstrap

> **If you are an AI coding agent, start here.** Read this file fully, then
> `docs/UI_UX_SPEC.md`, then `docs/ARCHITECTURE.md`. Do not write code until
> you have read all three. When the human says "start developing", begin with
> Phase 1 of `docs/ROADMAP.md`.

## 1. Mission

Build **SatyaBid** — an Intelligent Bid Scrutiny & Cross-Bidder Cartel Detection
Platform — into a demo-winning web application for **Smart India Hackathon 2026**,
problem statement **SIH26100** (CPCL tender/bid compliance platform, Software
category). College internal round cleared — now competing at national level.

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
| `mvp/satyabid/checks.py` | 8 compliance rules (R1–R8) per bidder, evidence-linked | ✅ working |
| `mvp/satyabid/collusion.py` | networkx collusion graph: shared directors/phones/addresses, cover-bidding price proximity, shared PDF author metadata, ML-weighted edges | ✅ working |
| `mvp/satyabid/mlforensics.py` | **ML forensics (scikit-learn): TF-IDF word n-gram cosine paraphrase detection + char n-gram fuzzy identity matching.** Every finding carries method, bidders, compared evidence, similarity, review_status | ✅ working, wired into graph + ledger |
| `mvp/satyabid/priceforensics.py` | Price forensics: CV/DIFFP/RD/skew/Benford/PRICE_CLUSTER screens | ✅ working |
| `mvp/satyabid/docforensics.py` | Document forensics: shared-boilerplate sentences, identical-typo markers, metadata-triple match | ✅ working |
| `mvp/satyabid/tenderintegrity.py` | Tender integrity: SHA-256 tender seal, corrigendum diff, two-cover price-hint scan | ✅ working |
| `mvp/satyabid/evidence.py` | PASS/FAIL/REVIEW verdicts as "speaking orders" | ✅ working |
| `mvp/satyabid/audit.py` | SHA-256 hash-chained tamper-evident ledger | ✅ working (20 entries on demo data) |
| `mvp/gen_data.py` | Synthetic demo dataset: 1 tender + 5 bidders, planted frauds (incl. paraphrased draft C/D, shared bank/IP/DSC, bad PAN, E price hint, corrigendum relaxations) | ✅ working |
| `mvp/run_mvp.py` | Headless CLI pipeline | ✅ working |
| `mvp/diagnose.py` | 13-stage backend diagnostic, all PASS | ✅ working |
| `mvp/tests/test_mvp.py` | Ground-truth tests, all PASS | ✅ working |
| `mvp/app.py` | Old Streamlit UI | ⚠️ **replace** — this is the "just the UI" the human rejected |

Verify before you build: `cd mvp && pip install -r requirements.txt &&
python diagnose.py` — all 13 stages must PASS. If any fail, fix the engine
first; do not build UI on a broken backend. (`scikit-learn>=1.3` is required
for the ML stage — it is in `requirements.txt`.)

**Ground truth of the demo dataset** (your UI must reproduce exactly this):
- A Apex Computing Solutions → PASS, L1 (₹4.32 Cr), clean
- B Brightline Technologies → FAIL (R1 turnover shortfall, R2 claim-vs-cert
  mismatch 118%, R3 invalid CA number `FCA-0987X4`, R8 malformed PAN)
- C Crestline Systems → REVIEW, HIGH collusion
- D Deltaforce IT Services → FAIL (R5 missing GFR 144(xi) declaration),
  HIGH collusion
- C+D form a **suspected cartel ring**: ring score **26.32 HIGH**, **10 signal
  types** — 2 shared directors, same phone, same address, shared bank/IP/DSC,
  prices within **0.68%**, same PDF author, **ML paraphrase find (TF-IDF
  cosine 0.62)** on their capability statements (reworded common draft that
  exact matching misses)
- E Everest Digital → FAIL (R4 Class-I claim at 28% local content,
  R6 past performance ₹40L < ₹75L required, price hint hidden in technical bid)
- Tender corrigendum detected: turnover ₹1.5Cr → ₹1Cr, EMD ₹2L → ₹1L
- Audit ledger: 20 entries, chain intact
- **Honesty note:** the fuzzy-identity matcher is implemented and unit-tested
  (`Vikram Shah` vs `V. Shah` ≈ 0.85), but the current synthetic data uses the
  exact name in both C and D, so the pipeline reports **0 fuzzy findings**.
  Present fuzzy matching as a tested capability, never as a demo finding.

## 3. What to build (priority order — demo ROI, not screen number)

Build screens in this exact order. If time runs out, whatever is built is
exactly what the 90-second video needs:

1. **S3 Command dashboard** — verdict table, KPIs, L1 banner, ring banner
2. **S5 Evidence viewer** — split-pane clause vs document, the trust screen
3. **S6 Collusion graph** — the C+D ring, the wow factor
4. **S7 Audit trail** — one-click chain verification
5. **S4 Bidder dossier** — rule checklist + speaking order
6. **S1/S2 Upload + pipeline stepper** — demo-dataset button is the judge
   path; full upload robustness is lowest priority

Then follow `docs/ROADMAP.md` Phase 2+ (PDF report export, demo video,
submission assets).

### Fallback rule (Track B)
`mvp/app.py` (Streamlit) + `run_mvp.py` (CLI) are a **working end-to-end
fallback** and must be kept runnable at all times — never break them while
building the new UI. A polished working demo beats a half-built beautiful one:
if the new UI is not demo-recordable, stop new-UI work and reskin the
Streamlit app per `docs/FALLBACK.md` instead.

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

- [ ] Screens built in demo order (S3 → S5 → S6 → S7 → S4 → S1/S2),
      each per `docs/UI_UX_SPEC.md`
- [ ] Demo dataset loads in ≤ 3 clicks to the verdict dashboard
- [ ] Demo-choreography acceptance: S1 to S7 in ≤ 5 clicks, zero dead ends
      (`docs/UI_UX_SPEC.md §10`)
- [ ] `diagnose.py` still all-PASS (engine untouched or improved)
- [ ] Every verdict pill links to its evidence view
- [ ] Collusion graph renders the C+D ring with all 10 signal types explorable
      (incl. the ML paraphrase edge at 0.62)
- [ ] Audit ledger verifies with one click
- [ ] Works from a fresh `pip install -r requirements.txt` with no manual steps
- [ ] `mvp/app.py` fallback still runs (Track B intact)

## 6. Agent operating constraints

- Follow `docs/UI_UX_SPEC.md` exactly — do not redesign, restyle, or rename
  R1–R8 / PASS/FAIL/REVIEW. Ask the human before any deviation.
- Do not gold-plate. Demo choreography (§10 of the spec) is the acceptance
  test, not visual novelty.
- After each screen: re-run `diagnose.py` (engine must stay green) and show
  the human the screen before continuing.
- If stuck on one screen for more than ~30 minutes, stop and report instead
  of working around it.
- Never break `mvp/app.py` or `run_mvp.py` — they are the Track B fallback.

## 7. First task

Read `docs/UI_UX_SPEC.md` and `docs/ARCHITECTURE.md`, verify the backend
(`cd mvp && python diagnose.py` → 13/13 PASS), then present a build plan for
S3 first (component breakdown only) and wait for approval before writing
code.
