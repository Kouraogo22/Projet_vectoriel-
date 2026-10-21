"""Local FR/EN extension of passage-size comparison; never accesses Docker.

FR: all local FQuADRetrieval documents and native validation/test questions.
EN: seeded sample of 500 PubMedQA records; contexts only, never question/answer
in indexed text; 100 validation + 400 test questions. Source abstract is the
single relevance target (retrieval adaptation, not a biomedical QA score).
All queries search the shared bilingual corpus without a language filter.
Selection: best equal-language validation MRR@10, then Recall@10, fewer passages.
Test: only selected size versus historical 120; paired bootstrap per language
and stratified bootstrap of their equal-weight mean. No final evaluation rerun.
"""
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from qdrant_client import QdrantClient, models
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.evaluate_chunk_sizes import MODEL, SIZES, OVERLAP, load, measure
from src.preprocessing import clean_text, split_into_chunks
from src.embeddings import EmbeddingEncoder
OUT=ROOT/'evaluation/results/chunk_sizes_bilingual'
EN_PATH=ROOT/'data/raw/huggingface_cache/pubmedqa_labeled_train.parquet'


def datasets():
    fr=pd.concat([load('corpus',s) for s in ('validation','test')]).drop_duplicates('_id')
    fr=fr.assign(_id='fr:'+fr['_id'].astype(str),language='fr')
    docs=fr[['_id','text','language']].to_dict('records')
    groups={}
    for split in ['validation','test']:
        q=load('queries',split); q['_id']='fr:'+q['_id'].astype(str)
        rel=load('qrels',split)
        rel['query-id']='fr:'+rel['query-id'].astype(str)
        rel['corpus-id']='fr:'+rel['corpus-id'].astype(str)
        groups['fr',split]=(q,rel)
    en=pd.read_parquet(EN_PATH).sort_values('pubid').reset_index(drop=True)
    assert en.pubid.is_unique
    en=en.iloc[np.random.default_rng(20261020).permutation(len(en))[:500]]
    eq=[]
    for i,row in enumerate(en.to_dict('records')):
        identifier='en:'+str(row['pubid'])
        # Original context only. Do not copy the question into indexed text.
        text=' '.join(row['context']['contexts'])
        assert text.strip() and str(row['question']).strip()
        docs.append({'_id':identifier,'text':text,'language':'en'})
        eq.append({'_id':identifier,'text':row['question'],'split':'validation' if i<100 else 'test'})
    for split in ['validation','test']:
        q=pd.DataFrame([r for r in eq if r['split']==split])
        rel=pd.DataFrame({'query-id':q['_id'],'corpus-id':q['_id'],'score':1})
        groups['en',split]=(q,rel)
    frame=pd.DataFrame(docs)
    assert frame['_id'].is_unique
    for (language,split),(q,r) in groups.items():
        assert len(q)==(100 if split=='validation' else 400)
        assert set(r['corpus-id'])<=set(frame['_id'])
    return frame,groups


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    corpus,groups=datasets()
    corpus.to_json(OUT/'corpus.json',orient='records',force_ascii=False,indent=2)
    queries=[]
    for (lang,split),(q,rel) in groups.items():
        for row in q.to_dict('records'):
            queries.append({'language':lang,'split':split,'query_id':row['_id'],'text':row['text'],
                'relevant_ids':rel.loc[rel['query-id']==row['_id'],'corpus-id'].tolist()})
    (OUT/'queries.json').write_text(json.dumps(queries,ensure_ascii=False,indent=2))
    torch.set_num_threads(4);torch.manual_seed(0)
    encoder=EmbeddingEncoder(MODEL);encoder.model.to('cpu')
    qvectors={key:encoder.encode(q.text.tolist()) for key,(q,r) in groups.items()}
    clients={};summaries=[];traces=[];audits=[]
    for size in SIZES:
        start=time.perf_counter();texts=[];ids=[];languages=[]
        for doc in corpus.to_dict('records'):
            chunks=split_into_chunks(clean_text(doc['text']),size,OVERLAP)
            texts.extend(chunks);ids.extend([doc['_id']]*len(chunks));languages.extend([doc['language']]*len(chunks))
        vectors=encoder.encode(texts)
        client=QdrantClient(':memory:')
        client.create_collection('passages',vectors_config=models.VectorParams(size=encoder.dimension,distance=models.Distance.COSINE))
        client.upload_points('passages',[models.PointStruct(id=i,vector=v.tolist(),payload={'document_id':d}) for i,(v,d) in enumerate(zip(vectors,ids))])
        index_s=time.perf_counter()-start
        lengths=np.array([len(x) for x in encoder.model.tokenizer(texts,truncation=False)['input_ids']])
        for lang in ['fr','en']:
            mask=np.array(languages)==lang
            audits.append({'size':size,'language':lang,'passages':int(mask.sum()),'truncated_pct':float((lengths[mask]>encoder.model.max_seq_length).mean()*100)})
            key=(lang,'validation');q,r=groups[key]
            observations=measure(client,qvectors[key],q,r,size,'validation')
            for row in observations:row['language']=lang
            traces.extend(observations)
            summaries.append({'size':size,'language':lang,'mrr_10':np.mean([r['mrr_10'] for r in observations]),
                'recall_10':np.mean([r['recall_10'] for r in observations]),'passages_total':len(texts),'index_s':index_s})
        clients[size]=client
        print('VALIDATION',json.dumps(summaries[-2:]),flush=True)
    summary=pd.DataFrame(summaries)
    macro=summary.groupby('size',as_index=False)[['mrr_10','recall_10','passages_total','index_s']].mean()
    winner=int(macro.sort_values(['mrr_10','recall_10','passages_total','size'],ascending=[False,False,True,True]).iloc[0]['size'])
    summary.to_csv(OUT/'validation_by_language.csv',index=False)
    macro.to_csv(OUT/'validation_macro.csv',index=False)
    pd.DataFrame(audits).to_csv(OUT/'token_audit.csv',index=False)
    tests=[]
    for size in sorted({winner,120}):
        for lang in ['fr','en']:
            key=(lang,'test');q,r=groups[key]
            observations=measure(clients[size],qvectors[key],q,r,size,'test')
            for row in observations:row['language']=lang
            traces.extend(observations)
            tests.append({'size':size,'language':lang,'mrr_10':np.mean([r['mrr_10'] for r in observations]),'recall_10':np.mean([r['recall_10'] for r in observations])})
    pd.DataFrame(tests).to_csv(OUT/'test_by_language.csv',index=False)
    observations=pd.DataFrame(traces);observations.to_csv(OUT/'query_metrics.csv',index=False)
    intervals={};boots=[]
    if winner!=120:
        for lang in ['fr','en']:
            p=observations[(observations.language==lang)&(observations.split=='test')].pivot(index='query_id',columns='size',values='mrr_10')
            delta=(p[winner]-p[120]).to_numpy();rng=np.random.default_rng(123 if lang=='fr' else 456)
            boot=np.array([rng.choice(delta,len(delta),replace=True).mean() for _ in range(10000)]);boots.append(boot)
            intervals[lang]={'difference':float(delta.mean()),'ci95':np.quantile(boot,[.025,.975]).tolist()}
        intervals['macro']={'difference':float(np.mean([intervals[x]['difference'] for x in ['fr','en']])),
            'ci95':np.quantile(np.mean(boots,axis=0),[.025,.975]).tolist()}
    manifest={'model':MODEL,'max_seq_length':encoder.model.max_seq_length,'sizes':SIZES,'overlap':OVERLAP,
        'selected_size':winner,'selection':'equal-language validation MRR@10, Recall@10, fewer passages, smaller size',
        'documents_by_language':corpus.language.value_counts().to_dict(),'validation_queries_per_language':100,'test_queries_per_language':400,
        'english_seed':20261020,'english_source':'PubMedQA question -> original context; question and long_answer excluded from index',
        'search':'shared bilingual corpus; exact local in-memory Qdrant; top ten passages; no language/category filter',
        'limitations':'Different domains by language; source-document relevance for English; not a cross-language retrieval test. French questions previously used: extension, not fresh independent replication.',
        'test_mrr_difference_vs_120':intervals,'device':'cpu','threads':4,'platform':platform.platform(),
        'inputs_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [EN_PATH,*sorted((ROOT/'data/raw/fquad_retrieval').glob('*/*.parquet'))]},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    for c in clients.values():c.close()
    print('SELECTED',winner,'TEST',json.dumps(tests),'INTERVALS',json.dumps(intervals),flush=True)

if __name__=='__main__':main()
