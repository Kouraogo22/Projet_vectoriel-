"""Chapter 4 rerun with validation-selected chunk size and true passage indexing.

Run after evaluate_chunk_sizes.py. Reads a frozen 900-document source snapshot;
creates a NEW Qdrant collection, preserving earlier collections and measurements.
Vector scores are the maximum passage similarity per document. TF-IDF uses full
cleaned documents. All methods rank the same candidate document IDs.
"""
from __future__ import annotations
import hashlib
import json
import platform
import sys
import time
import uuid
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from qdrant_client import QdrantClient, models
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.evaluate_balanced_collection import build_queries, metrics_at_k, minmax
from src.embeddings import EmbeddingEncoder
from src.preprocessing import clean_text, split_into_chunks

OUT = ROOT / 'evaluation/results/chapter4_selected'
MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
K_VALUES = (1, 3, 5, 10)


def aggregate_passages(hits):
    """Retain best passage score; hit order must not change document scores."""
    scores = {}
    for hit in hits:
        identifier = str(hit.payload['document_id'])
        scores[identifier] = max(scores.get(identifier, -np.inf), float(hit.score))
    return scores


def ranked(ids, scores):
    return [identifier for identifier, score in sorted(zip(ids, scores), key=lambda p: (-p[1], p[0]))]


