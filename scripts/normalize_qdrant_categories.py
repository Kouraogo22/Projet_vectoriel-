"""Normalise les catégories des documents déjà indexés dans Qdrant.

Le script modifie uniquement le champ de métadonnées ``category``. Les textes
et les vecteurs déjà calculés ne sont ni relus ni recalculés.
"""

from __future__ import annotations

import argparse
import os

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue


COLLECTION = os.getenv("COLLECTION_NAME", "fquad_retrieval")
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")

CATEGORY_BY_DOCUMENT_ID = {
    "8b346d66-1348-5ba1-b9a3-4cdb1e91fac3": "Mémoire académique",
    "0b7f333d-668a-5a98-92ab-b1f5e01b487b": "Mémoire académique",
    "4d2a6f88-c4ad-546a-9cdc-729290e90143": "Droit et réglementation",
    "44e7a858-bd5f-51e8-82332ec1f3b1": "Sciences et technologies",
    "6d42155f-2104-5977-8960-7af63dd012f0": "Actualités",
    "1586ee88-9857-5d0d-b7f0-404f52d1ede7": "Santé et recherche biomédicale",
}

CATEGORY_BY_TITLE = {
    "ag_news_0_1_actualites-internationales": "Actualités internationales",
    "ag_news_0_2_actualites-internationales": "Actualités internationales",
    "ag_news_1_1_sport": "Sport",
    "ag_news_1_2_sport": "Sport",
    "ag_news_2_1_economie-et-entreprises": "Économie et entreprises",
    "ag_news_2_2_economie-et-entreprises": "Économie et entreprises",
    "ag_news_3_1_sciences-et-technologies": "Sciences et technologies",
    "ag_news_3_2_sciences-et-technologies": "Sciences et technologies",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Applique les mises à jour dans Qdrant.")
    args = parser.parse_args()

    client = QdrantClient(url=QDRANT_URL)
    if not client.collection_exists(COLLECTION):
        raise RuntimeError(f"Collection introuvable : {COLLECTION}")

    targets = [
        ("document_id", document_id, category)
        for document_id, category in CATEGORY_BY_DOCUMENT_ID.items()
    ] + [
        ("title", title, category)
        for title, category in CATEGORY_BY_TITLE.items()
    ]
    for field, identifier, category in targets:
        selector = Filter(must=[FieldCondition(key=field, match=MatchValue(value=identifier))])
        records, _ = client.scroll(COLLECTION, scroll_filter=selector, limit=1, with_vectors=False)
        if not records:
            print(f"ABSENT  {field}={identifier}")
            continue
        current = (records[0].payload or {}).get("category")
        action = "APPLIQUÉ" if args.apply else "PRÉVU"
        print(f"{action}  {field}={identifier}: {current!r} -> {category!r}")
        if args.apply:
            client.set_payload(COLLECTION, {"category": category}, points=selector, wait=True)


if __name__ == "__main__":
    main()
