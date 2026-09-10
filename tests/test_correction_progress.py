import types
import unittest
from unittest.mock import patch
from flask import Flask
from nexus.correction_queue_runner import process_queue
from nexus import correction_routes as routes


class ProgressTests(unittest.TestCase):
    def test_runner_counts_completed_and_failed_separately(self):
        events = []
        def preview(key, sid, text):
            if sid == 'bad':
                raise ValueError('Falha de teste')
            return {'token': sid}
        service = types.SimpleNamespace(project=lambda _: ('folder', 'games', []),
            preview=preview, set_draft_status=lambda *a, **kw: None,
            apply=lambda *a: None, queue=lambda _: {}, manifest=lambda _: {})
        snapshots = [{'segment_id': sid, 'text': 'fala', 'revision': i} for i, sid in enumerate(['ok', 'bad', 'ok2'])]
        result = process_queue(service, 'key', progress=events.append, snapshots=snapshots)
        self.assertEqual(events[0]['total'], 3)
        self.assertEqual(events[0]['current'], 'ok')
        self.assertEqual(events[1]['completed'], 1)
        self.assertEqual(events[-1]['completed'], 2)
        self.assertEqual(events[-1]['failed'], 1)
        self.assertEqual(len(result['failures']), 1)

    def test_api_queued_counts_logs_and_error_survive_polling(self):
        app = Flask(__name__); app.register_blueprint(routes.correction_blueprint)
        jobs = []
        fake = types.SimpleNamespace(is_engine_busy=lambda _: False)
        with patch.object(routes, 'executor', types.SimpleNamespace(submit=jobs.append)), patch.object(routes, 'tasks', {}), patch.dict('sys.modules', {'nexus.nexus_routes': fake}):
            def action(progress):
                progress({'message': 'Gerando: fala_a', 'total': 3, 'completed': 0, 'failed': 0, 'current': 'fala_a'})
                progress({'message': 'Fala concluída: fala_a', 'completed': 1, 'current': None})
                raise RuntimeError('Erro de teste')
            with app.app_context():
                response, _ = routes.submit('project', action, total=3)
            token = response.get_json()['task_id']
            client = app.test_client()
            queued = client.get('/api/corrections/tasks/' + token).get_json()
            self.assertEqual(queued['progress']['total'], 3)
            self.assertEqual(queued['status'], 'queued')
            jobs[0]()
            done = client.get('/api/corrections/tasks/' + token).get_json()
            self.assertEqual(done['status'], 'error')
            self.assertEqual(done['progress']['completed'], 1)
            self.assertIn('Erro de teste', done['logs'][-1]['message'])
            self.assertEqual(len({e['sequence'] for e in done['logs']}), len(done['logs']))


if __name__ == '__main__':
    unittest.main()
