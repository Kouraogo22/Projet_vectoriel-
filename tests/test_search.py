import pytest
from src.search import SemanticRetriever

def test_search_rejects_blank_query():
    retriever = SemanticRetriever(store=object(), encoder=object())
    with pytest.raises(ValueError, match="ne peut pas être vide"):
        retriever.search("   ")
