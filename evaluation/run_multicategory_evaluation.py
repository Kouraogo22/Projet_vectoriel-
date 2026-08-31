"""Évalue la recherche sur toutes les catégories de la collection Qdrant active.

Le script utilise les 400 requêtes de test FQuADRetrieval, les 60 requêtes du
guide bilingue et trois requêtes sur les extraits du mémoire. Les résultats
produits décrivent une recherche globale et une recherche filtrée par catégorie.
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_hf_query_guide import CORPUS  # noqa: E402
from src.config import settings  # noqa: E402
from src.database import VectorStore  # noqa: E402
from src.embeddings import EmbeddingEncoder  # noqa: E402


RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"
FQUAD_DIR = PROJECT_ROOT / "data" / "raw" / "fquad_retrieval"
K_VALUES = (1, 3, 5, 10)

DOMAIN_TO_CATEGORY = {
    "Juridique et réglementation": "Droit et réglementation",
    "Actualités": "Actualités",
    "International news": "Actualités internationales",
    "Sports": "Sport",
    "Economy and business": "Économie et entreprises",
    "Science and technology": "Sciences et technologies",
    "Health and biomedical research": "Santé et recherche biomédicale",
}

MEMORY_QUERIES = (
    "Quelles sont les principales étapes de la démarche scientifique ?",
    "Quel rôle joue la problématique dans une démarche scientifique ?",
    "Comment une hypothèse de recherche est-elle formulée ?",
)


def load_documents(store: VectorStore) -> tuple[dict[str, dict], dict[str, str]]:
    """Retourne les textes agrégés par document et leur catégorie."""
    points, _ = store.client.scroll(
        collection_name=store.collection_name,
        with_payload=True,
        with_vectors=False,
        limit=10_000,
    )
    chunks: dict[str, list[tuple[int, str]]] = defaultdict(list)
    metadata: dict[str, dict] = {}
    for point in points:
        payload = point.payload or {}
        document_id = payload.get("document_id")
        if not document_id:
            continue
        chunks[document_id].append((int(payload.get("chunk_index", 0)), payload.get("text", "")))
        metadata.setdefault(document_id, {
            "title": payload.get("title", ""),
            "category": payload.get("category") or "Sans catégorie",
        })
    documents = {
        document_id: {**metadata[document_id], "text": " ".join(text for _, text in sorted(parts))}
        for document_id, parts in chunks.items()
    }
    categories = {document_id: item["category"] for document_id, item in documents.items()}
    return documents, categories


def build_queries(documents: dict[str, dict]) -> list[dict]:
    """Construit les jugements de pertinence pour chaque catégorie de Qdrant."""
    available = set(documents)
    queries: list[dict] = []

    fquad_queries = pd.read_parquet(FQUAD_DIR / "queries" / "test-00000-of-00001.parquet")
    fquad_qrels = pd.read_parquet(FQUAD_DIR / "qrels" / "test-00000-of-00001.parquet")
    relevant_by_query = fquad_qrels.groupby("query-id")["corpus-id"].agg(set).to_dict()
    for query_id, query_text in zip(fquad_queries["_id"], fquad_queries["text"]):
        relevant = set(relevant_by_query.get(query_id, set())) & available
        if relevant:
            queries.append({"query": query_text, "category": "FQuADRetrieval", "relevant": relevant})

    by_title: dict[tuple[str, str], set[str]] = defaultdict(set)
    for document_id, item in documents.items():
        by_title[(item["title"], item["category"])].add(document_id)
    for _language, domain, entries in CORPUS:
        category = DOMAIN_TO_CATEGORY[domain]
        for _label, source_path, questions in entries:
            title = Path(source_path).stem
            relevant = by_title.get((title, category), set())
            if not relevant:
                raise RuntimeError(f"Document de test absent de Qdrant : {title} ({category})")
            for question in questions:
                queries.append({"query": question, "category": category, "relevant": relevant})

    memory_ids = {
        document_id for document_id, item in documents.items()
        if item["category"] == "Mémoire académique"
    }
    if not memory_ids:
        raise RuntimeError("La catégorie « Mémoire académique » est absente de Qdrant.")
    for question in MEMORY_QUERIES:
        queries.append({"query": question, "category": "Mémoire académique", "relevant": memory_ids})
    return queries


def unique_document_ids(results: list) -> list[str]:
    """Déduplique les passages renvoyés par Qdrant pour une évaluation au document."""
    seen: set[str] = set()
    ranking: list[str] = []
    for result in results:
        document_id = (result.payload or {}).get("document_id")
        if document_id and document_id not in seen:
            seen.add(document_id)
            ranking.append(document_id)
    return ranking


def evaluate_rankings(records: list[dict], category: str | None = None) -> list[dict]:
    output = []
    selected = [record for record in records if category is None or record["category"] == category]
    for k in K_VALUES:
        recalls, reciprocal_ranks, latencies = [], [], []
        for record in selected:
            ranking = record["ranking"][:k]
            ranks = [rank for rank, item in enumerate(ranking, 1) if item in record["relevant"]]
            recalls.append(float(bool(ranks)))
            reciprocal_ranks.append(1 / ranks[0] if ranks else 0.0)
            latencies.append(record["latency_ms"])
        output.append({
            "Catégorie": category or "Toutes catégories",
            "k": k,
            "Recall@k": sum(recalls) / len(recalls),
            "MRR@k": sum(reciprocal_ranks) / len(reciprocal_ranks),
            "Temps moyen (ms)": sum(latencies) / len(latencies),
            "Nombre de requêtes": len(selected),
        })
    return output


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    store = VectorStore(settings.qdrant_url, settings.qdrant_api_key, settings.collection_name)
    documents, _categories = load_documents(store)
    queries = build_queries(documents)
    encoder = EmbeddingEncoder(settings.embedding_model)

    qdrant_global, qdrant_filtered = [], []
    for item in queries:
        vector = encoder.encode(item["query"])
        start = time.perf_counter()
        global_ranking = unique_document_ids(store.search(vector, limit=20))
        global_latency = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        filtered_ranking = unique_document_ids(store.search(vector, limit=20, category=item["category"]))
        filtered_latency = (time.perf_counter() - start) * 1000
        qdrant_global.append({**item, "ranking": global_ranking, "latency_ms": global_latency})
        qdrant_filtered.append({**item, "ranking": filtered_ranking, "latency_ms": filtered_latency})

    document_ids = list(documents)
    vectorizer = TfidfVectorizer(lowercase=True)
    matrix = vectorizer.fit_transform([documents[document_id]["text"] for document_id in document_ids])
    query_matrix = vectorizer.transform([item["query"] for item in queries])
    tfidf_records = []
    for item, query_vector in zip(queries, query_matrix):
        start = time.perf_counter()
        scores = (matrix @ query_vector.T).toarray().ravel()
        ranking = [document_ids[index] for index in scores.argsort()[::-1][:20]]
        tfidf_records.append({**item, "ranking": ranking, "latency_ms": (time.perf_counter() - start) * 1000})

    rows = []
    for method, records in (
        ("Qdrant vectoriel — sans filtre", qdrant_global),
        ("Qdrant vectoriel — filtre de catégorie", qdrant_filtered),
        ("TF-IDF — sans filtre", tfidf_records),
    ):
        for row in evaluate_rankings(records):
            rows.append({"Méthode et scénario": method, **row})
    metrics = pd.DataFrame(rows)
    metrics.to_csv(RESULTS_DIR / "multicategory_metrics.csv", index=False)

    category_rows = []
    for category in sorted({item["category"] for item in queries}):
        for row in evaluate_rankings(qdrant_global, category):
            if row["k"] == 10:
                category_rows.append({"Scénario": "Sans filtre", **row})
        for row in evaluate_rankings(qdrant_filtered, category):
            if row["k"] == 10:
                category_rows.append({"Scénario": "Filtre de catégorie", **row})
    pd.DataFrame(category_rows).to_csv(RESULTS_DIR / "multicategory_category_metrics_at_10.csv", index=False)

    manifest = {
        "collection": settings.collection_name,
        "document_count": len(documents),
        "query_count": len(queries),
        "queries_by_category": pd.Series([item["category"] for item in queries]).value_counts().sort_index().to_dict(),
        "scenarios": ["Qdrant sans filtre", "Qdrant avec filtre de catégorie", "TF-IDF sans filtre"],
        "k_values": list(K_VALUES),
    }
    (RESULTS_DIR / "multicategory_evaluation_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
