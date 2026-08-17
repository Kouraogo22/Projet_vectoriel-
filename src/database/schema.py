from qdrant_client.models import Distance, VectorParams

def vector_params(dimension: int) -> VectorParams:
    if dimension < 1:
        raise ValueError("La dimension d'un vecteur doit être positive.")
    return VectorParams(size=dimension, distance=Distance.COSINE)
