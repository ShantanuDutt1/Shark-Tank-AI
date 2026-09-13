"""Tests for utils.pdf_extraction.extract_pdf_text."""

from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

from utils.pdf_extraction import PdfExtractionError, extract_pdf_text


def _pdf_with_text(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, text)
    c.save()
    return buf.getvalue()


def _blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_extracts_text_from_a_real_pdf():
    pdf_bytes = _pdf_with_text("We sell eco-friendly packaging to grocery chains.")
    text = extract_pdf_text(pdf_bytes)
    assert "eco-friendly packaging" in text


def test_blank_pdf_raises_extraction_error():
    with pytest.raises(PdfExtractionError):
        extract_pdf_text(_blank_pdf())


def test_garbage_bytes_raise_extraction_error():
    with pytest.raises(PdfExtractionError):
        extract_pdf_text(b"this is not a pdf file")


def test_empty_bytes_raise_extraction_error():
    with pytest.raises(PdfExtractionError):
        extract_pdf_text(b"")
