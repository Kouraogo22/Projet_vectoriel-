"""Conserve dans data/uploads les fichiers correspondant aux documents déjà indexés.

Si le fichier source est absent (cas des anciens téléversements temporaires),
le script produit un fichier TXT à partir du contenu conservé dans Qdrant.
"""
from __future__ import annotations

from pathlib import Path
from shutil import copy2
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings
from src.database import VectorStore

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}


def destination_for(document_id: str, filename: str) -> Path:
    safe_name = Path(filename).name or f"{document_id}.txt"
    return UPLOAD_DIR / f"{document_id}_{safe_name}"


def main() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    store = VectorStore(settings.qdrant_url, settings.qdrant_api_key, settings.collection_name)
    copied = reconstructed = 0

    for summary in store.list_documents():
        document_id = summary["document_id"]
        document = store.get_document_content(document_id)
        if document is None:
            continue

        source = Path(str(document.get("source") or ""))
        original_name = document.get("original_filename") or source.name
        already_managed = source.is_file() and source.resolve().is_relative_to(UPLOAD_DIR.resolve())
        if already_managed:
            destination = source
            storage_kind = document.get("storage_kind") or (
                "reconstructed" if source.name.endswith(f"{document_id}.txt") else "original"
            )
            original_name = document.get("original_filename") or source.name
        elif source.is_file() and source.suffix.lower() in ALLOWED_SUFFIXES:
            destination = destination_for(document_id, original_name)
            if source.resolve() != destination.resolve():
                copy2(source, destination)
            copied += 1
            storage_kind = "original"
        else:
            destination = destination_for(document_id, f"{document_id}.txt")
            destination.write_text(document["content"], encoding="utf-8")
            original_name = destination.name
            reconstructed += 1
            storage_kind = "reconstructed"

        store.update_document_storage(document_id, str(destination), original_name, storage_kind)

    print(f"Migration terminée : {copied} fichier(s) original(aux) copié(s), {reconstructed} fichier(s) texte reconstitué(s).")


if __name__ == "__main__":
    main()
