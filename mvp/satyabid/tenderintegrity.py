"""Tender integrity: seal the tender at publication, catch mid-tender
condition changes, and enforce the two-cover system.

  seal_tender(pages)          -> SHA-256 of the normalized tender text.
                                 Recorded in the audit ledger at intake; any
                                 later alteration is detectable.
  diff_requirements(bp1, bp2) -> which eligibility requirements were relaxed
                                 between the published tender and a corrigendum.
  scan_price_hints(pages)     -> price figures hidden in the TECHNICAL bid
                                 (GeM terms: price indication in the technical
                                 cover = disqualification). Only text BEFORE
                                 the financial-bid section is scanned, so the
                                 legitimate Cover-2 summary is not flagged.
"""
import hashlib
import re

# price-context keywords: a money figure is only a "hint" near these
_PRICE_CTX = re.compile(
    r"quoted\s+price|commercial\s+offer|our\s+offer|bid\s+price|total\s+price|"
    r"financial\s+offer|offer\s+price|rate\s+quoted|lump\s*sum|unit\s+rate",
    re.IGNORECASE)
_MONEY = re.compile(r"(Rs\.?|\u20b9|INR)\s*([\d,]+)")
# nearby contexts that are NOT price hints (turnover/EMD/experience figures)
_SAFE_CTX = re.compile(
    r"turnover|earnest money|past performance|estimated|experience|"
    r"purchase order", re.IGNORECASE)


def _normalize(pages):
    text = "\n".join(t for _, t, _ in pages)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def seal_tender(pages):
    """SHA-256 hex of the normalized tender text."""
    return hashlib.sha256(_normalize(pages).encode("utf-8")).hexdigest()


def diff_requirements(bp_v1, bp_v2):
    """Compare two blueprints; report relaxed (lowered) requirements.

    Returns [{requirement, before, after, type}]. A relaxation issued after
    publication that matches one bidder's credentials is the classic
    mid-tender tailoring pattern.
    """
    tracked = {
        "turnover_min": "minimum average annual turnover",
        "past_performance_min": "past performance threshold",
        "emd": "Earnest Money Deposit",
        "local_content_min": "Class-I local content threshold",
    }
    findings = []
    for key, label in tracked.items():
        v1 = (bp_v1.get(key) or {}).get("value")
        v2 = (bp_v2.get(key) or {}).get("value")
        if v1 and v2 and v2 < v1:
            findings.append({
                "requirement": label,
                "before": v1, "after": v2,
                "type": "relaxation",
                "detail": f"{label} relaxed from Rs. {v1:,.0f}/- to "
                          f"Rs. {v2:,.0f}/- after publication — check whether "
                          f"the new threshold matches a specific bidder's "
                          f"credentials.",
            })
        elif v1 and v2 and v2 > v1:
            findings.append({
                "requirement": label,
                "before": v1, "after": v2,
                "type": "tightening",
                "detail": f"{label} raised from Rs. {v1:,.0f}/- to "
                          f"Rs. {v2:,.0f}/- after publication.",
            })
    return findings


def scan_price_hints(pages):
    """Find price figures hidden in the technical bid.

    Returns [{page, excerpt, detail}]. Empty list = clean.
    """
    findings = []
    for page_no, text, _src in pages:
        # cut off at the financial-bid section: Cover-2 summary is legitimate
        m = re.search(r"financial\s+bid", text, re.IGNORECASE)
        scan = text[:m.start()] if m else text
        for pm in _PRICE_CTX.finditer(scan):
            window = scan[max(0, pm.start() - 40):pm.end() + 120]
            if _SAFE_CTX.search(window):
                continue
            # search for a money figure just after the price keyword
            tail = scan[pm.start():pm.start() + 160]
            mon = _MONEY.search(tail)
            if mon and not _SAFE_CTX.search(tail[:mon.start()]):
                findings.append({
                    "page": page_no,
                    "excerpt": tail.strip()[:160],
                    "detail": f"Price indication '{mon.group(0).strip()}' found "
                              f"in the TECHNICAL bid (p{page_no}) near "
                              f"'{pm.group(0)}' — GeM terms make this a "
                              f"disqualification ground.",
                })
    # de-duplicate identical excerpts
    seen, uniq = set(), []
    for f in findings:
        if f["excerpt"] not in seen:
            seen.add(f["excerpt"])
            uniq.append(f)
    return uniq
