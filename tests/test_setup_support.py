import ast
import hashlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from nexus.build_tools import setup_support as setup

ROOT = Path(__file__).resolve().parents[1]


class SetupSupportTests(unittest.TestCase):
    def test_modular_requirements_share_constraints(self):
        base = setup.requirement_plan(ROOT, {'base': True})
        self.assertIn('Flask==3.1.0', base)
        self.assertNotIn('torch==2.6.0+cu124', base)
        voice = setup.requirement_plan(ROOT, {'voice': True, 'llama': True})
        for requirement in ['torch==2.6.0+cu124', 'faster-qwen3-tts==0.2.6', 'transformers==4.57.3', 'whisperx==3.3.4']:
            self.assertIn(requirement, voice)
        self.assertEqual(voice[-2:], ['-c', str(ROOT/'requirements.txt')])

    def test_broken_env_never_uses_global_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'env').mkdir()
            with patch.object(setup.subprocess, 'run') as run, self.assertRaises(ValueError):
                setup.ensure_environment(root)
            run.assert_not_called()

    def test_existing_environment_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); py = root/'env/Scripts/python.exe';py.parent.mkdir(parents=True);py.write_bytes(b'fixture')
            with patch.object(setup.subprocess, 'run') as run:
                self.assertEqual(setup.ensure_environment(root), str(py.resolve()))
            self.assertEqual(run.call_count, 1)
            self.assertEqual(py.read_bytes(), b'fixture')

    def test_existing_ffmpeg_prevents_download(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(setup.shutil, 'which', return_value='ffmpeg'), \
                patch.object(setup, 'working_tool', return_value=True), patch.object(setup.urllib.request, 'urlopen') as download:
            setup.ensure_ffmpeg(Path(tmp), lambda message: None)
            download.assert_not_called()

    def archive(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            z.writestr('build/bin/ffmpeg.exe', b'ffmpeg')
            z.writestr('build/bin/ffprobe.exe', b'ffprobe')
            z.writestr('../escape.txt', b'never extract')
        return data.getvalue()

    def test_ffmpeg_checksum_and_allowlist(self):
        data = self.archive()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ), \
                patch.object(setup.shutil, 'which', return_value=None), patch.object(setup, 'working_tool', return_value=True), \
                patch.object(setup.urllib.request, 'urlopen', side_effect=[io.BytesIO(hashlib.sha256(data).hexdigest().encode()), io.BytesIO(data)]):
            root = Path(tmp);setup.ensure_ffmpeg(root, lambda message: None)
            self.assertEqual((root/'env/ffmpeg/bin/ffmpeg.exe').read_bytes(), b'ffmpeg')
            self.assertEqual((root/'env/ffmpeg/bin/ffprobe.exe').read_bytes(), b'ffprobe')
            self.assertFalse((root/'escape.txt').exists())
            self.assertIn(str(root/'env/ffmpeg/bin'), os.environ['PATH'])

    def test_corrupt_download_does_not_install(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(setup.shutil, 'which', return_value=None), \
                patch.object(setup.urllib.request, 'urlopen', side_effect=[io.BytesIO(b'0'*64), io.BytesIO(self.archive())]):
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                setup.ensure_ffmpeg(Path(tmp), lambda message: None)
            self.assertFalse((Path(tmp)/'env/ffmpeg/bin/ffmpeg.exe').exists())

    def test_model_downloader_has_no_local_subprocess_import(self):
        tree = ast.parse((ROOT/'nexus/build_tools/nexus_setup.py').read_text(encoding='utf-8'))
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'download_model_with_retry')
        self.assertFalse(any(isinstance(n, ast.Import) and any(a.name == 'subprocess' for a in n.names) for n in ast.walk(method)))

    def test_bat_uses_script_directory_and_checks_failures(self):
        text = (ROOT/'TESTAR_SETUP.bat').read_text()
        self.assertIn('pushd "%~dp0"', text)
        self.assertNotIn('%HF_TOKEN', text)
        self.assertNotIn('%errorlevel%', text)
        self.assertIn('if errorlevel 1 goto :failed', text)
        self.assertIn('Setup_Nexus.py', text)
