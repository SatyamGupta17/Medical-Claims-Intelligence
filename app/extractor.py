from io import BytesIO
from pathlib import Path


def extract_text(pdf_source: str | bytes | BytesIO) -> str:
    """Extract PDF text directly from bytes or a path without creating upload files."""
    if isinstance(pdf_source, (bytes, bytearray)):
        pdf_bytes = bytes(pdf_source)
        path = None
    elif isinstance(pdf_source, BytesIO):
        pdf_bytes = pdf_source.getvalue()
        path = None
    else:
        path = Path(pdf_source)
        pdf_bytes = path.read_bytes() if path.exists() else b""

    if not pdf_bytes:
        raise ValueError("The uploaded PDF is empty.")

    errors = []
    try:
        import fitz

        source = pdf_bytes if pdf_bytes else str(path)
        with fitz.open(stream=source, filetype="pdf" if pdf_bytes else None) as document:
            text = "\n".join(page.get_text() for page in document).strip()
        if text:
            return text
    except Exception as error:
        errors.append(f"PyMuPDF: {error}")

    try:
        from pypdf import PdfReader

        reader_source = BytesIO(pdf_bytes) if pdf_bytes else str(path)
        text = "\n".join(page.extract_text() or "" for page in PdfReader(reader_source).pages).strip()
        if text:
            return text
    except Exception as error:
        errors.append(f"pypdf: {error}")

    detail = "; ".join(errors)
    raise ValueError("No readable text was found in this PDF. Upload a text-based PDF or run OCR before upload." + (f" ({detail})" if detail else ""))