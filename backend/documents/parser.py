import io

from docx import Document as DocxDocument
from pptx import Presentation
from pypdf import PdfReader

SUPPORTED = {"pdf", "docx", "pptx"}


def parse_document(data: bytes, file_type: str) -> list[tuple[int, str]]:
    """Return (page_number, text) pairs. DOCX is one page; PPTX uses slide numbers."""
    if file_type == "pdf":
        reader = PdfReader(io.BytesIO(data))
        return [(i + 1, p.extract_text() or "") for i, p in enumerate(reader.pages)]
    if file_type == "docx":
        doc = DocxDocument(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text.strip() for c in row.cells))
        return [(1, "\n".join(parts))]
    if file_type == "pptx":
        prs = Presentation(io.BytesIO(data))
        pages: list[tuple[int, str]] = []
        for i, slide in enumerate(prs.slides, start=1):
            texts = [
                shape.text_frame.text
                for shape in slide.shapes
                if shape.has_text_frame and shape.text_frame.text.strip()
            ]
            pages.append((i, "\n".join(texts)))
        return pages
    raise ValueError(f"Unsupported file type: {file_type}")
