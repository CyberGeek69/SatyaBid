# SatyaBid — Workflow

## Setup (fresh machine)
```bash
git clone <repo-url> && cd satyabid
cd mvp && python -m venv .venv
.venv/bin/pip install -r requirements.txt   # Windows: .venv\Scripts\pip install -r requirements.txt
```

## The three commands that matter
| Command | Does | When |
|---|---|---|
| `.venv/bin/python diagnose.py` | 8-stage backend health check | **before any UI work, after any engine change** |
| `.venv/bin/python tests/test_mvp.py` | ground-truth: planted fraud caught? | after engine changes |
| `.venv/bin/python run_mvp.py` | headless pipeline → `mvp/outputs/` | sanity / CI |

If `diagnose.py` is not 8/8 PASS, stop and fix the engine. Never build UI
on a red backend.

## Regenerating the demo dataset
```bash
.venv/bin/python gen_data.py   # rewrites mvp/data/*.pdf (deterministic)
```
The dataset is committed (`mvp/data/`), so a fresh clone works with zero
steps. Regenerate only if you change the planted fraud scenarios — and then
update the ground-truth table in `ANTIGRAVITY.md §2` and the tests.

## Running the UI (Phase 1+)
Run the local web server (serves S1–S7 and local APIs with zero extra dependencies):
```bash
python mvp/serve.py
```
Open `http://localhost:8000` in the browser.

Note: The early Streamlit prototype has been retired and renamed to `mvp/streamlit_legacy.py`. Do not iterate on it. See `docs/FALLBACK.md` for full fallback runbook.

## Git workflow
- `main` always runs: diagnose 8/8 PASS + tests PASS.
- Branch per screen: `ui/s3-dashboard`, `ui/s6-graph`, …
- Commit messages: `ui(s3): verdict table with status pills`.
- Never commit: `.venv/`, `__pycache__/`, `*.pyc`, OS junk (see `.gitignore`).

## Demo-day checklist
- [ ] Fresh-clone install works (test on a second machine if possible)
- [ ] Demo dataset runs end-to-end in < 60s
- [ ] Projector check: 1366px, pills readable from 3m
- [ ] `diagnose.py` 8/8 PASS, printed as backup slide if asked
- [ ] Audit "Verify chain" clicked live at least once in rehearsal
- [ ] 90-second video rendered, QR codes live on deck slide 6
