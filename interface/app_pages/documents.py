"""Liste filtrable et suppression explicite des documents de l'index actif."""
import os
from urllib.parse import quote
from uuid import uuid4

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
st.title("Documents")
st.caption("Consultez les documents indexés et sélectionnez ceux à supprimer.")

if feedback := st.session_state.pop("documents_feedback", None):
    if feedback["deleted"]:
        st.success(f"{len(feedback['deleted'])} document(s) supprimé(s).")
    for message in feedback["errors"]:
        st.error(message)

st.button("Actualiser la liste", icon=":material/refresh:")
try:
    response = requests.get(f"{API_URL}/documents", timeout=30)
    response.raise_for_status()
    documents = sorted(response.json(), key=lambda d: ((d.get("title") or "").casefold(), d["document_id"]))
except requests.RequestException as exc:
    st.error(f"Impossible de charger les documents : {exc}")
    st.stop()

if st.session_state.pop("documents_reset_selection", False):
    st.session_state.pop("documents_selection", None)

collection = None
busy = True
try:
    response = requests.get(f"{API_URL}/reindex", timeout=10)
    response.raise_for_status()
    state = response.json()
    collection = state["active"]["collection"]
    busy = bool(state["job"] and state["job"]["status"] in {"queued", "running", "cancelling"})
    if busy:
        st.info("Une réindexation est en cours. La suppression sera disponible à sa fin.")
except requests.RequestException:
    st.warning("L’état de l’index est indisponible. La suppression est temporairement désactivée.")

st.caption(f"{len(documents)} document(s) dans l’index actif.")
if not documents:
    st.info("Aucun document indexé. Ajoutez un document depuis la page Recherche.")
    st.session_state.pop("documents_pending", None)
    st.stop()

query = st.text_input("Rechercher un document", placeholder="Titre ou identifiant")
categories = st.multiselect("Filtrer par catégorie", sorted({d.get("category") or "Sans catégorie" for d in documents}))
filtered = [d for d in documents
            if (not categories or (d.get("category") or "Sans catégorie") in categories)
            and (not query.strip() or query.strip().casefold() in (d.get("title") or "").casefold()
                 or query.strip().casefold() in d["document_id"].casefold())]
st.caption(f"{len(filtered)} document(s) affiché(s).")
st.dataframe([{"Titre": d.get("title") or "Sans titre", "Catégorie": d.get("category") or "Sans catégorie",
               "Identifiant": d["document_id"]} for d in filtered], hide_index=True, width="stretch")
by_id = {d["document_id"]: d for d in filtered}
selected = st.multiselect("Documents à supprimer", options=list(by_id),
                          format_func=lambda id: f"{by_id[id].get('title') or 'Sans titre'} — {id}",
                          key="documents_selection", disabled=busy,
                          help="Sélectionnez un ou plusieurs documents parmi la liste filtrée.")
# A confirmation never carries over to another selection or another index.
pending = st.session_state.get("documents_pending")
if pending and (pending["ids"] != selected or pending["collection"] != collection):
    st.session_state.pop("documents_pending", None)
    pending = None

if st.button("Supprimer la sélection", icon=":material/delete:", disabled=busy or not selected):
    pending = {"ids": list(selected), "collection": collection, "nonce": uuid4().hex,
               "titles": {id: by_id[id].get("title") or "Sans titre" for id in selected}}
    st.session_state.documents_pending = pending

if pending:
    st.subheader("Confirmer la suppression")
    st.write(f"Vous allez supprimer {len(pending['ids'])} document(s) :")
    for id in pending["ids"]:
        st.write(f"• {pending['titles'][id]} — {id}")
    st.warning("Cette action supprime leurs passages de l’index actif et leurs fichiers conservés dans l’application. Elle est définitive. Les anciennes collections de réindexation ne sont pas purgées.")
    confirmed = st.checkbox("Je confirme la suppression de ces documents", key=f"documents_confirm_{pending['nonce']}")
    a, b = st.columns(2)
    if b.button("Annuler", key="documents_cancel"):
        st.session_state.pop("documents_pending", None)
        st.rerun()
    if a.button("Confirmer et supprimer", type="primary", disabled=busy or not confirmed):
        deleted, errors = [], []
        progress = st.progress(0, text="Suppression en cours…")
        for index, id in enumerate(pending["ids"], 1):
            try:
                response = requests.delete(f"{API_URL}/documents/{quote(id, safe='')}",
                                           params={"expected_collection": pending["collection"]}, timeout=30)
                response.raise_for_status()
                deleted.append(id)
            except requests.RequestException as exc:
                detail = str(exc)
                if exc.response is not None:
                    try:
                        detail = exc.response.json().get("detail", detail)
                    except ValueError:
                        pass
                errors.append(f"Suppression non confirmée pour {pending['titles'][id]} : {detail}")
                if exc.response is None or exc.response.status_code == 409:
                    errors.append("Traitement arrêté. Actualisez la liste avant de réessayer les documents restants.")
                    break
            progress.progress(index / len(pending["ids"]), text=f"{index} / {len(pending['ids'])} document(s) traités")
        st.cache_data.clear()
        st.session_state.search_results = []
        st.session_state.last_search_query = ""
        st.session_state.documents_feedback = {"deleted": deleted, "errors": errors}
        st.session_state.pop("documents_pending", None)
        # Change the widget state on the next run, before its construction.
        st.session_state.documents_reset_selection = True
        st.rerun()
