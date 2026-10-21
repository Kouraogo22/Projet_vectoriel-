"""Compare chunk sizes on validation; assess selected size versus 120 on held-out test.

Uses the application cleaner, splitter and embedding adapter. Qdrant local in-memory
mode provides exact cosine search without modifying deployed collections. Metrics
refer to the first ten PASSAGES, as in the application; a passage is relevant when
its source document has a positive qrel. Repeated passages occupy ranking slots.
"""
from __future__ import annotations
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from qdrant_client import QdrantClient, models

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.preprocessing import clean_text, split_into_chunks
from src.embeddings import EmbeddingEncoder

MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
SIZES = [60, 90, 120, 180, 240]
OVERLAP = 20
DATA = ROOT / 'data/raw/fquad_retrieval'
OUT = ROOT / 'evaluation/results/chunk_sizes'


def load(kind, split):
    return pd.read_parquet(DATA / kind / f'{split}-00000-of-00001.parquet')


def measure(client, vectors, queries, qrels, size, split):
    truth = {}
    for row in qrels.to_dict('records'):
        if row['score'] > 0:
            truth.setdefault(str(row['query-id']), set()).add(str(row['corpus-id']))
    rows = []
    for q, vec in zip(queries.to_dict('records'), vectors):
        relevant = truth[str(q['_id'])]
        start = time.perf_counter()
        hits = client.query_points('passages', query=vec.tolist(), limit=10,
                                   with_payload=True).points
        duration = (time.perf_counter() - start) * 1000
        docs = [str(h.payload['document_id']) for h in hits]
        rank = next((i for i, d in enumerate(docs, 1) if d in relevant), None)
        rows.append({'size': size, 'split': split, 'query_id': str(q['_id']),
                     'recall_10': len(set(docs) & relevant) / len(relevant),
                     'mrr_10': 1 / rank if rank else 0.,
                     'hit_1': float(bool(docs) and docs[0] in relevant),
                     'rank': rank, 'search_ms': duration})
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    torch.manual_seed(0)
    encoder = EmbeddingEncoder(MODEL)
    encoder.model.to('cpu')
    corpus = pd.concat([load('corpus', s) for s in ('validation', 'test')], ignore_index=True)
    assert corpus.groupby('_id')['text'].nunique().max() == 1, 'Conflicting document texts'
    corpus = corpus.drop_duplicates('_id').reset_index(drop=True)
    assert corpus['_id'].is_unique
    queries = {s: load('queries', s) for s in ('validation', 'test')}
    qrels = {s: load('qrels', s) for s in queries}
    assert all(set(qrels[s]['corpus-id']) <= set(corpus['_id']) for s in queries)
    qvectors = {s: encoder.encode(queries[s]['text'].tolist()) for s in queries}
    encoder.encode(['Préchauffage du modèle.'])
    summary, traces, cached = [], [], {}
    token_limit = encoder.model.max_seq_length
    for size in SIZES:
        passages, ids = [], []
        start = time.perf_counter()
        for doc in corpus.to_dict('records'):
            chunks = split_into_chunks(clean_text(doc['text']), size, OVERLAP)
            passages.extend(chunks)
            ids.extend([str(doc['_id'])] * len(chunks))
        chunk_s = time.perf_counter() - start
        lengths = [len(tokens) for tokens in encoder.model.tokenizer(
            passages, truncation=False, padding=False)['input_ids']]
        start = time.perf_counter()
        vectors = encoder.encode(passages)
        encode_s = time.perf_counter() - start
        client = QdrantClient(':memory:')
        start = time.perf_counter()
        client.create_collection('passages', vectors_config=models.VectorParams(
            size=encoder.dimension, distance=models.Distance.COSINE))
        client.upload_points('passages', [models.PointStruct(id=i, vector=v.tolist(),
            payload={'document_id': d}) for i, (v, d) in enumerate(zip(vectors, ids))])
        insert_s = time.perf_counter() - start
        rows = measure(client, qvectors['validation'], queries['validation'], qrels['validation'], size, 'validation')
        traces.extend(rows)
        result = {'size': size, 'overlap': OVERLAP, 'passages': len(passages),
            'truncated_pct': float(np.mean(np.array(lengths) > token_limit) * 100),
            'max_tokens': max(lengths), 'chunk_s': chunk_s, 'encode_s': encode_s,
            'insert_s': insert_s, 'index_s': chunk_s + encode_s + insert_s,
            'recall_10': float(np.mean([r['recall_10'] for r in rows])),
            'mrr_10': float(np.mean([r['mrr_10'] for r in rows])),
            'hit_1': float(np.mean([r['hit_1'] for r in rows]))}
        summary.append(result)
        cached[size] = client
        pd.DataFrame(summary).to_csv(OUT / 'validation_summary.csv', index=False)
        print(json.dumps(result), flush=True)
    # Predeclared selection: highest validation MRR@10, then Recall@10,
    # then fewer passages, then smaller size. Never select on test metrics.
    winner = max(summary, key=lambda r: (r['mrr_10'], r['recall_10'], -r['passages'], -r['size']))['size']
    test_summary = []
    for size in sorted({120, winner}):
        rows = measure(cached[size], qvectors['test'], queries['test'], qrels['test'], size, 'test')
        traces.extend(rows)
        test_summary.append({'size': size, **{k: float(np.mean([r[k] for r in rows]))
                                            for k in ('recall_10', 'mrr_10', 'hit_1')}})
    pd.DataFrame(test_summary).to_csv(OUT / 'test_summary.csv', index=False)
    frame = pd.DataFrame(traces)
    frame.to_csv(OUT / 'query_metrics.csv', index=False)
    # Paired bootstrap expresses uncertainty for the held-out difference.
    interval = None
    if winner != 120:
        paired = frame[frame.split == 'test'].pivot(index='query_id', columns='size', values='mrr_10')
        delta = (paired[winner] - paired[120]).to_numpy()
        rng = np.random.default_rng(0)
        means = np.array([rng.choice(delta, len(delta), replace=True).mean() for _ in range(10000)])
        interval = {'difference': float(delta.mean()), 'ci95': np.quantile(means, [.025, .975]).tolist()}
    manifest = {'model': MODEL, 'max_seq_length': token_limit, 'dimension': encoder.dimension,
        'device': 'cpu', 'threads': 4, 'platform': platform.platform(),
        'documents': len(corpus), 'validation_queries': len(queries['validation']),
        'test_queries': len(queries['test']), 'sizes': SIZES, 'overlap': OVERLAP,
        'selected_size': winner, 'selection': 'max validation MRR@10, Recall@10, fewer passages, smaller size',
        'search': 'Qdrant local in-memory exact cosine, top 10 passages, no category filter',
        'timing': 'one run; warm model; index=chunking+encoding+insertion; excludes token audit and model load',
        'test_mrr_difference_bootstrap': interval,
        'inputs_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(DATA.glob('*/*.parquet'))}}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print('TEST', json.dumps(test_summary), 'SELECTED', winner, 'CI', interval, flush=True)
    for client in cached.values(): client.close()

if __name__ == '__main__':
    main()
