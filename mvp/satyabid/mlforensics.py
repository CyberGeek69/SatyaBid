"""ML forensics: machine-learning screens that catch what rules can't.

Two deterministic, fully-offline ML screens (scikit-learn, no randomness):

1. paraphrase_screen — TF-IDF (word unigrams+bigrams) + cosine similarity
   across bid sentences, clustered by near-duplicate similarity. Catches
   "same hand, different words": a draft shared by a bidder SUBSET in
   reworded form, which the exact sentence matcher in docforensics misses.
   Tender wording, compliance boilerplate and signature blocks are excluded;
   drafts appearing in every bid are template text, not authorship evidence.

2. fuzzy_entity_screen — character n-gram TF-IDF + cosine similarity on
   identity strings (director names, registered addresses), with initial
   handling ("V. Shah" vs "Vikram Shah"). Catches deliberate spelling
   variants that exact matching misses. Exact-equal strings are skipped
   (already covered by the collusion graph).

Design rule: ML *proposes* similarity signals; deterministic rules still
decide every verdict. Every ML finding cites the two texts and the
similarity score, so an officer can verify it by eye.
"""
import re
from itertools import combinations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .docforensics import _sentences, _norm, _MANDATED

# Cosine similarity at/above this counts as "same draft, paraphrased".
# Only clusters whose owner set is a strict bidder SUBSET are reported
# (template language shared by every bid is excluded by that rule, exactly
# like docforensics' exact screen) — so the threshold only needs to sit
# above innocent subset prose, not above ubiquitous template text.
PARAPHRASE_THRESHOLD = 0.55
# Near-1.0 means byte-identical (modulo normalisation) — docforensics'
# exact screen already owns those; the ML screen only reports true paraphrases.
IDENTICAL_CUTOFF = 0.995
# Fuzzy identity strings at/above this count as spelling variants.
FUZZY_THRESHOLD = 0.80

# Signature blocks ("Authorised Signatory ... date ... place ...") are form
# artifacts, not prose — every bid has one, so they carry no authorship
# signal and are excluded from paraphrase detection.
_SIGNATURE = re.compile(r"authorised\s+signatory", re.IGNORECASE)
# Bidder-particulars tables extract as one long pseudo-sentence beginning
# with the header row "Field / Details / Legal name". They are structured
# data, not prose — paraphrase detection targets prose, and the identity
# graph already owns field-level matches.
_TABLE_HEADER = re.compile(r"field\s+details\s+legal\s+name")

# Bounded collusion-graph weights: ML corroborates, never dominates.
W_PARAPHRASE = 1.5
W_FUZZY = 1.0


def _candidates(bid_texts, tender_text=""):
    """Candidate sentences per bidder, after the same exclusions as the
    exact screen (tender wording, mandated compliance boilerplate), plus
    signature blocks (form artifacts, not prose)."""
    tender_norm = _norm(tender_text)
    out = {}
    for bid, text in bid_texts.items():
        sents = []
        for s in _sentences(text):
            ns = _norm(s)
            if len(ns) < 40 or len(ns) > 400:
                continue
            if ns in tender_norm:
                continue
            if _MANDATED.search(ns):
                continue
            if _SIGNATURE.search(ns):
                continue
            if _TABLE_HEADER.search(ns):
                continue  # structured table dump, not prose
            sents.append((s.strip()[:220], ns))
        out[bid] = sents
    return out


