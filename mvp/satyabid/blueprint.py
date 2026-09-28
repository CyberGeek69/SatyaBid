"""Tender blueprinting: convert a tender document into structured requirements.

Each extracted requirement keeps its evidence (the exact clause text + page)
so every downstream verdict can point at the clause it was judged against.

Note: PDF text extraction wraps lines arbitrarily, so every multi-word
literal uses \\s+ instead of literal spaces.
"""
import re


def _inr_to_number(s):
    """'Rs. 1,50,00,000/-' -> 15000000.0 ; 'Rs. 75,00,000/-' -> 7500000.0"""
    digits = re.sub(r"[^0-9]", "", s or "")
    return float(digits) if digits else None


def extract_blueprint(pages):
    text = "\n".join(t for _, t, _ in pages)

    def page_of(snippet):
        for no, t, _ in pages:
            if snippet[:60] in t:
                return no
        return None

    reqs = {}

    # --- minimum average annual turnover ---
    m = re.search(
        r"minimum\s+average\s+annual\s+turnover.*?shall\s+be\s*(Rs\.\s*[\d,]+/-)",
        text, re.IGNORECASE | re.DOTALL)
    if m:
        reqs["turnover_min"] = {
            "value": _inr_to_number(m.group(1)),
            "evidence": m.group(0).strip()[:400],
            "page": page_of(m.group(0)),
        }

    # --- EMD ---
    m = re.search(r"Earnest\s+Money\s+Deposit\s*\(EMD\):\s*(Rs\.\s*[\d,]+/-)",
                  text, re.IGNORECASE)
    if m:
        reqs["emd"] = {"value": _inr_to_number(m.group(1)),
                       "evidence": m.group(0).strip()[:300],
                       "page": page_of(m.group(0))}

    # --- past performance ---
    m = re.search(
        r"Past\s+performance:.*?not\s+less\s+than\s*(Rs\.\s*[\d,]+/-)",
        text, re.IGNORECASE | re.DOTALL)
    if m:
        reqs["past_performance_min"] = {
            "value": _inr_to_number(m.group(1)),
            "evidence": m.group(0).strip()[:400],
            "page": page_of(m.group(0)),
        }

    # --- Make in India: Class-I local content threshold ---
    m = re.search(
        r"Class-I\s+Local\s+Supplier.*?local\s+content\s+of\s*(\d+)\s*%?\s*or\s+more",
        text, re.IGNORECASE | re.DOTALL)
    if m:
        reqs["local_content_min"] = {
            "value": float(m.group(1)),
            "evidence": m.group(0).strip()[:400],
            "page": page_of(m.group(0)),
        }

    # --- GFR 144(xi) declaration mandatory ---
    m = re.search(
        r"GFR\s+Rule\s+144\(xi\).*?Bids\s+without\s+this\s+declaration\s+shall\s+be\s+summarily\s+rejected",
        text, re.IGNORECASE | re.DOTALL)
    if m:
        reqs["requires_144xi"] = {"value": True,
                                  "evidence": m.group(0).strip()[:400],
                                  "page": page_of(m.group(0))}

    # --- delivery schedule ---
    m = re.search(r"within\s*(\d+)\s*days\s*of\s+purchase\s+order", text,
                  re.IGNORECASE)
    if m:
        reqs["delivery_days"] = {"value": float(m.group(1)),
                                 "evidence": m.group(0).strip(),
                                 "page": page_of(m.group(0))}

    # --- bid number / estimated value (context, not a check) ---
    m = re.search(r"Bid\s+Number:\s*([A-Z0-9/]+)", text)
    if m:
        reqs["bid_number"] = {"value": m.group(1), "evidence": m.group(0),
                              "page": page_of(m.group(0))}
    m = re.search(r"Estimated\s+bid\s+value:\s*(Rs\.\s*[\d,]+/-)", text,
                  re.IGNORECASE)
    if m:
        reqs["estimated_value"] = {"value": _inr_to_number(m.group(1)),
                                   "evidence": m.group(0),
                                   "page": page_of(m.group(0))}

    return reqs
