import pytest
from src.search import SemanticRetriever
from src.database.qdrant_client import VectorStore

def test_search_rejects_blank_query():
    retriever = SemanticRetriever(store=object(), encoder=object())
    with pytest.raises(ValueError, match="ne peut pas être vide"):
        retriever.search("   ")


class FakeQdrantClient:
    def query_points(self, **kwargs):
        self.kwargs = kwargs
        return type("Response", (), {"points": []})()


def test_vector_store_combines_category_and_document_filters():
    store = VectorStore.__new__(VectorStore)
    store.client = FakeQdrantClient()
    store.collection_name = "documents_semantiques"

    store.search(
        query_vector=[0.1, 0.2],
        limit=10,
        categories=["informatique", "santé"],
        document_ids=["document-1", "document-2"],
    )

    conditions = store.client.kwargs["query_filter"].must
    assert conditions[0].key == "category"
    assert conditions[0].match.any == ["informatique", "santé"]
    assert conditions[1].key == "document_id"
    assert conditions[1].match.any == ["document-1", "document-2"]
