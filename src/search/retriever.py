from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from src.config import settings
from src.database import VectorStore
from src.embeddings import EmbeddingEncoder
from src.extraction import extract_text
from src.preprocessing import clean_text, split_into_chunks

class SemanticRetriever:
    def __init__(self, store: VectorStore, encoder: EmbeddingEncoder) -> None:
        self.store, self.encoder = store, encoder

    def index_document(
        self,
        file_path: str | Path,
        title: str | None = None,
        category: str | None = None,
        source: str | Path | None = None,
        original_filename: str | None = None,
    ) -> tuple[str, int]:
        path = Path(file_path)
        text = clean_text(extract_text(path))
        if not text:
            raise ValueError("Le document ne contient aucun texte indexable.")
        stored_source = Path(source) if source is not None else path
        document_id = str(uuid5(NAMESPACE_URL, str(stored_source.resolve())))
        chunks = split_into_chunks(text, settings.chunk_size, settings.chunk_overlap)
        passages = [{"passage_id": f"{document_id}_chunk_{index:04d}", "document_id": document_id, "chunk_index": index, "text": chunk, "title": title or path.stem, "category": category, "source": str(stored_source), "original_filename": original_filename or stored_source.name, "language": "fr"} for index, chunk in enumerate(chunks)]
        vectors = self.encoder.encode([p["text"] for p in passages])
        self.store.ensure_collection(self.encoder.dimension)
        self.store.upsert_passages(passages, vectors)
        return document_id, len(passages)

    def search(
        self,
        query: str,
        limit: int = 5,
        category: str | None = None,
        categories: list[str] | None = None,
        document_ids: list[str] | None = None,
    ) -> list[dict]:
        if not query.strip():
            raise ValueError("La requête ne peut pas être vide.")
        self.store.ensure_collection(self.encoder.dimension)
        selected_categories = list(categories or [])
        if category and category not in selected_categories:
            selected_categories.append(category)
        return [
            {"score": result.score, **(result.payload or {})}
            for result in self.store.search(
                self.encoder.encode(query),
                limit,
                categories=selected_categories or None,
                document_ids=document_ids,
            )
        ]