def paraphrase_screen(bid_texts, tender_text=""):
    """-> {"findings": [...], "max_similarity": float}

    Near-duplicate sentences are union-find clustered; a cluster is
    reported only when its owner set is a strict bidder subset
    (2 <= owners < n) — drafts shared by every bid are template text.
    Findings have type "paraphrased_boilerplate", severity HIGH, the
    bidder set, the top example pair and its cosine similarity.
    """
    cand = _candidates(bid_texts, tender_text)
    bids = sorted(cand)
    n = len(bids)
    flat, owners = [], []
    for b in bids:
        for raw, ns in cand[b]:
            flat.append(ns)
            owners.append(b)
    findings, max_sim = [], 0.0
    if len(flat) < 2:
        return {"findings": findings, "max_similarity": max_sim}

    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    mat = vec.fit_transform(flat)
    sim = cosine_similarity(mat)

    # union-find over near-duplicate links (paraphrase band only)
    parent = list(range(len(flat)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i, j in combinations(range(len(flat)), 2):
        if owners[i] == owners[j]:
            continue
        s = sim[i][j]
        max_sim = max(max_sim, s)
        if PARAPHRASE_THRESHOLD <= s < IDENTICAL_CUTOFF:
            union(i, j)

    clusters = {}
    for i in range(len(flat)):
        clusters.setdefault(find(i), []).append(i)
    for members in clusters.values():
        own = sorted({owners[i] for i in members})
        if not (2 <= len(own) < n):
            continue
        # top example pair inside the cluster
        best, best_s = None, -1.0
        for i, j in combinations(members, 2):
            if owners[i] != owners[j] and sim[i][j] > best_s:
                best, best_s = (i, j), sim[i][j]
        if best is None:
            continue
        i, j = best
        findings.append({
            "type": "paraphrased_boilerplate",
            "severity": "HIGH",
            "bidders": own,
            "similarity": round(float(best_s), 3),
            "text_a": flat[i][:180],
            "text_b": flat[j][:180],
            "detail": f"ML (TF-IDF cosine {best_s:.2f}): bids "
                      f"{', '.join(own)} share the same draft in different "
                      f"words — exact sentence matching misses this, "
                      f"paraphrase detection catches it. Suggests common "
                      f"authorship.",
        })
    findings.sort(key=lambda f: -f["similarity"])
    return {"findings": findings, "max_similarity": round(float(max_sim), 3)}


def entity_similarity(a, b):
    """Character n-gram TF-IDF cosine similarity between two identity
    strings (names, addresses), with initial handling: a single-letter
    token matching another token's first letter ("V. Shah" vs
    "Vikram Shah") scores 0.85 — the classic deliberate-variant dodge.
    Deterministic, offline."""
    na, nb = _norm(a or ""), _norm(b or "")
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = na.split(), nb.split()
    if len(ta) == len(tb) and all(
            x == y or (len(x) == 1 and y.startswith(x))
            or (len(y) == 1 and x.startswith(y)) for x, y in zip(ta, tb)):
        return 0.85
    vec = TfidfVectorizer(analyzer="char", ngram_range=(3, 5),
                          sublinear_tf=True)
    mat = vec.fit_transform([na, nb])
    return float(cosine_similarity(mat[0], mat[1])[0][0])


def fuzzy_entity_screen(facts_list):
    """-> {"findings": [...]} — spelling-variant directors/addresses.

    Only fires on NON-identical strings (exact matches are already covered
    by the collusion graph's shared_directors / shared_address signals).
    """
    findings = []
    for a, b in combinations(facts_list, 2):
        pair = sorted((a.bidder_id, b.bidder_id))
        checked = set()
        for field, avals, bvals in (
                ("director", a.directors, b.directors),
                ("address", [a.address], [b.address])):
            for x in avals:
                for y in bvals:
                    if not x or not y:
                        continue
                    nx, ny = _norm(x), _norm(y)
                    if nx == ny or (nx, ny) in checked:
                        continue  # exact — already covered
                    checked.add((nx, ny))
                    s = entity_similarity(x, y)
                    if s >= FUZZY_THRESHOLD:
                        findings.append({
                            "type": "fuzzy_identity_match",
                            "severity": "MEDIUM",
                            "bidders": pair,
                            "field": field,
                            "similarity": round(s, 3),
                            "text_a": x[:80],
                            "text_b": y[:80],
                            "detail": f"ML (char n-gram cosine {s:.2f}): "
                                      f"{field} '{x[:60]}' ({pair[0]}) looks "
                                      f"like a spelling variant of "
                                      f"'{y[:60]}' ({pair[1]}) — possible "
                                      f"deliberate variation to dodge exact "
                                      f"matching.",
                        })
    return {"findings": findings}


def ml_pair_markers(paraphrase_result, fuzzy_result):
    """-> {frozenset({a,b}): {'weight': float, 'signals': [str], 'detail': str}}

    Feeds the collusion graph: bounded weights so ML corroborates rather
    than dominates the deterministic identity signals.
    """
    pairs = {}
    for f in paraphrase_result.get("findings", []):
        key = frozenset(f["bidders"])
        d = pairs.setdefault(key, {"weight": 0.0, "signals": [],
                                   "details": []})
        d["weight"] += W_PARAPHRASE
        d["signals"].append("ml_paraphrase")
        d["details"].append(
            f"ML paraphrase detection (TF-IDF cosine "
            f"{f['similarity']:.2f}): same draft, different words")
    for f in fuzzy_result.get("findings", []):
        key = frozenset(f["bidders"])
        d = pairs.setdefault(key, {"weight": 0.0, "signals": [],
                                   "details": []})
        d["weight"] += W_FUZZY
        d["signals"].append("ml_fuzzy_identity")
        d["details"].append(
            f"ML fuzzy {f['field']} match (cosine {f['similarity']:.2f})")
    for d in pairs.values():
        d["weight"] = round(min(d["weight"], 2.5), 2)
        d["detail"] = "; ".join(d["details"])
        del d["details"]
    return pairs
