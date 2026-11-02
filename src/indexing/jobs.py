"""Réindexation en arrière-plan vers une nouvelle collection, puis activation."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from threading import Event, Lock, Thread
from uuid import uuid4

from src.config import settings
from src.database import VectorStore
from src.embeddings import EmbeddingEncoder
from src.extraction import extract_text
from src.indexing.options import IndexOptions, ReindexRequest
from src.preprocessing import clean_text, split_into_chunks
from src.search import SemanticRetriever

logger = logging.getLogger(__name__)
ACTIVE_STATES = {"queued", "running", "cancelling"}


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def make_retriever(collection: str, options: IndexOptions):
    store = VectorStore(settings.qdrant_url, settings.qdrant_api_key, collection, options)
    encoder = EmbeddingEncoder(options.embedding_model, normalize=options.normalize_embeddings,
                               device=options.device, max_seq_length=options.max_seq_length)
    return SemanticRetriever(store, encoder, options)


class Cancelled(Exception):
    pass


class ReindexManager:
    """Un seul travail et un seul processus API ; les recherches restent disponibles."""
    def __init__(self, app, state_dir: Path, uploads: Path, factory=make_retriever):
        self.app, self.state_dir, self.uploads, self.factory = app, state_dir, uploads, factory
        self.lock, self.cancel_event = Lock(), Event()
        self.writers = 0
        self.thread = None
        self.job = None
        self.active = {"collection": settings.collection_name, "options": IndexOptions().model_dump()}
        if (state_dir / "active.json").exists():
            self.active = json.loads((state_dir / "active.json").read_text())
            retriever = factory(self.active["collection"], IndexOptions(**self.active["options"]))
            app.state.retriever, app.state.store = retriever, retriever.store
        if (state_dir / "job.json").exists():
            self.job = json.loads((state_dir / "job.json").read_text())
            if self.job["status"] in ACTIVE_STATES:
                # A durable active pointer is the commit record if shutdown happened just after activation.
                committed = self.active.get("job_id") == self.job["id"]
                self.job.update(status="completed" if committed else "interrupted", finished_at=now(),
                                message="Index activé." if committed else "Traitement interrompu par le redémarrage de l’API. Relancez une réindexation.")
                atomic_json(state_dir / "job.json", self.job)

    def snapshot(self):
        with self.lock:
            return deepcopy({"active": self.active, "job": self.job})

    @contextmanager
    def mutation(self):
        with self.lock:
            if self.job and self.job["status"] in ACTIVE_STATES:
                raise ValueError("Une réindexation est en cours. Les ajouts et suppressions reprendront à sa fin.")
            self.writers += 1
        try:
            yield
        finally:
            with self.lock:
                self.writers -= 1

    def start(self, request: ReindexRequest):
        with self.lock:
            if self.writers or (self.job and self.job["status"] in ACTIVE_STATES):
                raise ValueError("Une modification ou une réindexation est déjà en cours.")
            job_id = uuid4().hex
            self.job = {"id": job_id, "status": "queued", "started_at": now(), "finished_at": None,
                        "source_collection": self.app.state.store.collection_name,
                        "target_collection": f"{request.collection_prefix}_{job_id}",
                        "parameters": request.model_dump(), "total": 0, "processed": 0,
                        "passages": 0, "truncated_passages": 0, "reconstructed_documents": 0,
                        "current_document": "", "message": "Préparation du corpus.", "errors": []}
            atomic_json(self.state_dir / "job.json", self.job)
            self.cancel_event.clear()
            source = self.app.state.store
            self.thread = Thread(target=self._run, args=(source, request), daemon=True, name="reindex")
            result = deepcopy(self.job)
            self.thread.start()
            return result

    def cancel(self):
        with self.lock:
            if not self.job or self.job["status"] not in ACTIVE_STATES:
                raise ValueError("Aucune réindexation en cours.")
            self.cancel_event.set()
            self.job.update(status="cancelling", message="Annulation demandée ; arrêt après le calcul en cours.")
            atomic_json(self.state_dir / "job.json", self.job)
            return deepcopy(self.job)

    def _update(self, **values):
        with self.lock:
            self.job.update(values)
            atomic_json(self.state_dir / "job.json", self.job)

    def _check_cancel(self):
        if self.cancel_event.is_set():
            raise Cancelled()

    def _managed_source(self, source):
        if not source:
            return None
        path = Path(source)
        root = self.uploads.resolve()
        candidates = [path, root / path.name]  # Supports the same mounted upload in host and Docker paths.
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.is_relative_to(root) and resolved.is_file():
                return resolved
        return None

    def _run(self, source, request):
        target = None
        committed = False
        try:
            self._update(status="running", message="Lecture de la liste des documents.")
            if not source.client.collection_exists(source.collection_name):
                raise ValueError("L’index actif est vide. Importez des documents avant de le réindexer.")
            documents = source.list_documents()
            if not documents:
                raise ValueError("Aucun document à réindexer.")
            self._update(total=len(documents), message="Chargement du modèle. Un premier téléchargement peut prendre plusieurs minutes.")
            options = IndexOptions(**request.model_dump(include=set(IndexOptions.model_fields)))
            self._check_cancel()
            target = self.factory(self.job["target_collection"], options)
            dimension = target.encoder.dimension
            self._check_cancel()
            target.store.ensure_collection(dimension)
            self._update(dimension=dimension, effective_max_tokens=target.encoder.model.max_seq_length)
            for position, summary in enumerate(documents, 1):
                self._check_cancel()
                self._update(current_document=summary.get("title") or summary["document_id"], message="Extraction et découpage du document.")
                doc = source.get_document_content(summary["document_id"])
                if doc is None:
                    raise ValueError("Un document source a disparu pendant la lecture.")
                path = self._managed_source(doc.get("source"))
                fallback = request.source_mode == "indexed_text" or path is None or doc.get("storage_kind") == "reconstructed"
                if fallback:
                    if not request.allow_reconstructed:
                        raise ValueError(f"Texte reconstitué interdit pour {doc['title']}. Le fichier original est requis.")
                    text = doc["content"]
                    self._update(reconstructed_documents=self.job["reconstructed_documents"] + 1)
                else:
                    text = extract_text(path)
                if options.clean_text:
                    text = clean_text(text)
                chunks = split_into_chunks(text, options.chunk_size, options.chunk_overlap)
                if not chunks:
                    raise ValueError(f"Aucun texte indexable dans {doc['title']}.")
                language = SemanticRetriever._detect_language(text)
                for start in range(0, len(chunks), options.batch_size):
                    self._check_cancel()
                    batch = chunks[start:start + options.batch_size]
                    lengths = target.encoder.model.tokenizer(batch, truncation=False, add_special_tokens=True)["input_ids"]
                    truncated = sum(len(tokens) > target.encoder.model.max_seq_length for tokens in lengths)
                    passages = [{"document_id": doc["document_id"],
                                 "passage_id": f"{doc['document_id']}_chunk_{start+i:04d}",
                                 "chunk_index": start+i, "chunk_overlap": options.chunk_overlap,
                                 "text": chunk, "title": doc["title"], "category": doc.get("category"),
                                 "source": str(path) if path else doc.get("source"),
                                 "original_filename": doc.get("original_filename"),
                                 "storage_kind": doc.get("storage_kind", "unknown"), "language": language}
                                for i, chunk in enumerate(batch)]
                    self._update(message="Calcul et enregistrement des vecteurs.")
                    vectors = target.encoder.encode(batch, batch_size=options.batch_size)
                    self._check_cancel()
                    target.store.upsert_passages(passages, vectors)
                    self._update(passages=self.job["passages"] + len(batch),
                                 truncated_passages=self.job["truncated_passages"] + truncated)
                self._update(processed=position)
            self._check_cancel()
            self._update(message="Vérification du nouvel index.")
            actual = target.store.client.count(collection_name=target.store.collection_name, exact=True).count
            if actual != self.job["passages"] or len(target.store.list_documents()) != len(documents):
                raise ValueError("La vérification du nombre de passages ou de documents a échoué.")
            with self.lock:
                self._check_cancel()
                active = {"collection": target.store.collection_name, "options": options.model_dump(),
                          "previous_collection": source.collection_name, "job_id": self.job["id"], "activated_at": now()}
                atomic_json(self.state_dir / "active.json", active)
                self.app.state.retriever = target
                self.app.state.store = target.store
                self.active = active
                committed = True
                self.job.update(status="completed", finished_at=now(), message="Nouvel index actif. L’ancienne collection est conservée.")
                atomic_json(self.state_dir / "job.json", self.job)
        except Cancelled:
            self._update(status="cancelled", finished_at=now(), message="Réindexation annulée. L’index actif est conservé.")
        except Exception as exc:
            logger.exception("Réindexation interrompue")
            if not committed:
                self._update(status="failed", finished_at=now(), errors=[str(exc)],
                             message="Échec de la réindexation. L’index actif est conservé.")
        finally:
            # Staging collections remain available for diagnosis; never delete user data on failure.
            if target is not None and not committed:
                target.store.client.close()
