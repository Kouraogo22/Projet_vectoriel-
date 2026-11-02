from collections.abc import Sequence
from sentence_transformers import SentenceTransformer

class EmbeddingEncoder:
    """Adaptateur Sentence Transformers chargé seulement au premier usage."""
    def __init__(self, model_name: str, *, normalize: bool = True, device: str | None = None, max_seq_length: int | None = None) -> None:
        self.model_name, self._model = model_name, None
        self.normalize, self.device, self.max_seq_length = normalize, device, max_seq_length

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            model = SentenceTransformer(self.model_name, device=self.device, trust_remote_code=False)
            if self.max_seq_length is not None:
                if self.max_seq_length > model.max_seq_length:
                    raise ValueError(f"Le modèle accepte au maximum {model.max_seq_length} tokens ; choisissez une limite inférieure.")
                model.max_seq_length = self.max_seq_length
            self._model = model
        return self._model

    @property
    def dimension(self) -> int:
        return int(self.model.get_embedding_dimension())

    def encode(self, texts: str | Sequence[str], batch_size: int = 32):
        return self.model.encode(texts, batch_size=batch_size, normalize_embeddings=self.normalize, show_progress_bar=False)
