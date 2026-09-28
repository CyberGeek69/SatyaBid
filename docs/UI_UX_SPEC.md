# SatyaBid — UI/UX Specification v1.0

> This spec is binding for Phase 1. Implement screens in S1→S7 order.
> Copy, layout, and status language are specified exactly — do not paraphrase
> user-facing strings unless fixing grammar.

## 1. Design philosophy

SatyaBid is used by **tender evaluation officers and vigilance staff** — busy,
non-technical government users — and demoed to **SIH judges on a projector**.
The design must communicate *institutional trust*, not startup flash.

**Principles:**
1. **Evidence first.** Every claim on screen must be one click from its proof.
   A verdict without visible evidence is a design bug.
2. **Calm authority.** Restrained color, generous whitespace, no gradients-for-
   decoration, no emoji in the product UI (status dots/pills only).
3. **Progressive disclosure.** Dashboard → bidder → rule → evidence. Four
   levels, never more.
4. **Demo-choreographed.** The 90-second video path (upload → dashboard →
   evidence → ring → audit) must be completable in ≤ 5 clicks with zero
   dead ends. See §10.
5. **Honest states.** Simulated checks are labeled "Simulated". Loading
   indicators map to real pipeline stages. Never show fake progress.

## 2. Design system

### 2.1 Color
| Token | Hex | Use |
|---|---|---|
| `--navy-900` | `#0B1F3A` | Top bar, primary buttons, headings |
| `--navy-700` | `#14325C` | Sidebar, hover states |
| `--gold-500` | `#C9A227` | Brand accent: logo mark, active nav indicator, L1 banner border |
| `--bg` | `#F4F6FA` | App background |
| `--surface` | `#FFFFFF` | Cards, panels |
| `--ink` | `#0F172A` | Primary text |
| `--ink-2` | `#475569` | Secondary text |
| `--line` | `#E2E8F0` | Borders, dividers |
| `--pass` | `#15803D` | PASS pill, success |
| `--pass-bg` | `#DCFCE7` | PASS pill background |
| `--fail` | `#B91C1C` | FAIL pill, danger |
| `--fail-bg` | `#FEE2E2` | FAIL pill background |
| `--review` | `#B45309` | REVIEW pill, warnings |
| `--review-bg` | `#FEF3C7` | REVIEW pill background |
| `--risk-high` | `#B91C1C` | Collusion HIGH |
| `--risk-med` | `#C2410C` | Collusion MEDIUM |
| `--risk-low` | `#A16207` | Collusion LOW |
| `--link` | `#1D4ED8` | Evidence links, clause references |

Status is **never color alone**: every pill pairs color with an explicit word
(PASS / FAIL / REVIEW) and, where space allows, an icon (✓ / ✕ / !).

### 2.2 Typography
- Font: **Inter** (Google Fonts), fallback system-ui. Tabular numerals for
  all money figures (`font-variant-numeric: tabular-nums`).
- H1 screen title: 24px / 700. H2 section: 16px / 700. Body: 14px / 400,
  line-height 1.55. Caption/meta: 12px / 400, `--ink-2`.
- Money: always `₹4,32,00,000` (Indian digit grouping). Never `$`, never
  `Rs.` in the UI (engine internals may keep `Rs.`).

### 2.3 Shape & elevation
- Radius: 10px cards, 999px pills, 8px buttons/inputs.
- Elevation: cards `0 1px 2px rgba(16,24,40,.06)`; overlays
  `0 8px 24px rgba(16,24,40,.12)`. No heavy shadows.
- Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 / 48.

### 2.4 Status pills (component)
Pill = 12px uppercase 700 letterspaced label + dot, colored per §2.1.
Sizes: `sm` (table cells), `md` (headers). Verdict pills are `md` minimum —
they are the most-scanned element on screen.

## 3. Information architecture

```
Top bar (always visible): [logo SatyaBid] [Bid context: GEM/2026/B/6123457 ▾]
                          [Search bidders…] [Export report] [avatar: Officer]

Sidebar nav:  ① New scrutiny   ② Dashboard   ③ Bidders   ④ Collusion graph
              ⑤ Audit trail

Main: screen content (S1–S7 below)
```

Sidebar items show a small count badge where meaningful (Bidders: 5,
Collusion: 1 ring alert). Active item: `--navy-700` background + 3px
`--gold-500` left indicator.

## 4. Screens

### S1 — New scrutiny (landing)
Purpose: start an analysis. Two equal cards side by side.

```
┌─────────────────────────────┐  ┌─────────────────────────────┐
│  📄  Upload tender package  │  │  ⚡  Run demo dataset       │
│                             │  │                             │
│  [ tender.pdf ......... ]   │  │  Pre-loaded GeM bid with    │
│  [ bidder PDFs .... add ]   │  │  5 bidders & planted fraud  │
│                             │  │  signals. One click.        │
│  [  Start scrutiny  ]       │  │  [  Run demo scrutiny  ]   │
└─────────────────────────────┘  └─────────────────────────────┘
        "Supported: digital PDFs. Scanned pages route to OCR."
```
- Upload card: drag-drop zones with file chips (name + pages + ✓ parsed).
  Start disabled until 1 tender + ≥1 bid present.
