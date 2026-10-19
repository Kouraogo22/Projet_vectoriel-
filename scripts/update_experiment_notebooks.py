"""Reconstruit et exécute les deux notebooks utilisés dans le chapitre 4."""
from __future__ import annotations

import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"


def code(source: str):
    return nbf.v4.new_code_cell(source)


def markdown(source: str):
    return nbf.v4.new_markdown_cell(source)


def save_and_execute(name: str, cells: list) -> None:
    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python (projet_vectoriel)",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": sys.version.split()[0]},
        },
    )
    path = NOTEBOOKS / name
    nbf.write(notebook, path)
    client = NotebookClient(notebook, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}})
    client.execute()
    nbf.write(notebook, path)
    print(f"Notebook exécuté : {path}")


def create_exploration_notebook() -> None:
    save_and_execute(
        "exploration.ipynb",
        [
            markdown(
                "# Exploration du corpus équilibré\n\n"
                "Ce notebook contrôle le corpus utilisé pour l'expérimentation : "
                "**900 documents**, répartis dans **9 catégories de 100 documents**. "
                "La collection Qdrant est explicitement fixée afin que l'analyse "
                "ne dépende pas de la collection active de l'application."
            ),
            code(
                "from pathlib import Path\n"
                "import sys\n"
                "import pandas as pd\n"
                "import matplotlib.pyplot as plt\n\n"
                "ROOT = Path.cwd()\n"
                "if not (ROOT / 'src').exists():\n"
                "    ROOT = ROOT.parent\n"
                "sys.path.insert(0, str(ROOT))\n\n"
                "from src.database import VectorStore\n\n"
                "COLLECTION = 'experiment_multicategory_900'\n"
                "store = VectorStore('http://localhost:6333', None, COLLECTION)\n"
                "points, _ = store.client.scroll(COLLECTION, with_payload=True, with_vectors=False, limit=1000)\n"
                "documents = pd.DataFrame([point.payload for point in points]).drop_duplicates('document_id')\n"
                "documents = documents[['document_id', 'title', 'category', 'text', 'source']]\n"
                "print(f'Collection analysée : {COLLECTION}')\n"
                "print(f'Nombre de documents : {len(documents)}')\n"
                "print(f'Nombre de catégories : {documents.category.nunique()}')"
            ),
            code(
                "distribution = documents.category.value_counts().sort_index().rename('Documents')\n"
                "display(distribution.to_frame())\n"
                "assert len(documents) == 900\n"
                "assert documents.category.nunique() == 9\n"
                "assert distribution.eq(100).all()\n"
                "print('Contrôle validé : 100 documents sont disponibles dans chaque catégorie.')"
            ),
            code(
                "ax = distribution.plot.barh(figsize=(11, 5), color='#2878B5')\n"
                "ax.set_xlabel('Nombre de documents')\n"
                "ax.set_ylabel('Catégorie')\n"
                "ax.set_title('Répartition équilibrée du corpus expérimental')\n"
                "ax.bar_label(ax.containers[0], padding=3)\n"
                "plt.xlim(0, 115)\n"
                "plt.tight_layout()\n"
                "plt.show()"
            ),
            code(
                "documents[['document_id', 'category', 'title', 'source']].sort_values(['category', 'document_id']).head(18)"
            ),
            markdown(
                "La répartition équilibrée évite qu'une catégorie surreprésentée "
                "influence les mesures globales. Les contenus restent stockés dans "
                "Qdrant sous forme de passages avec leurs métadonnées documentaires."
            ),
        ],
    )


def create_evaluation_notebook() -> None:
    save_and_execute(
        "evaluation.ipynb",
        [
            markdown(
                "# Évaluation comparative : TF-IDF, Qdrant vectoriel et recherche hybride\n\n"
                "L'évaluation porte sur le corpus équilibré de **900 documents**. "
                "Elle compare les trois méthodes prévues par le protocole, sans filtre "
                "puis avec filtre de catégorie. La combinaison hybride utilise "
                "$0,5 \\times$ score TF-IDF normalisé et $0,5 \\times$ score vectoriel normalisé."
            ),
            code(
                "from pathlib import Path\n"
                "import sys\n"
                "import pandas as pd\n"
                "import matplotlib.pyplot as plt\n\n"
                "ROOT = Path.cwd()\n"
                "if not (ROOT / 'evaluation').exists():\n"
                "    ROOT = ROOT.parent\n"
                "sys.path.insert(0, str(ROOT))\n\n"
                "from evaluation.evaluate_balanced_collection import main\n\n"
                "main()"
            ),
            code(
                "RESULTS = ROOT / 'evaluation' / 'results'\n"
                "summary = pd.read_csv(RESULTS / 'protocol_comparison_summary_metrics.csv')\n"
                "summary_at_10 = summary[['Méthode', 'Scénario', 'Precision@10', 'Recall@10', 'MRR@10', 'nDCG@10', 'Temps (ms)']].copy()\n"
                "display(summary_at_10.round(4))"
            ),
            code(
                "metric_columns = ['Precision@1', 'Precision@3', 'Precision@5', 'Precision@10', 'Recall@1', 'Recall@3', 'Recall@5', 'Recall@10', 'MRR@1', 'MRR@3', 'MRR@5', 'MRR@10', 'nDCG@1', 'nDCG@3', 'nDCG@5', 'nDCG@10']\n"
                "display(summary[['Méthode', 'Scénario'] + metric_columns].round(4))"
            ),
            code(
                "plot_data = summary[summary['Scénario'] == 'Sans filtre'].set_index('Méthode')[['Recall@10', 'MRR@10', 'nDCG@10']]\n"
                "ax = plot_data.plot.bar(figsize=(10, 5), rot=0, ylim=(0, 1.08), color=['#4C78A8', '#F58518', '#54A24B'])\n"
                "ax.set_ylabel('Valeur de la mesure')\n"
                "ax.set_title('Comparaison des méthodes sans filtre à K = 10')\n"
                "ax.legend(loc='lower right')\n"
                "plt.tight_layout()\n"
                "plt.show()"
            ),
            code(
                "category_metrics = pd.read_csv(RESULTS / 'protocol_comparison_category_metrics_at_10.csv')\n"
                "hybrid_by_category = category_metrics[category_metrics['Méthode'] == 'Recherche hybride'][['Scénario', 'Catégorie', 'Recall@10', 'MRR@10', 'nDCG@10']]\n"
                "display(hybrid_by_category.round(4))"
            ),
            markdown(
                "### Interprétation et limite\n\n"
                "Les 90 requêtes sont obtenues à partir de la première phrase de dix "
                "documents pertinents par catégorie. Elles constituent donc un protocole "
                "contrôlé et reproductible, mais ne remplacent pas un jeu de requêtes "
                "indépendantes formulées par des utilisateurs. Les résultats sont à lire "
                "en tenant compte de cette proximité lexicale avec le corpus."
            ),
        ],
    )


if __name__ == "__main__":
    create_exploration_notebook()
    create_evaluation_notebook()
