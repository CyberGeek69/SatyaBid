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
                      build_verdict)
from satyabid.checks import parse_bidder

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "outputs")


def bidder_id_from_path(path):
    m = re.search(r"bidder_([A-Z])_", os.path.basename(path))
    return m.group(1) if m else os.path.basename(path)


def run(tender_path, bid_paths, ledger=None, stage_callback=None):
    ledger = ledger or AuditLedger()
    ledger.append("pipeline_started",
                  {"tender": os.path.basename(tender_path),
                   "bids": [os.path.basename(p) for p in bid_paths]})

    # Stage 1: Ingesting documents (n files, p pages)
    t_pages = extract_pages(tender_path)
    total_pages = len(t_pages)

    facts_list, verdicts = [], []
    for bp in sorted(bid_paths):
        bid = bidder_id_from_path(bp)
        pages = extract_pages(bp)
        total_pages += len(pages)
        meta = extract_metadata(bp)
        m = re.search(r"Bidder:\s*(.+?),", "\n".join(t for _, t, _ in pages))
        name = m.group(1).strip() if m else bid
        facts = parse_bidder(bid, name, pages, meta)
        facts_list.append(facts)
        ledger.append("bidder_ingested",
                      {"bidder": bid, "name": name,
                       "doc_author": meta.get("author")})

    if stage_callback:
        stage_callback(1, "Ingesting documents", f"{len(bid_paths) + 1} files, {total_pages} pages parsed")

    # Stage 2: Blueprinting tender
    blueprint = extract_blueprint(t_pages)
    ledger.append("tender_blueprinted",
                  {"requirements": list(blueprint.keys())})

    if stage_callback:
        stage_callback(2, "Blueprinting tender", f"{len(blueprint)} requirements extracted")

    # Stage 3: Running compliance rules
    checks_count = 0
    checks_map = {}
    for facts in facts_list:
        checks = run_checks(facts, blueprint)
        checks_count += len(checks)
        checks_map[facts.bidder_id] = checks

    if stage_callback:
        stage_callback(3, f"Running 7 compliance rules × {len(facts_list)} bidders", f"{checks_count} compliance checks evaluated")

    # Stage 4: Mapping cross-bidder relationships
    coll = analyse_collusion(facts_list)
    ledger.append("collusion_analysis",
                  {"edges": [(e["pair"], e["risk"], e["score"])
                             for e in coll["edges"]],
                   "rings": coll["rings"]})

    if stage_callback:
        ring_text = f"suspected ring: {' + '.join(coll['rings'][0])}" if coll["rings"] else "no rings"
        stage_callback(4, "Mapping cross-bidder relationships", f"{len(coll['edges'])} edges mapped · {ring_text}")

    # Stage 5: Issuing verdicts & sealing audit ledger
    for facts in facts_list:
        v = build_verdict(facts, checks_map[facts.bidder_id], coll["flags"][facts.bidder_id])
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

    if stage_callback:
        stage_callback(5, "Issuing verdicts & sealing audit ledger", f"{len(ledger.entries)} entries committed to SHA-256 chain")

    return {"blueprint": blueprint, "verdicts": verdicts,
            "collusion": {"edges": coll["edges"], "rings": coll["rings"]},
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
    ok, msg = ledger.verify()
    print(f"  Audit chain: {msg}")
    print("=" * 64)
    print("outputs/analysis.json  outputs/audit_log.json written")


if __name__ == "__main__":
    main()
