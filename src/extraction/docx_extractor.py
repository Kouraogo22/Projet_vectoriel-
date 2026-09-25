from pathlib import Path
from docx import Document
from docx.document import Document as DocumentObject
from docx.table import Table
from docx.text.paragraph import Paragraph


def _iter_blocks(document: DocumentObject):
    """Parcourt les paragraphes et tableaux dans leur ordre d'apparition."""
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, document)
        elif child.tag.endswith("}tbl"):
            yield Table(child, document)

def extract_text_from_docx(file_path: str | Path) -> str:
    """Extrait les paragraphes non vides d'un document Word."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    if path.suffix.lower() != ".docx":
        raise ValueError("Le fichier doit être au format DOCX.")
    try:
        blocks = []
        for block in _iter_blocks(Document(path)):
            if isinstance(block, Paragraph):
                if text := block.text.strip():
                    blocks.append(text)
            else:
                for row in block.rows:
                    values = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    if any(values):
                        blocks.append(" | ".join(values))
    except Exception as exc:
        raise ValueError(f"Impossible de lire le document Word « {path.name} ».") from exc
    if not blocks:
        raise ValueError("Aucun texte n'a été extrait du document Word.")
    return "\n".join(blocks)
