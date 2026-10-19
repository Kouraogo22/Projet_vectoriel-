"""Évaluation reproductible du corpus équilibré selon le protocole de soutenance.

Trois approches sont évaluées sur les mêmes 90 requêtes contrôlées :
TF-IDF, recherche vectorielle Qdrant et recherche hybride. Chaque approche
est mesurée sur l'ensemble du corpus puis avec un filtre de catégorie.
Les résultats sont exportés dans evaluation/results et utilisés par le
notebook notebooks/evaluation.ipynb.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database import VectorStore
from src.embeddings import EmbeddingEncoder

COLLECTION = os.getenv("EVALUATION_COLLECTION", "experiment_multicategory_900")
OUT = ROOT / "evaluation" / "results"
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
K_VALUES = (1, 3, 5, 10)
HYBRID_ALPHA = 0.50


def minmax(scores: np.ndarray) -> np.ndarray:
    """Normalise les scores sans modifier l'ordre lorsque tous sont égaux."""
    minimum = float(scores.min())
    maximum = float(scores.max())
    if maximum == minimum:
        return np.ones_like(scores, dtype=float)
    return (scores - minimum) / (maximum - minimum)


def metrics_at_k(ranking: list[str], relevant_id: str, k: int) -> dict[str, float]:
    """Calcule les mesures à K pour un seul document jugé pertinent."""
    top = ranking[:k]
    rank = next((index for index, identifier in enumerate(top, 1) if identifier == relevant_id), None)
    hit = float(rank is not None)
    return {
        f"Precision@{k}": hit / k,
        f"Recall@{k}": hit,
        f"MRR@{k}": 1 / rank if rank else 0.0,
        f"nDCG@{k}": 1 / np.log2(rank + 1) if rank else 0.0,
    }


def fetch_documents(store: VectorStore) -> pd.DataFrame:
    points, _ = store.client.scroll(
        collection_name=COLLECTION,
        with_payload=True,
        with_vectors=False,
        limit=1_000,
    )
    documents = {}
    for point in points:
        payload = point.payload or {}
        identifier = payload.get("document_id")
        if identifier:
            documents[identifier] = payload
    frame = pd.DataFrame(documents.values())
    required = {"document_id", "title", "text", "category"}
    missing = required.difference(frame.columns)
    if missing:
        raise RuntimeError(f"Champs absents dans Qdrant : {sorted(missing)}")
    counts = frame["category"].value_counts().sort_index()
    if len(frame) != 900 or len(counts) != 9 or not (counts == 100).all():
        raise RuntimeError(
            "Le protocole attend 900 documents répartis en 9 catégories de 100 documents. "
            f"État observé : {len(frame)} documents ; {counts.to_dict()}"
        )
    return frame.reset_index(drop=True)


def build_queries(frame: pd.DataFrame) -> list[dict[str, str]]:
    """Conserve le protocole contrôlé historique : dix extraits par catégorie.

    Les requêtes sont les premières phrases de documents pertinents. Cette
    construction facilite la reproductibilité mais doit être interprétée comme
    une évaluation contrôlée, et non comme des requêtes indépendantes d'usagers.
    """
    queries: list[dict[str, str]] = []
    for category, group in frame.sort_values("document_id").groupby("category", sort=True):
        for _, document in group.head(10).iterrows():
            first_sentence = str(document["text"]).split(".")[0].strip()
            query = (first_sentence[:220] or str(document["title"])).strip()
            queries.append(
                {
                    "category": str(category),
                    "query": query,
                    "relevant_id": str(document["document_id"]),
                }
            )
    if len(queries) != 90:
        raise RuntimeError(f"90 requêtes étaient attendues, {len(queries)} ont été construites.")
    return queries


