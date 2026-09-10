import importlib.util
from pathlib import Path
from unittest import TestCase

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
