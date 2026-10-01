# AGENTS.md — SatyaBid repo conventions

## Entry point
`ANTIGRAVITY.md` is the bootstrap. Read order: ANTIGRAVITY.md →
docs/UI_UX_SPEC.md → docs/ARCHITECTURE.md → docs/ROADMAP.md.

## Before writing code
Run `cd mvp && python diagnose.py`. 13/13 PASS required. If red, fix engine
first.

## Stable APIs (do not change without updating tests + docs)
- Rule ids R1–R8 (R8 = PAN/GSTIN format validity), verdict vocabulary PASS/FAIL/REVIEW
- Blueprint requirement ids (`turnover_min`, `emd`, `past_performance_min`,
  `local_content_min`, `requires_144xi`, `delivery_days`, `bid_number`,
  `estimated_value`)
- Ledger entry format (see `docs/ARCHITECTURE.md §2`)
- UI copy specified verbatim in `docs/UI_UX_SPEC.md`

## Code rules
- Engine stays deterministic and offline; UI never reimplements parsing.
- New external services plug into existing seams (OCR adapter, registry
  adapters) — never inline branches in the pipeline.
- Every user-facing claim needs a visible evidence path.
- Simulated checks are labeled "Simulated" in the UI. No fake metrics, ever.
- Money: Indian grouping (`₹4,32,00,000`), tabular numerals. Time: IST.

## Git
- `main` is always green (diagnose + tests pass).
- Branch per unit of work: `ui/s3-dashboard`, `fix/r5-evidence`, …
- Commits: `ui(s3): verdict table with status pills`.

## Definition of done
`ANTIGRAVITY.md §5`. Nothing merges until every box is checked.
