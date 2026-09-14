import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask
from nexus.correction_service import CorrectionService, write_json
from nexus.correction_search import search_uploads
from nexus import correction_routes as routes


class GlobalSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        for name, text in [('a', 'Olha minhas costas'), ('b', 'Outra fala')]:
            write_json(self.base / 'uploads' / name / 'project_data.json',
                       [{'id': 'same_id', 'translated_text': text}])
        write_json(self.base / 'outside' / 'project_data.json',
                   [{'id': 'outside', 'translated_text': 'Olha minhas costas'}])
        self.service = CorrectionService(self.base)
        self.keys = {p['name']: p['id'] for p in self.service.discover()}
        app = Flask(__name__)
        app.register_blueprint(routes.correction_blueprint)
        self.client = app.test_client()
        mock = patch.object(routes, 'service', self.service)
        mock.start()
        self.addCleanup(mock.stop)

    def test_api_global_typo_and_optional_filter(self):
        for query in ['olhe as minhas costas', 'olhe as minahs costsa', 'OLHA MINHAS CÓSTAS!']:
            response = self.client.get('/api/corrections/segments', query_string={'q': query})
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['total'], 1)
            self.assertEqual(data['projects_searched'], 2)
            self.assertEqual(data['items'][0]['project_id'], self.keys['a'])
        filtered = self.client.get('/api/corrections/segments', query_string={
            'q': 'costas', 'project_id': self.keys['b']}).get_json()
        self.assertEqual(filtered['total'], 0)
        self.assertEqual(search_uploads(self.service, 'xyzq inexistente')['total'], 0)

    def test_pagination_and_exact_ranking(self):
        write_json(self.base / 'uploads' / 'c' / 'project_data.json',
                   [{'id': str(i), 'translated_text': 'olhe as minhas costas'} for i in range(45)])
        first = search_uploads(self.service, 'olhe as minhas costas')
        second = search_uploads(self.service, 'olhe as minhas costas', 40)
        self.assertEqual(first['total'], 46)
        self.assertEqual(len(first['items']), 40)
        self.assertEqual(len(second['items']), 6)
        self.assertFalse(first['items'][0]['approximate'])
        self.assertTrue(second['items'][-1]['approximate'])
        identities = [(x['project_id'], x['id']) for x in first['items'] + second['items']]
        self.assertEqual(len(set(identities)), 46)

    def test_draft_saved_to_result_project_and_searchable(self):
        result = search_uploads(self.service, 'minahs costsa')['items'][0]
        response = self.client.post('/api/corrections/draft', json={
            'project_id': result['project_id'], 'segment_id': result['id'],
            'text': 'Me dê cobertura', 'revision': 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.queue(self.keys['b'])['drafts'], 0)
        self.assertEqual(search_uploads(self.service, 'cobretura')['items'][0]['translated'],
                         'Me dê cobertura')
        self.assertEqual(self.service.queue(self.keys['a'])['pending'], 0)

    def test_invalid_filter_and_offset(self):
        for params in [{'project_id': '../outside'}, {'offset': 'oops'}]:
            self.assertEqual(self.client.get('/api/corrections/segments', query_string=params).status_code, 400)


if __name__ == '__main__':
    unittest.main()
