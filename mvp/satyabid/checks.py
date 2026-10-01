"""Compliance rule engine: check one bidder's documents against the blueprint.

Every check returns a CheckResult with:
  status    PASS / FAIL / REVIEW
  rule      human-readable rule name
  clause    the tender clause it was judged against (evidence)
  document  the bidder's own document excerpt (evidence)
  rationale "speaking order" style explanation
"""
import re
from dataclasses import dataclass, field


@dataclass
class CheckResult:
    rule: str
    status: str  # PASS | FAIL | REVIEW
    rationale: str
    clause_evidence: str = ""
    clause_page: int = None
    doc_evidence: str = ""
    doc_page: int = None


@dataclass
class BidderFacts:
    bidder_id: str
    name: str
    turnover_claimed: float = None
    turnover_claimed_text: str = ""
    turnover_rows: list = field(default_factory=list)  # [(fy, value)]
    turnover_certified_avg: float = None
    ca_name: str = ""
    ca_membership_no: str = ""
    local_content_pct: float = None
    local_class_claimed: str = ""
    has_144xi: bool = False
    past_performance_value: float = None
    price: float = None
    directors: list = field(default_factory=list)
    phone: str = ""
    address: str = ""
    has_emd: bool = False
    # identity-clustering fields (phantom / single-controller detection)
    pan: str = ""
    gstin: str = ""
    email: str = ""
    bank_account: str = ""
    ip_address: str = ""
    dsc_operator: str = ""
    metadata: dict = field(default_factory=dict)


def _inr(s):
    d = re.sub(r"[^0-9]", "", s or "")
    return float(d) if d else None


def parse_bidder(bidder_id, name, pages, metadata):
    text = "\n".join(t for _, t, _ in pages)

    def pg(snippet):
        for no, t, _ in pages:
            if snippet and snippet[:50] in t:
                return no
        return None

    f = BidderFacts(bidder_id=bidder_id, name=name, metadata=metadata)

    m = re.search(r"average\s+annual\s+turnover.*?is\s*(Rs\.\s*[\d,]+/-)",
                  text, re.IGNORECASE | re.DOTALL)
    if m:
        f.turnover_claimed = _inr(m.group(1))
        f.turnover_claimed_text, f._claim_pg = m.group(0).strip()[:300], pg(m.group(0))

    rows = re.findall(r"FY\s*\d{4}-\d{2,4}\s*\n?\s*([\d,]+)", text)
    f.turnover_rows = [(f"FY{i}", _inr(v)) for i, v in enumerate(rows)]
    vals = [v for _, v in f.turnover_rows if v]
    if vals:
        f.turnover_certified_avg = sum(vals) / len(vals)

    m = re.search(r"Certified\s+by:\s*(.+?),\s*Chartered\s+Accountant,\s*ICAI\s+Membership\s+No\.\s*([A-Z0-9-]+)",
                  text, re.IGNORECASE | re.DOTALL)
    if m:
        f.ca_name, f.ca_membership_no = m.group(1).strip(), m.group(2).strip()

    m = re.search(r"local\s+content.*?is\s*(\d+)\s*%", text, re.IGNORECASE | re.DOTALL)
    if m:
        f.local_content_pct = float(m.group(1))
    m = re.search(r"claim\s+status\s+of\s*(Class-[IV]+\s+Local\s+Supplier)", text, re.IGNORECASE)
    if m:
        f.local_class_claimed = m.group(1)

    f.has_144xi = ("[No declaration furnished]" not in text and
                   bool(re.search(r"Declaration\s+under\s+GFR\s+Rule\s+144\(xi\)", text,
                                  re.IGNORECASE)))

    m = re.search(r"Past\s+performance\..*?cumulative\s+value.*?[:\-]\s*(Rs\.\s*[\d,]+/-)",
                  text, re.IGNORECASE | re.DOTALL)
    if m:
        f.past_performance_value = _inr(m.group(1))

    m = re.search(r"total\s+quoted\s+price.*?is\s*(Rs\.\s*[\d,]+/-)", text,
                  re.IGNORECASE | re.DOTALL)
    if m:
        f.price = _inr(m.group(1))

    # directors / partners
    f.directors = []
    dm = re.search(r"Directors\s*/\s*Partners(.*?)(?:Contact\s+phone|\Z)", text,
                   re.IGNORECASE | re.DOTALL)
    if dm:
        for line in dm.group(1).splitlines():
            line = line.strip()
            nm = re.match(r"([A-Z][a-z]+\s+[A-Z][a-z]+)", line)
            if nm and nm.group(1) not in f.directors:
                f.directors.append(nm.group(1))

    m = re.search(r"Contact\s+phone\s*([\d\- ]+)", text)
    if m:
        f.phone = re.sub(r"\s+", "", m.group(1).strip())
    m = re.search(r"Registered\s+address\s*(.+)", text)
    if m:
        f.address = m.group(1).strip()[:120]

    f.has_emd = bool(re.search(r"Earnest\s+Money\s+Deposit\.\s*\S", text))

    # identity fields for phantom / single-controller bidder detection
    m = re.search(r"\bPAN\s*:?\s*([A-Z0-9]{10})\b", text)
    if m:
        f.pan = m.group(1).strip()
    m = re.search(r"\bGSTIN\s*:?\s*([0-9A-Z]{15})\b", text)
    if m:
        f.gstin = m.group(1).strip()
    m = re.search(r"[\w.\-+%]+@[\w.\-]+\.[A-Za-z]{2,}", text)
    if m:
        f.email = m.group(0).strip().lower()
    m = re.search(r"Bank\s*A/c\s*:?\s*(\d{6,})", text)
    if m:
        f.bank_account = m.group(1).strip()
    m = re.search(r"\bIP\s*:?\s*(\d{1,3}(?:\.\d{1,3}){3})", text)
    if m:
        f.ip_address = m.group(1).strip()
    m = re.search(r"DSC\s*(?:token)?\s*:?\s*([^\n]+)", text)
    if m:
        f.dsc_operator = m.group(1).strip()[:80]

    f._pages, f._pg = pages, pg
    return f


