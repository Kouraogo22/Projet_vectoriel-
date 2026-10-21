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

La taille retenue est de **60 mots par passage**, dont **20 mots de chevauchement inclus** (pas de 40 mots). Le choix initial sur FQuADRetrieval est confirmé par la meilleure moyenne de MRR@10 en validation **bilingue français–anglais**, parmi 60, 90, 120, 180 et 240 mots. Cette extension locale réunit 309 documents français et 500 résumés anglais de PubMedQA, avec 100 questions de validation et 400 de test par langue. La question anglaise et sa réponse ne sont pas ajoutées au texte indexé.

Les deux langues ont un poids égal dans la sélection. Le meilleur score anglais de validation est obtenu à 90 mots, mais 60 mots donne la meilleure moyenne bilingue. Les gains de MRR sur le test face à 120 mots ne sont pas statistiquement concluants : le choix repose sur la validation. Il ne s'agit pas d'un test de recherche interlangue.

L'évaluation finale réindexe les **900 documents du corpus bilingue équilibré** en **3 926 passages**, puis compare TF-IDF, Qdrant et la recherche hybride sur les mêmes 90 requêtes contrôlées. Qdrant utilise le meilleur score de passage par document. Les requêtes reprennent le début des documents : ces résultats ne remplacent pas une évaluation avec des questions indépendantes.

```bash
python evaluation/evaluate_chunk_sizes.py
python evaluation/evaluate_bilingual_chunk_sizes.py
python evaluation/evaluate_selected_chunks.py
python scripts/update_experiment_notebooks.py
```

La première commande reproduit l'étude française initiale. La deuxième reprend uniquement la comparaison bilingue en mémoire, à partir des fichiers Parquet locaux de FQuADRetrieval et PubMedQA et du modèle ; elle n'accède pas à Docker. Ses résultats sont dans `evaluation/results/chunk_sizes_bilingual/`.

La troisième commande nécessite Qdrant sur le port 6333 et le corpus figé `evaluation/results/chapter4_selected/source_documents.json`, exporté depuis la collection historique `experiment_multicategory_900`. Elle crée une nouvelle collection sans supprimer les précédentes. Les résultats et paramètres historiques restent dans `evaluation/results/chunk_sizes/` et `evaluation/results/chapter4_selected/`. La confirmation bilingue a conservé 60 mots et **n'a pas relancé cette évaluation finale**. Le fichier `chunk_sizes_bilingual/verification_receipt.json` conserve les empreintes des manifestes concernés. Ces dossiers de résultats sont ignorés par Git.

Lancez Jupyter depuis la racine du projet :

```bash
jupyter notebook
```

- `notebooks/exploration.ipynb` contrôle les 900 documents, les catégories et les passages réindexés.
- `notebooks/evaluation.ipynb` vérifie et présente les résultats sauvegardés de la sélection et de l'évaluation finale.

Les services définis dans Docker Compose sont Qdrant et l'API FastAPI. Streamlit, Jupyter et les scripts expérimentaux sont exécutés sur la machine hôte. La sélection utilise Qdrant en mémoire ; l'évaluation finale interroge le serveur Qdrant Docker.
