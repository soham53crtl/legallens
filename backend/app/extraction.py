"""Extract raw text from uploaded PDF, DOCX, or TXT files."""
import io
from pypdf import PdfReader
import docx


class ExtractionError(Exception):
    pass


def extract_text(filename: str, content: bytes) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "txt":
        for enc in ("utf-8", "latin-1"):
            try:
                return content.decode(enc)
            except UnicodeDecodeError:
                continue
        raise ExtractionError("Could not decode text file.")

    if ext == "pdf":
        try:
            reader = PdfReader(io.BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages).strip()
        except Exception as e:
            raise ExtractionError(f"Could not read PDF: {e}")
        if not text:
            raise ExtractionError(
                "No extractable text found in this PDF (it may be a scanned image)."
            )
        return text

    if ext == "docx":
        try:
            document = docx.Document(io.BytesIO(content))
            paragraphs = [p.text for p in document.paragraphs]
            text = "\n".join(paragraphs).strip()
        except Exception as e:
            raise ExtractionError(f"Could not read DOCX: {e}")
        if not text:
            raise ExtractionError("No extractable text found in this document.")
        return text

    raise ExtractionError(f"Unsupported file type: .{ext}. Use PDF, DOCX, or TXT.")
