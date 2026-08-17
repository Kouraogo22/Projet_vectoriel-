import re

def clean_text(text: str) -> str:
    """Supprime les caractères parasites et normalise les espaces."""
    if not isinstance(text, str):
        raise TypeError("Le texte doit être une chaîne de caractères.")
    return re.sub(r"\s+", " ", text.replace("\x00", " ")).strip()
