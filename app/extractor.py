from io import BytesIO
from pathlib import Path
import shutil


def _read_source(source: str | bytes | BytesIO) -> tuple[bytes, Path | None]:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source), None
    if isinstance(source, BytesIO):
        return source.getvalue(), None
    path = Path(source)
    return (path.read_bytes() if path.exists() else b""), path


def _ocr_image(image_source: str | bytes | BytesIO) -> str:
    try:
        import pytesseract
        from PIL import Image

        if shutil.which(pytesseract.pytesseract.tesseract_cmd) is None:
            standard_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
            if standard_path.exists():
                pytesseract.pytesseract.tesseract_cmd = str(standard_path)

        image_bytes, path = _read_source(image_source)
        image_input = BytesIO(image_bytes) if image_bytes else str(path)
        with Image.open(image_input) as image:
            return pytesseract.image_to_string(image).strip()
    except Exception as error:
        raise ValueError(
            "OCR could not read this image. Install pytesseract and the Tesseract OCR engine."
        ) from error


def extract_image_text(image_source: str | bytes | BytesIO) -> str:
    """Extract text from an uploaded image with Tesseract OCR."""
    image_bytes, _ = _read_source(image_source)
    if not image_bytes:
        raise ValueError("The uploaded image is empty.")
    text = _ocr_image(image_bytes)
    if not text:
        raise ValueError("OCR did not find readable text in this image.")
    return text


def extract_text(pdf_source: str | bytes | BytesIO) -> str:
    """Extract PDF text directly from bytes or a path without creating upload files."""
    pdf_bytes, path = _read_source(pdf_source)

    if not pdf_bytes:
        raise ValueError("The uploaded PDF is empty.")

    errors = []
    try:
        import fitz

        source = pdf_bytes if pdf_bytes else str(path)
        with fitz.open(stream=source, filetype="pdf" if pdf_bytes else None) as document:
            page_texts = [page.get_text().strip() for page in document]
            missing_pages = [index for index, text in enumerate(page_texts) if not text]
            if missing_pages:
                for index in missing_pages:
                    pixmap = document[index].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    page_texts[index] = _ocr_image(pixmap.tobytes("png"))
            text = "\n".join(page_texts).strip()
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

    try:
        import fitz

        ocr_text = []
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            for page in document:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                ocr_text.append(_ocr_image(pixmap.tobytes("png")))
        text = "\n".join(ocr_text).strip()
        if text:
            return text
    except Exception as error:
        errors.append(f"OCR: {error}")

    detail = "; ".join(errors)
    raise ValueError("No readable text was found in this PDF or image." + (f" ({detail})" if detail else ""))