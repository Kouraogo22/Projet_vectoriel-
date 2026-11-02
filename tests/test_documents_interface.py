from pathlib import Path
from unittest.mock import patch
import requests
from streamlit.testing.v1 import AppTest

PAGE = str(Path(__file__).resolve().parents[1] / 'interface/app_pages/documents.py')


class Response:
    def __init__(self, data=None, status=200):
        self.data, self.status_code = data, status
    def json(self):
        return self.data
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError('failure', response=self)


def button(app, label):
    return next(b for b in app.button if b.label == label)


def scenario(busy=False, fail=False):
    docs = [{'document_id':'a','title':'Alpha','category':'Droit'},
            {'document_id':'b','title':'Beta','category':'Sciences'}]
    def get(url, **kwargs):
        if url.endswith('/documents'):
            return Response(list(docs))
        return Response({'active':{'collection':'active'}, 'job':{'status':'running'} if busy else None})
    def delete(url, **kwargs):
        id = url.rsplit('/',1)[-1]
        if fail and id == 'b':
            return Response({'detail':'Service indisponible'}, 503)
        docs[:] = [d for d in docs if d['document_id'] != id]
        return Response(status=204)
    return docs, get, delete


def test_delete_requires_confirmation_and_removes_only_selected_document():
    docs,get,delete=scenario()
    with patch('requests.get',side_effect=get), patch('requests.delete',side_effect=delete) as calls:
        app=AppTest.from_file(PAGE).run()
        assert not app.exception
        assert len(app.dataframe[0].value)==2
        app.multiselect[1].set_value(['a']).run()
        button(app,'Supprimer la sélection').click().run()
        assert calls.call_count == 0
        assert button(app,'Confirmer et supprimer').disabled
        app.checkbox[0].check().run()
        button(app,'Confirmer et supprimer').click().run()
        assert not app.exception
        assert [d['document_id'] for d in docs] == ['b']
        assert len(app.dataframe[0].value)==1
        assert calls.call_args.kwargs['params']=={'expected_collection':'active'}
        assert '1 document(s)' in app.success[0].value


def test_filter_and_selection_change_cancel_pending_confirmation():
    _,get,delete=scenario()
    with patch('requests.get',side_effect=get), patch('requests.delete',side_effect=delete) as calls:
        app=AppTest.from_file(PAGE).run()
        app.text_input[0].set_value('Alpha').run()
        assert len(app.dataframe[0].value)==1
        app.multiselect[1].set_value(['a']).run()
        button(app,'Supprimer la sélection').click().run()
        app.multiselect[1].set_value([]).run()
        assert not app.checkbox
        assert calls.call_count==0


def test_reindex_blocks_delete_in_ui():
    _,get,delete=scenario(busy=True)
    with patch('requests.get',side_effect=get), patch('requests.delete',side_effect=delete) as calls:
        app=AppTest.from_file(PAGE).run()
        assert button(app,'Supprimer la sélection').disabled
        assert app.multiselect[1].disabled
        assert calls.call_count==0


def test_bulk_delete_reports_partial_failure():
    docs,get,delete=scenario(fail=True)
    with patch('requests.get',side_effect=get), patch('requests.delete',side_effect=delete):
        app=AppTest.from_file(PAGE).run()
        app.multiselect[1].set_value(['a','b']).run()
        button(app,'Supprimer la sélection').click().run()
        app.checkbox[0].check().run()
        button(app,'Confirmer et supprimer').click().run()
        assert not app.exception
        assert len(docs)==1
        assert 'Beta' in app.error[0].value
        assert '1 document(s)' in app.success[0].value
