"""SatyaBid engine: intelligent bid scrutiny & cross-bidder cartel detection."""
from .ingest import extract_pages, extract_metadata, OCRAdapter, TesseractAdapter
from .blueprint import extract_blueprint
from .checks import run_checks
from .collusion import analyse_collusion
from .audit import AuditLedger
from .evidence import build_verdict

__all__ = ["extract_pages", "extract_metadata", "OCRAdapter", "TesseractAdapter",
           "extract_blueprint", "run_checks", "analyse_collusion",
           "AuditLedger", "build_verdict"]
