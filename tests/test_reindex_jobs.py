from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from pydantic import ValidationError
from qdrant_client import QdrantClient

from api.routes import documents, reindex
from src.database import VectorStore
from src.indexing.jobs import ReindexManager
from src.indexing.options import IndexOptions, ReindexRequest
from src.search import SemanticRetriever
from tests.test_documents_api import request as http_request


class Encoder:
    dimension = 3
    model = SimpleNamespace(max_seq_length=128, tokenizer=lambda texts, **kw: {"input_ids": [t.split() for t in texts]})

    def encode(self, texts, batch_size=32):
        if isinstance(texts, str):
            return [1., 0., 0.]
        return [[1., 0., 0.] for _ in texts]


@pytest.fixture
def setup(tmp_path):
    client = QdrantClient(":memory:")
    client.close = lambda: None
    uploads = tmp_path / 'uploads'; uploads.mkdir()
    def factory(collection, options):
        store = VectorStore.__new__(VectorStore)
        store.client, store.collection_name, store.options = client, collection, options
        return SemanticRetriever(store, Encoder(), options)
    initial = factory('initial', IndexOptions(chunk_size=4, chunk_overlap=1))
    for name in ['a', 'b']:
        path = uploads / f'{name}.txt'
        path.write_text('le un deux trois quatre cinq six sept huit neuf dix onze')
        initial.index_document(path, title=name, category='Test')
    app = FastAPI()
    app.state.store, app.state.retriever = initial.store, initial
    manager = ReindexManager(app, tmp_path / 'state', uploads, factory)
    app.state.reindex = manager
    app.include_router(reindex.router); app.include_router(documents.router)
    return app, manager, factory, uploads


def wait(manager):
    manager.thread.join(timeout=10)
    assert not manager.thread.is_alive()
    return manager.snapshot()['job']


def test_reindex_preserves_identity_replaces_chunks_and_restores_configuration(setup):
    app, manager, factory, uploads = setup
    old = app.state.store
    ids = {d['document_id'] for d in old.list_documents()}
    old_count = old.client.count('initial').count
    job = manager.start(ReindexRequest(chunk_size=10, chunk_overlap=2, distance='Dot', batch_size=2))
    result = wait(manager)
    assert result['status'] == 'completed', result
    assert result['processed'] == 2 and result['passages'] == 4
    assert old.client.count('initial').count == old_count
    assert app.state.store.collection_name == job['target_collection']
    assert {d['document_id'] for d in app.state.store.list_documents()} == ids
    assert app.state.retriever.options.chunk_size == 10
    for id in ids:
        doc = app.state.store.get_document_content(id)
        assert doc['category'] == 'Test'
        assert doc['content'] == 'le un deux trois quatre cinq six sept huit neuf dix onze'
    restarted = SimpleNamespace(state=SimpleNamespace())
    restored = ReindexManager(restarted, manager.state_dir, uploads, factory)
    assert restored.active['collection'] == job['target_collection']
    assert restarted.state.retriever.options.distance == 'Dot'
    assert restarted.state.retriever.search('le texte')
    new_file = uploads / 'c.txt'; new_file.write_text(' '.join(['word'] * 30))
    _, count = restarted.state.retriever.index_document(new_file)
    assert count == 4


def test_missing_original_aborts_without_switching(setup):
    app, manager, _, uploads = setup
    (uploads / 'b.txt').unlink()
    original = app.state.retriever
    manager.start(ReindexRequest(allow_reconstructed=False))
    result = wait(manager)
    assert result['status'] == 'failed'
    assert 'original' in result['errors'][0]
    assert app.state.retriever is original
    assert not (manager.state_dir / 'active.json').exists()


def test_missing_file_falls_back_and_reports_it(setup):
    app, manager, _, uploads = setup
    (uploads / 'a.txt').unlink()
    manager.start(ReindexRequest())
    result = wait(manager)
    assert result['status'] == 'completed'
    assert result['reconstructed_documents'] == 1
    assert len(app.state.store.list_documents()) == 2


def test_cancel_and_exclusive_writes(setup):
    app, manager, _, _ = setup
    entered, release = Event(), Event()
    source = app.state.store
    original = source.list_documents
    def blocking():
        entered.set(); release.wait(5)
        return original()
    source.list_documents = blocking
    manager.start(ReindexRequest())
    assert entered.wait(3)
    try:
        assert http_request(app, 'POST', '/reindex', json={}).status_code == 409
        assert http_request(app, 'DELETE', '/documents/anything').status_code == 409
        assert http_request(app, 'POST', '/documents', files={'file': ('x.txt', b'x', 'text/plain')}).status_code == 409
        assert http_request(app, 'POST', '/reindex/cancel').status_code == 200
    finally:
        release.set()
    assert wait(manager)['status'] == 'cancelled'
    assert app.state.store is source


def test_active_upload_prevents_job_start(setup):
    app, manager, _, _ = setup
    with manager.mutation():
        assert http_request(app, 'POST', '/reindex', json={}).status_code == 409


def test_invalid_parameters_rejected_by_api(setup):
    app, manager, _, _ = setup
    for bad in [{'chunk_size': 20, 'chunk_overlap': 20}, {'distance':'wrong'},
                {'collection_prefix':'../bad'}, {'embedding_model':'/tmp/local'}, {'batch_size':0},
                {'unknown_parameter':True}]:
        assert http_request(app, 'POST', '/reindex', json=bad).status_code == 422
    assert manager.job is None


def test_restart_marks_incomplete_job_interrupted(setup):
    app, manager, factory, uploads = setup
    from src.indexing.jobs import atomic_json
    atomic_json(manager.state_dir / 'job.json', {'id':'old', 'status':'running'})
    recovered = ReindexManager(app, manager.state_dir, uploads, factory)
    assert recovered.job['status'] == 'interrupted'
    assert app.state.store.collection_name == 'initial'


def test_explicit_overlap_preserves_repeated_text():
    # Content-based overlap guesses would swallow the second full repeated block.
    assert VectorStore._merge_overlapping_chunks(['a a a a', 'a a a a'], overlap=1) == 'a a a a a a a'


def test_failure_during_encoding_does_not_activate(setup):
    app, manager, factory, _ = setup
    def broken(collection, options):
        retriever = factory(collection, options)
        def fail(*args, **kwargs):
            raise RuntimeError('encoding failed')
        retriever.encoder.encode = fail
        return retriever
    manager.factory = broken
    manager.start(ReindexRequest())
    assert wait(manager)['status'] == 'failed'
    assert app.state.store.collection_name == 'initial'