- Demo card: single primary button. **This is the judge path.**
- Footer note: *"Registries (GSTN/Udyam/MCA) run as simulated checks in this
  build — labeled wherever they appear."*

### S2 — Analysis progress (transient)
Full-screen takeover, auto-advances to S3. Vertical stepper, each step ticks
as the real engine stage completes:

1. Ingesting documents (n files, p pages)
2. Blueprinting tender → "8 requirements extracted"
3. Running 7 compliance rules × 5 bidders
4. Mapping cross-bidder relationships
5. Issuing verdicts & sealing audit ledger

Microcopy under stepper: *"Deterministic engine — every step is auditable."*
No fake timing: steps complete when the engine returns.

### S3 — Command dashboard (home after analysis)
```
┌──────────────────────────────────────────────────────────┐
│  Bid GEM/2026/B/6123457 · 500 Desktop Computers · CPCL    │
│  Analysed just now · 6 PDFs · 14 ledger entries           │
├──────────┬──────────┬──────────┬─────────────────────────┤
│ 5        │ 1        │ 3        │ 1                       │
│ BIDDERS  │RESPONSIVE│ REJECTED │ SUSPECTED RING          │
│ analysed │   ✓      │    ✕     │  C + D  [Investigate →] │
├──────────┴──────────┴──────────┴─────────────────────────┤
│  🏆 L1 — Apex Computing Solutions · ₹4,32,00,000         │
│  Lowest technically responsive bid (two-cover isolation) │
├──────────────────────────────────────────────────────────┤
│ Bidder              │ Verdict  │ Price        │ Collusion  │
│ A Apex Computing…   │ ✓ PASS  │ ₹4,32,00,000 │ —          │
│ B Brightline Tech…  │ ✕ FAIL  │ ₹4,55,00,000 │ LOW        │
│ C Crestline Systems │ ! REVIEW│ ₹4,41,00,000 │ HIGH       │
│ D Deltaforce IT…    │ ✕ FAIL  │ ₹4,44,00,000 │ HIGH       │
│ E Everest Digital   │ ✕ FAIL  │ ₹4,61,00,000 │ LOW        │
└──────────────────────────────────────────────────────────┘
        (rows click through to S4; ring banner → S6)
```
- KPI cards: big numeral (32px/700) + 11px uppercase label.
- Ring banner (only if rings exist): `--fail-bg` background, red left border,
  text: "Suspected cartel ring detected: C + D — 5 shared signals.
  [Investigate →]".
- L1 banner: white card, `--gold-500` left border, trophy glyph (SVG, not emoji).
- Table: row hover, verdict pill `sm`, collusion shown as pill only when
  ≥ LOW else em-dash. Price right-aligned, tabular numerals.
- "Export report" (top bar) downloads a PDF summary — Phase 2, show as
  disabled with tooltip "Coming in Phase 2" if not built.

### S4 — Bidder dossier
Header block:
```
[← All bidders]   C — Crestline Systems                    [! REVIEW]
Mumbai · 3 directors · Quote ₹4,41,00,000 · Collusion: HIGH
```
Body: two columns (2fr / 1fr).
- **Left — Rule checks** (the core): 7 rows, each an expandable:
  ```
  ┌─────────────────────────────────────────────────┐
  │ ✕ R2 · Turnover claim vs certificate   [View evidence →] │
  │   Covering letter claims ₹2.40 Cr; CA certificate       │
  │   averages ₹1.10 Cr (deviation 118.2%).                 │
  └─────────────────────────────────────────────────┘
  ```
  Row shows: status icon, rule id + name, one-line rationale, evidence link.
  Expanding reveals full rationale (never a modal — inline).
- **Right — Speaking order** panel: the verdict paragraph in a bordered
  quote-style block, heading "Speaking order". Below it: "Bidder facts"
  (directors, phone, address, CA, local content %, price) as definition list.
- "View evidence →" jumps to S5 with rule pre-selected.

### S5 — Evidence viewer
The trust screen. Split pane, bidder+rule selector on top:
```
 Bidder [C — Crestline Systems ▾]   Rule [R2 · Turnover claim… ▾]   [✕ FAIL]
┌──────────────────────┬──────────────────────┐
│ 📜 TENDER CLAUSE     │ 📄 BIDDER DOCUMENT   │
│ (tender p.1)         │ (bid p.2)            │
│                      │                      │
│ "…minimum average    │ "…average annual     │
│  annual turnover…    │  turnover… is        │
│  shall be            │  ₹2,40,00,000/-…"    │
│  ₹1,50,00,000/-…"   │                      │
│  ─────────────       │  ─────────────       │
│  CA certificate      │ CA certificate rows: │
│  rows avg ₹1.10 Cr   │ 1.00 / 1.20 / 1.10 Cr │
└──────────────────────┴──────────────────────┘
        Engine verdict on this rule: ✕ FAIL
```
- Key figures highlighted (`.hl` class, `--review-bg` background).
- Page citations as `--link` chips: "tender p.1", "bid p.2".
- Intra-document rules (R2: claim vs certificate) show "Bidder document A"
  vs "Bidder document B" with headers adjusted accordingly.