def main():
    selection_path = ROOT / 'evaluation/results/chunk_sizes/manifest.json'
    selection = json.loads(selection_path.read_text())
    size, overlap = int(selection['selected_size']), int(selection['overlap'])
    assert selection['model'] == MODEL
    source = OUT / 'source_documents.json'
    frame = pd.DataFrame(json.loads(source.read_text())).sort_values('document_id').reset_index(drop=True)
    counts = frame.category.value_counts()
    assert len(frame) == 900 and frame.document_id.is_unique and len(counts) == 9 and counts.eq(100).all()
    # Freeze queries before cleaning/rechunking, retaining the historical protocol.
    queries = build_queries(frame)
    (OUT / 'queries.json').write_text(json.dumps(queries, ensure_ascii=False, indent=2))
    frame['text'] = frame['text'].map(clean_text)
    torch.set_num_threads(4)
    torch.manual_seed(0)
    encoder = EmbeddingEncoder(MODEL)
    encoder.model.to('cpu')
    encoder.encode(['Préchauffage.'])
    start = time.perf_counter()
    passages = []
    for doc in frame.to_dict('records'):
        for index, text in enumerate(split_into_chunks(doc['text'], size, overlap)):
            passages.append({**doc, 'text': text, 'passage_id': f"{doc['document_id']}_{index}", 'chunk_index': index})
    vectors = encoder.encode([p['text'] for p in passages])
    encode_index_s = time.perf_counter() - start
    lengths = [len(t) for t in encoder.model.tokenizer([p['text'] for p in passages], truncation=False)['input_ids']]
    client = QdrantClient('http://localhost:6333', timeout=120)
    collection = f'experiment_multicategory_900_w{size}_{uuid.uuid4().hex[:8]}'
    start = time.perf_counter()
    client.create_collection(collection, vectors_config=models.VectorParams(size=encoder.dimension, distance=models.Distance.COSINE))
    client.upload_points(collection, [models.PointStruct(id=i, vector=v.tolist(), payload=p)
                                      for i, (v,p) in enumerate(zip(vectors, passages))], wait=True)
    insert_s = time.perf_counter() - start
    assert client.count(collection, exact=True).count == len(passages)
    print('INDEXED', collection, len(passages), 'passages', flush=True)
    pd.DataFrame(passages).drop(columns='text').assign(tokens=lengths).to_csv(OUT/'passage_manifest.csv', index=False)
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(frame.text)
    rows, traces = [], []
    for n, item in enumerate(queries, 1):
        start = time.perf_counter()
        qvector = encoder.encode(item['query']).tolist()
        encoding_ms = (time.perf_counter() - start) * 1000
        for filtered in (False, True):
            scenario = 'Avec filtre de catégorie' if filtered else 'Sans filtre'
            candidates = frame.loc[frame.category == item['category']] if filtered else frame
            ids = candidates.document_id.astype(str).tolist()
            start = time.perf_counter()
            scores = cosine_similarity(vectorizer.transform([item['query']]), tfidf_matrix[candidates.index]).ravel()
            lexical_ranking = ranked(ids, scores)
            lexical_ms = (time.perf_counter() - start) * 1000
            query_filter = models.Filter(must=[models.FieldCondition(key='category', match=models.MatchValue(value=item['category']))]) if filtered else None
            start = time.perf_counter()
            # Retrieve every candidate passage to aggregate exact document maxima;
            # this exhaustive benchmark is not an interactive top-k latency test.
            hits = client.query_points(collection, query=qvector, query_filter=query_filter,
                search_params=models.SearchParams(exact=True), limit=len(passages), with_payload=['document_id']).points
            best = aggregate_passages(hits)
            assert set(best) == set(ids)
            dense = np.array([best[i] for i in ids])
            vector_ranking = ranked(ids, dense)
            retrieval_ms = (time.perf_counter() - start) * 1000
            start = time.perf_counter()
            hybrid_ranking = ranked(ids, .5 * minmax(scores) + .5 * minmax(dense))
            fusion_ms = (time.perf_counter() - start) * 1000
            rankings = {'TF-IDF': lexical_ranking, 'Qdrant vectoriel': vector_ranking, 'Recherche hybride': hybrid_ranking}
            durations = {'TF-IDF': lexical_ms, 'Qdrant vectoriel': encoding_ms + retrieval_ms,
                         'Recherche hybride': lexical_ms + encoding_ms + retrieval_ms + fusion_ms}
            for method, ranking in rankings.items():
                row = {'Méthode': method, 'Scénario': scenario, 'Catégorie': item['category'],
                       'Temps (ms)': durations[method], 'Requête ID': n}
                for k in K_VALUES: row.update(metrics_at_k(ranking, item['relevant_id'], k))
                rows.append(row)
                traces.append({'Méthode': method, 'Scénario': scenario, 'Catégorie': item['category'],
                    'Requête ID': n, 'Requête': item['query'], 'Document pertinent': item['relevant_id'],
                    'Rang du document pertinent': ranking.index(item['relevant_id'])+1,
                    'Top 10': json.dumps(ranking[:10], ensure_ascii=False),
                    'Encodage (ms)': encoding_ms, 'Recherche vectorielle et agrégation (ms)': retrieval_ms,
                    'TF-IDF (ms)': lexical_ms, 'Fusion (ms)': fusion_ms})
        if n % 10 == 0: print('QUERIES', n, flush=True)
    observations = pd.DataFrame(rows)
    numeric = ['Temps (ms)'] + [f'{m}@{k}' for k in K_VALUES for m in ('Precision','Recall','MRR','nDCG')]
    summary = observations.groupby(['Méthode','Scénario'], as_index=False)[numeric].mean()
    category = observations.groupby(['Méthode','Scénario','Catégorie'], as_index=False)[numeric].mean()
    observations.to_csv(OUT/'protocol_comparison_detailed_metrics.csv', index=False)
    summary.to_csv(OUT/'protocol_comparison_summary_metrics.csv', index=False)
    category.to_csv(OUT/'protocol_comparison_category_metrics_at_10.csv', index=False)
    pd.DataFrame(traces).to_csv(OUT/'protocol_comparison_query_traces.csv', index=False)
    manifest = {'run_at_utc': datetime.now(timezone.utc).isoformat(), 'collection': collection,
        'source_collection': 'experiment_multicategory_900', 'documents': len(frame),
        'passages': len(passages), 'categories': counts.sort_index().to_dict(), 'queries': len(queries),
        'chunk_size': size, 'chunk_overlap': overlap, 'selection': str(selection_path.relative_to(ROOT)),
        'selection_sha256': hashlib.sha256(selection_path.read_bytes()).hexdigest(),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'model': MODEL, 'max_seq_length': encoder.model.max_seq_length,
        'truncated_passages': int(sum(n > encoder.model.max_seq_length for n in lengths)),
        'dimension': encoder.dimension, 'device': 'cpu', 'threads': 4,
        'index_encoding_s': encode_index_s, 'qdrant_insertion_s': insert_s,
        'query_protocol': 'First sentence limited to 220 characters; first 10 IDs per category',
        'ranking': 'Exact cosine over all passages; maximum per document; tie break by document_id',
        'hybrid_alpha': .5, 'k_values': list(K_VALUES),
        'timing': 'Single warm run: query encoding + HTTP exact retrieval of all passages + document aggregation/ranking. Hybrid adds TF-IDF and fusion. Excludes model loading and UI.',
        'platform': platform.platform(), 'python': platform.python_version(),
        'versions': {pkg: version(pkg) for pkg in ['sentence-transformers','qdrant-client','pandas','numpy','scikit-learn','torch']}}
    (OUT/'protocol_comparison_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(summary.round(4).to_string(index=False), flush=True)
    client.close()

if __name__ == '__main__': main()
