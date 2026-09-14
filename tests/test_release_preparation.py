import importlib.util
import contextlib
import io
import json
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('prepare_release',Path(__file__).resolve().parents[1]/'release/prepare_release.py')
release=importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleasePolicyTests(TestCase):
    def test_allowed_program_files(self):
        for name in ['nexus/updates.py','nexus/client/js/hub_updates.js','README.md','release/policy.json','tests/test_updates.py']:
            self.assertTrue(release.allowed(name),name)

    def test_private_and_experimental_files_excluded(self):
        for name in ['.nexus-development','backups/audio.wav','uploads/data.json','MODELS/model.gguf','env/python.exe',
                     'nexus/core/qwen_asr_loader.py','nexus/core/server_config.json','nexus/client/installer_ui.rar','scripts/benchmark.py','token_hf.txt']:
            self.assertFalse(release.allowed(name),name)

    def test_credentials_blocked_without_exposing_value(self):
        for credential in ['ghp_'+'A'*36,'hf_'+'A'*30]:
            with self.assertRaises(ValueError) as caught:
                release.scan('nexus/config.py', ('token = "'+credential+'"').encode())
            self.assertNotIn(credential,str(caught.exception))


class ReleaseMergeTests(TestCase):
    def exercise(self, conflicting=False, resolved=False):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()/'source'
            root.mkdir()

            def git(*args, cwd=None):
                return subprocess.check_output(['git', *args], cwd=cwd or root, stderr=subprocess.PIPE)

            git('init', '-b', 'main')
            git('config', 'user.email', 'fixture@example.invalid')
            git('config', 'user.name', 'Release test fixture')
            git('config', 'core.autocrlf', 'false')
            git('remote', 'add', 'origin', release.POLICY['repository'])
            original = b'first\n' + b'unchanged\n'*20 + b'last\n'
            (root/'README.md').write_bytes(original)
            (root/'nexus').mkdir()
            (root/'nexus/obsolete.py').write_bytes(b'pass\n')
            git('add', 'README.md', 'nexus/obsolete.py')
            git('commit', '-m', 'Fixture ancestor')
            ancestor = git('rev-parse', 'HEAD').decode().strip()
            remote = original.replace(b'first', b'remote') if conflicting else original.replace(b'last', b'remote')
            (root/'README.md').write_bytes(remote)
            git('add', 'README.md')
            git('commit', '-m', 'Fixture remote')
            base = git('rev-parse', 'HEAD').decode().strip()
            git('checkout', '-b', 'fixture-local', ancestor)
            local = original.replace(b'first', b'local')
            (root/'README.md').write_bytes(local)
            git('rm', 'nexus/obsolete.py')
            git('add', 'README.md')
            git('commit', '-m', 'Fixture local changes')
            git('config', 'core.autocrlf', 'true')
            (root/'README.md').write_bytes(local.replace(b'\n', b'\r\n'))
            self.assertEqual(git('diff', '--name-only', 'HEAD'), b'')
            destination = Path(temp)/'release'
            with patch.object(release, 'ROOT', root), patch.object(release, 'git', git), contextlib.redirect_stdout(io.StringIO()):
                if conflicting and not resolved:
                    with self.assertRaisesRegex(ValueError, 'returncode=1'):
                        release.prepare(destination, base)
                    self.assertFalse(destination.exists())
                    return
                release.prepare(destination, base, ['README.md'] if resolved else [])
            expected = local if resolved else local.replace(b'last', b'remote')
            self.assertEqual((destination/'README.md').read_bytes().replace(b'\r\n', b'\n'), expected)
            self.assertFalse((destination/'nexus/obsolete.py').exists())
            self.assertEqual((root/'README.md').read_bytes(), local.replace(b'\n', b'\r\n'))
            report = json.loads((root/'_updates/release-preparation/report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['ancestor'], ancestor)
            self.assertIn('README.md', report['included_changes'])
            self.assertIn('nexus/obsolete.py', report['included_changes'])
            self.assertEqual(report['resolved_remote'], ['README.md'] if resolved else [])

    def test_committed_changes_deletion_and_crlf_preserve_both_sides(self):
        self.exercise()

    def test_real_conflict_stops_before_worktree_creation(self):
        self.exercise(conflicting=True)

    def test_explicit_reconciliation_is_preserved_and_reported(self):
        self.exercise(conflicting=True, resolved=True)
