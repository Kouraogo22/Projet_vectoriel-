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

### Page de réindexation

La navigation Streamlit propose **Recherche** et **Réindexation**. La seconde page
reconstruit tous les documents de la collection active et affiche la progression,
les erreurs, les passages tronqués et les documents reconstitués. Le traitement
continue côté API lorsque l'utilisateur change de page. Son bilan est téléchargeable
au format JSON ; une annulation est possible entre deux lots (le chargement initial
du modèle ou un calcul en cours doit d'abord se terminer).

Réglages disponibles : taille en mots, chevauchement inclus dans cette taille,
nettoyage, modèle Sentence Transformers, normalisation, CPU/CUDA/MPS, taille des lots
de calcul et d'envoi, limite de tokens, métrique Qdrant (cosinus, produit scalaire,
Euclid, Manhattan), vecteurs sur disque, connexions et construction HNSW, seuils de
recherche exhaustive et d'indexation. Les seuils Qdrant sont exprimés en Ko. La
limite de tokens personnalisée ne peut pas dépasser celle du modèle. La dimension
est détectée automatiquement. CUDA/MPS exigent le matériel et le runtime adaptés
côté API ; l'image Docker fournie utilise PyTorch CPU. Un modèle absent du cache
nécessite un téléchargement Hugging Face. Aucun code distant du modèle n'est autorisé.

Les fichiers conservés dans `data/uploads` sont relus en priorité. Pour les anciens
chemins hôte/Docker, leur nom est recherché dans ce dossier uniquement. Si l'original
manque, la reconstitution depuis les passages est optionnelle et comptabilisée ;
elle ne restaure pas des informations absentes de l'ancien index. On peut aussi
choisir explicitement le texte indexé. Les fichiers non importés ne sont pas inclus.

Chaque travail crée une nouvelle collection avec un suffixe unique. Elle devient
active uniquement après traitement de tous les documents et vérification des
comptages. Les identifiants et métadonnées documentaires sont conservés. Les
recherches continuent sur l'ancien index pendant le travail ; les ajouts et
suppressions via l'API répondent temporairement 409 pour stabiliser le corpus.
Les écritures directes par scripts dans Qdrant doivent également être suspendues.
Les prochains imports et recherches utilisent les paramètres du nouvel index.
L'ancienne collection et les collections de travaux annulés/échoués sont conservées,
ce qui nécessite de l'espace disque ; aucune suppression automatique n'est effectuée.

`data/index_state/active.json` conserve la collection et ses paramètres, et
`job.json` le dernier travail. Ce dossier est monté dans Docker et ignoré par Git.
Ne pas le supprimer au redémarrage : il associe le bon modèle à la bonne collection.
Un travail interrompu par l'arrêt de l'API est signalé au redémarrage et doit être
relancé ; il ne reprend pas automatiquement à mi-parcours. Le service fonctionne
avec **un seul processus Uvicorn**, comme dans le Dockerfile ; un verrou de processus
empêche deux API d'utiliser le même dossier d'état simultanément.

Routes : `GET /reindex` (configuration active et suivi), `POST /reindex`
(paramètres validés, réponse 202), `POST /reindex/cancel` (demande d'annulation).
Après une mise à jour du code : `docker compose up -d --build api`, puis actualiser
Streamlit. La réindexation du corpus réel est lancée explicitement depuis sa page.

### Liste et suppression des documents

La page **Documents** affiche les titres, catégories et identifiants de l’index
actif. La recherche par titre/identifiant et le filtre de catégorie réduisent la
liste. Sélectionnez un ou plusieurs documents, cliquez sur **Supprimer la sélection**,
puis confirmez la liste présentée avant de valider **Confirmer et supprimer**.
La suppression retire les passages de l’index actif et le fichier géré dans
`data/uploads` lorsqu’il existe. Elle ne purge pas les anciennes collections.
Les suppressions sont bloquées pendant une réindexation ; une liste confirmée
pour une autre collection active est également refusée. En cas d’échec partiel,
le bilan distingue les suppressions réussies et celles non confirmées.
