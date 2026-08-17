import pytest
from src.preprocessing import split_into_chunks

def test_split_into_chunks_preserves_overlap():
    chunks = split_into_chunks(" ".join(f"mot{i}" for i in range(30)), chunk_size=10, overlap=2)
    assert len(chunks) == 4
    assert chunks[0].split()[-2:] == chunks[1].split()[:2]

def test_split_into_chunks_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        split_into_chunks("texte", chunk_size=10, overlap=10)
