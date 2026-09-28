"""Tamper-evident audit ledger: every scrutiny event is hash-chained.

Each entry commits to the previous entry's hash (SHA-256), so any later
modification of the log breaks the chain. verify() recomputes everything.
"""
import hashlib
import json
from datetime import datetime, timezone


def _h(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


class AuditLedger:
    def __init__(self):
        self.entries = []

    def append(self, event, payload):
        prev = self.entries[-1]["entry_hash"] if self.entries else "GENESIS"
        entry = {
            "seq": len(self.entries) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": event,
            "payload": payload,
            "payload_hash": _h(payload),
            "prev_hash": prev,
        }
        entry["entry_hash"] = _h({k: entry[k] for k in
                                  ("seq", "timestamp", "event",
                                   "payload_hash", "prev_hash")})
        self.entries.append(entry)
        return entry

    def verify(self):
        prev = "GENESIS"
        for e in self.entries:
            if e["prev_hash"] != prev:
                return False, f"chain broken at seq {e['seq']}"
            if e["payload_hash"] != _h(e["payload"]):
                return False, f"payload tampered at seq {e['seq']}"
            if e["entry_hash"] != _h({k: e[k] for k in
                                      ("seq", "timestamp", "event",
                                       "payload_hash", "prev_hash")}):
                return False, f"entry hash mismatch at seq {e['seq']}"
            prev = e["entry_hash"]
        return True, f"{len(self.entries)} entries verified — chain intact"

    def to_list(self):
        return self.entries
