import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from release import release_assistant as module


class AssistantTests(unittest.TestCase):
    def test_version_argument_rejects_paths(self):
        self.assertEqual(module.version_argument('v0.9.2'), '0.9.2')
        import argparse
        with self.assertRaises(argparse.ArgumentTypeError):
            module.version_argument('../0.9.2')

    def test_version_read_does_not_execute_python(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'nexus').mkdir()
            (root/'nexus/version.py').write_text('raise RuntimeError()\nAPP_VERSION = "0.9.2"\n')
            self.assertEqual(module.declared_version(root), '0.9.2')

    def test_modified_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'a').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'diverge'):
                module.Assistant.verify_hashes(root, {'a': hashlib.sha256(b'original').hexdigest()})

    def test_failure_is_reported_and_stops_before_preparing(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(module, 'ROOT', Path(temp)), \
                patch.object(module.Assistant, 'preflight', side_effect=ValueError('Version mismatch')), \
                patch.object(module.Assistant, 'prepare') as prepare:
            self.assertEqual(module.main(['--version', '0.9.2']), 1)
            prepare.assert_not_called()
            result = json.loads((Path(temp)/'_updates/release-assistant/ULTIMO_RESULTADO.json').read_text())
            self.assertEqual(result['status'], 'FALHOU')

    def test_check_only_does_not_prepare(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(module, 'ROOT', Path(temp)), \
                patch.object(module.Assistant, 'preflight'), patch.object(module.Assistant, 'prepare') as prepare:
            self.assertEqual(module.main(['--version', '0.9.2', '--check-only']), 0)
            prepare.assert_not_called()

    def test_nonzero_command_and_timeout_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            assistant = module.Assistant(Path(temp), '0.9.2')
            with patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 7)):
                with self.assertRaisesRegex(ValueError, 'codigo 7'):
                    assistant.command('test', ['test'])
            with patch.object(module.subprocess, 'run', side_effect=subprocess.TimeoutExpired([], 300)):
                with self.assertRaisesRegex(ValueError, 'codigo 124'):
                    assistant.command('timeout', ['test'])

    def test_offline_pipeline_uses_fixed_base_and_verifies_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()/'source'
            assistant = module.Assistant(root, '0.9.2', offline=True)
            commands = []

            def command(label, args, cwd=None):
                commands.append(args)
                if label == 'Fixar base':
                    return 'a'*40
                if label == 'Preparar copia isolada':
                    destination = Path(args[args.index('--destination') + 1])
                    (destination/'nexus').mkdir(parents=True)
                    content = b'APP_VERSION = "0.9.2"\n'
                    (destination/'nexus/version.py').write_bytes(content)
                    report_dir = root/'_updates/release-preparation'
                    report_dir.mkdir()
                    (report_dir/'report.json').write_text(json.dumps({
                        'base': 'a'*40, 'destination': str(destination),
                        'sha256': {'nexus/version.py': hashlib.sha256(content).hexdigest()}}))
                return ''

            with patch.object(assistant, 'command', side_effect=command):
                assistant.prepare()
            self.assertEqual(assistant.report['verified_hashes'], 1)
            self.assertFalse(any('fetch' in command or 'push' in command for command in commands))
            self.assertEqual(sum('unittest' in command for command in commands), 5)

    def test_personal_email_stops_preflight(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(module.shutil, 'which', return_value='tool'):
            assistant = module.Assistant(Path(tmp), '0.9.2')
            with patch.object(assistant, 'command', return_value='fixture@example.invalid'):
                with self.assertRaisesRegex(ValueError, 'noreply'):
                    assistant.preflight()
