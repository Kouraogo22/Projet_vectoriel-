"""Page de pilotage des travaux de réindexation gérés par l'API."""
import json
import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
ACTIVE = {"queued", "running", "cancelling"}


def api(method="GET", path="", **kwargs):
    response = requests.request(method, f"{API_URL}/reindex{path}", timeout=15, **kwargs)
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ValueError(str(detail))
    return response.json()


st.title("Réindexer les documents")
st.caption("Reconstruisez l’ensemble des documents indexés avec de nouveaux réglages.")
try:
    state = api()
except (requests.RequestException, ValueError) as exc:
    st.error(f"Le service de réindexation n’est pas accessible : {exc}")
    st.stop()

current = state["active"]; defaults = current["options"]
busy = bool(state["job"] and state["job"]["status"] in ACTIVE)
st.write(f"**Collection active :** {current['collection']}")
st.caption(f"Modèle : {defaults['embedding_model']} · {defaults['chunk_size']} mots · {defaults['chunk_overlap']} mots de chevauchement inclus")
st.info("Le nouvel index devient actif uniquement lorsque tous les documents sont traités et vérifiés. La recherche reste disponible ; les ajouts et suppressions sont suspendus pendant le traitement. L’ancienne collection est conservée.")

with st.form("reindex_parameters"):
    st.subheader("Documents sources")
    source = st.selectbox("Texte à utiliser", ["originals_preferred", "indexed_text"],
                          format_func=lambda x: {"originals_preferred": "Relire les fichiers conservés en priorité", "indexed_text": "Repartir du texte présent dans l’index"}[x],
                          help="Tous les documents de l’index actif sont repris. Les fichiers non encore importés ne sont pas ajoutés.")
    reconstruct = st.checkbox("Autoriser le texte reconstitué quand l’original est absent", value=True,
                              help="La reconstitution reprend les passages enregistrés ; elle ne peut pas restaurer des informations absentes de l’ancien index.")
    prefix = st.text_input("Nom de la nouvelle collection", value="documents_reindex", max_chars=60,
                           help="Lettres, chiffres, tirets et underscores. Un identifiant unique sera ajouté automatiquement.")
    st.subheader("Découpage des documents")
    a, b = st.columns(2)
    size = a.number_input("Mots par passage", min_value=1, max_value=10000, value=defaults["chunk_size"])
    overlap = b.number_input("Mots de chevauchement", min_value=0, max_value=9999, value=defaults["chunk_overlap"])
    st.caption("Le chevauchement fait partie du total : 60 mots avec 20 mots de chevauchement donnent des passages de 60 mots, avec 40 nouveaux mots à chaque étape.")
    cleaning = st.checkbox("Nettoyer les caractères nuls et normaliser les espaces", value=defaults["clean_text"])
    st.subheader("Modèle et calcul des embeddings")
    model = st.text_input("Identifiant du modèle Sentence Transformers", value=defaults["embedding_model"],
                          help="Identifiant Hugging Face sous la forme organisation/modèle. Le premier chargement peut télécharger le modèle. Sa dimension est détectée automatiquement.")
    a, b = st.columns(2)
    device = a.selectbox("Processeur utilisé", ["cpu", "cuda", "mps"], index=["cpu", "cuda", "mps"].index(defaults["device"]),
                          help="CPU : processeur classique. CUDA : GPU NVIDIA. MPS : GPU Apple, pour une API lancée directement sur le Mac. Le matériel doit être disponible côté API.")
    batch = b.number_input("Passages par lot de calcul", 1, 256, defaults["batch_size"],
                           help="Un lot plus grand utilise davantage de mémoire.")
    normalize = st.checkbox("Normaliser les vecteurs", value=defaults["normalize_embeddings"])
    max_tokens = st.number_input("Limite de tokens par passage — 0 pour la limite du modèle", 0, 32768, defaults["max_seq_length"] or 0,
                                 help="Une valeur personnalisée doit être au moins 8 et ne peut pas dépasser la limite native du modèle. Les dépassements seront comptés dans le bilan.")
    with st.expander("Paramètres avancés de Qdrant"):
        distances = ["Cosine", "Dot", "Euclid", "Manhattan"]
        distance = st.selectbox("Mesure de similarité ou de distance", distances, index=distances.index(defaults["distance"]),
                                help="Cosine compare les directions ; Dot le produit scalaire ; Euclid et Manhattan des distances. Avec une distance, les valeurs les plus faibles sont les plus proches.")
        on_disk = st.checkbox("Stocker les vecteurs sur disque", value=defaults["on_disk"])
        upload_batch = st.number_input("Passages par envoi vers Qdrant", 1, 1024, defaults["upload_batch_size"])
        a, b = st.columns(2)
        m = a.number_input("Liens par nœud HNSW", 0, 128, defaults["hnsw_m"], help="Contrôle les connexions de l’index de recherche. 0 désactive sa construction.")
        ef = b.number_input("Précision de construction HNSW", 4, 1024, defaults["ef_construct"], help="Une valeur élevée augmente le travail nécessaire pour construire l’index.")
        full_scan = st.number_input("Seuil de recherche exhaustive en Ko", 0, 1000000, defaults["full_scan_threshold"],
                                    help="Sous ce volume estimé de vecteurs candidats, Qdrant peut préférer un parcours exhaustif.")
        indexing = st.number_input("Seuil de construction de l’index en Ko", 0, 1000000, defaults["indexing_threshold"],
                                   help="Volume de vecteurs à partir duquel Qdrant construit HNSW. 0 désactive l’indexation HNSW automatique.")
    submitted = st.form_submit_button("Lancer la réindexation", type="primary", icon=":material/sync:", disabled=busy)

