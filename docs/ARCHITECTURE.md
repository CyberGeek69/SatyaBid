# SatyaBid — Architecture

## 1. System overview

```
                    ┌──────────────────────────────┐
                    │        PRESENTATION          │
                    │  6 screens (§ UI_UX_SPEC)    │
                    │  S1 upload → S7 audit       │
                    └──────────────┬───────────────┘
                                   │ calls (no re-parsing)
                    ┌──────────────▼───────────────┐
                    │         ENGINE (mvp/)        │
                    │  deterministic, offline      │
                    └──────────────┬───────────────┘
                                   │
        ┌──────────────┬───────────┼───────────┬──────────────┐
        ▼              ▼           ▼           ▼              ▼
   ┌─────────┐  ┌───────────┐ ┌────────┐ ┌───────────┐ ┌───────────┐
   │ ingest  │  │ blueprint │ │ checks │ │ collusion │ │   audit   │
   │ PDF→text│  │ tender→   │ │ R1–R7  │ │ networkx  │ │ SHA-256   │
   │ +OCR    │  │ require-  │ │ per    │ │ graph,    │ │ hash      │
   │ seam    │  │ ments     │ │ bidder │ │ rings     │ │ chain     │
   └─────────┘  └───────────┘ └────────┘ └───────────┘ └───────────┘
        │              │           │           │              │
        └──────────────┴───────────┴───────────┴──────────────┘
                                   ▼
                         ┌──────────────────┐
                         │ evidence.py      │
                         │ verdict assembly │
                         │ (speaking orders)│
                         └──────────────────┘
```

**Pipeline order** (`run_mvp.py::run()`): ingest tender → blueprint →
ingest bidders → collusion analysis → per-bidder checks → verdicts →
L1 ranking (PASS only) → ledger seal. Every stage appends to the audit
ledger.

## 2. Module contracts

### ingest.py
- `extract_pages(pdf_path, ocr_adapter=None) -> [(page_no, text, source)]`.
  Pages with < 50 chars route to the OCR adapter.
- `extract_metadata(pdf_path) -> {author, creator, producer, creationDate}`.
- `OCRAdapter.extract(pixmap_bytes) -> str`. **Seam:** production target is
  PaddleOCR; `TesseractAdapter` is the bundled fallback. Swap by passing a
  different adapter — never branch inside the pipeline.

### blueprint.py
- `extract_blueprint(pages) -> {req_id: {value, evidence, page}}`.
- Requirement ids (stable — UI/tests depend on them): `turnover_min`,
  `emd`, `past_performance_min`, `local_content_min`, `requires_144xi`,
  `delivery_days`, `bid_number`, `estimated_value`.
- All multi-word match patterns use `\s+` (PDF line-wrap hardening).

### checks.py
- `parse_bidder(bidder_id, name, pages, metadata) -> BidderFacts`
  (turnover claimed/certified, CA number, local content %, 144(xi) flag,
  past performance, price, directors, phone, address, EMD flag).
- `run_checks(facts, blueprint) -> [CheckResult]` — exactly 7, ids R1–R7:
  R1 turnover floor · R2 claim-vs-certificate consistency ·
  R3 CA membership format (simulated registry) · R4 Make-in-India
  local-content vs Class claim · R5 GFR 144(xi) declaration ·
  R6 past performance · R7 EMD.
- `CheckResult`: rule, status (PASS/FAIL/REVIEW), rationale, clause_evidence
  + clause_page, doc_evidence + doc_page. **A check without evidence is a
  bug** (except R2's clause side, which is intra-document by nature).

### collusion.py
- `analyse_collusion([BidderFacts]) -> {graph, edges, rings, flags}`.
- Edge weights: shared director 3.0 each, shared phone 2.5, shared address
  2.0, price proximity ≤2% up to 2.0, shared PDF author 1.5.
- Risk: ≥5 HIGH, ≥2.5 MEDIUM, >0 LOW. Rings = connected components over
  HIGH edges. Tune weights here only — never in the UI.

### evidence.py
- `build_verdict(facts, checks, collusion_flag) -> verdict dict`:
  any FAIL → FAIL; else HIGH/MEDIUM collusion or REVIEW checks → REVIEW;
  else PASS. Includes `speaking_order` (plain-language paragraph) and the
  evidence list.

### audit.py
- `AuditLedger.append(event, payload)`, `.verify() -> (ok, msg)`.
  Entry = seq, ISO-8601 UTC timestamp, event, payload, payload_hash,
  prev_hash, entry_hash (SHA-256). UI displays times in IST.

## 3. Data flow for one scrutiny run

1. PDFs in → `extract_pages`/`extract_metadata`.
2. Tender pages → `extract_blueprint` → requirements dict.
3. Each bid → `parse_bidder` → `BidderFacts`.
4. All facts → `analyse_collusion` → edges/rings/flags.
5. Each fact × requirements → `run_checks` → `build_verdict`.
6. PASS verdicts with prices → L1 = min price (**two-cover isolation**).
7. Every step appended to `AuditLedger`; UI offers one-click `verify()`.

## 4. Extension seams (Phase 2+, do not build in Phase 1)

| Seam | Current | Target |
|---|---|---|
| OCR backend | TesseractAdapter fallback | PaddleOCR + LayoutLM |
| Registries | R3 format check (labeled *simulated*) | Adapter per registry: GSTN / Udyam / MCA / DPIIT |
| Clause NLP | Regex blueprinting | Local quantized LLM paraphrase adapter (Ollama) — deterministic rules stay the verdict authority |
| Report export | — | PDF summary generator from verdicts + evidence |
| Persistence | In-memory per run | SQLite run history (optional) |

Rules for extensions: new adapters plug into existing seams; the 7 rule ids,
verdict vocabulary, and ledger format are stable APIs — changing them breaks
tests, demo script, and deck claims.