- Keyboard: ←/→ moves between rules.

### S6 — Collusion graph
```
┌────────────────────────────┬───────────────────────────────┐
│                            │  🚨 Suspected ring: C + D      │
│      (C)━━━━━━(D)           │  5 signals · risk score 13.32  │
│    HIGH edge, thick red     │                               │
│                            │  Pairwise signals             │
│  (A)   (B)––(E)            │  ┌───────────────────────────┐ │
│        thin amber, LOW      │  │ C ↔ D · HIGH (13.32)  [>] │ │
│                            │  │ B ↔ E · LOW (0.70)    [>] │ │
│  Legend: — HIGH — MEDIUM    │  └───────────────────────────┘ │
│          — LOW              │  Expanding a pair lists each   │
└────────────────────────────┴─signal with weight & detail ───┘
```
- Canvas/SVG network: node = bidder pill (id + short name + verdict dot).
  Edge width ∝ score, color = risk. HIGH edges pulse subtly (CSS animation,
  pauses with `prefers-reduced-motion`).
- Clicking an edge/node selects the pair in the side panel; signal rows show
  `type`, weight, and plain-English detail
  (e.g. "Common directors: Vikram Shah, Anita Desai").
- Ring alert card at top of panel when rings exist, red-tinted.
- Empty state: "No cross-bidder relationships above the LOW threshold."

### S7 — Audit trail
- Header: "Tamper-evident ledger" + [Verify chain] primary button +
  result inline ("✓ 14 entries verified — chain intact", green).
- Table: Seq | Time (IST) | Event | Details (human summary) | Hash (first
  12 chars, mono, click-to-copy full).
- Event names are humanised: `verdict_issued` → "Verdict issued",
  `collusion_analysis` → "Collusion analysis".
- Footer note: *"Each entry commits to the previous entry's SHA-256 hash.
  Altering any record breaks the chain."*
- Export JSON button (downloads `audit_log.json`).

## 5. Component inventory (build once, reuse)
1. `StatusPill` (verdict/risk) 2. `KpiCard` 3. `BidderRow`
4. `RuleRow` (expandable) 5. `EvidencePane` 6. `GraphCanvas`
7. `SignalRow` 8. `LedgerTable` 9. `Stepper` 10. `EmptyState`
11. `PageHeader` (title + context + actions)

## 6. Interaction & microcopy rules
- Buttons: primary = `--navy-900` fill, white text; never gradient.
- Destructive/irreversible actions: none in the product (analysis is
  re-runnable) — no confirm dialogs needed.
- Numbers: Indian grouping everywhere; prefix ₹.
- Time: IST, format `29 Sep 2026, 14:32 IST`.
- Copy tone: plain, official, no exclamation marks, no marketing adjectives.
- Every async action has three states: idle → working (label changes,
  e.g. "Verifying…") → done (inline result, never a toast alone).

## 7. States
- **Loading:** S2 stepper (real stages); inline skeletons for table rows
  elsewhere. No spinners without labels.
- **Empty:** S6 no-relationships; S1 pre-upload. Illustration: simple
  line-icon, 12px `--ink-2` caption, one action button.
- **Error:** upload of non-PDF → inline red note under dropzone
  ("Only PDF files are supported."); engine exception → full-screen error
  with "Download diagnostic log" and "Start over".

## 8. Responsive
Desktop-first (1366px+ is the demo target). Down to 1024px: sidebar collapses
to icons. Below 1024: single column, evidence panes stack, graph becomes
horizontally scrollable. Mobile is out of scope for Phase 1.

## 9. Accessibility (minimum bar)
- All status conveyed by text, not color alone (§2.1).
- Focus-visible outlines on every interactive element.
- Graph has a text alternative: the pairwise signal list (already in S6).
- Contrast: body text ≥ 4.5:1.

## 10. Demo choreography (90-second video)
The UI must make this exact sequence effortless:
| Time | Action | Screen |
|---|---|---|
| 0–12s | Click "Run demo scrutiny", watch stepper | S1→S2 |
| 12–35s | Dashboard: KPIs, ring banner, L1, verdict table | S3 |
| 35–55s | Open Bidder B → expand R2 → "View evidence" | S4→S5 |
| 55–75s | Collusion graph: ring alert, expand C↔D signals | S6 |
| 75–90s | Audit trail: Verify chain ✓, closing line | S7 |

Closing line (voiceover): *"SatyaBid — every verdict carries its evidence."*

## 11. Anti-patterns (do not)
- No dark-mode-inverted "AI" aesthetic, no purple/blue gradients.
- No emoji in product UI (this spec's emoji are shorthand only).
- No fake charts or invented statistics anywhere.
- No "AI confidence 98.2%"-style pseudo-precision. The engine is
  deterministic; say so.
- Do not rename the 7 rules (R1–R7) or the verdict vocabulary
  (PASS/FAIL/REVIEW) — the demo script and tests depend on them.
