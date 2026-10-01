#!/usr/bin/env python3
"""SatyaBid MVP pipeline (headless).

  python3 run_mvp.py            # analyse bundled synthetic dataset
  python3 run_mvp.py --verify   # also verify the audit chain afterwards

Writes outputs/analysis.json and outputs/audit_log.json, prints a summary.
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from satyabid import (extract_pages, extract_metadata, extract_blueprint,
                      run_checks, analyse_collusion, AuditLedger,
                      build_verdict, screen_prices, analyse_documents,
                      doc_pair_markers, seal_tender, diff_requirements,
                      scan_price_hints, paraphrase_screen,
                      fuzzy_entity_screen, ml_pair_markers)
from satyabid.checks import parse_bidder
from satyabid.ingest import full_text
import re as _re


def _norm_tok(t):
    return _re.sub(r"[^a-z0-9]", "", t.lower())

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "outputs")


def bidder_id_from_path(path):
    m = re.search(r"bidder_([A-Z])_", os.path.basename(path))
    return m.group(1) if m else os.path.basename(path)


def run(tender_path, bid_paths, ledger=None):
    ledger = ledger or AuditLedger()
    ledger.append("pipeline_started",
                  {"tender": os.path.basename(tender_path),
                   "bids": [os.path.basename(p) for p in bid_paths]})

    t_pages = extract_pages(tender_path)
    blueprint = extract_blueprint(t_pages)
    ledger.append("tender_blueprinted",
                  {"requirements": list(blueprint.keys())})

    # tender integrity: seal the published tender; catch mid-tender changes
    tseal = seal_tender(t_pages)
    ledger.append("tender_sealed", {"sha256": tseal})
    corr_path = os.path.join(os.path.dirname(tender_path),
                             "tender_corrigendum.pdf")
    tender_integrity = {"seal": tseal, "corrigendum": None,
                        "relaxations": []}
    if os.path.exists(corr_path):
        corr_pages = extract_pages(corr_path)
        corr_bp = extract_blueprint(corr_pages)
        relax = diff_requirements(blueprint, corr_bp)
        changed = seal_tender(corr_pages) != tseal
        tender_integrity["corrigendum"] = os.path.basename(corr_path)
        tender_integrity["relaxations"] = relax
        ledger.append("corrigendum_checked",
                      {"file": os.path.basename(corr_path),
                       "requirements_relaxed": [r["requirement"]
                                                for r in relax
                                                if r["type"] == "relaxation"]})

    facts_list, verdicts = [], []
    bid_texts, bid_metas, bid_pages = {}, {}, {}
    for bp in sorted(bid_paths):
        bid = bidder_id_from_path(bp)
        pages = extract_pages(bp)
        meta = extract_metadata(bp)
        m = re.search(r"Bidder:\s*(.+?),", "\n".join(t for _, t, _ in pages))
        name = m.group(1).strip() if m else bid
        facts = parse_bidder(bid, name, pages, meta)
        facts_list.append(facts)
        bid_texts[bid] = full_text(pages)
        bid_metas[bid] = meta
        bid_pages[bid] = pages
        ledger.append("bidder_ingested",
                      {"bidder": bid, "name": name,
                       "doc_author": meta.get("author")})

    # document forensics BEFORE the graph: shared-draft markers feed it.
    # identity-field tokens are excluded — the graph already covers them.
    ident_toks = set()
    for f in facts_list:
        for src in [f.address, f.dsc_operator, f.email,
                    " ".join(f.directors)]:
            ident_toks.update(_norm_tok(t) for t in src.split())
    docf = analyse_documents(bid_texts,
                             tender_text=full_text(t_pages),
                             metadatas=bid_metas,
                             identity_tokens=ident_toks)
    doc_pairs = doc_pair_markers(docf)
    ledger.append("doc_forensics",
                  {"findings": len(docf["findings"]),
                   "shared_markers": docf["n_shared_markers"]})

    # ML forensics: TF-IDF paraphrase detection + fuzzy entity matching.
    # ML proposes similarity signals; deterministic rules still decide.
    mlp = paraphrase_screen(bid_texts, tender_text=full_text(t_pages))
    mlf = fuzzy_entity_screen(facts_list)
    ml_pairs = ml_pair_markers(mlp, mlf)
    ledger.append("ml_forensics",
                  {"paraphrase_findings": len(mlp["findings"]),
                   "fuzzy_findings": len(mlf["findings"]),
                   "pairs_flagged": len(ml_pairs)})

    coll = analyse_collusion(facts_list, doc_pairs=doc_pairs,
                             ml_pairs=ml_pairs)
    ledger.append("collusion_analysis",
                  {"edges": [(e["pair"], e["risk"], e["score"])
                             for e in coll["edges"]],
                   "rings": coll["rings"]})

    # price forensics: statistical bid-rigging screens over the tender
    pricef = screen_prices({f.bidder_id: f.price for f in facts_list
                            if f.price})
    ledger.append("price_forensics",
                  {"cv": pricef["stats"].get("cv"),
                   "findings": [(x["screen"], x["severity"]) for x in
                                pricef["findings"]]})

    # two-cover scan: price hints hidden in technical bids
    twocover = {bid: scan_price_hints(pgs)
                for bid, pgs in bid_pages.items()}
    ledger.append("twocover_scan",
                  {"bidders_with_hints": [b for b, h in twocover.items()
                                          if h]})

    for facts in facts_list:
        checks = run_checks(facts, blueprint)
        v = build_verdict(facts, checks, coll["flags"][facts.bidder_id])
        verdicts.append(v)
        ledger.append("verdict_issued",
                      {"bidder": facts.bidder_id, "verdict": v["verdict"],
                       "price": facts.price,
                       "collusion_risk": v["collusion_risk"]})

    # L1 among PASS bidders (two-cover isolation: only responsive bids ranked)
    responsive = [v for v in verdicts if v["verdict"] == "PASS"
                  and v["price"]]
    l1 = min(responsive, key=lambda v: v["price"]) if responsive else None
    ledger.append("l1_determined",
                  {"l1": l1["bidder_id"] if l1 else None,
                   "price": l1["price"] if l1 else None})

    return {"blueprint": blueprint, "verdicts": verdicts,
            "collusion": {"edges": coll["edges"], "rings": coll["rings"]},
            "price_forensics": pricef,
            "doc_forensics": docf,
            "ml_forensics": {"paraphrase": mlp, "fuzzy": mlf},
            "tender_integrity": tender_integrity,
            "twocover": twocover,
            "l1": l1["bidder_id"] if l1 else None,
            "ledger": ledger}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    tender = os.path.join(DATA, "tender.pdf")
    bids = sorted(glob.glob(os.path.join(DATA, "bids", "*.pdf")))
    if not os.path.exists(tender) or not bids:
        sys.exit("dataset missing — run: python3 gen_data.py")

    result = run(tender, bids)
    ledger = result.pop("ledger")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "analysis.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "audit_log.json"), "w", encoding="utf-8") as f:
        json.dump(ledger.to_list(), f, indent=2, ensure_ascii=False)

    print("=" * 64)
    print("SatyaBid MVP — scrutiny report  |  Bid GEM/2026/B/6123457")
    print("=" * 64)
    for v in result["verdicts"]:
        tag = {"PASS": "PASS", "FAIL": "FAIL",
               "REVIEW": "REVIEW"}[v["verdict"]]
        price = f"Rs. {v['price']:,.0f}" if v["price"] else "n/a"
        print(f"  [{tag:6}] {v['bidder_id']}  {v['name']:<28} {price}"
              f"   collusion: {v['collusion_risk']}")
    print("-" * 64)
    if result["l1"]:
        w = next(v for v in result["verdicts"]
                 if v["bidder_id"] == result["l1"])
        print(f"  L1 (lowest responsive): {w['bidder_id']} — {w['name']} "
              f"at Rs. {w['price']:,.0f}")
    else:
        print("  No responsive bidder — L1 cannot be determined.")
    rings = result["collusion"]["rings"]
    if rings:
        print(f"  Suspected cartel ring(s): "
              + "; ".join("+".join(r) for r in rings))
    pf = result["price_forensics"]
    if pf["findings"]:
        print(f"  Price forensics ({pf['n']} bids, CV {pf['stats']['cv']:.2%}):")
        for x in pf["findings"]:
            print(f"    [{x['severity']}] {x['screen']}: {x['detail'][:110]}")
    else:
        print("  Price forensics: no anomalous screens fired.")
    df = result["doc_forensics"]
    if df["findings"]:
        print(f"  Document forensics: {len(df['findings'])} finding(s)")
        for x in df["findings"][:6]:
            print(f"    [{x['severity']}] {x['type']} "
                  f"({', '.join(x['bidders'])}): {x['detail'][:110]}")
    tc = result["twocover"]
    hinted = [b for b, h in tc.items() if h]
    if hinted:
        print(f"  Two-cover violations: price hint(s) in technical bid of "
              f"{', '.join(hinted)}")
    else:
        print("  Two-cover scan: clean.")
    ti = result["tender_integrity"]
    print(f"  Tender seal: sha256:{ti['seal'][:16]}…")
    if ti["corrigendum"]:
        rel = [r for r in ti["relaxations"] if r["type"] == "relaxation"]
        if rel:
            print(f"  Corrigendum {ti['corrigendum']}: RELAXED "
                  + "; ".join(f"{r['requirement']} "
                              f"Rs. {r['before']:,.0f} → Rs. {r['after']:,.0f}"
                              for r in rel))
        else:
            print(f"  Corrigendum {ti['corrigendum']}: no relaxations.")
    ok, msg = ledger.verify()
    print(f"  Audit chain: {msg}")
    print("=" * 64)
    print("outputs/analysis.json  outputs/audit_log.json written")


if __name__ == "__main__":
    main()
