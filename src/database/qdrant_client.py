from collections.abc import Sequence
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue, PointStruct
from .schema import vector_params

class VectorStore:
    def __init__(self, url: str, api_key: str | None, collection_name: str) -> None:
        self.client = QdrantClient(url=url, api_key=api_key)
        self.collection_name = collection_name

    def ensure_collection(self, dimension: int) -> None:
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(self.collection_name, vectors_config=vector_params(dimension))
            return
        configured_vectors = self.client.get_collection(self.collection_name).config.params.vectors
        configured_dimension = getattr(configured_vectors, "size", None)
        if configured_dimension is not None and int(configured_dimension) != dimension:
            raise ValueError(
                f"La collection utilise des vecteurs de dimension {configured_dimension}, "
                f"mais le modèle courant produit une dimension {dimension}."
            )

    def upsert_passages(self, passages: Sequence[dict], vectors: Sequence[Sequence[float]]) -> None:
        if len(passages) != len(vectors):
            raise ValueError("Chaque passage doit posséder un vecteur.")
        points = [PointStruct(id=str(uuid5(NAMESPACE_URL, p["passage_id"])), vector=list(v), payload=p) for p, v in zip(passages, vectors)]
        for start in range(0, len(points), 128):
            self.client.upsert(collection_name=self.collection_name, points=points[start:start + 128], wait=True)

    def search(
        self,
        query_vector: Sequence[float],
        limit: int,
        category: str | None = None,
        categories: Sequence[str] | None = None,
        document_ids: Sequence[str] | None = None,
    ):
        selected_categories = list(categories or [])
        if category and category not in selected_categories:
            selected_categories.append(category)
        conditions = []
        if selected_categories:
            conditions.append(FieldCondition(key="category", match=MatchAny(any=selected_categories)))
        if document_ids:
            conditions.append(FieldCondition(key="document_id", match=MatchAny(any=list(document_ids))))
        query_filter = Filter(must=conditions) if conditions else None
        return self.client.query_points(collection_name=self.collection_name, query=list(query_vector), query_filter=query_filter, limit=limit, with_payload=True).points

    def list_documents(self) -> list[dict]:
        records = self._scroll_all()
        documents = {}
        for record in records:
            payload = record.payload or {}
            if payload.get("document_id"):
                documents.setdefault(payload["document_id"], {key: payload.get(key) for key in ("document_id", "title", "category", "source")})
        return list(documents.values())

    def get_document_content(self, document_id: str) -> dict | None:
        """Reconstruit un document à partir de ses passages stockés dans Qdrant."""
        records = self._scroll_all(
            Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
        )
        if not records:
            return None

        payloads = sorted(
            (record.payload or {} for record in records),
            key=lambda payload: int(payload.get("chunk_index", 0)),
        )
        first = payloads[0]
        return {
            "document_id": document_id,
            "title": first.get("title") or "Document sans titre",
            "category": first.get("category"),
            "source": first.get("source"),
            "original_filename": first.get("original_filename") or Path(str(first.get("source") or document_id)).name,
            "storage_kind": first.get("storage_kind") or "unknown",
            "content": self._merge_overlapping_chunks(
                [str(payload.get("text", "")) for payload in payloads]
            ),
            "chunks_indexed": len(payloads),
        }

    @staticmethod
    def _merge_overlapping_chunks(chunks: Sequence[str]) -> str:
        """Reconstitue le texte sans répéter les mots communs aux passages voisins."""
        if not chunks:
            return ""
        merged = chunks[0].split()
        for chunk in chunks[1:]:
            words = chunk.split()
            max_overlap = min(len(merged), len(words), 256)
            overlap = next(
                (size for size in range(max_overlap, 0, -1) if merged[-size:] == words[:size]),
                0,
            )
            merged.extend(words[overlap:])
        return " ".join(merged)

    def _scroll_all(self, scroll_filter: Filter | None = None) -> list:
        """Parcourt toutes les pages Qdrant au lieu de tronquer les résultats."""
        records = []
        offset = None
        while True:
            page, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                offset=offset,
                with_payload=True,
                with_vectors=False,
                limit=256,
            )
            records.extend(page)
            if next_offset is None:
                return records
            offset = next_offset

    def update_document_storage(self, document_id: str, source: str, original_filename: str, storage_kind: str) -> None:
        """Met à jour le chemin de stockage associé à tous les passages d'un document."""
        selector = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
        self.client.set_payload(
            collection_name=self.collection_name,
            payload={"source": source, "original_filename": original_filename, "storage_kind": storage_kind},
            points=selector,
            wait=True,
        )

    def delete_document(self, document_id: str) -> None:
        selector = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
        self.client.delete(collection_name=self.collection_name, points_selector=selector, wait=True)
