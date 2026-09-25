import os
from urllib.parse import quote
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", API_URL)
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))
st.set_page_config(page_title="Recherche sémantique", layout="wide")
st.title("Recherche sémantique de documents")
st.caption("Interrogez les documents indexés à partir de leur sens.")

st.session_state.setdefault("search_results", [])
st.session_state.setdefault("last_search_query", "")

DEFAULT_DOCUMENT_CATEGORIES = [
    "Actualités",
    "Droit et réglementation",
    "Économie et entreprises",
    "Éducation",
    "Informatique et technologies",
    "Santé et recherche biomédicale",
    "Sciences et technologies",
    "Sport",
]


@st.cache_data(ttl=60, max_entries=4)
def fetch_documents() -> list[dict]:
    response = requests.get(f"{API_URL}/documents", timeout=20)
    response.raise_for_status()
    return response.json()


def reset_result_filters() -> None:
    for key in ("result_min_score", "result_categories", "result_documents", "result_text"):
        st.session_state.pop(key, None)


@st.cache_data(ttl=60, max_entries=20)
def fetch_document_content(document_id: str) -> dict:
    response = requests.get(f"{API_URL}/documents/{document_id}/content", timeout=30)
    response.raise_for_status()
    return response.json()


@st.dialog("Consulter le document", width="large", icon=":material/article:")
def open_document_dialog(result: dict) -> None:
    """Affiche le texte complet reconstitué du document sélectionné."""
    document_id = result["document_id"]
    loading_slot = st.empty()
    try:
        with loading_slot.container():
            with st.status("Chargement du document indexé...", expanded=True) as status:
                st.write("Récupération des passages dans la base vectorielle.")
                document = fetch_document_content(document_id)
                st.write("Reconstitution du contenu dans son ordre d'indexation.")
                status.update(label="Document prêt à consulter", state="complete", expanded=False)
        loading_slot.empty()
    except requests.RequestException as exc:
        loading_slot.empty()
        detail = exc.response.text if exc.response is not None else str(exc)
        st.error(f"Impossible d'ouvrir ce document : {detail}")
        return

    st.subheader(document["title"])
    metadata = [f"{document['chunks_indexed']} passage(s) indexé(s)"]
    if document.get("category"):
        metadata.insert(0, f"Catégorie : {document['category']}")
    st.caption(" · ".join(metadata))
    st.caption(f"Fichier : {document['original_filename']}")

    if document["original_available"] and not document.get("original_is_reconstructed", False):
        st.link_button(
            "Télécharger le fichier original",
            url=f"{PUBLIC_API_URL}/documents/{quote(document_id, safe='')}/download",
            icon=":material/download:",
            type="primary",
        )
    else:
        st.info("Le fichier original n'est pas disponible ; seul le texte reconstitué depuis l'index peut être téléchargé.")

    st.download_button(
        "Télécharger le texte indexé",
        data=document["content"],
        file_name=f"{document_id}.txt",
        mime="text/plain",
        icon=":material/download:",
        width="content",
    )
    st.text_area(
        "Contenu du document indexé",
        value=document["content"],
        height=480,
        disabled=True,
    )

@st.dialog("Ajouter un document", width="large", icon=":material/upload_file:")
def import_document_dialog() -> None:
    st.caption("Formats acceptés : PDF, DOCX, TXT et Markdown.")
    try:
        existing_categories = [
            document["category"]
            for document in fetch_documents()
            if document.get("category")
        ]
    except requests.RequestException:
        existing_categories = []
    category_options = sorted(set(DEFAULT_DOCUMENT_CATEGORIES + existing_categories))

    with st.form("import_document", clear_on_submit=True):
        uploaded_file = st.file_uploader(
            "Document à indexer",
            type=["pdf", "docx", "txt", "md"],
            max_upload_size=MAX_UPLOAD_SIZE_MB,
        )
        document_title = st.text_input("Titre du document (facultatif)")
        document_category = st.selectbox(
            "Catégorie du document",
            options=category_options,
            index=None,
            placeholder="Choisir ou saisir une catégorie",
            accept_new_options=True,
            help="La catégorie servira aux filtres avant et après la recherche.",
        )
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
    if not document_category or not document_category.strip():
        st.warning("Choisissez ou saisissez une catégorie avant de lancer l'indexation.")
        return

    status = st.status("Préparation de l'indexation...", expanded=True)
    try:
        with status:
            st.write("Lecture du fichier sélectionné.")
            data = {}
            if document_title.strip():
                data["title"] = document_title.strip()
            data["category"] = document_category.strip()
            uploaded_file.seek(0)
            files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
            st.write("Envoi du document à l'API et création des embeddings.")
            response = requests.post(f"{API_URL}/documents", files=files, data=data, timeout=120)
            response.raise_for_status()
            indexed = response.json()
            st.write("Document indexé dans la base vectorielle.")
        status.update(label="Indexation terminée", state="complete", expanded=False)
        st.session_state.import_feedback = (
            f"Document indexé : {indexed['chunks_indexed']} passage(s) ajouté(s)."
        )
        fetch_documents.clear()
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
try:
    indexed_documents = fetch_documents()
