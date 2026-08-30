from collections.abc import Sequence
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

    def upsert_passages(self, passages: Sequence[dict], vectors: Sequence[Sequence[float]]) -> None:
        if len(passages) != len(vectors):
            raise ValueError("Chaque passage doit posséder un vecteur.")
        points = [PointStruct(id=str(uuid5(NAMESPACE_URL, p["passage_id"])), vector=list(v), payload=p) for p, v in zip(passages, vectors)]
        if points:
            self.client.upsert(collection_name=self.collection_name, points=points, wait=True)

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
        records, _ = self.client.scroll(self.collection_name, with_payload=True, with_vectors=False, limit=1000)
        documents = {}
        for record in records:
            payload = record.payload or {}
            if payload.get("document_id"):
                documents.setdefault(payload["document_id"], {key: payload.get(key) for key in ("document_id", "title", "category", "source")})
        return list(documents.values())

    def delete_document(self, document_id: str) -> None:
        selector = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
        self.client.delete(collection_name=self.collection_name, points_selector=selector, wait=True)
