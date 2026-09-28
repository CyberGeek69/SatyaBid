#!/usr/bin/env python3
"""SatyaBid Web Application Server.

Serves the SatyaBid UI (spec §4 S1-S7) and API endpoints.
Runs using Python standard library with zero extra dependencies.

Usage:
    python serve.py [--port 8000]
"""

import argparse
import glob
import json
import mimetypes
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from satyabid import AuditLedger
import run_mvp

WEB_DIR = os.path.join(BASE_DIR, "web")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
DATA_DIR = os.path.join(BASE_DIR, "data")


def get_or_create_analysis():
    analysis_file = os.path.join(OUTPUTS_DIR, "analysis.json")
    audit_file = os.path.join(OUTPUTS_DIR, "audit_log.json")

    if os.path.exists(analysis_file) and os.path.exists(audit_file):
        with open(analysis_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        with open(audit_file, "r", encoding="utf-8") as f:
            audit = json.load(f)
        data["ledger_count"] = len(audit)
        return data

    # Run pipeline if outputs don't exist yet
    tender = os.path.join(DATA_DIR, "tender.pdf")
    bids = sorted(glob.glob(os.path.join(DATA_DIR, "bids", "*.pdf")))
    if not os.path.exists(tender) or not bids:
        return None

    ledger = AuditLedger()
    result = run_mvp.run(tender, bids, ledger=ledger)
    result.pop("ledger", None)
    led_list = ledger.to_list()
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    with open(analysis_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(led_list, f, indent=2, ensure_ascii=False)

    result["ledger_count"] = len(led_list)
    return result


class SatyaBidHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        # API endpoints
        if self.path == "/api/analysis":
            self.send_json_response(get_or_create_analysis() or {})
            return
        elif self.path == "/api/audit":
            audit_file = os.path.join(OUTPUTS_DIR, "audit_log.json")
            if os.path.exists(audit_file):
                with open(audit_file, "r", encoding="utf-8") as f:
                    self.send_json_response(json.load(f))
            else:
                self.send_json_response([])
            return
        elif self.path == "/api/verify":
            audit_file = os.path.join(OUTPUTS_DIR, "audit_log.json")
            if os.path.exists(audit_file):
                with open(audit_file, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                ledger = AuditLedger()
                ledger.entries = entries
                ok, msg = ledger.verify()
                self.send_json_response({"ok": ok, "message": msg, "count": len(entries)})
            else:
                self.send_json_response({"ok": False, "message": "No ledger found", "count": 0})
            return
        elif self.path == "/api/download-audit":
            audit_file = os.path.join(OUTPUTS_DIR, "audit_log.json")
            if os.path.exists(audit_file):
                with open(audit_file, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="audit_log.json"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            else:
                self.send_error(404, "audit_log.json not found")
                return
        elif self.path == "/api/run-scrutiny-stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            def send_event(event_name, data):
                msg = f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")
                self.wfile.write(msg)
                self.wfile.flush()

            tender = os.path.join(DATA_DIR, "tender.pdf")
            bids = sorted(glob.glob(os.path.join(DATA_DIR, "bids", "*.pdf")))
            ledger = AuditLedger()

            def stage_cb(stage_num, title, detail):
                send_event("stage", {"stage": stage_num, "title": title, "detail": detail})

            result = run_mvp.run(tender, bids, ledger=ledger, stage_callback=stage_cb)
            result.pop("ledger", None)
            led_list = ledger.to_list()
            os.makedirs(OUTPUTS_DIR, exist_ok=True)
            with open(os.path.join(OUTPUTS_DIR, "analysis.json"), "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            with open(os.path.join(OUTPUTS_DIR, "audit_log.json"), "w", encoding="utf-8") as f:
                json.dump(led_list, f, indent=2, ensure_ascii=False)
            result["ledger_count"] = len(led_list)
            send_event("complete", result)
            return
        elif self.path == "/api/health":
            self.send_json_response({"status": "ok", "app": "SatyaBid", "version": "1.0"})
            return

        # Static web assets
        if self.path == "/" or self.path == "":
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/run-scrutiny":
            tender = os.path.join(DATA_DIR, "tender.pdf")
            bids = sorted(glob.glob(os.path.join(DATA_DIR, "bids", "*.pdf")))
            ledger = AuditLedger()
            result = run_mvp.run(tender, bids, ledger=ledger)
            result.pop("ledger", None)
            led_list = ledger.to_list()
            os.makedirs(OUTPUTS_DIR, exist_ok=True)
            with open(os.path.join(OUTPUTS_DIR, "analysis.json"), "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            with open(os.path.join(OUTPUTS_DIR, "audit_log.json"), "w", encoding="utf-8") as f:
                json.dump(led_list, f, indent=2, ensure_ascii=False)
            result["ledger_count"] = len(led_list)
            self.send_json_response(result)
            return

        self.send_error(404, "Endpoint not found")

    def send_json_response(self, data, status_code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Concise logging
        sys.stderr.write(f"[SatyaBid] {args[0]} - {args[1]}\n")


def find_free_port(start_port=8000, max_attempts=20):
    import socket
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


def main():
    parser = argparse.ArgumentParser(description="SatyaBid UI Web Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default 127.0.0.1)")
    parser.add_argument("--open", action="store_true", help="Automatically open browser")
    args = parser.parse_args()

    port = args.port
    server_address = (args.host, port)
    try:
        httpd = ThreadingHTTPServer(server_address, SatyaBidHTTPHandler)
    except OSError:
        port = find_free_port(args.port + 1)
        server_address = (args.host, port)
        httpd = ThreadingHTTPServer(server_address, SatyaBidHTTPHandler)

    app_url = f"http://{server_address[0]}:{port}/"
    print("=" * 64)
    print(f"  SatyaBid — Intelligent Bid Scrutiny Platform")
    print(f"  Running at: {app_url}")
    print("=" * 64)
    print("Press Ctrl+C to stop.")

    if args.open:
        import webbrowser
        webbrowser.open(app_url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    main()
