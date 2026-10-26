"""In-memory PDF/DOCX extraction. Never writes uploaded files to disk."""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from docx.table import Table
from pypdf import PdfReader

from .analysis import ValidationError, validate_text

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_EXPANDED_BYTES = 25 * 1024 * 1024
MAX_PDF_PAGES = 50


@dataclass(frozen=True)
class ParsedResume:
    text: str
    file_type: str
    size_bytes: int
    pages: int | None


def extract_resume(filename: str, content: bytes) -> ParsedResume:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise ValidationError("Unsupported file. Upload a PDF or DOCX résumé.")
    if not content:
        raise ValidationError("The uploaded file is empty. Choose another file.")
    if len(content) > MAX_FILE_BYTES:
        raise ValidationError("File exceeds 5 MB. Please upload a smaller document.")
    pages = None
    try:
        if suffix == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise ValidationError("This file is not a valid PDF. Export it again as PDF.")
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise ValidationError("Password-protected PDFs are not supported. Upload an unlocked copy.")
            pages = len(reader.pages)
            if pages > MAX_PDF_PAGES:
                raise ValidationError("PDF exceeds 50 pages. Upload a shorter résumé.")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            with ZipFile(BytesIO(content)) as archive:
                if sum(item.file_size for item in archive.infolist()) > MAX_EXPANDED_BYTES:
                    raise ValidationError("DOCX expands beyond the safe size limit. Export a simpler document.")
                if "word/document.xml" not in archive.namelist():
                    raise ValidationError("This file is not a valid Word DOCX document.")
            document = Document(BytesIO(content))
            parts = []
            for block in document.iter_inner_content():
                if isinstance(block, Table):
                    parts.extend(" | ".join(cell.text for cell in row.cells) for row in block.rows)
                else:
                    parts.append(block.text)
            text = "\n".join(parts)
    except ValidationError:
        raise
    except Exception as exc:
        # Do not echo parser diagnostics or document contents into the UI.
        raise ValidationError("Could not read this document. It may be damaged or mislabeled. Export a fresh PDF or DOCX.") from exc
    if not text.strip():
        raise ValidationError("No readable text found. Scanned/image-only PDFs need OCR first; this app does not include OCR.")
    return ParsedResume(validate_text(text, "Résumé text"), suffix[1:].upper(), len(content), pages)
