from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from src.indexing.options import IndexOptions

PAGE = str(Path(__file__).resolve().parents[1] / 'interface/app_pages/reindex.py')


class Response:
    ok = True
    def json(self):
        return {'active': {'collection':'test', 'options':IndexOptions().model_dump()}, 'job':None}


def test_page_renders_all_parameters_and_validates_overlap():
    with patch('requests.request', return_value=Response()) as call:
        app = AppTest.from_file(PAGE).run()
        assert not app.exception
        assert len(app.number_input) == 9
        assert len(app.checkbox) == 4
        inputs = {widget.label: widget for widget in app.number_input}
        inputs['Mots par passage'].set_value(10)
        inputs['Mots de chevauchement'].set_value(20)
        app.button[0].click().run()
        assert 'inférieur' in app.error[0].value
        assert all(args.args[0]=='GET' for args in call.call_args_list)


def test_page_submits_actual_config_to_api():
    submitted = []
    def call(method, url, **kwargs):
        if method == 'POST':
            submitted.append(kwargs['json'])
        return Response()
    with patch('requests.request', side_effect=call):
        app = AppTest.from_file(PAGE).run()
        inputs = {widget.label:widget for widget in app.number_input}
        inputs['Mots par passage'].set_value(90)
        app.button[0].click().run()
        assert not app.exception
        assert submitted[0]['chunk_size'] == 90
        assert submitted[0]['chunk_overlap'] == 20
        assert set(IndexOptions.model_fields) <= set(submitted[0])
