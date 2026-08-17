from unittest.mock import MagicMock
from src.embeddings import EmbeddingEncoder

def test_encoder_normalizes_embeddings():
    encoder = EmbeddingEncoder("model-test")
    encoder._model = MagicMock()
    encoder.encode("bonjour")
    encoder.model.encode.assert_called_once_with("bonjour", batch_size=32, normalize_embeddings=True, show_progress_bar=False)
