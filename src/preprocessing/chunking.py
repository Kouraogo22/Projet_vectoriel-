def split_into_chunks(text: str, chunk_size: int = 120, overlap: int = 20) -> list[str]:
    """Découpe un texte en passages de mots avec chevauchement."""
    if chunk_size < 1:
        raise ValueError("La taille d'un passage doit être positive.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("Le chevauchement doit être positif ou nul et inférieur à la taille.")
    words, chunks = text.split(), []
    for start in range(0, len(words), chunk_size - overlap):
        chunk = words[start:start + chunk_size]
        if not chunk:
            break
        chunks.append(" ".join(chunk))
        if start + chunk_size >= len(words):
            break
    return chunks
