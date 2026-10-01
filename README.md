# SatyaBid — Intelligent Bid Scrutiny & Cross-Bidder Cartel Detection

SIH 2026 · Problem Statement SIH26100 · Software category

SatyaBid scrutinises public-procurement bids the way an evaluation committee
should: every tender becomes a structured blueprint, every bidder is checked
against it rule by rule, relationships *between* bidders are mapped for cartel
signals, and every verdict carries its evidence — sealed in a tamper-evident
ledger.

## What it does

1. **Ingests** tender + bidder PDFs (OCR seam for scanned pages)
2. **Blueprints the tender** — turnover floor, EMD, past performance,
   Make-in-India local-content %, mandatory GFR 144(xi) declaration
3. **Runs 8 compliance rules per bidder (R1–R8)**, each citing the tender clause
   *and* the bidder's document excerpt
4. **Maps the collusion graph** — shared directors, phones, addresses,
   cover-bidding price proximity, shared document metadata,
   **ML paraphrase detection (TF-IDF)** → suspected rings
5. **Issues verdicts** (PASS / FAIL / REVIEW) as speaking orders, with
   two-cover isolation: only responsive bids are ranked for L1
6. **Seals everything** in a SHA-256 hash-chained audit ledger

Deterministic and fully offline. No invented metrics: registries run as
labeled simulated checks until live adapters land.

## Quickstart

```bash
cd mvp
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python diagnose.py        # 13-stage backend health check (incl. ML forensics)
.venv/bin/python run_mvp.py         # headless pipeline → mvp/outputs/
.venv/bin/python tests/test_mvp.py  # ground-truth tests
```

## Repo map

| Path | What |
|---|---|
| `ANTIGRAVITY.md` | **AI agents start here** — mission, state, build order |
| `AGENTS.md` | Agent working conventions |
| `docs/UI_UX_SPEC.md` | Binding interface specification (Phase 1) |
| `docs/ARCHITECTURE.md` | Engine design, module contracts, extension seams |
| `docs/ROADMAP.md` | Phased plan to the SIH deadline |
| `docs/WORKFLOW.md` | Setup, commands, git, demo-day checklist |
| `docs/DEMO_SCRIPT.md` | 90-second demo video script |
| `docs/FALLBACK.md` | Track B: Streamlit reskin plan if the new UI stalls |
| `mvp/` | Working engine + synthetic dataset + CLI + tests |

## Status

- [x] Phase 0 — deterministic engine, tested on synthetic GeM tender
- [ ] Phase 1 — judge-facing UI per spec
- [ ] Phase 2 — demo video, report export, submission assets
