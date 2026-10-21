"""Execute notebooks auditing and visualizing the saved selected-size experiment.

Recompute retrieval with evaluation/evaluate_selected_chunks.py first. Notebook
execution reads that frozen run so rebuilding the report does not rerun timings.
"""
from pathlib import Path
import sys
import nbformat as nbf
from nbclient import NotebookClient
ROOT = Path(__file__).resolve().parents[1]


def execute(name, cells):
    notebook = nbf.v4.new_notebook(cells=cells, metadata={'kernelspec': {
        'name': 'python3', 'display_name': 'Python', 'language': 'python'}})
    client = NotebookClient(notebook, timeout=600, kernel_name='python3',
                            resources={'metadata': {'path': str(ROOT)}})
    client.execute()
    nbf.write(notebook, ROOT/'notebooks'/name)
    print('Executed', name, flush=True)


def main():
    md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    setup = """from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
ROOT = Path.cwd()
if not (ROOT / 'src').exists(): ROOT = ROOT.parent
RESULTS = ROOT / 'evaluation/results/chapter4_selected'
manifest = json.loads((RESULTS/'protocol_comparison_manifest.json').read_text())
print('Collection :', manifest['collection'])
print('Taille retenue :', manifest['chunk_size'], 'mots ; chevauchement inclus :', manifest['chunk_overlap'])
"""
    execute('exploration.ipynb', [md('# Corpus réindexé après sélection de la taille des passages\n\nContrôle du corpus figé et du manifeste des passages de la nouvelle expérience.'), code(setup), code("""documents = pd.DataFrame(json.loads((RESULTS/'source_documents.json').read_text()))
passages = pd.read_csv(RESULTS/'passage_manifest.csv')
assert len(documents)==900 and documents.document_id.is_unique
assert passages.document_id.nunique()==900
assert len(passages)==manifest['passages']
distribution = documents.category.value_counts().sort_index().rename('Documents')
assert distribution.eq(100).all() and len(distribution)==9
display(distribution.to_frame())
print(len(passages), 'passages ;', manifest['truncated_passages'], 'dépassent la limite de tokens.')
"""),code("""ax=distribution.plot.barh(figsize=(11,5),color='#2878B5')
ax.set_xlabel('Nombre de documents'); ax.set_ylabel('Catégorie')
ax.set_title('Corpus réindexé : 900 documents, neuf catégories')
ax.bar_label(ax.containers[0],padding=3)
plt.xlim(0,115); plt.tight_layout(); plt.show()
""")])
    execute('evaluation.ipynb', [md('# Sélection de la taille puis évaluation finale\n\nLa taille est sélectionnée sur les 100 questions de validation de FQuADRetrieval. Les 400 questions réservées vérifient ce choix. La comparaison finale reprend ensuite les 900 documents et les 90 requêtes contrôlées, avec indexation réelle en passages.\n\nPour recalculer les mesures : `python evaluation/evaluate_chunk_sizes.py`, puis `python evaluation/evaluate_selected_chunks.py`. Ce notebook contrôle et affiche les résultats sauvegardés de cette exécution.'),code(setup),code("""selection = pd.read_csv(ROOT/'evaluation/results/chunk_sizes/validation_summary.csv')
display(selection[['size','passages','truncated_pct','recall_10','mrr_10','index_s']].round(4))
best=selection.sort_values(['mrr_10','recall_10','passages','size'],ascending=[False,False,True,True]).iloc[0]
assert int(best['size'])==manifest['chunk_size']==60
"""),code("""summary=pd.read_csv(RESULTS/'protocol_comparison_summary_metrics.csv')
observations=pd.read_csv(RESULTS/'protocol_comparison_detailed_metrics.csv')
assert len(observations)==90*3*2
for _, group in observations.groupby(['Méthode','Scénario']): assert len(group)==90
summary_at_10=summary[['Méthode','Scénario','Precision@10','Recall@10','MRR@10','nDCG@10','Temps (ms)']]
display(summary_at_10.round(4))
"""),code("""plot_data=summary[summary['Scénario']=='Sans filtre'].set_index('Méthode')[['Recall@10','MRR@10','nDCG@10']]
ax=plot_data.plot.bar(figsize=(10,5),rot=0,ylim=(0,1.08),color=['#4C78A8','#F58518','#54A24B'])
ax.set_ylabel('Valeur'); ax.set_title('Recherche documentaire après découpage à 60 mots')
ax.legend(loc='lower right'); plt.tight_layout(); plt.show()
"""),code("""category_metrics=pd.read_csv(RESULTS/'protocol_comparison_category_metrics_at_10.csv')
display(category_metrics[(category_metrics['Méthode']=='Qdrant vectoriel') & (category_metrics['Scénario']=='Avec filtre de catégorie')][['Catégorie','Recall@10','MRR@10','nDCG@10']].round(4))
"""),md('Les scores vectoriels sont agrégés par maximum des passages de chaque document. Les temps incluent l’encodage et la récupération exhaustive des passages : ils ne constituent pas une mesure de latence de l’interface. Les requêtes finales reprennent la première phrase des documents, ce qui favorise la recherche lexicale. Les résultats français de sélection ne prouvent pas une optimalité universelle du seuil retenu.')])

if __name__=='__main__': main()
