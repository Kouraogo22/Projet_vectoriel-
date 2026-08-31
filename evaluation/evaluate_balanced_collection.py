"""Évaluation par catégorie de la collection Qdrant équilibrée."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.database import VectorStore
from src.embeddings import EmbeddingEncoder
COLLECTION="experiment_multicategory_900"; OUT=ROOT/"evaluation/results"
def main():
 store=VectorStore("http://localhost:6333",None,COLLECTION)
 points,_=store.client.scroll(COLLECTION,with_payload=True,with_vectors=False,limit=1000)
 docs={p.payload["document_id"]:p.payload for p in points}
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
   rows.append({"Scénario":"Avec filtre" if filtered else "Sans filtre","Catégorie":category,
                "Recall@10":float(rank is not None),"MRR@10":1/rank if rank else 0,
                "Temps (ms)":(time.perf_counter()-start)*1000})
 frame=pd.DataFrame(rows).groupby(["Scénario","Catégorie"],as_index=False).mean(numeric_only=True)
 frame.to_csv(OUT/"balanced_collection_metrics.csv",index=False)
 summary=frame.groupby("Scénario",as_index=False).mean(numeric_only=True)
 summary.to_csv(OUT/"balanced_collection_summary_metrics.csv",index=False)
 print(summary.to_string(index=False)); print(frame.to_string(index=False))
if __name__=="__main__": main()
