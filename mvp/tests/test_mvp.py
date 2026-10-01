"""Ground-truth tests: the planted fraud must be caught, the clean bid passed."""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from run_mvp import run

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.path.join(BASE, "data")


def main():
    tender = os.path.join(DATA, "tender.pdf")
    bids = sorted(glob.glob(os.path.join(DATA, "bids", "*.pdf")))
    assert os.path.exists(tender) and len(bids) == 5, "dataset incomplete"

    res = run(tender, bids)
    v = {x["bidder_id"]: x for x in res["verdicts"]}

    bp = res["blueprint"]
    for k in ("turnover_min", "emd", "past_performance_min",
              "local_content_min", "requires_144xi", "bid_number"):
        assert k in bp, f"blueprint missing requirement: {k}"

    assert v["A"]["verdict"] == "PASS", f"A should PASS, got {v['A']['verdict']}"
    assert v["B"]["verdict"] == "FAIL", f"B should FAIL, got {v['B']['verdict']}"
    assert v["D"]["verdict"] == "FAIL", f"D should FAIL, got {v['D']['verdict']}"
    assert v["E"]["verdict"] == "FAIL", f"E should FAIL, got {v['E']['verdict']}"
    assert v["C"]["verdict"] == "REVIEW", \
        f"C should be REVIEW (collusion), got {v['C']['verdict']}"
    assert v["C"]["collusion_risk"] == "HIGH", "C-D ring must be HIGH risk"
    assert v["D"]["collusion_risk"] == "HIGH", "C-D ring must be HIGH risk"
    assert ["C", "D"] in res["collusion"]["rings"] or \
        any(set(r) == {"C", "D"} for r in res["collusion"]["rings"]), \
        "C+D suspected ring missing"
    assert res["l1"] == "A", f"L1 should be A, got {res['l1']}"

    # B must fail specifically on turnover inconsistency + CA number + PAN
    b_rules = {c["rule"].split("·")[0].strip(): c["status"]
               for c in v["B"]["checks"]}
    assert len(v["B"]["checks"]) == 8, "expected 8 rules (R1-R8)"
    assert b_rules.get("R2") == "FAIL", "B: R2 turnover mismatch not caught"
    assert b_rules.get("R3") == "FAIL", "B: R3 bad CA number not caught"
    assert b_rules.get("R8") == "FAIL", "B: R8 malformed PAN not caught"
    # D must fail on missing 144(xi)
    d_rules = {c["rule"].split("·")[0].strip(): c["status"]
               for c in v["D"]["checks"]}
    assert d_rules.get("R5") == "FAIL", "D: R5 missing 144(xi) not caught"
    # E must fail on local content + past performance
    e_rules = {c["rule"].split("·")[0].strip(): c["status"]
               for c in v["E"]["checks"]}
    assert e_rules.get("R4") == "FAIL", "E: R4 Class-I misrepresentation not caught"
    assert e_rules.get("R6") == "FAIL", "E: R6 past performance not caught"

    # --- price forensics: cover-bid screens must fire ---
    pf = res["price_forensics"]
    screens = {(x["screen"], x["severity"]) for x in pf["findings"]}
    assert any(s == "CV" for s, _ in screens), "CV low-dispersion not flagged"
    clusters = [x for x in pf["findings"] if x["screen"] == "PRICE_CLUSTER"]
    assert any(set(x["bidders"]) == {"C", "D"} for x in clusters), \
        "C-D cover-bid price cluster not flagged"

    # --- document forensics: single-hand markers between C and D ---
    df = res["doc_forensics"]
    markers = [f for f in df["findings"] if f["type"] == "shared_marker"]
    assert any(f["text"] == "theirin" and set(f["bidders"]) == {"C", "D"}
               for f in markers), "planted identical typo not caught"
    assert all(set(f["bidders"]) == {"C", "D"} for f in df["findings"]), \
        f"doc-forensics noise: {df['findings']}"

    # --- ML forensics: the AI in the loop (TF-IDF paraphrase + fuzzy entity) ---
    mlp = res["ml_forensics"]["paraphrase"]
    assert any(f["type"] == "paraphrased_boilerplate"
               and f["bidders"] == ["C", "D"] and f["similarity"] >= 0.55
               for f in mlp["findings"]), "planted C-D paraphrase not caught"
    assert all(f["bidders"] == ["C", "D"] for f in mlp["findings"]), \
        f"ML paraphrase noise outside C-D: {mlp['findings']}"
    assert all(f["similarity"] < 0.995 for f in mlp["findings"]), \
        "ML screen must not double-count exact duplicates"

    # --- identity clustering: C-D edge must carry bank/IP/DSC signals ---
    cd = next(e for e in res["collusion"]["edges"]
              if set(e["pair"]) == {"C", "D"})
    sig_types = {s["type"] for s in cd["signals"]}
    for sig in ("shared_bank", "shared_ip", "shared_dsc",
                "common_authorship_markers", "ml_paraphrase"):
        assert sig in sig_types, f"C-D edge missing signal: {sig}"

    # --- two-cover scan: E hid a price hint in its technical bid ---
    tc = res["twocover"]
    assert tc["E"], "E's technical-bid price hint not caught"
    assert not any(tc[b] for b in "ABCD"), \
        f"two-cover false positives: {[b for b in 'ABCD' if tc[b]]}"

    # --- tender integrity: corrigendum relaxed eligibility ---
    ti = res["tender_integrity"]
    assert ti["corrigendum"], "corrigendum not processed"
    relax = {r["requirement"]: (r["before"], r["after"]) for r in
             ti["relaxations"] if r["type"] == "relaxation"}
    assert relax.get("minimum average annual turnover") == \
        (15000000.0, 10000000.0), f"turnover relaxation not caught: {relax}"
    assert len(ti["seal"]) == 64, "tender seal not a SHA-256 hex"

    ok, msg = res["ledger"].verify()
    assert ok, f"audit chain broken: {msg}"
    n_entries = len(res["ledger"].to_list())
    assert n_entries == 20, f"expected 20 ledger entries, got {n_entries}"

    print("ALL GROUND-TRUTH TESTS PASSED [OK]")
    print(f"  verdicts: { {k: x['verdict'] for k, x in v.items()} }")
    print(f"  L1: {res['l1']} | rings: {res['collusion']['rings']} | {msg}")


if __name__ == "__main__":
    main()
