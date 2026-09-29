# SatyaBid — Roadmap

Deadline: **SIH 2026 national submission, 30 Sep 2026.** Work backwards from
the demo video.

## Phase 0 — Engine MVP ✅ DONE
Deterministic pipeline, synthetic dataset, ground-truth tests, CLI,
diagnostic. Verified: `cd mvp && python diagnose.py` → 8/8 PASS.

## Phase 1 — Judge-facing UI (CURRENT TASK)
Rebuild the UI exactly per `docs/UI_UX_SPEC.md`, wired to the existing
engine. Old `mvp/streamlit_legacy.py` (Streamlit) is retired — do not iterate on it.

Order: S1 upload → S2 stepper → S3 dashboard → S4 dossier → S5 evidence →
S6 graph → S7 audit → shared components extracted as you go.

Exit criteria: `ANTIGRAVITY.md §5` Definition of Done, all checked.

## Phase 2 — Demo & submission assets
- [ ] PDF report export (verdict table + speaking orders + evidence refs)
      → un-disables the "Export report" button from the spec
- [ ] 90-second demo video, shot against the UI following
      `docs/DEMO_SCRIPT.md`
- [ ] GitHub repo public; README badges (tests passing)
- [ ] QR codes: repo + demo video → replace placeholders on deck slide 6
- [ ] Team ID + Team Name into deck slide 1

## Phase 3 — Judge hardening (only if time remains)
- [ ] PaddleOCR adapter behind the OCR seam (scanned-PDF path)
- [ ] Upload-your-own-PDFs robustness: malformed files → clean S1 errors
- [ ] Judge Q&A rehearsal against `docs/JUDGE_QA.md`

## Phase 4 — Post-SIH (do NOT build now)
Live registry adapters, LLM clause paraphrase, multi-tender history,
role-based access. Listed here so nobody builds them during the hackathon.

## Non-goals (never)
Invented accuracy metrics · dark "AI" redesign · renaming R1–R7 or
PASS/FAIL/REVIEW · mock data in the demo path · anything requiring
credentials the human hasn't provided.
