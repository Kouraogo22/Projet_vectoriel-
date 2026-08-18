# Recherche sémantique de documents

Prototype d'indexation sémantique : extraction des documents PDF/DOCX/TXT, découpage en passages, génération d'embeddings et recherche par similarité avec Qdrant.

## Démarrage

1. Copiez `.env.example` vers `.env` et adaptez les paramètres si nécessaire.
2. Lancez Qdrant : `docker compose up qdrant -d`.
3. Activez l'environnement Python puis installez les dépendances : `pip install -r requirements.txt`.
4. Démarrez l'API : `uvicorn api.main:app --reload`.
5. Démarrez l'interface dans un second terminal : `streamlit run interface/app.py`.

La documentation interactive de l'API est disponible sur `http://127.0.0.1:8000/docs`.

## Routes

- `POST /documents` : importe et indexe un fichier PDF, DOCX, TXT ou MD.
- `GET /documents` : liste les documents indexés.
- `DELETE /documents/{document_id}` : supprime les passages d'un document.
- `POST /search` : retourne les passages sémantiquement les plus proches.

## Tests

```bash
pytest
```

## Données et expérimentation

Les expérimentations de recherche sémantique utilisent le corpus français **FQuADRetrieval**, téléchargé depuis Hugging Face dans `data/raw/fquad_retrieval`. Il contient 366 documents, 500 requêtes et 500 jugements de pertinence, ce qui permet de calculer Recall@k et MRR@k.

Lancez Jupyter depuis la racine du projet :

```bash
jupyter notebook
```

- `notebooks/exploration.ipynb` vérifie le corpus et affiche les résultats d'une recherche française.
- `notebooks/evaluation.ipynb` produit les métriques et enregistre `evaluation/results/fquad_metrics.csv`.
