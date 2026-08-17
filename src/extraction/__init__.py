"""Extraction de texte à partir des documents pris en charge."""
from pathlib import Path
from .docx_extractor import extract_text_from_docx
from .pdf_extractor import extract_text_from_pdf

def extract_text(file_path: str | Path) -> str:
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(path)
    if path.suffix.lower() == ".docx":
        return extract_text_from_docx(path)
    if path.suffix.lower() in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    raise ValueError("Format non pris en charge. Utilisez PDF, DOCX, TXT ou MD.")

__all__ = ["extract_text", "extract_text_from_docx", "extract_text_from_pdf"]