if submitted:
    if overlap >= size:
        st.error("Le chevauchement doit être inférieur au nombre de mots par passage.")
    elif max_tokens and max_tokens < 8:
        st.error("Choisissez 0 ou une limite d’au moins 8 tokens.")
    elif source == "indexed_text" and not reconstruct:
        st.error("Autorisez la reconstitution pour utiliser le texte présent dans l’index.")
    else:
        try:
            api("POST", json={"chunk_size": size, "chunk_overlap": overlap, "clean_text": cleaning,
                 "embedding_model": model.strip(), "device": device, "batch_size": batch,
                 "normalize_embeddings": normalize, "max_seq_length": max_tokens or None,
                 "distance": distance, "on_disk": on_disk, "upload_batch_size": upload_batch,
                 "hnsw_m": m, "ef_construct": ef, "full_scan_threshold": full_scan,
                 "indexing_threshold": indexing, "source_mode": source,
                 "allow_reconstructed": reconstruct, "collection_prefix": prefix.strip()})
            st.rerun()
        except (requests.RequestException, ValueError) as exc:
            st.error(f"Impossible de démarrer : {exc}")


@st.fragment(run_every="2s" if busy else None)
def progress():
    try:
        latest = api()
    except (requests.RequestException, ValueError) as exc:
        st.warning(f"Suivi temporairement indisponible : {exc}")
        return
    job = latest["job"]
    if not job:
        st.caption("Aucune réindexation lancée depuis cette page.")
        return
    running = job["status"] in ACTIVE
    if running != busy:
        st.cache_data.clear()
        st.session_state.pop("search_results", None)
        st.session_state.pop("last_search_query", None)
        st.rerun()
    st.subheader("Suivi du dernier traitement")
    labels = {"queued": "En attente", "running": "En cours", "cancelling": "Annulation en cours",
              "completed": "Terminé", "failed": "Échec", "cancelled": "Annulé", "interrupted": "Interrompu"}
    st.write(f"**{labels.get(job['status'], job['status'])}** — {job['message']}")
    total = job["total"]
    st.progress(job["processed"] / total if total else 0,
                text=f"{job['processed']} / {total} documents traités")
    a, b, c = st.columns(3)
    a.metric("Passages enregistrés", job["passages"])
    b.metric("Passages tronqués", job["truncated_passages"])
    c.metric("Documents reconstitués", job["reconstructed_documents"])
    if job["current_document"]:
        st.caption(f"Dernier document traité : {job['current_document']}")
    st.caption(f"Début : {job['started_at']} · Nouvelle collection : {job['target_collection']}")
    if job.get("effective_max_tokens"):
        st.caption(f"Vecteurs : {job['dimension']} dimensions · Limite effective : {job['effective_max_tokens']} tokens")
    for error in job["errors"]:
        st.error(error)
    if job["status"] == "completed":
        st.success("Les recherches et les prochains imports utilisent maintenant les nouveaux paramètres.")
    if running and st.button("Annuler le traitement", disabled=job["status"] == "cancelling"):
        try:
            api("POST", "/cancel")
            st.rerun()
        except (requests.RequestException, ValueError) as exc:
            st.error(str(exc))
    if not running:
        st.download_button("Télécharger le bilan et les paramètres", json.dumps(job, ensure_ascii=False, indent=2),
                           file_name=f"reindexation_{job['id']}.json", mime="application/json")
    with st.expander("Paramètres utilisés pour ce traitement"):
        st.json(job["parameters"])


progress()
