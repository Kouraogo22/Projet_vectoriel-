from pathlib import Path
from pypdf import PdfReader

def extract_text_from_pdf(file_path: str | Path) -> str:
    """Extrait le texte sélectionnable de toutes les pages d'un PDF."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError("Le fichier doit être au format PDF.")
    try:
        text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    except Exception as exc:
        raise ValueError(f"Impossible de lire le PDF « {path.name} ».") from exc
    if not text.strip():
        raise ValueError("Aucun texte extrait : un OCR est peut-être nécessaire.")
    return text
