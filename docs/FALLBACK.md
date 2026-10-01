# SatyaBid — Operational Fallback Runbook

This document defines execution tiers and disaster-recovery runbooks for demo-day evaluation, network outages, and local inspection.

---

## 1. Execution Tiers

| Tier | Component | Command | Purpose |
|---|---|---|---|
| **Tier 1 (Production)** | Vercel Deployment | Live Production URL | Primary judge evaluation interface (FastAPI + S1–S7 Web UI) |
| **Tier 2 (Local Web)** | Python Web Server | `python mvp/serve.py` | Local zero-dependency web server (`http://127.0.0.1:8000`) |
| **Tier 3 (Headless CLI)** | Python MVP Engine | `python mvp/run_mvp.py --verify` | Direct terminal execution; generates `outputs/analysis.json` & verifies SHA-256 audit ledger |
| **Tier 4 (Diagnostics)** | Backend Health Check | `cd mvp && python diagnose.py` | 8-stage deterministic verification suite |
| **Tier 5 (Archival Prototype)** | Legacy Streamlit App | `streamlit run mvp/app.py` | Retired Phase 0 prototype (preserved for reference only) |

---

## 2. Fallback Procedures

### Scenario A: Cloud / Network Outage during Evaluation
If internet connectivity is interrupted:
1. Launch local web server:
   ```bash
   cd mvp
   python serve.py
   ```
2. Navigate to `http://127.0.0.1:8000/`. All S1–S7 screens operate 100% offline and deterministic with the bundled dataset.

### Scenario B: Browser / Frontend Asset Failure
If web browser rendering fails:
1. Run headless engine from terminal:
   ```bash
   python mvp/run_mvp.py --verify
   ```
2. Inspect deterministic outcomes in `mvp/outputs/analysis.json` and cryptographic proof in `mvp/outputs/audit_log.json`.

### Scenario C: Legacy Reference
`mvp/app.py` was renamed to `mvp/app.py` to prevent confusion. It is an early throwaway prototype and is not part of the active Phase 1 release. Do not build or test features against it.
