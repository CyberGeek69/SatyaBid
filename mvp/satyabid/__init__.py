"""SatyaBid engine: intelligent bid scrutiny & cross-bidder cartel detection."""
from .ingest import extract_pages, extract_metadata, OCRAdapter, TesseractAdapter
from .blueprint import extract_blueprint
from .checks import run_checks
from .collusion import analyse_collusion
from .audit import AuditLedger
from .evidence import build_verdict
from .priceforensics import screen_prices
from .docforensics import analyse_documents, doc_pair_markers
from .mlforensics import (paraphrase_screen, fuzzy_entity_screen,
                          entity_similarity, ml_pair_markers)
from .tenderintegrity import seal_tender, diff_requirements, scan_price_hints

__all__ = ["extract_pages", "extract_metadata", "OCRAdapter", "TesseractAdapter",
           "extract_blueprint", "run_checks", "analyse_collusion",
           "AuditLedger", "build_verdict", "screen_prices",
           "analyse_documents", "doc_pair_markers", "seal_tender",
           "diff_requirements", "scan_price_hints",
           "paraphrase_screen", "fuzzy_entity_screen", "entity_similarity",
           "ml_pair_markers"]