def evaluate() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    OUT.mkdir(parents=True, exist_ok=True)
    store = VectorStore("http://localhost:6333", None, COLLECTION)
    frame = fetch_documents(store)
    queries = build_queries(frame)
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(frame["text"].fillna(""))
    encoder = EmbeddingEncoder(MODEL)
    encoded_queries = encoder.model.encode(
        [item["query"] for item in queries],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    query_vectors = {
        item["relevant_id"]: vector.tolist() for item, vector in zip(queries, encoded_queries)
    }
    rows: list[dict[str, object]] = []
    traces: list[dict[str, object]] = []

    for use_filter in (False, True):
        scenario = "Avec filtre de catégorie" if use_filter else "Sans filtre"
        for item in queries:
            category = item["category"]
            query = item["query"]
            relevant_id = item["relevant_id"]
            candidates = frame if not use_filter else frame.loc[frame["category"] == category]

            lexical_start = time.perf_counter()
            lexical_query = vectorizer.transform([query])
            lexical_scores = cosine_similarity(lexical_query, tfidf_matrix[candidates.index]).ravel()
            lexical_time = (time.perf_counter() - lexical_start) * 1000

            vector_start = time.perf_counter()
            query_vector = query_vectors[relevant_id]
            vector_hits = store.search(
                query_vector,
                limit=len(candidates),
                category=category if use_filter else None,
            )
            vector_time = (time.perf_counter() - vector_start) * 1000
            vector_scores = {
                str(hit.payload.get("document_id")): float(hit.score)
                for hit in vector_hits
                if hit.payload and hit.payload.get("document_id")
            }

            candidate_ids = candidates["document_id"].astype(str).tolist()
            vector_array = np.array([vector_scores.get(identifier, 0.0) for identifier in candidate_ids])
            hybrid_scores = HYBRID_ALPHA * minmax(lexical_scores) + (1 - HYBRID_ALPHA) * minmax(vector_array)

            rankings = {
                "TF-IDF": [
                    identifier
                    for _, identifier in sorted(
                        zip(lexical_scores, candidate_ids), key=lambda item: item[0], reverse=True
                    )
                ],
                "Qdrant vectoriel": [
                    identifier
                    for _, identifier in sorted(
                        zip(vector_array, candidate_ids), key=lambda item: item[0], reverse=True
                    )
                ],
                "Recherche hybride": [
                    identifier
                    for _, identifier in sorted(
                        zip(hybrid_scores, candidate_ids), key=lambda item: item[0], reverse=True
                    )
                ],
            }
            durations = {
                "TF-IDF": lexical_time,
                "Qdrant vectoriel": vector_time,
                "Recherche hybride": lexical_time + vector_time,
            }

            for method, ranking in rankings.items():
                row: dict[str, object] = {
                    "Méthode": method,
                    "Scénario": scenario,
                    "Catégorie": category,
                    "Temps (ms)": durations[method],
                }
                for k in K_VALUES:
                    row.update(metrics_at_k(ranking, relevant_id, k))
                rows.append(row)
                traces.append(
                    {
                        "Méthode": method,
                        "Scénario": scenario,
                        "Catégorie": category,
                        "Requête": query,
                        "Document pertinent": relevant_id,
                        "Rang du document pertinent": (
                            ranking.index(relevant_id) + 1 if relevant_id in ranking else None
                        ),
                    }
                )

    observations = pd.DataFrame(rows)
    summary = observations.groupby(["Méthode", "Scénario"], as_index=False).mean(numeric_only=True)
    per_category = observations.groupby(
        ["Méthode", "Scénario", "Catégorie"], as_index=False
    ).mean(numeric_only=True)
    trace_frame = pd.DataFrame(traces)
    return observations, summary, per_category, trace_frame


def main() -> None:
    observations, summary, per_category, traces = evaluate()
    observations.to_csv(OUT / "protocol_comparison_detailed_metrics.csv", index=False)
    summary.to_csv(OUT / "protocol_comparison_summary_metrics.csv", index=False)
    per_category.to_csv(OUT / "protocol_comparison_category_metrics_at_10.csv", index=False)
    traces.to_csv(OUT / "protocol_comparison_query_traces.csv", index=False)
    manifest = {
        "collection": COLLECTION,
        "documents": 900,
        "categories": 9,
        "documents_per_category": 100,
        "queries": 90,
        "query_protocol": "Première phrase de dix documents pertinents par catégorie",
        "methods": ["TF-IDF", "Qdrant vectoriel", "Recherche hybride"],
        "scenarios": ["Sans filtre", "Avec filtre de catégorie"],
        "k_values": list(K_VALUES),
        "hybrid_alpha": HYBRID_ALPHA,
        "embedding_model": MODEL,
    }
    (OUT / "protocol_comparison_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Résultats de l'évaluation selon le protocole :")
    print(summary.round(4).to_string(index=False))
    print()
    print("Résultats par catégorie à K=10 :")
    print(
        per_category[
            ["Méthode", "Scénario", "Catégorie", "Precision@10", "Recall@10", "MRR@10", "nDCG@10"]
        ]
        .round(4)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