def _ev(req):
    return (req.get("evidence", "") if req else "",
            req.get("page") if req else None)


def run_checks(facts, blueprint):
    R = []
    cev, cpg = _ev(blueprint.get("turnover_min"))

    # R1: certified turnover meets minimum
    req = blueprint.get("turnover_min", {}).get("value")
    if req and facts.turnover_certified_avg:
        ok = facts.turnover_certified_avg >= req
        R.append(CheckResult(
            "R1 · Minimum average annual turnover", "PASS" if ok else "FAIL",
            f"CA-certified 3-year average turnover is Rs. {facts.turnover_certified_avg:,.0f}/- "
            f"against the required Rs. {req:,.0f}/-. " +
            ("Requirement met." if ok else "Shortfall — bidder is not financially eligible."),
            cev, cpg,
            f"CA certificate rows: {', '.join(f'{v:,.0f}' for _, v in facts.turnover_rows)} "
            f"(avg {facts.turnover_certified_avg:,.0f})",
            facts._pg("turnover")))

    # R2: claimed vs certified consistency (forgery/misrepresentation signal)
    if facts.turnover_claimed and facts.turnover_certified_avg:
        gap = abs(facts.turnover_claimed - facts.turnover_certified_avg) / facts.turnover_certified_avg
        bad = gap > 0.05
        R.append(CheckResult(
            "R2 · Turnover claim vs CA certificate consistency",
            "FAIL" if bad else "PASS",
            f"Covering letter claims Rs. {facts.turnover_claimed:,.0f}/- but the enclosed CA "
            f"certificate averages Rs. {facts.turnover_certified_avg:,.0f}/- "
            f"(deviation {gap*100:.1f}%). " +
            ("Material inconsistency between the bidder's own documents — "
             "treated as misrepresentation." if bad else "Documents are consistent."),
            "", None, facts.turnover_claimed_text, getattr(facts, "_claim_pg", None)))

    # R3: CA membership number format (simulated registry check)
    valid_ca = bool(re.match(r"^(FCA|ACA)-\d{6}$", facts.ca_membership_no or ""))
    R.append(CheckResult(
        "R3 · CA certificate authenticity (membership format)",
        "PASS" if valid_ca else "FAIL",
        f"ICAI membership number '{facts.ca_membership_no}' " +
        ("matches the valid FCA/ACA-###### pattern (simulated registry check passed)."
         if valid_ca else "does NOT match the ICAI membership pattern — the certificate "
                         "cannot be verified and is treated as suspect."),
        "GFR tender clause 3: turnover 'duly certified by a practicing Chartered "
        "Accountant with valid ICAI membership number.'",
        blueprint.get("turnover_min", {}).get("page"),
        f"Membership No. {facts.ca_membership_no} (CA {facts.ca_name})",
        facts._pg("Membership")))

    # R4: Make in India local-content claim
    need = blueprint.get("local_content_min", {}).get("value", 50)
    cev4, cpg4 = _ev(blueprint.get("local_content_min"))
    if facts.local_content_pct is not None:
        claimed_i = "Class-I" in (facts.local_class_claimed or "")
        ok = (not claimed_i) or facts.local_content_pct >= need
        R.append(CheckResult(
            "R4 · Make-in-India local content declaration",
            "PASS" if ok else "FAIL",
            f"Bidder claims '{facts.local_class_claimed}' with declared local content "
            f"{facts.local_content_pct}%. Class-I requires ≥ {need:.0f}%. " +
            ("Declaration is consistent." if ok else
             "Declared content only qualifies as Class-II — the Class-I claim is a "
             "misrepresentation under the DPIIT Order."),
            cev4, cpg4,
            f"Local content declared: {facts.local_content_pct}%; "
            f"status claimed: {facts.local_class_claimed}",
            facts._pg("content")))

    # R5: GFR 144(xi) declaration
    cev5, cpg5 = _ev(blueprint.get("requires_144xi"))
    R.append(CheckResult(
        "R5 · GFR Rule 144(xi) land-border declaration",
        "PASS" if facts.has_144xi else "FAIL",
        ("Declaration furnished — bidder eligible under Rule 144(xi)."
         if facts.has_144xi else
         "No declaration furnished. The tender states bids without this declaration "
         "shall be summarily rejected."),
        cev5, cpg5,
        "Declaration present in bid." if facts.has_144xi else
        "Section 5 of bid: '[No declaration furnished]'",
        facts._pg("144(xi)")))

    # R6: past performance
    need_pp = blueprint.get("past_performance_min", {}).get("value")
    cev6, cpg6 = _ev(blueprint.get("past_performance_min"))
    if need_pp and facts.past_performance_value:
        ok = facts.past_performance_value >= need_pp
        R.append(CheckResult(
            "R6 · Past performance (similar supplies)",
            "PASS" if ok else "FAIL",
            f"Cumulative similar-supply value Rs. {facts.past_performance_value:,.0f}/- "
            f"against required Rs. {need_pp:,.0f}/-. " +
            ("Requirement met." if ok else "Bidder does not meet the experience criterion."),
            cev6, cpg6,
            f"Past performance declared: Rs. {facts.past_performance_value:,.0f}/-",
            facts._pg("Past")))

    # R7: EMD
    R.append(CheckResult(
        "R7 · Earnest Money Deposit",
        "PASS" if facts.has_emd else "REVIEW",
        ("EMD instrument enclosed." if facts.has_emd else
         "No EMD instrument found in the bid — verify MSE/Startup exemption before "
         "rejection."),
        _ev(blueprint.get("emd"))[0], _ev(blueprint.get("emd"))[1],
        "EMD section of covering letter.", facts._pg("Earnest")))

    # R8: bidder identity documents — PAN / GSTIN format validity.
    # A malformed PAN/GSTIN is a forgery signal (cf. Bombay HC Nashik fake-CA
    # case; MP EOW Sep-2026 fake-bidder case). Real registry verification
    # (NSDL/GSTN) plugs in here when live APIs are available.
    pan_ok = bool(re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", facts.pan or ""))
    gst_ok = bool(re.match(r"^\d{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]$",
                           facts.gstin or ""))
    if facts.pan and not pan_ok:
        r8_status, r8_why = "FAIL", (
            f"PAN '{facts.pan}' does not match the Income-Tax PAN pattern "
            f"(5 letters + 4 digits + 1 letter) — the identity document is "
            f"suspect.")
    elif facts.gstin and not gst_ok:
        r8_status, r8_why = "FAIL", (
            f"GSTIN '{facts.gstin}' does not match the GSTN pattern — the "
            f"identity document is suspect.")
    elif not facts.pan:
        r8_status, r8_why = "REVIEW", "No PAN found in the bid documents."
    else:
        r8_status, r8_why = "PASS", (
            f"PAN '{facts.pan}' and GSTIN '{facts.gstin}' match the statutory "
            f"formats (format-level check; live registry verification is a "
            f"planned integration).")
    R.append(CheckResult(
        "R8 · Bidder identity documents (PAN/GSTIN)",
        r8_status, r8_why,
        "Tender requires valid bidder identity documents with the bid.",
        blueprint.get("bid_number", {}).get("page"),
        f"PAN: {facts.pan or '—'}; GSTIN: {facts.gstin or '—'}",
        facts._pg("PAN")))
    return R
