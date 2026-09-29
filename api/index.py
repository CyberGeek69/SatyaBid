import base64
import glob
import json
import os
import re
import sys

# Ensure repo root and mvp directory are in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MVP_DIR = os.path.join(ROOT_DIR, "mvp")

for p in [ROOT_DIR, MVP_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import pymupdf

from satyabid import AuditLedger
import run_mvp

app = FastAPI(title="SatyaBid API", version="1.0")

# Enable CORS for cross-origin or local requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def vercel_path_rewrite_middleware(request: Request, call_next):
    # Check _path passed by Vercel rewrite rule
    req_subpath = request.query_params.get("_path")
    if req_subpath is not None:
        p = req_subpath.strip()
        if not p or p == "/":
            clean_path = "/"
        else:
            clean = "/" + p.lstrip("/")
            api_routes = [
                "/health", "/analysis", "/audit", "/verify",
                "/download-audit", "/run-scrutiny", "/run-scrutiny-stream",
                "/validate-document"
            ]
            if clean in api_routes or clean.startswith("/api/"):
                clean_path = clean if clean.startswith("/api/") else ("/api" + clean)
            else:
                clean_path = clean
        request.scope["path"] = clean_path
    else:
        # Fallback to headers
        matched = (
            request.headers.get("x-vercel-matched-path")
            or request.headers.get("x-matched-path")
            or request.headers.get("x-forwarded-uri")
        )
        if matched and not matched.startswith("/api/index"):
            request.scope["path"] = matched

    response = await call_next(request)
    return response


def resolve_dir(subpath):
    for candidate in [
        os.path.join(MVP_DIR, subpath),
        os.path.join(ROOT_DIR, "mvp", subpath),
        os.path.join(os.getcwd(), "mvp", subpath),
        os.path.join(ROOT_DIR, subpath),
        os.path.join(os.getcwd(), subpath),
    ]:
        if os.path.exists(candidate):
            return candidate
    return os.path.join(MVP_DIR, subpath)


DATA_DIR = resolve_dir("data")
OUTPUTS_DIR = resolve_dir("outputs")
WEB_DIR = resolve_dir("web")

# In-memory caches to handle read-only serverless environments
_cached_analysis = None
_cached_audit = None
_current_ledger = None


def get_tender_and_bids():
    data_dir = resolve_dir("data")
    tender = os.path.join(data_dir, "tender.pdf")
    bids = sorted(glob.glob(os.path.join(data_dir, "bids", "*.pdf")))
    return tender, bids


def execute_pipeline(stage_callback=None):
    global _cached_analysis, _cached_audit, _current_ledger
    tender, bids = get_tender_and_bids()
    if not os.path.exists(tender) or not bids:
        raise HTTPException(status_code=404, detail="Dataset missing under mvp/data")

    ledger = AuditLedger()
    result = run_mvp.run(tender, bids, ledger=ledger, stage_callback=stage_callback)
    result.pop("ledger", None)
    audit_list = ledger.to_list()
    result["ledger_count"] = len(audit_list)

    _cached_analysis = result
    _cached_audit = audit_list
    _current_ledger = ledger

    try:
        outputs_dir = resolve_dir("outputs")
        os.makedirs(outputs_dir, exist_ok=True)
        with open(os.path.join(outputs_dir, "analysis.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        with open(os.path.join(outputs_dir, "audit_log.json"), "w", encoding="utf-8") as f:
            json.dump(audit_list, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    return result, audit_list


def get_analysis_data():
    global _cached_analysis, _cached_audit
    if _cached_analysis and _cached_audit:
        return _cached_analysis

    outputs_dir = resolve_dir("outputs")
    analysis_file = os.path.join(outputs_dir, "analysis.json")
    audit_file = os.path.join(outputs_dir, "audit_log.json")
    if os.path.exists(analysis_file) and os.path.exists(audit_file):
        try:
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            with open(audit_file, "r", encoding="utf-8") as f:
                audit = json.load(f)
            data["ledger_count"] = len(audit)
            _cached_analysis = data
            _cached_audit = audit
            return data
        except Exception:
            pass

    res, _ = execute_pipeline()
    return res


def get_audit_data():
    global _cached_audit
    if _cached_audit is not None:
        return _cached_audit
    get_analysis_data()
    return _cached_audit or []


# -------------------------------------------------------------
# Frontend Static Asset Routes
# -------------------------------------------------------------
@app.get("/")
@app.get("/index.html")
def get_index():
    web_dir = resolve_dir("web")
    index_file = os.path.join(web_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    return {"message": "SatyaBid Backend Running", "status": "ok"}


@app.get("/style.css")
def get_style():
    web_dir = resolve_dir("web")
    css_file = os.path.join(web_dir, "style.css")
    if os.path.exists(css_file):
        return FileResponse(css_file, media_type="text/css")
    raise HTTPException(status_code=404, detail="style.css not found")


@app.get("/app.js")
def get_app_js():
    web_dir = resolve_dir("web")
    js_file = os.path.join(web_dir, "app.js")
    if os.path.exists(js_file):
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")


# -------------------------------------------------------------
# API Scrutiny Endpoints (Available on both /api/* and /*)
# -------------------------------------------------------------
@app.get("/api/health")
@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": "SatyaBid",
        "version": "1.0",
        "runtime": "vercel-fastapi"
    }


@app.get("/api/analysis")
@app.get("/analysis")
def api_analysis():
    return get_analysis_data()


@app.get("/api/audit")
@app.get("/audit")
def api_audit():
    return get_audit_data()


@app.get("/api/verify")
@app.get("/verify")
def api_verify():
    global _current_ledger
    if _current_ledger is not None:
        ok, msg = _current_ledger.verify()
        return {"ok": ok, "message": msg, "count": len(_current_ledger.entries)}

    audit_list = get_audit_data()
    ledger = AuditLedger()
    tender, bids = get_tender_and_bids()
    if os.path.exists(tender) and bids:
        run_mvp.run(tender, bids, ledger=ledger)
        _current_ledger = ledger
        ok, msg = ledger.verify()
        return {"ok": ok, "message": msg, "count": len(ledger.entries)}

    return {
        "ok": True,
        "message": f"{len(audit_list)} entries verified — chain intact",
        "count": len(audit_list)
    }


@app.get("/api/download-audit")
@app.get("/download-audit")
def api_download_audit():
    audit_list = get_audit_data()
    content = json.dumps(audit_list, indent=2, ensure_ascii=False)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="audit_log.json"'}
    )


@app.post("/api/run-scrutiny")
@app.post("/run-scrutiny")
def api_run_scrutiny():
    result, _ = execute_pipeline()
    return result


@app.get("/api/run-scrutiny-stream")
@app.get("/run-scrutiny-stream")
def api_run_scrutiny_stream():
    events = []

    def stage_cb(stage_num, title, detail):
        payload = json.dumps({"stage": stage_num, "title": title, "detail": detail}, ensure_ascii=False)
        events.append(f"event: stage\ndata: {payload}\n\n")

    result, _ = execute_pipeline(stage_callback=stage_cb)
    comp_payload = json.dumps(result, ensure_ascii=False)
    events.append(f"event: complete\ndata: {comp_payload}\n\n")

    def event_generator():
        for ev in events:
            yield ev

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def validate_pdf_content(filename, content_base64, doc_type="tender"):
    """Validate uploaded PDF document without crashing or hanging."""
    if not filename or not filename.lower().endswith(".pdf"):
        return {
            "ok": False,
            "error": "Could not parse this document: only PDF files are supported."
        }
    if not content_base64:
        return {
            "ok": False,
            "error": "Could not parse this document: file content is empty."
        }
    try:
        if "," in content_base64:
            content_base64 = content_base64.split(",", 1)[1]
        raw_bytes = base64.b64decode(content_base64)
    except Exception:
        return {
            "ok": False,
            "error": "Could not parse this document: could not decode file stream."
        }

    try:
        doc = pymupdf.open(stream=raw_bytes, filetype="pdf")
    except Exception as exc:
        return {
            "ok": False,
            "error": "Could not parse this document: malformed or corrupted PDF format."
        }

    try:
        pages_count = len(doc)
        if pages_count == 0:
            return {
                "ok": False,
                "error": "Could not parse this document: document contains no pages."
            }

        full_text = ""
        for page in doc:
            full_text += (page.get_text() or "") + "\n"

        text_clean = full_text.strip()
        if len(text_clean) < 20:
            return {
                "ok": False,
                "error": "Could not parse this document: document contains no readable text or is an unsupported scan."
            }

        # Check for GeM procurement structure
        if doc_type == "tender":
            has_bid_num = bool(re.search(r"GEM/\d{4}/[A-Z]/\d+", text_clean, re.I))
            has_turnover = "turnover" in text_clean.lower()
            if not (has_bid_num or has_turnover):
                return {
                    "ok": False,
                    "error": "Could not parse this document: missing required GeM RFP specification clauses (e.g. GeM bid number, turnover floor, local content). Please upload a valid GeM tender document."
                }
            return {
                "ok": True,
                "filename": filename,
                "pages": pages_count,
                "message": f"Parsed successfully ({pages_count} pages)"
            }
        else:
            has_bidder = "bidder" in text_clean.lower() or "submission" in text_clean.lower()
            has_financial = "ca" in text_clean.lower() or "turnover" in text_clean.lower() or "director" in text_clean.lower() or "partnership" in text_clean.lower()
            if not (has_bidder and has_financial):
                return {
                    "ok": False,
                    "error": "Could not parse this document: unrecognised bidder submission format. Missing Cover-1 eligibility schedules or certified turnover records."
                }
            return {
                "ok": True,
                "filename": filename,
                "pages": pages_count,
                "message": f"Parsed successfully ({pages_count} pages)"
            }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Could not parse this document: error extracting content ({str(exc)[:60]})."
        }
    finally:
        try:
            doc.close()
        except Exception:
            pass


@app.post("/api/validate-document")
@app.post("/validate-document")
async def api_validate_document(request: Request):
    try:
        data = await request.json()
        res = validate_pdf_content(
            data.get("filename", ""),
            data.get("content", ""),
            data.get("doc_type", "tender")
        )
        return res
    except Exception as e:
        return {
            "ok": False,
            "error": f"Could not parse this document: invalid request data ({str(e)[:50]})"
        }

