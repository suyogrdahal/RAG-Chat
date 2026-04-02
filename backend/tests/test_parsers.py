from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.ingestion.parsers import ParseError, parse_pdf, parse_txt


def _make_pdf_bytes_with_text(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)

    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref}),
        }
    )

    content_stream = DecodedStreamObject()
    safe_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content_stream.set_data(f"BT /F1 12 Tf 36 150 Td ({safe_text}) Tj ET".encode("utf-8"))
    content_ref = writer._add_object(content_stream)
    page[NameObject("/Contents")] = content_ref

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_parse_txt_basic() -> None:
    raw = b"hello   world\r\n\r\nthis\tis   a   test\r\nnext line"
    result = parse_txt(raw)
    assert result.page_count is None
    assert result.text == "hello world\n\nthis is a test next line"


def test_parse_pdf_basic() -> None:
    raw_pdf = _make_pdf_bytes_with_text("Hello PDF")
    result = parse_pdf(raw_pdf)
    assert result.page_count == 1
    assert "Hello PDF" in result.text


def test_parse_pdf_invalid_raises() -> None:
    with pytest.raises(ParseError):
        parse_pdf(b"not-a-real-pdf")
