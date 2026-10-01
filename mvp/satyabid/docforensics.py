"""Bid-document forensics: catch bids written by a single hand.

Signals (all deterministic, all shown as evidence):
  - shared_boilerplate: a normalized sentence appearing in >=2 bids but NOT
    in all of them (template text shared by everyone is excluded) and NOT in
    the tender document itself. Compliance-mandated wording is filtered.
  - shared_markers: distinctive tokens (typos, unusual vocabulary) shared by
    a bidder subset — the classic "identical mistakes" cartel tell (OECD).
  - metadata_triple: author+creator+producer identical across a bidder
    subset — bids produced on the same machine.

`doc_pair_markers()` converts findings into per-pair weights for the
collusion graph.
"""
import re
from collections import defaultdict

# Sentences containing these are compliance boilerplate every bidder must
# write — sharing them proves nothing. (Matched against NORMALIZED text,
# where punctuation like the parentheses in "144(xi)" is already stripped.)
_MANDATED = re.compile(
    r"144\s*xi|land border|make in india|local content|earnest money|"
    r"declaration|turnover|chartered accountant|purchase order|"
    r"general financial rules", re.IGNORECASE)

_SENT_SPLIT = re.compile(r"[.!?\u2022]\s+|\n{2,}")


def _norm(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _sentences(text):
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


def analyse_documents(bid_texts, tender_text="", metadatas=None,
                      identity_tokens=None):
    """bid_texts: {bidder_id: full_text}. metadatas: {bidder_id: meta dict}.

    identity_tokens: normalized tokens from structured identity fields
    (addresses, directors, DSC brands...) — the collusion graph already
    covers those, so they are not double-counted as document markers.
    """
    n = len(bid_texts)
    identity_tokens = identity_tokens or set()
    excluded = [_norm(tender_text)]  # tender wording + mandated sentences
    tender_norm = _norm(tender_text)
    findings = []

    # --- shared boilerplate sentences (subset only) ---
    sent_owners = defaultdict(set)
    sent_example = {}
    for bid, text in bid_texts.items():
        for s in _sentences(text):
            ns = _norm(s)
            if len(ns) < 40 or len(ns) > 400:
                continue
            if ns in tender_norm:        # wording straight from the tender
                continue
            if _MANDATED.search(ns):     # compliance boilerplate
                excluded.append(ns)
                continue
            sent_owners[ns].add(bid)
            sent_example.setdefault(ns, s.strip()[:180])

    for ns, owners in sorted(sent_owners.items()):
        if 2 <= len(owners) < n:
            findings.append({
                "type": "shared_boilerplate",
                "severity": "MEDIUM",
                "bidders": sorted(owners),
                "text": sent_example[ns],
                "detail": f"Identical sentence in {len(owners)} of {n} bids "
                          f"({', '.join(sorted(owners))}) — not tender wording, "
                          f"not compliance boilerplate. Suggests common authorship.",
            })

    # --- shared distinctive tokens (identical mistakes / unusual vocabulary) ---
    # Only tokens sitting inside an already-flagged shared sentence are
    # elevated: this keeps the "identical mistakes" evidence anchored to
    # demonstrably shared text instead of flagging stray common words.
    hot_tokens = set()
    for ns in sent_owners:
        if 2 <= len(sent_owners[ns]) < n and ns not in excluded:
            hot_tokens.update(t for t in ns.split() if len(t) >= 6)
    excluded_text = " ".join(excluded)
    tok_owners = defaultdict(set)
    for bid, text in bid_texts.items():
        for tok in set(_norm(text).split()):
            if (len(tok) >= 6 and tok.isalpha()
                    and tok not in identity_tokens and tok in hot_tokens):
                tok_owners[tok].add(bid)
    for tok, owners in sorted(tok_owners.items()):
        if 2 <= len(owners) < n and tok not in excluded_text:
            findings.append({
                "type": "shared_marker",
                "severity": "HIGH",
                "bidders": sorted(owners),
                "text": tok,
                "detail": f"Distinctive token '{tok}' appears in bids "
                          f"{', '.join(sorted(owners))} but in no other bid and "
                          f"not in the tender — identical-mistake / shared-draft "
                          f"indicator.",
            })

    # --- metadata triple: same machine produced multiple bids ---
    if metadatas:
        triple_owners = defaultdict(set)
        for bid, m in metadatas.items():
            triple = tuple((m.get(k) or "").strip().lower()
                           for k in ("author", "creator", "producer"))
            if any(triple):
                triple_owners[triple].add(bid)
        for triple, owners in sorted(triple_owners.items()):
            if 2 <= len(owners) < n:
                findings.append({
                    "type": "metadata_triple",
                    "severity": "MEDIUM",
                    "bidders": sorted(owners),
                    "text": " / ".join(t for t in triple if t),
                    "detail": f"Bids {', '.join(sorted(owners))} share identical "
                              f"author/creator/producer metadata — produced on "
                              f"the same machine/software.",
                })

    return {"findings": findings,
            "n_shared_boilerplate": sum(1 for f in findings
                                       if f["type"] == "shared_boilerplate"),
            "n_shared_markers": sum(1 for f in findings
                                   if f["type"] == "shared_marker")}


def doc_pair_markers(doc_result):
    """-> {frozenset({a,b}): {'markers': int, 'weight': float, 'detail': str}}

    Feeds the collusion graph: pairs sharing authorship markers get a
    bounded weight (max 2.0) so document forensics corroborates rather
    than dominates identity signals.
    """
    pair_counts = defaultdict(int)
    pair_texts = defaultdict(list)
    for f in doc_result["findings"]:
        bs = f["bidders"]
        for i in range(len(bs)):
            for j in range(i + 1, len(bs)):
                key = frozenset((bs[i], bs[j]))
                pair_counts[key] += 1
                if len(pair_texts[key]) < 3:
                    pair_texts[key].append(f["text"][:60])
    out = {}
    for key, cnt in pair_counts.items():
        weight = round(min(2.0, 1.0 + 0.5 * (cnt - 1)), 2)
        a, b = sorted(key)
        out[key] = {
            "markers": cnt,
            "weight": weight,
            "detail": (f"{cnt} shared authorship marker(s) between {a} and {b} "
                       f"(identical sentences/typos/metadata): "
                       + "; ".join(pair_texts[key])),
        }
    return out
