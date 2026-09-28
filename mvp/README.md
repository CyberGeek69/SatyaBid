# SatyaBid MVP — Intelligent Bid Scrutiny & Cross-Bidder Cartel Detection

Working prototype for **SIH26100** (CPCL tender/bid compliance platform).
Deterministic, runs fully offline on a commodity laptop.

## What it does

1. **Ingests** a tender PDF + N bidder PDFs (`satyabid/ingest.py` — PyMuPDF;
   near-empty pages route to an OCR adapter seam where PaddleOCR plugs in).
2. **Blueprints the tender** into structured requirements — turnover floor, EMD,
   past-performance threshold, Make-in-India Class-I local-content %, mandatory
   GFR 144(xi) declaration (`satyabid/blueprint.py`). Every requirement keeps
   its clause text + page as evidence.
3. **Runs 7 compliance rules per bidder** — turnover floor, claim-vs-certificate
   consistency (forgery signal), CA membership format (simulated registry),
   local-content vs Class-I claim, 144(xi) declaration, past performance, EMD
   (`satyabid/checks.py`). Each check cites the tender clause *and* the
   bidder's document excerpt.
4. **Maps the collusion graph** (`satyabid/collusion.py`, networkx): shared
   directors, phones, addresses, cover-bidding price proximity, identical PDF
   author metadata → weighted edges, HIGH/MEDIUM/LOW risk, suspected rings.
5. **Issues evidence-linked verdicts** (PASS / FAIL / REVIEW) written as
   speaking orders, with two-cover isolation — only PASS bids are ranked for L1
   (`satyabid/evidence.py`).
6. **Hash-chains every event** into a tamper-evident audit ledger (SHA-256),
   verifiable with one click (`satyabid/audit.py`).

## Quick start

```bash
cd mvp
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# (re)generate the synthetic demo dataset: 1 tender + 5 bidders
.venv/bin/python gen_data.py

# headless pipeline — prints the scrutiny report, writes outputs/
.venv/bin/python run_mvp.py

# ground-truth tests (planted fraud must be caught, clean bid passed)
.venv/bin/python tests/test_mvp.py

# interactive demo UI
.venv/bin/streamlit run app.py
```

## Demo dataset ground truth

| Bid | Bidder | Planted issue | Expected |
|-----|--------|---------------|----------|
| A | Apex Computing Solutions | none — clean | **PASS**, L1 |
| B | Brightline Technologies | claims ₹2.4 Cr turnover, CA cert shows ₹1.1 Cr; bad CA no. `FCA-0987X4` | **FAIL** (R1/R2/R3) |
| C | Crestline Systems | 2 shared directors + phone + address + 0.7% price band + same PDF author as D | **REVIEW**, HIGH collusion |
| D | Deltaforce IT Services | same as C, plus missing GFR 144(xi) declaration | **FAIL** (R5), HIGH collusion |
| E | Everest Digital | claims Class-I at 28% local content; past performance ₹40L < ₹75L | **FAIL** (R4/R6) |

Suspected cartel ring: **C + D**.

## Honest scope notes (for judges)

- Registries (GSTN/Udyam/MCA/DPIIT) are **simulated format checks** in the MVP;
  the architecture exposes them as adapters for live APIs post-hackathon.
- OCR path is an adapter seam (Tesseract fallback bundled); production target
  is PaddleOCR + LayoutLM as per the deck.
- The NLP layer in the deck (local quantized LLM via Ollama) is intentionally
  **not** in the MVP: deterministic rules are auditable and demo-safe; the LLM
  is scoped as an optional clause-paraphrase adapter.
