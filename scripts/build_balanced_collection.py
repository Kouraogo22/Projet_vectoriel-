"""Construit une collection Qdrant équilibrée de 100 unités par catégorie."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
from qdrant_client.models import PointStruct

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.database.schema import vector_params
from src.embeddings import EmbeddingEncoder
from src.database import VectorStore

COLLECTION = "experiment_multicategory_900"
RAW = ROOT / "data" / "raw"
OUT = ROOT / "evaluation" / "results"

def record(category, key, title, text):
    return {"document_id": key, "title": title, "text": re.sub(r"\s+", " ", str(text)).strip(),
            "category": category, "source": "Corpus expérimental équilibré", "language": "fr" if category in {"Actualités", "Droit et réglementation", "Mémoire académique", "FQuADRetrieval"} else "en"}

def memory_records():
    tex = (ROOT.parent.parent / "Rapport" / "Rapport Joel KOURAOGO.tex").read_text(encoding="utf-8")
    plain = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^]]*\])?(?:\{[^}]*\})?", " ", tex)
    words = re.sub(r"[^A-Za-zÀ-ÿ0-9\s]", " ", plain).split()
    chunks = [" ".join(words[i:i+90]) for i in range(0, len(words)-90, 30)][:100]
    if len(chunks) < 100:
        raise RuntimeError("Le mémoire ne contient pas assez de texte pour 100 extraits.")
    return [record("Mémoire académique", f"memoire_{i:03}", f"Mémoire académique — extrait {i}", text) for i, text in enumerate(chunks, 1)]

def main():
    rows = []
    fquad = pd.read_parquet(RAW/"fquad_retrieval/corpus/test-00000-of-00001.parquet").head(100)
    rows += [record("FQuADRetrieval", f"fquad_{doc_id}", title, f"{title}. {text}") for doc_id, title, text in zip(fquad["_id"], fquad["title"], fquad["text"])]
    frenchqa = pd.read_parquet(RAW/"huggingface_cache/frenchqa_validation.parquet").head(100)
    rows += [record("Actualités", f"frenchqa_{i:03}", str(r.title), f"{r.context} Question : {r.question}") for i, r in enumerate(frenchqa.itertuples(index=False), 1)]
    ag = pd.read_parquet(RAW/"huggingface_cache/ag_news_train.parquet")
    labels = {0:"Actualités internationales",1:"Sport",2:"Économie et entreprises",3:"Sciences et technologies"}
    for label, category in labels.items():
        sample = ag.loc[ag.label == label].head(100)
        rows += [record(category, f"ag_{label}_{i:03}", category, r.text) for i, r in enumerate(sample.itertuples(index=False),1)]
    raw_legal = (RAW/"huggingface_cache/french_legal_sample.jsonl").read_text(encoding="utf-8")
    decoder, position, legal = json.JSONDecoder(), 0, []
    while position < len(raw_legal):
        while position < len(raw_legal) and raw_legal[position].isspace():
            position += 1
        if position < len(raw_legal):
            item, position = decoder.raw_decode(raw_legal, position)
            legal.append(item)
    legal = [r for r in legal if r.get("text") and r.get("n_words",0) >= 80][:100]
    rows += [record("Droit et réglementation", f"legal_{i:03}", r.get("source","Document juridique"), r["text"]) for i,r in enumerate(legal,1)]
    pub = pd.read_parquet(RAW/"huggingface_cache/pubmedqa_labeled_train.parquet").head(100)
    for i,r in enumerate(pub.itertuples(index=False),1):
        context = " ".join(r.context["contexts"])
        rows.append(record("Santé et recherche biomédicale", f"pubmed_{r.pubid}", f"PubMedQA — {r.pubid}", f"Question : {r.question}. Résumé : {context}. Conclusion : {r.long_answer}"))
    rows += memory_records()
    counts = pd.Series([r["category"] for r in rows]).value_counts()
    if len(rows) != 900 or not (counts == 100).all():
        raise RuntimeError(f"Répartition invalide : {counts.to_dict()}")
    store = VectorStore("http://localhost:6333", None, COLLECTION)
    if store.client.collection_exists(COLLECTION):
        store.client.delete_collection(COLLECTION)
    encoder = EmbeddingEncoder("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    store.client.create_collection(COLLECTION, vectors_config=vector_params(encoder.dimension))
    vectors = encoder.encode([r["text"] for r in rows], batch_size=32)
    points = [PointStruct(id=i+1, vector=list(v), payload={**r, "passage_id": f"{r['document_id']}_0", "chunk_index":0}) for i,(r,v) in enumerate(zip(rows,vectors))]
    store.client.upsert(COLLECTION, points, wait=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).drop(columns="text").to_csv(OUT/"balanced_collection_manifest.csv",index=False)
    (OUT/"balanced_collection_summary.json").write_text(json.dumps({"collection":COLLECTION,"document_count":len(rows),"categories":counts.sort_index().to_dict()},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"collection":COLLECTION,"document_count":len(rows),"categories":counts.sort_index().to_dict()},ensure_ascii=False,indent=2))
if __name__ == "__main__":
    main()
