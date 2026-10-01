"""Price forensics: statistical bid-rigging screens.

Implements the screens documented in cartel-detection literature
(CV, SPD, DIFFP, RD, skewness, Benford's law) with conservative,
documented thresholds. A screen firing is an INDICATOR, not a verdict —
every finding carries the underlying numbers so an officer can judge.

Threshold notes (from research): screens have no universal cut-offs;
these are calibrated to the published cartel-vs-competitive benchmarks
(e.g. Swiss data: cartel CV ~3.5 vs ~7.9 competitive; RD ~2.69 vs ~0.83)
and set conservatively to favour precision over recall.
"""
import math
from collections import Counter

# Conservative, documented thresholds
CV_LOW = 0.05        # abnormally low dispersion -> cover-bid clustering
DIFFP_LOW = 0.015    # engineered winner/runner-up gap (<1.5%) with low CV
RD_HIGH = 2.0        # winner isolated far below a clustered loser pack
SKEW_NEG = -0.5      # isolated low winner + clustered covers above
CLUSTER_GAP = 0.01   # any pair within 1% -> suspicious price proximity
BENFORD_MIN_N = 10   # Benford needs enough prices to be meaningful
BENFORD_MAD = 0.06   # mean abs deviation from Benford distribution

_BENFORD = {d: math.log10(1 + 1 / d) for d in range(1, 10)}


def _mean(xs):
    return sum(xs) / len(xs)


def _stdev(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    mu = _mean(xs)
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1))


def _skew(xs):
    n = len(xs)
    if n < 3:
        return 0.0
    mu, sd = _mean(xs), _stdev(xs)
    if sd == 0:
        return 0.0
    m3 = sum(((x - mu) / sd) ** 3 for x in xs)
    return n / ((n - 1) * (n - 2)) * m3


def screen_prices(prices):
    """prices: {bidder_id: price}. Returns {stats, findings}.

    Each finding: {screen, severity, detail, bidders, value, threshold}.
    """
    ids = sorted(prices, key=lambda k: prices[k])
    vals = [prices[k] for k in ids]
    n = len(vals)
    out = {"n": n, "stats": {}, "findings": []}
    if n < 3:
        out["note"] = "fewer than 3 priced bids — screens not meaningful"
        return out

    mu, sd = _mean(vals), _stdev(vals)
    cv = sd / mu if mu else 0.0
    spd = (max(vals) - min(vals)) / min(vals) if min(vals) else 0.0
    diffp = (vals[1] - vals[0]) / vals[0] if vals[0] else 0.0
    losers = vals[1:]
    lsd = _stdev(losers)
    rd = (vals[1] - vals[0]) / lsd if lsd else None
    sk = _skew(vals)
    out["stats"] = {"mean": round(mu, 2), "stdev": round(sd, 2),
                    "cv": round(cv, 4), "spread": round(spd, 4),
                    "diffp": round(diffp, 4),
                    "rel_distance": round(rd, 3) if rd is not None else None,
                    "skewness": round(sk, 3)}
    F = out["findings"].append

    # F1: abnormally low dispersion — bids clustered like cover bids
    if cv < CV_LOW:
        F({"screen": "CV", "severity": "MEDIUM",
           "value": round(cv, 4), "threshold": CV_LOW,
           "bidders": ids,
           "detail": f"Coefficient of variation {cv:.2%} is abnormally low "
                     f"(cartel benchmark ~3.5% vs ~7.9% competitive) — bids are "
                     f"clustered far tighter than genuine price rivalry produces."})

    # F2: engineered winner/runner-up gap with clustered field
    if diffp < DIFFP_LOW and cv < CV_LOW:
        F({"screen": "DIFFP", "severity": "MEDIUM",
           "value": round(diffp, 4), "threshold": DIFFP_LOW,
           "bidders": ids[:2],
           "detail": f"Winner/runner-up gap only {diffp:.2%} inside an already "
                     f"tight field — consistent with a pre-agreed winner margin "
                     f"rather than open competition."})

    # F3: winner isolated below a clustered loser pack (classic cover pattern)
    if rd is not None and rd > RD_HIGH:
        F({"screen": "RD", "severity": "MEDIUM",
           "value": round(rd, 3), "threshold": RD_HIGH,
           "bidders": ids,
           "detail": f"Relative distance {rd:.2f} (cartel benchmark ~2.69 vs "
                     f"~0.83 competitive) — the winning bid sits far below a "
                     f"tightly grouped pack of losers, the textbook cover-bid "
                     f"shape."})

    # F4: negative skew — isolated low winner, clustered covers above
    if sk < SKEW_NEG:
        F({"screen": "SKEW", "severity": "LOW",
           "value": round(sk, 3), "threshold": SKEW_NEG,
           "bidders": ids,
           "detail": f"Bid distribution is negatively skewed ({sk:.2f}; cartel "
                     f"benchmark ~-0.60 vs +0.31 competitive) — one low bid with "
                     f"the rest piled above it."})

    # F5: suspiciously close pairs (cover-bid pairs / identical-rate groups)
    for i in range(n):
        for j in range(i + 1, n):
            gap = abs(vals[i] - vals[j]) / max(vals[i], vals[j])
            if gap < CLUSTER_GAP:
                sev = "HIGH" if gap < 0.005 else "MEDIUM"
                F({"screen": "PRICE_CLUSTER", "severity": sev,
                   "value": round(gap, 4), "threshold": CLUSTER_GAP,
                   "bidders": [ids[i], ids[j]],
                   "detail": f"{ids[i]} and {ids[j]} quoted within {gap:.2%} "
                             f"(Rs. {vals[i]:,.0f} vs Rs. {vals[j]:,.0f}) — "
                             f"possible cover-bid pair."})

    # F6: Benford first-digit test — only with enough prices
    if n >= BENFORD_MIN_N:
        digits = [int(str(abs(v)).lstrip("0")[0])
                  for v in vals if str(abs(v)).lstrip("0")]
        obs = Counter(digits)
        mad = sum(abs(obs.get(d, 0) / len(digits) - _BENFORD[d])
                  for d in range(1, 10)) / 9
        out["stats"]["benford_mad"] = round(mad, 4)
        if mad > BENFORD_MAD:
            F({"screen": "BENFORD", "severity": "LOW",
               "value": round(mad, 4), "threshold": BENFORD_MAD,
               "bidders": ids,
               "detail": f"First-digit distribution deviates from Benford's "
                         f"law (MAD {mad:.3f}) — 'made-up' prices are a known "
                         f"cartel tell. Weak signal on its own; corroborate."})
    else:
        out["note"] = (f"Benford test skipped: needs >= {BENFORD_MIN_N} priced "
                       f"bids (have {n}).")

    return out