except requests.RequestException:
    indexed_documents = []
    st.info("Les filtres par document seront disponibles dès que l'API sera accessible.")

available_categories = sorted(
    {document["category"] for document in indexed_documents if document.get("category")}
)
document_labels = {
    f"{document['title']} — {document['document_id'][:8]}": document["document_id"]
    for document in indexed_documents
}

with st.form("semantic_search"):
    query = st.text_input("Saisissez votre requête", placeholder="Exemple : fonctionnement d'une base vectorielle")
    limit = st.slider("Nombre de résultats à récupérer", min_value=1, max_value=20, value=5)
    with st.expander("Filtres avant la recherche", expanded=True):
        pre_categories = st.multiselect(
            "Catégories à interroger",
            options=available_categories,
            placeholder="Toutes les catégories",
            help="La recherche ne sera exécutée que sur les passages des catégories choisies.",
        )
        pre_documents = st.multiselect(
            "Documents à interroger",
            options=list(document_labels),
            placeholder="Tous les documents indexés",
            help="Vous pouvez limiter la recherche à un ou plusieurs documents précis.",
        )
    search_submitted = st.form_submit_button("Rechercher", type="primary", icon=":material/search:")

if search_submitted and query.strip():
    status = st.status("Recherche sémantique en cours...", expanded=True)
    try:
        with status:
            st.write("Encodage de la requête.")
            st.write("Interrogation de la base vectorielle.")
            response = requests.post(
                f"{API_URL}/search",
                json={
                    "query": query.strip(),
                    "limit": limit,
                    "categories": pre_categories or None,
                    "document_ids": [document_labels[label] for label in pre_documents] or None,
                },
                timeout=60,
            )
            response.raise_for_status()
            results = response.json()["results"]
            st.write("Classement des résultats terminé.")
        status.update(label="Recherche terminée", state="complete", expanded=False)
        st.session_state.search_results = results
        st.session_state.last_search_query = query.strip()
        reset_result_filters()
    except requests.RequestException as exc:
        status.update(label="Échec de la recherche", state="error", expanded=True)
        st.error(f"L'API est indisponible : {exc}")
        st.session_state.search_results = []
        st.session_state.last_search_query = query.strip()
        reset_result_filters()
elif search_submitted:
    st.warning("Saisissez une requête avant de lancer la recherche.")


results = st.session_state.search_results
if results:
    st.subheader("Résultats de la recherche")
    st.caption(f"Requête exécutée : « {st.session_state.last_search_query} »")

    result_categories = sorted({result["category"] for result in results if result.get("category")})
    result_labels = {
        f"{result['title']} — {result['document_id'][:8]}": result["document_id"]
        for result in results
    }
    lowest_score = min(float(result["score"]) for result in results)
    highest_score = max(float(result["score"]) for result in results)

    with st.expander("Affiner les résultats obtenus", expanded=True):
        st.caption("Ces filtres s'appliquent immédiatement aux résultats affichés et ne relancent pas la recherche sémantique.")
        result_min_score = st.number_input(
            "Score minimal",
            min_value=lowest_score,
            max_value=highest_score,
            value=lowest_score,
            step=0.01,
            format="%.4f",
            key="result_min_score",
        )
        selected_result_categories = st.multiselect(
            "Catégories des résultats",
            options=result_categories,
            placeholder="Toutes les catégories",
            key="result_categories",
        )
        selected_result_documents = st.multiselect(
            "Documents des résultats",
            options=list(result_labels),
            placeholder="Tous les documents",
            key="result_documents",
        )
        result_text = st.text_input(
            "Mot ou expression dans le résultat",
            placeholder="Exemple : vecteur",
            key="result_text",
        )
        st.button(
            "Réinitialiser les filtres",
            icon=":material/filter_alt_off:",
            on_click=reset_result_filters,
        )

    selected_document_ids = {result_labels[label] for label in selected_result_documents}
    refined_results = [
        result
        for result in results
        if float(result["score"]) >= result_min_score
        and (not selected_result_categories or result.get("category") in selected_result_categories)
        and (not selected_document_ids or result.get("document_id") in selected_document_ids)
        and (
            not result_text.strip()
            or result_text.strip().casefold() in result.get("text", "").casefold()
            or result_text.strip().casefold() in result.get("title", "").casefold()
        )
    ]

    st.caption(f"{len(refined_results)} résultat(s) affiché(s) sur {len(results)} résultat(s) récupéré(s).")
    if not refined_results:
        st.warning("Aucun résultat ne correspond aux filtres appliqués.")
    for index, result in enumerate(refined_results, 1):
        with st.container(border=True):
            st.subheader(f"Résultat {index} — score : {result['score']:.4f}")
            st.write(result["text"])
            category_label = result.get("category") or "Sans catégorie"
            st.caption(f"Document : {result['title']} · Catégorie : {category_label}")
            if st.button(
                "Ouvrir le document",
                key=f"open_document_{result['passage_id']}",
                icon=":material/open_in_new:",
            ):
                open_document_dialog(result)
elif st.session_state.last_search_query:
    st.warning("Aucun résultat trouvé pour cette requête et les filtres appliqués.")
