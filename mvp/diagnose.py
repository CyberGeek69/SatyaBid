#!/usr/bin/env python3
"""SatyaBid backend diagnostic: runs every pipeline stage and reports
PASS/FAIL/SKIP per stage. Run:  python diagnose.py   — paste the output."""
import glob
import os
import sys
import traceback

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

ctx = {}
status = {}

print("SatyaBid backend diagnostic")
print("-" * 55)


def stage(name, needs=()):
    def deco(fn):
        if any(status.get(n) != "PASS" for n in needs):
            status[name] = "SKIP"
            print(f"  [SKIP] {name} (prerequisite failed)")
            return
        try:
            detail = fn()
            status[name] = "PASS"
            print(f"  [PASS] {name}" + (f" — {detail}" if detail else ""))
        except Exception as e:
            status[name] = "FAIL"
            print(f"  [FAIL] {name} — {type(e).__name__}: {e}")
            traceback.print_exc(limit=2)
    return deco


@stage("imports")
def _():
    missing = []
    for mod in ("streamlit", "pymupdf", "networkx", "reportlab", "matplotlib"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    assert not missing, f"pip install: {' '.join(missing)}"
    return "all deps importable"


@stage("dataset present")
def _():
    t = os.path.join(BASE, "data", "tender.pdf")
    bs = glob.glob(os.path.join(BASE, "data", "bids", "*.pdf"))
    assert os.path.exists(t), "data/tender.pdf missing — run: python gen_data.py"
    assert len(bs) == 5, f"expected 5 bid PDFs, found {len(bs)}"
    ctx["tender"], ctx["bids"] = t, sorted(bs)
    return "1 tender + 5 bids"


@stage("ingestion", needs=("dataset present",))
def _():
    from satyabid import extract_pages, extract_metadata
    pages = extract_pages(ctx["tender"])
    assert len(pages) >= 1 and len(pages[0][1]) > 200, "tender text too short"
    meta = extract_metadata(ctx["bids"][0])
    assert meta["author"], "bidder PDF author metadata empty"
    ctx["pages"] = pages
    return f"{len(pages)} tender page(s), metadata ok"


@stage("blueprinting", needs=("ingestion",))
def _():
    from satyabid import extract_blueprint
    bp = extract_blueprint(ctx["pages"])
    for k in ("turnover_min", "emd", "past_performance_min",
              "local_content_min", "requires_144xi", "bid_number"):
        assert k in bp, f"missing requirement: {k}"
    ctx["blueprint"] = bp
    return f"{len(bp)} requirements extracted"


@stage("checks R1-R8", needs=("blueprinting",))
def _():
    import re
    from satyabid import extract_pages, extract_metadata, run_checks
    from satyabid.checks import parse_bidder
    facts = []
    for bpath in ctx["bids"]:
        pages = extract_pages(bpath)
        text = "\n".join(t for _, t, _ in pages)
        m = re.search(r"Bidder:\s*(.+?),", text)
        bid = re.search(r"bidder_([A-Z])_", os.path.basename(bpath)).group(1)
        f = parse_bidder(bid, m.group(1).strip() if m else bid,
                         pages, extract_metadata(bpath))
        assert f.price, f"bidder {bid}: price not parsed"
        assert f.turnover_certified_avg, f"bidder {bid}: turnover not parsed"
        assert f.pan, f"bidder {bid}: PAN not parsed"
        assert len(run_checks(f, ctx["blueprint"])) == 8, \
            f"bidder {bid}: expected 8 checks"
        facts.append(f)
    ctx["facts"] = facts
    return "8 rules x 5 bidders, all fields parsed"


@stage("collusion graph", needs=("checks R1-R8",))
def _():
    from satyabid import analyse_collusion
    coll = analyse_collusion(ctx["facts"])
    assert any(e["risk"] == "HIGH" for e in coll["edges"]), \
        "expected a HIGH-risk edge (C-D ring)"
    assert any(set(r) == {"C", "D"} for r in coll["rings"]), \
        "C+D ring not detected"
    ctx["coll"] = coll
    return f"{len(coll['edges'])} edge(s), ring {coll['rings']}"


@stage("price forensics", needs=("checks R1-R8",))
def _():
    from satyabid import screen_prices
    pf = screen_prices({f.bidder_id: f.price for f in ctx["facts"]})
    screens = {x["screen"] for x in pf["findings"]}
    assert "CV" in screens, "CV low-dispersion screen did not fire"
    assert any(x["screen"] == "PRICE_CLUSTER"
               and set(x["bidders"]) == {"C", "D"}
               for x in pf["findings"]), "C-D price cluster not flagged"
    return f"CV {pf['stats']['cv']:.2%}, {len(pf['findings'])} finding(s)"


@stage("document forensics", needs=("checks R1-R8",))
def _():
    from satyabid import extract_pages, analyse_documents
    from satyabid.ingest import full_text
    texts = {}
    for bpath, f in zip(ctx["bids"], ctx["facts"]):
        texts[f.bidder_id] = full_text(extract_pages(bpath))
    df = analyse_documents(texts, tender_text=full_text(ctx["pages"]))
    assert any(f["text"] == "theirin" and set(f["bidders"]) == {"C", "D"}
               for f in df["findings"] if f["type"] == "shared_marker"), \
        "planted identical typo not caught"
    assert all(set(f["bidders"]) == {"C", "D"} for f in df["findings"]), \
        "doc-forensics fired outside the planted C-D pair"
    return f"{len(df['findings'])} finding(s), all C-D"


@stage("ml forensics", needs=("checks R1-R8",))
def _():
    from satyabid import (extract_pages, paraphrase_screen,
                          fuzzy_entity_screen, entity_similarity,
                          ml_pair_markers)
    from satyabid.ingest import full_text
    texts = {}
    for bpath, f in zip(ctx["bids"], ctx["facts"]):
        texts[f.bidder_id] = full_text(extract_pages(bpath))
    mlp = paraphrase_screen(texts, tender_text=full_text(ctx["pages"]))
    # planted paraphrase must be caught, and ONLY the planted C-D pair
    assert any(f["type"] == "paraphrased_boilerplate"
               and f["bidders"] == ["C", "D"] and f["similarity"] >= 0.55
               for f in mlp["findings"]), "planted C-D paraphrase not caught"
    assert all(f["bidders"] == ["C", "D"] for f in mlp["findings"]), \
        "ML paraphrase fired outside the planted C-D pair"
    # exact duplicates belong to the exact screen, not the ML screen
    assert all(f["similarity"] < 0.995 for f in mlp["findings"]), \
        "ML screen double-counting exact duplicates"
    mlf = fuzzy_entity_screen(ctx["facts"])
    assert all(f["similarity"] < 1.0 for f in mlf["findings"]), \
        "fuzzy screen double-counting exact matches"
    # unit checks: initial-variant caught, unrelated names not
    assert entity_similarity("Vikram Shah", "V. Shah") >= 0.80, \
        "initial-variant not caught"
    assert entity_similarity("Vikram Shah", "Kavita Rao") < 0.5, \
        "false positive on unrelated names"
    mp = ml_pair_markers(mlp, mlf)
    assert frozenset(("C", "D")) in mp, "C-D missing from ML pair markers"
    assert "ml_paraphrase" in mp[frozenset(("C", "D"))]["signals"], \
        "ml_paraphrase signal missing"
    return (f"{len(mlp['findings'])} paraphrase finding(s), "
            f"{len(mlf['findings'])} fuzzy finding(s)")


@stage("tender integrity", needs=("blueprinting",))
def _():
    from satyabid import (extract_pages, extract_blueprint, seal_tender,
                          diff_requirements)
    from satyabid import extract_blueprint as eb
    corr = os.path.join(BASE, "data", "tender_corrigendum.pdf")
    assert os.path.exists(corr), "tender_corrigendum.pdf missing"
    assert len(seal_tender(ctx["pages"])) == 64, "seal not SHA-256"
    relax = diff_requirements(ctx["blueprint"], eb(extract_pages(corr)))
    assert any(r["type"] == "relaxation"
               and r["before"] == 15000000.0 and r["after"] == 10000000.0
               for r in relax), "turnover relaxation not detected"
    return f"{len(relax)} change(s), relaxation caught"


@stage("two-cover scan", needs=("checks R1-R8",))
def _():
    from satyabid import extract_pages, scan_price_hints
    hits = {}
    for bpath, f in zip(ctx["bids"], ctx["facts"]):
        hits[f.bidder_id] = scan_price_hints(extract_pages(bpath))
    assert hits["E"], "E's technical-bid price hint not caught"
    assert not any(hits[b] for b in "ABCD"), "false positive price hint"
    return "E flagged, others clean"


@stage("verdicts", needs=("collusion graph",))
def _():
    from satyabid import run_checks, build_verdict
    vs = {}
    for f in ctx["facts"]:
        v = build_verdict(f, run_checks(f, ctx["blueprint"]),
                          ctx["coll"]["flags"][f.bidder_id])
        vs[f.bidder_id] = v["verdict"]
    assert vs == {"A": "PASS", "B": "FAIL", "C": "REVIEW",
                  "D": "FAIL", "E": "FAIL"}, f"wrong verdicts: {vs}"
    return str(vs)


@stage("audit ledger")
def _():
    from satyabid import AuditLedger
    led = AuditLedger()
    led.append("diagnostic", {"ok": True})
    ok, msg = led.verify()
    assert ok, msg
    return msg


print("-" * 55)
fails = [n for n, s in status.items() if s == "FAIL"]
if fails:
    print(f"{len(fails)} stage(s) FAILED — paste this whole output.")
else:
    print("Backend fully working. If the UI still misbehaves, the bug is in "
          "app.py, not the engine.")
