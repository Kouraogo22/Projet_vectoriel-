from types import SimpleNamespace

from evaluation.evaluate_selected_chunks import aggregate_passages, ranked
from evaluation.evaluate_balanced_collection import metrics_at_k
from src.preprocessing import split_into_chunks


def test_document_aggregation_keeps_best_passage_regardless_of_order():
    hits = [SimpleNamespace(payload={'document_id': d}, score=s)
            for d, s in [('a', .9), ('b', .8), ('a', .2)]]
    assert aggregate_passages(hits) == {'a': .9, 'b': .8}
    assert aggregate_passages(list(reversed(hits))) == {'a': .9, 'b': .8}
    assert ranked(['b', 'a'], [.8, .9]) == ['a', 'b']


def test_document_metrics_do_not_count_repeated_passages_as_documents():
    hits = [SimpleNamespace(payload={'document_id': d}, score=s)
            for d,s in [('a', .9), ('a', .8), ('b', .7)]]
    scores = aggregate_passages(hits)
    order = ranked(list(scores), list(scores.values()))
    measures = metrics_at_k(order, 'b', 2)
    assert measures['Recall@2'] == 1
    assert measures['MRR@2'] == .5
    assert measures['Precision@2'] == .5


def test_selected_default_includes_twenty_word_overlap():
    passages = split_into_chunks(' '.join(map(str, range(100))))
    assert [len(p.split()) for p in passages] == [60, 60]
    assert passages[0].split()[-20:] == passages[1].split()[:20]
