"""Ingestion layer: multi-modal document intake.

Digital PDFs are read with PyMuPDF. Pages that come back nearly empty
(scanned images) are routed to an OCR adapter. The production adapter is
PaddleOCR; the bundled fallback tries Tesseract when installed. The adapter
interface is deliberately narrow so the OCR backend can be swapped without
touching the pipeline.
"""
import pymupdf


class OCRAdapter:
    """Narrow seam: given page pixmap bytes, return extracted text."""

    name = "base"

    def extract(self, pixmap_bytes):
        raise NotImplementedError


class TesseractAdapter(OCRAdapter):
    name = "tesseract"

    def extract(self, pixmap_bytes):
        try:
            import pytesseract
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(pixmap_bytes))
            return pytesseract.image_to_string(img)
        except Exception:
            return ""


def extract_metadata(pdf_path):
    """Document metadata: author/creator/producer/timestamps.

    Used by the fraud-analytics layer (e.g. two bids authored on the same
    machine is a collusion signal).
    """
    with pymupdf.open(pdf_path) as doc:
        meta = doc.metadata or {}
    return {
        "author": (meta.get("author") or "").strip(),
        "creator": (meta.get("creator") or "").strip(),
        "producer": (meta.get("producer") or "").strip(),
        "creationDate": (meta.get("creationDate") or "").strip(),
    }


def extract_pages(pdf_path, ocr_adapter=None, min_chars=50):
    """Return [(page_no, text, source)] where source is 'pdf-text' or ocr name."""
    ocr_adapter = ocr_adapter or TesseractAdapter()
    pages = []
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            source = "pdf-text"
            if len(text.strip()) < min_chars:
                pix = page.get_pixmap(dpi=200)
                ocr_text = ocr_adapter.extract(pix.tobytes("png"))
                if len(ocr_text.strip()) > len(text.strip()):
                    text, source = ocr_text, f"ocr:{ocr_adapter.name}"
            pages.append((i + 1, text, source))
    return pages


def full_text(pages):
    return "\n".join(t for _, t, _ in pages)
