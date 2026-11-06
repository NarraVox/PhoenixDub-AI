"""Regressões do fluxo YuE2 com compositor, CLI e FFmpeg simulados; sem GPU."""
import ast
import importlib.util
import io
import json
import logging
import math
import os
from pathlib import Path
import random
import re
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'nexus/dj/vortex_music.py'
spec = importlib.util.spec_from_file_location('yue2_under_test', ROOT / 'nexus/dj/yu_backend.py')
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


class Yue2FlowTests(unittest.TestCase):
    def run_flow(self, duration=60, batch_count=1, result=None, override=False, exit_code=0):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = root / 'env/tools_acestep'
            models = root / 'MODELS'
            tools.mkdir(parents=True)
            models.mkdir()
            tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
            flow = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                        and n.name == 'run_music_generation_flow_logic')
            # Satisfy existing preflight using empty fixtures; never download models.
            for node in ast.walk(flow):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    name = node.value
                    if not any(c in name for c in '/\\*?') and name.endswith(('.exe', '.dll', '.gguf')):
                        (models if name.endswith('.gguf') else tools).joinpath(name).touch()
            dj = SimpleNamespace(generated_music_dir=root, live_logs=[], project_state={},
                                 save_status=Mock(), stop_ace_server=Mock(),
                                 download_file_with_progress=Mock(side_effect=AssertionError('download')),
                                 worker_busy=True, generating_music=False)
            client = Mock()
            client.post.return_value = SimpleNamespace(status_code=200, json=lambda: {'id': 'lm'})

            def get(url, **kwargs):
                self.assertTrue(url.startswith('http://127.0.0.1:8085/job?id=lm'))
                data = {'caption': 'LM caption', 'lyrics': 'LM lyrics'} if 'result=1' in url else {'status': 'done'}
                return SimpleNamespace(status_code=200, headers={}, json=lambda: data)

            client.get.side_effect = get
            start = Mock()
            commands, exported = [], []
            wav = b'RIFF-simulated-YuE2-output'

            def popen(command, **kwargs):
                commands.append(command)
                # Compositor must have been released before the CLI starts.
                self.assertGreaterEqual(dj.stop_ace_server.call_count, 1)
                (root / 'yue2_output.wav').write_bytes(wav)
                return SimpleNamespace(pid=987654321, returncode=exit_code,
                                       stdout=io.StringIO(''), stderr=io.StringIO(''), wait=Mock())

            def export(command, **kwargs):
                self.assertEqual(command[0], 'ffmpeg')
                self.assertTrue(kwargs.get('check'))
                exported.append(Path(command[command.index('-i') + 1]).read_bytes())
                Path(command[-1]).write_bytes(b'simulated-mp3')

            log = Mock()
            scope = dict(Path=Path, BASE_DIR=root, ENV_DIR=root / 'env', UPLOAD_FOLDER=root,
                         os=SimpleNamespace(name='posix', remove=os.remove),
                         np=SimpleNamespace(isfinite=math.isfinite),
                         torch=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)),
                         time=SimpleNamespace(sleep=Mock(), time=lambda: 1234567890,
                                              strftime=lambda *a: 'test'),
                         requests=client, subprocess=SimpleNamespace(run=export),
                         json=json, logging=log, logger=log, re=re, random=random,
                         unload_local_gemma_engine=Mock(), unload_whisper_model=Mock(),
                         start_ace_server_helper=start)
            exec(compile(ast.Module(body=[flow], type_ignores=[]), str(SOURCE), 'exec'), scope)
            with patch.dict('sys.modules', {'nexus.dj.yu_backend': backend}), \
                 patch.object(backend.subprocess, 'Popen', side_effect=popen), \
                 patch.object(backend, 'Path', side_effect=lambda name: root / name), \
                 patch.object(backend.random, 'randint', return_value=123):
                call = lambda: scope[flow.name](dj, 'Teste', 'future house', '[Verse 1]\nHello',
                                                duration=duration, batch_count=batch_count)
                if override:
                    with patch.object(backend.YuE2Backend, 'generate_music', return_value=result):
                        call()
                else:
                    call()
            history_file = root / 'history.json'
            history = json.loads(history_file.read_text()) if history_file.exists() else []
            self.assertFalse(dj.worker_busy)
            self.assertFalse(dj.generating_music)
            self.assertEqual(backend._audio_cpp_processes, [])
            return SimpleNamespace(commands=commands, exported=exported, history=history,
                                   client=client, start=start, dj=dj, wav=wav)

    def test_duration_reaches_cli_without_changing_proven_arguments(self):
        for seconds, minimum, maximum in [(15, 337, 2250), (60, 1350, 9000), (180, 4050, 27000)]:
            with self.subTest(seconds=seconds):
                run = self.run_flow(seconds)
                expected = [backend.AUDIO_CPP_CLI, '--backend', 'cuda', '--task', 'gen',
                            '--threads', '8', '--family', 'yue2', '--model', r'C:\IA_dublagem\MODELS',
                            '--session-option', 'yue2.model_gguf=yue2-3b-q4_k_m.gguf',
                            '--session-option', 'yue2.vae_gguf=yue2-vae-f16.gguf',
                            '--lyrics', '[verse]\nHello', '--request-option', 'style=future house',
                            '--request-option', 'cot=off', '--seed', '123', '--out', 'yue2_output.wav', '--log',
                            '--request-option', f'semantic_min_tokens={minimum}',
                            '--request-option', f'semantic_max_tokens={maximum}']
                self.assertEqual(run.commands, [expected])
                self.assertEqual(run.exported, [run.wav])
                self.assertEqual(len(run.history), 1)
                self.assertIn('[100%]', run.dj.project_state['current_task'])
                run.start.assert_called_once()
                self.assertEqual(run.client.post.call_count, 1)
                self.assertTrue(run.client.post.call_args.args[0].endswith('/lm'))
                self.assertEqual(run.client.get.call_count, 2)

    def test_batch_exports_each_cli_result(self):
        run = self.run_flow(batch_count=2)
        self.assertEqual(len(run.commands), 2)
        self.assertEqual(run.exported, [run.wav, run.wav])
        self.assertEqual(len(run.history), 2)
        self.assertEqual({x['title'] for x in run.history}, {'Teste_1 (Sem Master)', 'Teste_2 (Sem Master)'})

    def test_cli_failure_does_not_export_or_report_success(self):
        run = self.run_flow(exit_code=1)
        self.assertFalse(run.exported)
        self.assertFalse(run.history)
        self.assertIn('Geração falhou', run.dj.project_state['current_task'])
        self.assertNotIn('[100%]', run.dj.project_state['current_task'])

    def test_invalid_or_empty_backend_result_does_not_export(self):
        for result in (None, {'success': False, 'message': 'falha teste'},
                       {'success': True, 'audio_data': b''}):
            with self.subTest(result=result):
                run = self.run_flow(result=result, override=True)
                self.assertFalse(run.exported)
                self.assertFalse(run.history)
                self.assertNotIn('[100%]', run.dj.project_state['current_task'])

    def test_invalid_duration_fails_before_loading_models(self):
        for duration in (0, -1, float('nan'), float('inf'), 'invalid'):
            with self.subTest(duration=duration):
                run = self.run_flow(duration)
                run.start.assert_not_called()
                run.client.post.assert_not_called()
                self.assertFalse(run.commands)
                self.assertFalse(run.history)


if __name__ == '__main__':
    unittest.main()
