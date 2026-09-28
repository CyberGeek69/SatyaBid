"""Verdict assembly: combine rule checks + collusion flags into one
evidence-linked verdict per bidder, written as a 'speaking order'.
"""


def build_verdict(facts, check_results, collusion_flag):
    fails = [c for c in check_results if c.status == "FAIL"]
    reviews = [c for c in check_results if c.status == "REVIEW"]
    crisk = (collusion_flag or {}).get("risk", "NONE")

    if fails:
        verdict = "FAIL"
    elif crisk == "HIGH" or reviews:
        verdict = "REVIEW"
    elif crisk == "MEDIUM":
        verdict = "REVIEW"
    else:
        verdict = "PASS"

    lines = []
    if verdict == "PASS":
        lines.append(
            f"{facts.name} is TECHNICALLY RESPONSIVE. All eligibility criteria "
            f"are met against tender clauses.")
    elif verdict == "FAIL":
        lines.append(
            f"{facts.name} is NOT TECHNICALLY RESPONSIVE and its Cover-2 "
            f"financial bid must not be opened, for the following reasons:")
        for c in fails:
            lines.append(f"  \u2022 {c.rule}: {c.rationale}")
    else:
        lines.append(
            f"{facts.name} is marked FOR MANUAL REVIEW before its Cover-2 bid "
            f"is opened:")
        for c in reviews:
            lines.append(f"  \u2022 {c.rule}: {c.rationale}")

    if crisk in ("HIGH", "MEDIUM"):
        lines.append(
            f"  \u2022 Collusion analytics: {crisk} risk relationship with "
            f"{len(collusion_flag['edges'])} other bidder(s). " +
            " ".join(s["detail"] for e in collusion_flag["edges"]
                     for s in e["signals"]))

    evidence = []
    for c in check_results:
        if c.clause_evidence or c.doc_evidence:
            evidence.append({
                "rule": c.rule, "status": c.status,
                "clause": c.clause_evidence, "clause_page": c.clause_page,
                "document": c.doc_evidence, "doc_page": c.doc_page,
            })

    return {
        "bidder_id": facts.bidder_id,
        "name": facts.name,
        "verdict": verdict,
        "price": facts.price,
        "speaking_order": "\n".join(lines),
        "checks": [{"rule": c.rule, "status": c.status,
                    "rationale": c.rationale} for c in check_results],
        "evidence": evidence,
        "collusion_risk": crisk,
    }
