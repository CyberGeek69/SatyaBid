"""Cross-bidder fraud analytics: collusion / cartel detection.

Builds a bidder-relationship graph (networkx). Nodes are bidders; edges carry
weighted collusion signals:

  shared_directors   3.0 per shared person   (strongest: common control)
  shared_phone       2.5                       (common office / operator)
  shared_address     2.0
  price_proximity    up to 2.0                 (cover-bidding pattern: quotes
                                               suspiciously close together)
  shared_doc_author  1.5                       (bids prepared on same machine)

Edge risk: score >= 5 HIGH (suspected ring), >= 2.5 MEDIUM, > 0 LOW.
Connected components of HIGH edges are reported as suspected rings.
"""
import itertools
import networkx as nx

W_DIRECTOR = 3.0
W_PHONE = 2.5
W_ADDRESS = 2.0
W_PRICE = 2.0
W_AUTHOR = 1.5
# identity-clustering weights (phantom / single-controller bidders)
W_PAN = 4.0      # same PAN = same legal entity behind two "bidders"
W_GSTIN = 3.5
W_BANK = 3.5     # shared bank account across "competitors"
W_IP = 3.0       # bids submitted from the same IP (cf. CCI GAIL case)
W_DSC = 3.0      # same digital-signature token operator
W_EMAIL = 2.5


def _norm_phone(p):
    return "".join(c for c in (p or "") if c.isdigit())


def _norm_bank(b):
    return "".join(c for c in (b or "") if c.isdigit())


def pairwise_signals(a, b, doc_pairs=None, ml_pairs=None):
    signals = []

    shared = sorted(set(a.directors) & set(b.directors))
    if shared:
        signals.append(("shared_directors", W_DIRECTOR * len(shared),
                        f"Common directors/partners: {', '.join(shared)}"))

    if a.phone and b.phone and _norm_phone(a.phone) == _norm_phone(b.phone):
        signals.append(("shared_phone", W_PHONE,
                        f"Identical contact phone: {a.phone}"))

    if a.address and b.address and a.address.strip().lower() == b.address.strip().lower():
        signals.append(("shared_address", W_ADDRESS,
                        f"Identical registered address: {a.address[:60]}"))

    if a.price and b.price:
        prox = abs(a.price - b.price) / max(a.price, b.price)
        if prox <= 0.02:  # within 2% — classic cover-bidding band
            w = W_PRICE * (1 - prox / 0.02)
            signals.append(("price_proximity", round(w, 2),
                            f"Quoted prices within {prox*100:.2f}% "
                            f"(Rs. {a.price:,.0f} vs Rs. {b.price:,.0f}) — "
                            f"possible cover bidding"))

    auth_a = (a.metadata.get("author") or "").strip()
    auth_b = (b.metadata.get("author") or "").strip()
    if auth_a and auth_a == auth_b:
        signals.append(("shared_doc_author", W_AUTHOR,
                        f"Both bid documents authored on '{auth_a}' "
                        f"(identical PDF metadata)"))

    # --- identity clustering: one controller behind multiple "bidders" ---
    if a.pan and b.pan and a.pan == b.pan:
        signals.append(("shared_pan", W_PAN,
                        f"Same PAN {a.pan} behind two bidders — one legal "
                        f"entity masquerading as competitors"))
    if a.gstin and b.gstin and a.gstin == b.gstin:
        signals.append(("shared_gstin", W_GSTIN,
                        f"Same GSTIN {a.gstin} across bidders"))
    if a.bank_account and b.bank_account and \
            _norm_bank(a.bank_account) == _norm_bank(b.bank_account):
        signals.append(("shared_bank", W_BANK,
                        f"Same bank account {a.bank_account} across 'competing' "
                        f"bidders"))
    if a.ip_address and b.ip_address and a.ip_address == b.ip_address:
        signals.append(("shared_ip", W_IP,
                        f"Bids submitted from the same IP {a.ip_address}"))
    if a.dsc_operator and b.dsc_operator and \
            a.dsc_operator.strip().lower() == b.dsc_operator.strip().lower():
        signals.append(("shared_dsc", W_DSC,
                        f"Same DSC token operator: {a.dsc_operator}"))
    if a.email and b.email and a.email == b.email:
        signals.append(("shared_email", W_EMAIL,
                        f"Same contact email: {a.email}"))

    # --- document-forensics corroboration (bounded so it can't dominate) ---
    if doc_pairs:
        dp = doc_pairs.get(frozenset((a.bidder_id, b.bidder_id)))
        if dp:
            signals.append(("common_authorship_markers", dp["weight"],
                            dp["detail"]))

    # --- ML forensics corroboration (bounded so it can't dominate) ---
    # ML proposes similarity signals; deterministic rules still decide.
    if ml_pairs:
        mp = ml_pairs.get(frozenset((a.bidder_id, b.bidder_id)))
        if mp:
            for sig in mp["signals"]:
                signals.append((sig, round(mp["weight"] / len(mp["signals"]),
                                           2),
                                mp["detail"]))

    return signals


def risk_level(score):
    if score >= 5:
        return "HIGH"
    if score >= 2.5:
        return "MEDIUM"
    if score > 0:
        return "LOW"
    return "NONE"


def analyse_collusion(facts_list, doc_pairs=None, ml_pairs=None):
    G = nx.Graph()
    for f in facts_list:
        G.add_node(f.bidder_id, name=f.name, price=f.price)

    edges = []
    for a, b in itertools.combinations(facts_list, 2):
        sigs = pairwise_signals(a, b, doc_pairs=doc_pairs, ml_pairs=ml_pairs)
        if not sigs:
            continue
        score = round(sum(w for _, w, _ in sigs), 2)
        level = risk_level(score)
        G.add_edge(a.bidder_id, b.bidder_id, weight=score,
                   risk=level, signals=[s for s, _, _ in sigs])
        edges.append({
            "pair": (a.bidder_id, b.bidder_id),
            "names": (a.name, b.name),
            "score": score,
            "risk": level,
            "signals": [{"type": s, "weight": w, "detail": d}
                        for s, w, d in sigs],
        })

    # suspected rings: connected components over HIGH edges only
    high = [(u, v) for u, v, d in G.edges(data=True) if d["risk"] == "HIGH"]
    H = nx.Graph()
    H.add_nodes_from(G.nodes(data=True))
    H.add_edges_from(high)
    rings = [sorted(c) for c in nx.connected_components(H) if len(c) > 1]

    # per-bidder collusion flag
    flags = {}
    for f in facts_list:
        worst = "NONE"
        details = []
        for e in edges:
            if f.bidder_id in e["pair"]:
                details.append(e)
                order = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
                if order[e["risk"]] > order[worst]:
                    worst = e["risk"]
        flags[f.bidder_id] = {"risk": worst, "edges": details}

    return {"graph": G, "edges": edges, "rings": rings, "flags": flags}
