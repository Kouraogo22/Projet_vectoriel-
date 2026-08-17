import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="Recherche sémantique", layout="wide")
st.title("Recherche sémantique de documents")
st.caption("Interrogez les documents indexés à partir de leur sens.")

query = st.text_input("Saisissez votre requête", placeholder="Exemple : fonctionnement d'une base vectorielle")
limit = st.slider("Nombre de résultats", min_value=1, max_value=20, value=5)
category = st.text_input("Catégorie (facultatif)")
if st.button("Rechercher", type="primary") and query.strip():
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
