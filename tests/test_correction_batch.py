import types
import unittest
from pathlib import Path
from unittest.mock import patch
from flask import Flask
from tests import test_corrections as fixtures
from nexus import correction_routes as routes
from nexus.correction_service import read_json, write_json


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.CorrectionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.service = self.fixture.service
        self.second = self.fixture.make_project('outro_personagem', 'games')
        self.keys = {p['name']: p['id'] for p in self.service.discover()}
        self.references = []
        self.expected = set()
        for folder in [self.fixture.game, self.second]:
            data = read_json(folder / 'project_data.json')
            for i, seg in enumerate(data):
                seg['speaker'] = f'personagem_{folder.name}_{i}'
                seg['original_text'] = 'Watch my back.'
                seg['translated_text'] = seg['text_pt'] = 'Olha minhas costas'
                ref = folder / '_2_PARA_AS_PASTAS_DE_VOZ' / seg['speaker'] / f"{seg['id']}.wav"
                ref.parent.mkdir(parents=True)
                ref.write_bytes((folder / '_2_PARA_AS_PASTAS_DE_VOZ/voz1' / ref.name).read_bytes())
                self.expected.add(str(ref.resolve()))
            write_json(folder / 'project_data.json', data)
        def synth(text, reference, output, duration, emotion):
            self.references.append((text, str(reference), str(output)))
            self.fixture.synth(text, reference, output, duration, emotion)
        self.service.synthesizer = synth
        self.jobs = []
        for mock in [patch.object(routes, 'service', self.service),
                     patch.object(routes, 'tasks', {}),
                     patch.object(routes, 'executor', types.SimpleNamespace(submit=self.jobs.append)),
                     patch.dict('sys.modules', {'nexus.nexus_routes': types.SimpleNamespace(is_engine_busy=lambda _: False)})]:
            mock.start(); self.addCleanup(mock.stop)
        app = Flask(__name__); app.register_blueprint(routes.correction_blueprint)
        self.client = app.test_client()

    def save(self, key, sid='seg_0', revision=10):
        self.service.save_draft(key, sid, 'Me dê cobertura.', revision)
        return {'project_id': key, 'segment_id': sid, 'revision': revision}

    def test_same_original_across_projects_and_separate_voices(self):
        data = self.client.get('/api/corrections/selection', query_string={'original': 'Watch my back.'}).get_json()
        self.assertEqual(data['total'], 4)
        self.assertEqual(len({i['speaker'] for i in data['items']}), 4)
        items = [self.save(i['project_id'], i['id']) for i in data['items']]
        result = self.client.post('/api/corrections/enqueue-many', json={'items': items + items[:1]})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.get_json()['count'], 4)
        self.assertEqual(len(self.jobs), 2)
        for callback in self.jobs:
            callback()
        self.assertTrue(all(t['status'] == 'done' for t in routes.tasks.values()))
        self.assertEqual({ref for _, ref, _ in self.references}, self.expected)
        self.assertEqual(len({out for _, _, out in self.references}), 4)
        self.assertTrue(all(text == 'Me dê cobertura.' for text, _, _ in self.references))

    def test_one_selected_and_video_stays_staged(self):
        items = [self.save(self.keys['jogo']), self.save(self.keys['video'])]
        result = self.client.post('/api/corrections/enqueue-many', json={'items': items}).get_json()
        self.assertEqual(len(self.jobs), 1)
        self.assertEqual(result['staged_video_projects'], [self.keys['video']])
        self.assertEqual(self.service.queue(self.keys['outro_personagem'])['pending'], 0)
        self.assertEqual(self.service.queue(self.keys['jogo'])['pending'], 1)

    def test_stale_revision_does_not_enqueue_any(self):
        items = [self.save(self.keys['jogo']), self.save(self.keys['outro_personagem'])]
        self.service.save_draft(self.keys['outro_personagem'], 'seg_0', 'Edição mais nova', 11)
        result = self.client.post('/api/corrections/enqueue-many', json={'items': items})
        self.assertEqual(result.status_code, 400)
        self.assertEqual(self.jobs, [])
        self.assertEqual(self.service.queue(self.keys['jogo'])['pending'], 0)

    def test_global_selection_includes_other_pages(self):
        folder = self.fixture.base / 'uploads' / 'mais_falas'
        write_json(folder / 'project_data.json', [{'id': str(i), 'translated_text': 'Olha minhas costas'} for i in range(45)])
        data = self.client.get('/api/corrections/selection', query_string={'q': 'olha minhas costas'}).get_json()
        self.assertEqual(len(data['items']), 49)


if __name__ == '__main__':
    unittest.main()
