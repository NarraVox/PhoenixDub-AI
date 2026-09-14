import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import zipfile
from flask import Flask
import requests
from nexus import updates
from nexus.update_manager import UpdateManager
from nexus import update_worker as worker


class UpdateTests(unittest.TestCase):
    def release(self, tag='v0.9.0'):
        return {'tag_name': tag, 'body': '<script>unsafe()</script>', 'assets': []}

    def check(self, release):
        response = Mock()
        response.json.return_value = release
        with patch.object(updates.requests, 'get', return_value=response):
            return updates.check_release()

    def test_newer_equal_older(self):
        for tag, status in [('v0.9.0', 'available'), ('v' + updates.APP_VERSION, 'current'), ('v0.6.0', 'ahead'), ('v0.10.0', 'available')]:
            self.assertEqual(self.check(self.release(tag))['status'], status)

    def test_invalid_version_and_prerelease(self):
        for release in [self.release('v0.9.0-beta'), {**self.release(), 'prerelease': True}, self.release('../../bad')]:
            with self.assertRaises(ValueError):
                self.check(release)

    def test_offline_is_error_not_current(self):
        app = Flask(__name__)
        app.register_blueprint(updates.updates_blueprint)
        with patch.object(updates.requests, 'get', side_effect=requests.Timeout):
            response = app.test_client().get('/api/check-update')
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json['success'])
        self.assertNotIn('has_update', response.json)

    def test_asset_must_be_official(self):
        release = self.release()
        release['assets'] = [{'name': 'PhoenixDub_Update.zip', 'state': 'uploaded',
                              'browser_download_url': 'https://evil.example/file.zip', 'size': 1}]
        self.assertIsNone(self.check(release)['package'])
        release['assets'][0]['browser_download_url'] = f'https://github.com/{updates.REPOSITORY}/releases/download/v0.9.0/PhoenixDub_Update.zip'
        self.assertIsNotNone(self.check(release)['package'])

    def test_mutation_requires_header_and_local_origin(self):
        app = Flask(__name__)
        app.register_blueprint(updates.updates_blueprint)
        for headers in [{}, {'X-Nexus-Update': '1', 'Origin': 'http://localhost.evil.example:5000'}]:
            self.assertEqual(app.test_client().post('/api/updates/install', headers=headers).status_code, 403)

    def test_dev_checkout_blocked(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / '.git').write_text('gitdir: elsewhere')
            with self.assertRaises(ValueError):
                UpdateManager(root).ensure_installable()

    def test_development_marker_protects_without_git_and_in_subfolder(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root/'.nexus-development').write_text('protected')
            for target in (root, root/'dist'):
                self.assertTrue(worker.development_copy(target))
                with self.assertRaises(ValueError):
                    UpdateManager(target).ensure_installable()

    def test_downgrade_and_equal_version_blocked_before_download(self):
        with tempfile.TemporaryDirectory() as name:
            manager = UpdateManager(name)
            for version in ('0.6.0', updates.APP_VERSION):
                with patch('nexus.update_manager.threading.Thread') as thread:
                    with self.assertRaises(ValueError):
                        manager.start({'has_update': True, 'latest_version': version, 'package': {'url': 'unused'}})
                    thread.assert_not_called()

    def test_worker_blocks_development_even_if_manager_is_bypassed(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            stage, target = root/'stage', root/'app'
            target.mkdir()
            (target/'.nexus-development').write_text('protected')
            (target/'Nexus_AI_Pro.py').write_bytes(b'unpublished local work')
            manifest = worker.stage_package(self.package(root), stage, '0.9.0')
            with self.assertRaises(ValueError):
                worker.apply_files(target, stage, root/'backup', manifest['files'], '0.8.0')
            self.assertEqual((target/'Nexus_AI_Pro.py').read_bytes(), b'unpublished local work')
            self.assertFalse((root/'backup').exists())

    def test_worker_rechecks_newer_disk_version_before_copy(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            stage, target = root/'stage', root/'app'
            (target/'nexus').mkdir(parents=True)
            (target/'nexus/version.py').write_text('APP_VERSION="0.10.0"')
            manifest = worker.stage_package(self.package(root), stage, '0.9.0')
            with self.assertRaises(ValueError):
                worker.apply_files(target, stage, root/'backup', manifest['files'], '0.8.0')
            self.assertEqual((target/'nexus/version.py').read_text(), 'APP_VERSION="0.10.0"')
            self.assertFalse((target/'Nexus_AI_Pro.py').exists())

    def test_worker_blocks_equal_and_old_package(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            manifest = worker.stage_package(self.package(root), root/'stage', '0.9.0')
            for current in ('0.9.0', '0.10.0'):
                with self.assertRaises(ValueError):
                    worker.apply_files(root/'app', root/'stage', root/'backup', manifest['files'], current)
                self.assertFalse((root/'app').exists())

    def test_marker_added_after_download_blocks_restart(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            manager = UpdateManager(root)
            manager.state['status'] = 'ready'
            manager.plan = {'version': '0.9.0'}
            (root/'.nexus-development').write_text('protected')
            with patch('nexus.update_manager.subprocess.Popen') as launch:
                with self.assertRaises(ValueError):
                    manager.launch()
                launch.assert_not_called()

    def test_api_exposes_development_protection(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root/'.nexus-development').write_text('protected')
            with patch.object(updates, 'manager', UpdateManager(root)):
                result = self.check(self.release())
            self.assertTrue(result['development_copy'])
            self.assertFalse(result['automatic_supported'])

    def package(self, root, extra=None, bad_hash=False):
        content = {'Nexus_AI_Pro.py': b'entry', 'Nexus_AI_Pro.exe': b'exe',
                   'nexus/version.py': b'APP_VERSION="0.9.0"', 'requirements.txt': b'flask'}
        content.update(extra or {})
        hashes = {n: hashlib.sha256(data).hexdigest() for n, data in content.items()}
        if bad_hash:
            hashes['Nexus_AI_Pro.py'] = '0' * 64
        archive = root / 'package.zip'
        with zipfile.ZipFile(archive, 'w') as package:
            for n, data in content.items():
                package.writestr(n, data)
            package.writestr('manifest.json', json.dumps({'version': '0.9.0', 'files': hashes}))
        return archive

    def test_stage_and_preserve_user_data(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            stage, target, backup = root/'stage', root/'app', root/'backup'
            (target/'uploads').mkdir(parents=True)
            (target/'uploads/voice.wav').write_bytes(b'user audio')
            (target/'Nexus_AI_Pro.py').write_bytes(b'old')
            manifest = worker.stage_package(self.package(root), stage, '0.9.0')
            worker.apply_files(target, stage, backup, manifest['files'], '0.8.0')
            self.assertEqual((target/'Nexus_AI_Pro.py').read_bytes(), b'entry')
            self.assertEqual((backup/'Nexus_AI_Pro.py').read_bytes(), b'old')
            self.assertEqual((target/'uploads/voice.wav').read_bytes(), b'user audio')

    def test_bad_paths_hash_and_version_rejected(self):
        for extra, bad_hash, version in [({'../escape.py': b'x'}, False, '0.9.0'),
                                        ({'uploads/user.py': b'x'}, False, '0.9.0'),
                                        ({'nexus/core/server_config.json': b'{}'}, False, '0.9.0'),
                                        ({}, True, '0.9.0'), ({}, False, '0.8.0')]:
            with self.subTest(extra=extra, version=version), tempfile.TemporaryDirectory() as name:
                root = Path(name)
                with self.assertRaises(ValueError):
                    worker.stage_package(self.package(root, extra, bad_hash), root/'stage', version)

    def test_copy_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            stage, target, backup = root/'stage', root/'app', root/'backup'
            target.mkdir()
            (target/'Nexus_AI_Pro.py').write_bytes(b'old')
            manifest = worker.stage_package(self.package(root), stage, '0.9.0')
            real_copy = worker.atomic_copy
            def fail(source, destination):
                if source == stage/'Nexus_AI_Pro.exe':
                    raise OSError('simulated locked file')
                return real_copy(source, destination)
            with patch.object(worker, 'atomic_copy', side_effect=fail), self.assertRaises(OSError):
                worker.apply_files(target, stage, backup, manifest['files'], '0.8.0')
            self.assertEqual((target/'Nexus_AI_Pro.py').read_bytes(), b'old')
            self.assertFalse((target/'Nexus_AI_Pro.exe').exists())

    def test_modified_stage_rejected_before_copy(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            manifest = worker.stage_package(self.package(root), root/'stage', '0.9.0')
            (root/'stage/Nexus_AI_Pro.py').write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                worker.apply_files(root/'app', root/'stage', root/'backup', manifest['files'], '0.8.0')
            self.assertFalse((root/'app').exists())

    def test_download_verified_and_dependencies_checked(self):
        for requirements, expected_status in [('flask', 'ready'), ('different', 'error')]:
            with self.subTest(requirements=requirements), tempfile.TemporaryDirectory() as name:
                root = Path(name)
                (root/'requirements.txt').write_text(requirements)
                archive = self.package(root)
                data = archive.read_bytes()
                release = {'latest_version': '0.9.0', 'package': {'url': 'https://example.test/package',
                           'size': len(data), 'digest': 'sha256:' + hashlib.sha256(data).hexdigest()}}
                response = Mock()
                response.__enter__ = Mock(return_value=response)
                response.__exit__ = Mock(return_value=False)
                response.iter_content.return_value = [data]
                manager = UpdateManager(root)
                with patch('nexus.update_manager.requests.get', return_value=response):
                    manager.download(release)
                self.assertEqual(manager.status()['status'], expected_status)
                self.assertEqual((root/'requirements.txt').read_text(), requirements)

    def test_bad_download_digest_never_becomes_ready(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.iter_content.return_value = [b'bad']
            manager = UpdateManager(root)
            with patch('nexus.update_manager.requests.get', return_value=response):
                manager.download({'latest_version': '0.9.0', 'package': {'url': 'https://example.test', 'size': 3, 'digest': 'sha256:' + '0'*64}})
            self.assertEqual(manager.status()['status'], 'error')
            self.assertIsNone(manager.plan)

    def test_worker_launch_is_external_and_does_not_copy_yet(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            stage = root/'_updates/test/stage'
            stage.mkdir(parents=True)
            manager = UpdateManager(root)
            manager.state['status'] = 'ready'
            manager.plan = {'root': str(root), 'stage': str(stage), 'backup': str(stage.parent/'backup'),
                            'files': {}, 'version': '0.9.0'}
            with patch('nexus.update_manager.subprocess.Popen') as launch:
                manager.launch()
            command = launch.call_args.args[0]
            self.assertTrue(Path(command[1]).is_file())
            plan = json.loads(Path(command[2]).read_text())
            self.assertEqual(plan['root'], str(root))
            self.assertEqual(manager.status()['status'], 'installing')
            self.assertFalse((root/'Nexus_AI_Pro.py').exists())


if __name__ == '__main__':
    unittest.main()
