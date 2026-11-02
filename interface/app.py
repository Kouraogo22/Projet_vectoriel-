import streamlit as st

st.set_page_config(page_title="Recherche sémantique", layout="wide")
st.navigation([
    st.Page("app_pages/search.py", title="Recherche", icon=":material/search:", default=True),
    st.Page("app_pages/documents.py", title="Documents", icon=":material/folder:", url_path="documents"),
    st.Page("app_pages/reindex.py", title="Réindexation", icon=":material/sync:", url_path="reindexation"),
], position="top").run()
