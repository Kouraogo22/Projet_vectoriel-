from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from src.indexing.options import IndexOptions
from src.database import VectorStore
from src.embeddings import EmbeddingEncoder
from src.extraction import extract_text
from src.preprocessing import clean_text, split_into_chunks

class SemanticRetriever:
    def __init__(self, store: VectorStore, encoder: EmbeddingEncoder, options: IndexOptions | None = None) -> None:
        self.store, self.encoder = store, encoder
        self.options = options or IndexOptions()

    def index_document(
        self,
        file_path: str | Path,
        title: str | None = None,
        category: str | None = None,
        source: str | Path | None = None,
        original_filename: str | None = None,
        storage_kind: str = "original",
    ) -> tuple[str, int]:
        path = Path(file_path)
        text = extract_text(path)
        if self.options.clean_text:
            text = clean_text(text)
        if not text:
            raise ValueError("Le document ne contient aucun texte indexable.")
        stored_source = Path(source) if source is not None else path
        document_id = str(uuid5(NAMESPACE_URL, str(stored_source.resolve())))
        chunks = split_into_chunks(text, self.options.chunk_size, self.options.chunk_overlap)
        language = self._detect_language(text)
        passages = [{"passage_id": f"{document_id}_chunk_{index:04d}", "document_id": document_id, "chunk_index": index, "text": chunk, "title": title or path.stem, "category": category, "source": str(stored_source), "original_filename": original_filename or stored_source.name, "storage_kind": storage_kind, "language": language, "chunk_overlap": self.options.chunk_overlap} for index, chunk in enumerate(chunks)]
        vectors = self.encoder.encode([p["text"] for p in passages], batch_size=self.options.batch_size)
        self.store.ensure_collection(self.encoder.dimension)
        self.store.upsert_passages(passages, vectors)
        return document_id, len(passages)

    @staticmethod
    def _detect_language(text: str) -> str:
        """Détermine simplement si le contenu est plutôt français ou anglais."""
        words = {word.strip(".,;:!?()[]{}\"'«»").casefold() for word in text.split()[:2000]}
        french_markers = {"le", "la", "les", "des", "une", "dans", "avec", "pour", "est", "sont"}
        english_markers = {"the", "and", "of", "to", "in", "with", "for", "is", "are", "from"}
        return "en" if len(words & english_markers) > len(words & french_markers) else "fr"

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
