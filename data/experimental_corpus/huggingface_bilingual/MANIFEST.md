# Manifeste du corpus expérimental bilingue

Ce dossier contient 20 documents TXT issus de quatre jeux de données publics Hugging Face. Ils sont destinés à être importés individuellement via l’interface Streamlit, puis à tester l’indexation et la recherche sémantique.

## Répartition

| Langue | Domaine | Type de document | Nombre | Source Hugging Face | Licence déclarée |
|---|---|---:|---:|---|---|
| Français | Actualités et société | Extrait d’actualité avec question associée | 4 | [CATIE-AQ/frenchQA](https://huggingface.co/datasets/CATIE-AQ/frenchQA) | CC BY 4.0 |
| Français | Réglementation financière, fiscalité, droit administratif et droit du travail | Document juridique ou réglementaire | 4 | [finaleads/french-corpus-llm-sample](https://huggingface.co/datasets/finaleads/french-corpus-llm-sample) | Etalab-2.0 |
| Anglais | Actualités internationales, sport, économie et sciences/technologies | Brève d’actualité | 8 | [fancyzhx/ag_news](https://huggingface.co/datasets/fancyzhx/ag_news) | Inconnue dans la carte du jeu de données |
| Anglais | Santé et biomédecine | Résumé d’article biomédical | 4 | [qiaojin/PubMedQA](https://huggingface.co/datasets/qiaojin/PubMedQA) | MIT |

## Importation dans l’interface

1. Démarrer Qdrant, l’API FastAPI et Streamlit.
2. Dans l’interface, choisir **Ajouter un document**.
3. Sélectionner un fichier TXT dans les sous-dossiers `fr/` ou `en/`.
4. Reprendre le domaine indiqué dans `manifest.json` comme catégorie afin d’activer les filtres de recherche.

`manifest.json` fournit, pour chaque fichier, le jeu de données, le split, le fichier source, le type de document, la langue, le domaine, l’identifiant de la ligne source et l’empreinte SHA-256.

## Limite d’usage

Ce corpus est destiné à l’expérimentation technique du prototype. Il ne doit pas être utilisé pour rendre un conseil juridique, médical ou financier. La licence et les conditions de chaque source doivent être vérifiées avant toute redistribution au-delà de ce cadre.
