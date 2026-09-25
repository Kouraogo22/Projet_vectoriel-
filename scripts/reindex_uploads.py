"""Réindexe de façon idempotente les documents conservés dans data/uploads."""
from __future__ import annotations

from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings
from src.database import VectorStore
from src.embeddings import EmbeddingEncoder
from src.search import SemanticRetriever

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
UUID_TEXT_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.txt$",
    re.IGNORECASE,
)
STORED_FILE_PREFIX = re.compile(r"^[0-9a-f]{32}_(.+)$", re.IGNORECASE)


def is_reconstructed_text(path: Path) -> bool:
    if path.suffix.lower() != ".txt":
        return False
    stem = path.stem
    return any(stem[:index] == stem[index + 1:] for index, char in enumerate(stem) if char == "_")


def legacy_id_for(path: Path) -> str | None:
    if path.suffix.lower() != ".txt":
        return None
    stem = path.stem
    return next(
        (stem[:index] for index, char in enumerate(stem) if char == "_" and stem[:index] == stem[index + 1:]),
        None,
    )


def load_legacy_metadata(store: VectorStore) -> tuple[dict[str, dict], dict[str, dict]]:
    """Récupère les métadonnées de l'ancien index lorsqu'il est encore disponible."""
    collection = "fquad_retrieval"
    if not store.client.collection_exists(collection):
        return {}, {}
    by_id = {}
    by_title = {}
    offset = None
    while True:
        records, next_offset = store.client.scroll(
            collection_name=collection,
            offset=offset,
            limit=256,
            with_payload=True,
            with_vectors=False,
        )
        for record in records:
            payload = record.payload or {}
            if document_id := payload.get("document_id"):
                by_id.setdefault(str(document_id), payload)
            if title := payload.get("title"):
                by_title.setdefault(str(title).casefold(), payload)
        if next_offset is None:
            return by_id, by_title
        offset = next_offset


def metadata_for(
    path: Path,
    legacy_by_id: dict[str, dict] | None = None,
    legacy_by_title: dict[str, dict] | None = None,
) -> tuple[str, str, str, str]:
    """Déduit les anciennes catégories lorsque le manifeste Qdrant n'existe plus."""
    name = path.name.casefold()
    stored_match = STORED_FILE_PREFIX.match(path.name)
    original_filename = stored_match.group(1) if stored_match else path.name
    title = Path(original_filename).stem
    storage_kind = "reconstructed" if is_reconstructed_text(path) else "original"
    legacy = (legacy_by_id or {}).get(legacy_id_for(path) or "")
    legacy = legacy or (legacy_by_title or {}).get(title.casefold())
    if legacy:
        title = str(legacy.get("title") or title)
        category = str(legacy.get("category") or "Autres documents")
    elif any(marker in name for marker in ("amf_", "bofip_", "jade_", "kali_")):
        category = "Droit et réglementation"
    elif "ag_news" in name:
        category = "Actualités internationales"
    elif "frenchqa_actualite" in name:
        category = "Actualités"
    elif any(marker in name for marker in ("chp1_", "soutenance")):
        category = "Éducation"
    elif UUID_TEXT_PATTERN.match(path.name):
        category = "Autres documents"
    else:
        category = "FQuADRetrieval"
    return title, category, storage_kind, original_filename


def main() -> None:
    files = sorted(path for path in UPLOAD_DIR.iterdir() if path.suffix.lower() in SUPPORTED_SUFFIXES)
    if not files:
        raise SystemExit("Aucun document compatible n'est présent dans data/uploads.")

    store = VectorStore(settings.qdrant_url, settings.qdrant_api_key, settings.collection_name)
    retriever = SemanticRetriever(store, EmbeddingEncoder(settings.embedding_model))
    legacy_by_id, legacy_by_title = load_legacy_metadata(store)
    indexed = failed = 0
    for position, path in enumerate(files, 1):
        title, category, storage_kind, original_filename = metadata_for(
            path, legacy_by_id, legacy_by_title
        )
        try:
            retriever.index_document(
                path,
                title=title,
                category=category,
                source=path,
                original_filename=original_filename,
                storage_kind=storage_kind,
            )
            indexed += 1
        except (OSError, ValueError) as exc:
            failed += 1
            print(f"[{position}/{len(files)}] Ignoré : {path.name} ({exc})")
        if position % 25 == 0 or position == len(files):
            print(f"Progression : {position}/{len(files)}")

    print(f"Réindexation terminée : {indexed} document(s), {failed} échec(s).")


if __name__ == "__main__":
    main()
