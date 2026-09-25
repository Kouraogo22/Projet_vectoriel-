"""Comparaison de Qdrant et TF-IDF sur la collection Qdrant équilibrée."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.database import VectorStore
from src.embeddings import EmbeddingEncoder
COLLECTION="experiment_multicategory_900"; OUT=ROOT/"evaluation/results"
def main():
 store=VectorStore("http://localhost:6333",None,COLLECTION)
 points,_=store.client.scroll(COLLECTION,with_payload=True,with_vectors=False,limit=1000)
 docs={p.payload["document_id"]:p.payload for p in points}
 document_frame=pd.DataFrame(docs.values())
 vectorizer=TfidfVectorizer(lowercase=True, ngram_range=(1,2))
 tfidf_matrix=vectorizer.fit_transform(document_frame["text"].fillna(""))
 queries=[]
 for category in sorted({d["category"] for d in docs.values()}):
  sample=[d for d in docs.values() if d["category"]==category][:10]
  for d in sample:
   text=d["text"].split(".")[0][:220] or d["title"]
   queries.append((category,text,d["document_id"]))
 encoder=EmbeddingEncoder("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
 rows=[]
 for filtered in (False,True):
  for category,query,relevant in queries:
   vector=encoder.encode(query); start=time.perf_counter()
   results=store.search(vector,10,category=category if filtered else None)
   rank=next((i for i,r in enumerate(results,1) if r.payload["document_id"]==relevant),None)
   rows.append({"Méthode":"Qdrant", "Scénario":"Avec filtre" if filtered else "Sans filtre","Catégorie":category,
                "Recall@10":float(rank is not None),"MRR@10":1/rank if rank else 0,
                "Temps (ms)":(time.perf_counter()-start)*1000})
 for filtered in (False, True):
  for category,query,relevant in queries:
   start=time.perf_counter()
   candidate=document_frame if not filtered else document_frame[document_frame["category"] == category]
   query_vector=vectorizer.transform([query])
   scores=cosine_similarity(query_vector, tfidf_matrix[candidate.index]).ravel()
   ranked_ids=candidate.iloc[scores.argsort()[::-1][:10]]["document_id"].tolist()
   rank=next((i for i, document_id in enumerate(ranked_ids, 1) if document_id == relevant), None)
   rows.append({"Méthode":"TF-IDF", "Scénario":"Avec filtre" if filtered else "Sans filtre", "Catégorie":category,
                "Recall@10":float(rank is not None), "MRR@10":1/rank if rank else 0,
                "Temps (ms)":(time.perf_counter()-start)*1000})
 frame=pd.DataFrame(rows).groupby(["Méthode", "Scénario", "Catégorie"],as_index=False).mean(numeric_only=True)
 frame.to_csv(OUT/"balanced_collection_metrics.csv",index=False)
 summary=frame.groupby(["Méthode", "Scénario"],as_index=False).mean(numeric_only=True)
 summary.to_csv(OUT/"balanced_collection_summary_metrics.csv",index=False)
 print("Comparaison calculée à partir de ce notebook :")
 print(summary.to_string(index=False)); print(frame.to_string(index=False))
if __name__=="__main__": main()
