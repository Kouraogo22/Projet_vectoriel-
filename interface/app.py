import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="Recherche sémantique", layout="wide")
st.title("Recherche sémantique de documents")
st.caption("Interrogez les documents indexés à partir de leur sens.")

@st.dialog("Ajouter un document", width="large", icon=":material/upload_file:")
def import_document_dialog() -> None:
    st.caption("Formats acceptés : PDF, DOCX, TXT et Markdown.")
    with st.form("import_document", clear_on_submit=True):
        uploaded_file = st.file_uploader(
            "Document à indexer",
            type=["pdf", "docx", "txt", "md"],
        )
        document_title = st.text_input("Titre du document (facultatif)")
        document_category = st.text_input("Catégorie (facultatif)")
        import_submitted = st.form_submit_button(
            "Indexer le document",
            type="primary",
            icon=":material/database_upload:",
        )

    if not import_submitted:
        return
    if uploaded_file is None:
        st.warning("Sélectionnez un document avant de lancer l'indexation.")
        return

    status = st.status("Préparation de l'indexation...", expanded=True)
    try:
        with status:
            st.write("Lecture du fichier sélectionné.")
            data = {}
            if document_title.strip():
                data["title"] = document_title.strip()
            if document_category.strip():
                data["category"] = document_category.strip()
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            st.write("Envoi du document à l'API et création des embeddings.")
            response = requests.post(f"{API_URL}/documents", files=files, data=data, timeout=120)
            response.raise_for_status()
            indexed = response.json()
            st.write("Document indexé dans la base vectorielle.")
        status.update(label="Indexation terminée", state="complete", expanded=False)
        st.session_state.import_feedback = (
            f"Document indexé : {indexed['chunks_indexed']} passage(s) ajouté(s)."
        )
        st.rerun()
    except requests.RequestException as exc:
        status.update(label="Échec de l'indexation", state="error", expanded=True)
        detail = exc.response.text if exc.response is not None else str(exc)
        st.error(f"Impossible d'indexer le document : {detail}")


with st.container(horizontal=True, horizontal_alignment="right"):
    if st.button("Ajouter un document", type="primary", icon=":material/upload_file:"):
        import_document_dialog()

if feedback := st.session_state.pop("import_feedback", None):
    st.success(feedback)

st.subheader("Rechercher dans les documents")
with st.form("semantic_search"):
    query = st.text_input("Saisissez votre requête", placeholder="Exemple : fonctionnement d'une base vectorielle")
    limit = st.slider("Nombre de résultats", min_value=1, max_value=20, value=5)
    category = st.text_input("Filtrer par catégorie (facultatif)")
    search_submitted = st.form_submit_button("Rechercher", type="primary")

if search_submitted and query.strip():
    status = st.status("Recherche sémantique en cours...", expanded=True)
    try:
        with status:
            st.write("Encodage de la requête.")
            st.write("Interrogation de la base vectorielle.")
            response = requests.post(
                f"{API_URL}/search",
                json={"query": query, "limit": limit, "category": category or None},
                timeout=60,
            )
            response.raise_for_status()
            results = response.json()["results"]
            st.write("Classement des résultats terminé.")
        status.update(label="Recherche terminée", state="complete", expanded=False)
        if not results:
            st.warning("Aucun résultat trouvé.")
        for index, result in enumerate(results, 1):
            st.subheader(f"Résultat {index} — score : {result['score']:.4f}")
            st.write(result["text"])
            st.caption(f"Document : {result['title']}")
            st.divider()
    except requests.RequestException as exc:
        status.update(label="Échec de la recherche", state="error", expanded=True)
        st.error(f"L'API est indisponible : {exc}")
elif search_submitted:
    st.warning("Saisissez une requête avant de lancer la recherche.")
