import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="Recherche sémantique", layout="wide")
st.title("Recherche sémantique de documents")
st.caption("Interrogez les documents indexés à partir de leur sens.")

st.subheader("Ajouter un document")
with st.form("import_document", clear_on_submit=True):
    uploaded_file = st.file_uploader(
        "Document à indexer",
        type=["pdf", "docx", "txt", "md"],
        help="Formats acceptés : PDF, DOCX, TXT et Markdown.",
    )
    document_title = st.text_input("Titre du document (facultatif)")
    document_category = st.text_input("Catégorie (facultatif)")
    import_submitted = st.form_submit_button("Indexer le document", type="primary")

if import_submitted:
    if uploaded_file is None:
        st.warning("Sélectionnez un document avant de lancer l'indexation.")
    else:
        try:
            data = {}
            if document_title.strip():
                data["title"] = document_title.strip()
            if document_category.strip():
                data["category"] = document_category.strip()
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            response = requests.post(f"{API_URL}/documents", files=files, data=data, timeout=120)
            response.raise_for_status()
            indexed = response.json()
            st.success(f"Document indexé : {indexed['chunks_indexed']} passage(s) ajouté(s).")
        except requests.RequestException as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            st.error(f"Impossible d'indexer le document : {detail}")

st.subheader("Rechercher dans les documents")
with st.form("semantic_search"):
    query = st.text_input("Saisissez votre requête", placeholder="Exemple : fonctionnement d'une base vectorielle")
    limit = st.slider("Nombre de résultats", min_value=1, max_value=20, value=5)
    category = st.text_input("Filtrer par catégorie (facultatif)")
    search_submitted = st.form_submit_button("Rechercher", type="primary")

if search_submitted and query.strip():
    try:
        response = requests.post(f"{API_URL}/search", json={"query": query, "limit": limit, "category": category or None}, timeout=60)
        response.raise_for_status()
        results = response.json()["results"]
        if not results:
            st.warning("Aucun résultat trouvé.")
        for index, result in enumerate(results, 1):
            st.subheader(f"Résultat {index} — score : {result['score']:.4f}")
            st.write(result["text"])
            st.caption(f"Document : {result['title']}")
            st.divider()
    except requests.RequestException as exc:
        st.error(f"L'API est indisponible : {exc}")
