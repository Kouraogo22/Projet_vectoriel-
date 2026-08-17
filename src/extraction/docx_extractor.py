from pathlib import Path
from docx import Document

def extract_text_from_docx(file_path: str | Path) -> str:
    """Extrait les paragraphes non vides d'un document Word."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    if path.suffix.lower() != ".docx":
        raise ValueError("Le fichier doit être au format DOCX.")
    try:
        paragraphs = [p.text.strip() for p in Document(path).paragraphs if p.text.strip()]
    except Exception as exc:
        raise ValueError(f"Impossible de lire le document Word « {path.name} ».") from exc
    if not paragraphs:
        raise ValueError("Aucun texte n'a été extrait du document Word.")
    return "\n".join(paragraphs)
