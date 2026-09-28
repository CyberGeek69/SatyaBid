"""SatyaBid MVP — Streamlit demo UI.

Run:  streamlit run app.py
"""
import glob
import hashlib
import io
import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import streamlit as st

from run_mvp import run
from satyabid import AuditLedger

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")

st.set_page_config(page_title="SatyaBid — Bid Scrutiny MVP",
                   page_icon="⚖️", layout="wide")

VERDICT_COLOR = {"PASS": "🟢", "FAIL": "🔴", "REVIEW": "🟡"}
RISK_COLOR = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡", "NONE": "⚪"}


def _sig(paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        with open(p, "rb") as f:
            h.update(f.read())
    return h.hexdigest()


@st.cache_data(show_spinner=False)
def analyse(tender_path, bid_paths, sig):
    ledger = AuditLedger()
    return run(tender_path, list(bid_paths), ledger)


def load_bundled():
    tender = os.path.join(DATA, "tender.pdf")
    bids = sorted(glob.glob(os.path.join(DATA, "bids", "*.pdf")))
    return tender, bids


# ---------------------------------------------------------------- sidebar ---
st.sidebar.title("⚖️ SatyaBid")
st.sidebar.caption("Intelligent Bid Scrutiny & Cross-Bidder Cartel Detection — MVP")
mode = st.sidebar.radio("Dataset",
                        ["Bundled synthetic tender (demo)",
                         "Upload your own PDFs"])
uploaded = {}
if mode.startswith("Upload"):
    t = st.sidebar.file_uploader("Tender document (PDF)", type="pdf")
    bs = st.sidebar.file_uploader("Bidder documents (PDF)", type="pdf",
                                  accept_multiple_files=True)
    if t and bs:
        tmp = tempfile.mkdtemp()
        tp = os.path.join(tmp, "tender.pdf")
        open(tp, "wb").write(t.read())
        bps = []
        for b in bs:
            p = os.path.join(tmp, b.name)
            open(p, "wb").write(b.read())
            bps.append(p)
        uploaded = {"tender": tp, "bids": bps}

run_btn = st.sidebar.button("▶ Run scrutiny", type="primary", use_container_width=True)
st.sidebar.divider()
st.sidebar.caption("MVP scope: digital PDFs · deterministic rules · "
                   "simulated registries (GSTN/Udyam/MCA adapters are stubs). "
                   "OCR adapter seam ready for PaddleOCR on scanned pages.")

# ---------------------------------------------------------------- main -----
st.title("SatyaBid — Bid Scrutiny Report")
st.caption("Bid GEM/2026/B/6123457 · Supply, Installation & Commissioning of "
           "500 Desktop Computers · CPCL")

if mode.startswith("Bundled"):
    tender_path, bid_paths = load_bundled()
else:
    tender_path, bid_paths = uploaded.get("tender"), uploaded.get("bids", [])

if not tender_path or not bid_paths:
    st.info("Upload a tender PDF and at least one bidder PDF, then press **Run scrutiny**.")
    st.stop()
if not os.path.exists(tender_path):
    st.error("Bundled dataset not found — run `python3 gen_data.py` first.")
    st.stop()

if run_btn or "result" not in st.session_state:
    with st.spinner("Ingesting documents → blueprinting tender → running checks → "
                     "mapping collusion graph…"):
        res = analyse(tender_path, tuple(bid_paths), _sig([tender_path] + bid_paths))
        st.session_state["result"] = res
        st.session_state["ledger"] = res["ledger"]

res = st.session_state["result"]
ledger = st.session_state["ledger"]
verdicts = res["verdicts"]

tab1, tab2, tab3, tab4 = st.tabs(
    ["📋 Scrutiny dashboard", "🔍 Evidence viewer",
     "🕸️ Collusion graph", "🔗 Audit trail"])

# ------------------------------------------------------- tab 1: dashboard ---
with tab1:
    n_pass = sum(1 for v in verdicts if v["verdict"] == "PASS")
    n_fail = sum(1 for v in verdicts if v["verdict"] == "FAIL")
    n_rev = sum(1 for v in verdicts if v["verdict"] == "REVIEW")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bidders analysed", len(verdicts))
    c2.metric("✅ Technically responsive", n_pass)
    c3.metric("❌ Rejected", n_fail)
    c4.metric("🟡 Manual review", n_rev)

    if res["l1"]:
        w = next(v for v in verdicts if v["bidder_id"] == res["l1"])
        st.success(f"**L1 — lowest responsive bidder:** {w['bidder_id']} · "
                   f"{w['name']} · Rs. {w['price']:,.0f}/- "
                   f"(two-cover isolation: only PASS bids ranked)")
    else:
        st.warning("No responsive bidder — L1 cannot be determined.")

    st.subheader("Bidder verdicts")
    for v in verdicts:
        icon = VERDICT_COLOR[v["verdict"]]
        price = f"Rs. {v['price']:,.0f}/-" if v["price"] else "n/a"
        with st.expander(
                f"{icon} **{v['bidder_id']} — {v['name']}** · {v['verdict']} · "
                f"{price} · collusion {RISK_COLOR[v['collusion_risk']]}{v['collusion_risk']}"):
            st.markdown("**Speaking order**")
            st.code(v["speaking_order"], language=None)
            st.markdown("**Rule checks**")
            for c in v["checks"]:
                st.markdown(f"{VERDICT_COLOR[c['status']]} `{c['rule']}` — {c['rationale']}")

# -------------------------------------------------- tab 2: evidence viewer ---
with tab2:
    st.subheader("Evidence viewer — every verdict traces to clause + document")
    bid_sel = st.selectbox("Bidder", [f"{v['bidder_id']} — {v['name']}"
                                     for v in verdicts])
    v = next(x for x in verdicts
             if f"{x['bidder_id']} — {x['name']}" == bid_sel)
    if not v["evidence"]:
        st.info("No evidence excerpts for this bidder.")
    else:
        rule_sel = st.selectbox("Rule", [e["rule"] for e in v["evidence"]])
        e = next(x for x in v["evidence"] if x["rule"] == rule_sel)
        left, right = st.columns(2)
        with left:
            st.markdown(f"📜 **Tender clause**"
                        + (f" (page {e['clause_page']})" if e["clause_page"] else ""))
            st.info(e["clause"] or "—")
        with right:
            st.markdown(f"📄 **Bidder's document**"
                        + (f" (page {e['doc_page']})" if e["doc_page"] else ""))
            st.warning(e["document"] or "—")
        st.markdown(f"**Engine verdict on this rule:** "
                    f"{VERDICT_COLOR[e['status']]} {e['status']}")

# -------------------------------------------------- tab 3: collusion graph ---
with tab3:
    st.subheader("Cross-bidder relationship graph")
    edges = res["collusion"]["edges"]
    G = nx.Graph()
    for v in verdicts:
        G.add_node(v["bidder_id"], name=v["name"])
    for e in edges:
        u, vv = e["pair"]
        G.add_edge(u, vv, risk=e["risk"], score=e["score"])

    if G.number_of_edges() == 0:
        st.info("No cross-bidder relationships detected.")
    else:
        fig, ax = plt.subplots(figsize=(8, 5))
        pos = nx.spring_layout(G, seed=42)
        color = {"HIGH": "#d62728", "MEDIUM": "#ff7f0e", "LOW": "#ffbb00"}
        nx.draw_networkx_nodes(G, pos, ax=ax, node_size=2600,
                               node_color="#dbe7f5", edgecolors="#0f2a4a")
        nx.draw_networkx_labels(
            G, pos, ax=ax,
            labels={n: f"{n}\n{G.nodes[n]['name'].split()[0]}" for n in G.nodes()},
            font_size=10, font_weight="bold")
        for u, vv, d in G.edges(data=True):
            nx.draw_networkx_edges(G, pos, ax=ax, edgelist=[(u, vv)],
                                   width=1 + d["score"],
                                   edge_color=color.get(d["risk"], "#999"))
        edge_labels = {(u, vv): f"{d['risk']} ({d['score']})"
                       for u, vv, d in G.edges(data=True)}
        nx.draw_networkx_edge_labels(G, pos, edge_labels, ax=ax, font_size=9)
        ax.set_axis_off()
        st.pyplot(fig)

        rings = res["collusion"]["rings"]
        if rings:
            st.error("🚨 **Suspected cartel ring(s):** "
                     + "; ".join(" + ".join(r) for r in rings))
        st.markdown("**Pairwise signals**")
        for e in sorted(edges, key=lambda x: -x["score"]):
            with st.expander(f"{RISK_COLOR[e['risk']]} "
                             f"{e['pair'][0]} ↔ {e['pair'][1]} · "
                             f"{e['risk']} (score {e['score']})"):
                for s in e["signals"]:
                    st.markdown(f"- *{s['type']}* (w={s['weight']}): {s['detail']}")

# ----------------------------------------------------- tab 4: audit trail ---
with tab4:
    st.subheader("Tamper-evident audit ledger (SHA-256 hash chain)")
    if st.button("🔍 Verify chain"):
        ok, msg = ledger.verify()
        (st.success if ok else st.error)(msg)
    rows = [{"seq": e["seq"], "time": e["timestamp"], "event": e["event"],
             "entry_hash": e["entry_hash"][:16] + "…",
             "prev_hash": (e["prev_hash"][:16] + "…"
                           if e["prev_hash"] != "GENESIS" else "GENESIS")}
            for e in ledger.to_list()]
    st.dataframe(rows, use_container_width=True)
    st.caption("Each entry commits to the previous entry's hash — altering any "
               "verdict after issue breaks the chain.")
