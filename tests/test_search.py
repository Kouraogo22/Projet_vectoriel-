import pytest
from types import SimpleNamespace
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


class PaginatedQdrantClient:
    def __init__(self):
        self.offsets = []

    def scroll(self, **kwargs):
        self.offsets.append(kwargs["offset"])
        if kwargs["offset"] is None:
            return [SimpleNamespace(payload={"document_id": "document-1", "title": "A"})], "page-2"
        return [SimpleNamespace(payload={"document_id": "document-2", "title": "B"})], None


def test_list_documents_reads_all_qdrant_pages():
    store = VectorStore.__new__(VectorStore)
    store.client = PaginatedQdrantClient()
    store.collection_name = "documents_semantiques"

    documents = store.list_documents()

    assert [document["document_id"] for document in documents] == ["document-1", "document-2"]
    assert store.client.offsets == [None, "page-2"]


def test_document_reconstruction_removes_chunk_overlap():
    chunks = ["un deux trois quatre", "trois quatre cinq six", "cinq six sept"]

    assert VectorStore._merge_overlapping_chunks(chunks) == "un deux trois quatre cinq six sept"


def test_language_detection_supports_french_and_english():
    assert SemanticRetriever._detect_language("Le document est dans la base avec les données") == "fr"
    assert SemanticRetriever._detect_language("The document is in the database with the data") == "en"
