from collections.abc import Sequence
from sentence_transformers import SentenceTransformer

class EmbeddingEncoder:
    """Adaptateur Sentence Transformers chargé seulement au premier usage."""
    def __init__(self, model_name: str) -> None:
        self.model_name, self._model = model_name, None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        return int(self.model.get_embedding_dimension())

    def encode(self, texts: str | Sequence[str], batch_size: int = 32):
        return self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
