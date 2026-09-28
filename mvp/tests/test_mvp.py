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

    # B must fail specifically on turnover inconsistency + CA number
    b_rules = {c["rule"].split("·")[0].strip(): c["status"]
               for c in v["B"]["checks"]}
    assert b_rules.get("R2") == "FAIL", "B: R2 turnover mismatch not caught"
    assert b_rules.get("R3") == "FAIL", "B: R3 bad CA number not caught"
    # D must fail on missing 144(xi)
    d_rules = {c["rule"].split("·")[0].strip(): c["status"]
               for c in v["D"]["checks"]}
    assert d_rules.get("R5") == "FAIL", "D: R5 missing 144(xi) not caught"
    # E must fail on local content + past performance
    e_rules = {c["rule"].split("·")[0].strip(): c["status"]
               for c in v["E"]["checks"]}
    assert e_rules.get("R4") == "FAIL", "E: R4 Class-I misrepresentation not caught"
    assert e_rules.get("R6") == "FAIL", "E: R6 past performance not caught"

    ok, msg = res["ledger"].verify()
    assert ok, f"audit chain broken: {msg}"

    print("ALL GROUND-TRUTH TESTS PASSED [OK]")
    print(f"  verdicts: { {k: x['verdict'] for k, x in v.items()} }")
    print(f"  L1: {res['l1']} | rings: {res['collusion']['rings']} | {msg}")


if __name__ == "__main__":
    main()
