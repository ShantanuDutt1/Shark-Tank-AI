"""
Minimal PDF text extraction for Shark Tank AI.

Release 0.6 spec Part P: a submitted PDF's actual text must enter the
validation/research/Shark pipeline, not just its filename. This is
deliberately the smallest maintainable solution -- plain text
extraction via `pypdf`, no OCR, no layout/table reconstruction, no
image extraction. If a PDF is scanned/image-only or otherwise yields
no extractable text, that is surfaced as an explicit, honest failure
(`PdfExtractionError`), never silently treated as an empty-but-valid
proposal.
"""

from __future__ import annotations

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PdfExtractionError(Exception):
    """Raised when a PDF's text cannot be extracted (corrupt file,
    encrypted with no accessible text layer, or a scanned/image-only
    document with no embedded text)."""


def extract_pdf_text(file_bytes: bytes) -> str:
    """Extract and return the concatenated plain text of every page in
    a PDF given as raw bytes.

    Raises `PdfExtractionError` if the file can't be read as a PDF, or
    if it contains no extractable text at all (e.g. a scanned
    document with no text layer) -- callers should treat this the
    same as "no proposal content," not silently proceed with an empty
    string as if the founder had submitted nothing on purpose.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except (PdfReadError, ValueError) as exc:
        raise PdfExtractionError(f"Could not read the PDF file: {exc}") from exc

    try:
        pages_text = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        # internal parsing errors for malformed PDFs; all of them mean
        # the same thing to a caller here: extraction failed. This is
        # the one place in the codebase where such a broad catch is
        # appropriate, since the alternative is silently returning
        # empty text for a corrupt file rather than surfacing the
        # failure explicitly (spec Part Q: "fail in a controlled
        # manner").
        raise PdfExtractionError(f"Could not extract text from the PDF: {exc}") from exc

    text = "\n\n".join(p.strip() for p in pages_text if p.strip())
    if not text.strip():
        raise PdfExtractionError(
            "The PDF contained no extractable text (it may be a scanned "
            "image with no text layer)."
        )
    return text
