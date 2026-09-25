"""Évalue la référence classique TF-IDF sur le corpus expérimental équilibré."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "evaluation" / "results"


def record(category: str, key: str, title: str, text: str) -> dict:
    return {
        "document_id": key,
        "title": title,
        "text": re.sub(r"\s+", " ", str(text)).strip(),
        "category": category,
    }


def memory_records() -> list[dict]:
    report = (ROOT.parent.parent / "Rapport" / "Rapport Joel KOURAOGO.tex").read_text(encoding="utf-8")
    plain = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^]]*\])?(?:\{[^}]*\})?", " ", report)
    words = re.sub(r"[^A-Za-zÀ-ÿ0-9\s]", " ", plain).split()
    chunks = [" ".join(words[index:index + 90]) for index in range(0, len(words) - 90, 30)][:100]
    return [record("Mémoire académique", f"memoire_{index:03}", f"Mémoire académique — extrait {index}", text) for index, text in enumerate(chunks, 1)]


def build_corpus() -> pd.DataFrame:
    rows: list[dict] = []
    fquad = pd.read_parquet(RAW / "fquad_retrieval/corpus/test-00000-of-00001.parquet").head(100)
    rows += [record("FQuADRetrieval", f"fquad_{doc_id}", title, f"{title}. {text}") for doc_id, title, text in zip(fquad["_id"], fquad["title"], fquad["text"])]
    frenchqa = pd.read_parquet(RAW / "huggingface_cache/frenchqa_validation.parquet").head(100)
    rows += [record("Actualités", f"frenchqa_{index:03}", str(row.title), f"{row.context} Question : {row.question}") for index, row in enumerate(frenchqa.itertuples(index=False), 1)]
    ag_news = pd.read_parquet(RAW / "huggingface_cache/ag_news_train.parquet")
    labels = {0: "Actualités internationales", 1: "Sport", 2: "Économie et entreprises", 3: "Sciences et technologies"}
    for label, category in labels.items():
        sample = ag_news.loc[ag_news.label == label].head(100)
        rows += [record(category, f"ag_{label}_{index:03}", category, row.text) for index, row in enumerate(sample.itertuples(index=False), 1)]
    raw_legal = (RAW / "huggingface_cache/french_legal_sample.jsonl").read_text(encoding="utf-8")
    decoder, position, legal = json.JSONDecoder(), 0, []
    while position < len(raw_legal):
        while position < len(raw_legal) and raw_legal[position].isspace():
            position += 1
        if position < len(raw_legal):
            item, position = decoder.raw_decode(raw_legal, position)
            legal.append(item)
    legal = [item for item in legal if item.get("text") and item.get("n_words", 0) >= 80][:100]
    rows += [record("Droit et réglementation", f"legal_{index:03}", item.get("source", "Document juridique"), item["text"]) for index, item in enumerate(legal, 1)]
    pubmed = pd.read_parquet(RAW / "huggingface_cache/pubmedqa_labeled_train.parquet").head(100)
    for row in pubmed.itertuples(index=False):
        context = " ".join(row.context["contexts"])
        rows.append(record("Santé et recherche biomédicale", f"pubmed_{row.pubid}", f"PubMedQA — {row.pubid}", f"Question : {row.question}. Résumé : {context}. Conclusion : {row.long_answer}"))
    rows += memory_records()
    corpus = pd.DataFrame(rows)
    if len(corpus) != 900 or not corpus["category"].value_counts().eq(100).all():
        raise RuntimeError("La reconstruction du corpus équilibré est invalide.")
    return corpus


def main() -> None:
    corpus = build_corpus()
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(corpus["text"])
    queries = []
    for category, group in corpus.groupby("category", sort=True):
        for row in group.head(10).itertuples(index=False):
            query = row.text.split(".")[0][:220] or row.title
            queries.append((category, query, row.document_id))

    rows = []
    for filtered in (False, True):
        for category, query, relevant in queries:
            start = time.perf_counter()
            candidates = corpus if not filtered else corpus[corpus["category"] == category]
            scores = cosine_similarity(vectorizer.transform([query]), matrix[candidates.index]).ravel()
            ranking = candidates.iloc[scores.argsort()[::-1][:10]]["document_id"].tolist()
            rank = next((index for index, document_id in enumerate(ranking, 1) if document_id == relevant), None)
            rows.append({
                "Méthode": "TF-IDF",
                "Scénario": "Avec filtre" if filtered else "Sans filtre",
                "Catégorie": category,
                "Recall@10": float(rank is not None),
                "MRR@10": 1 / rank if rank else 0,
                "Temps (ms)": (time.perf_counter() - start) * 1000,
            })
    by_category = pd.DataFrame(rows).groupby(["Méthode", "Scénario", "Catégorie"], as_index=False).mean(numeric_only=True)
    summary = by_category.groupby(["Méthode", "Scénario"], as_index=False).mean(numeric_only=True)
    OUT.mkdir(parents=True, exist_ok=True)
    by_category.to_csv(OUT / "classical_baseline_metrics.csv", index=False)
    summary.to_csv(OUT / "classical_baseline_summary_metrics.csv", index=False)
    print("Référence classique TF-IDF :")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
