import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import zipfile
from nexus.distribution import deploy_runtime


class DistributionTests(TestCase):
    def test_extract_and_preserve_config(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            bundle, target = root/'bundle', root/'app'
            bundle.mkdir()
            (target/'nexus/core').mkdir(parents=True)
            (target/'nexus/core/server_config.json').write_text('local config')
            with zipfile.ZipFile(bundle/'runtime.zip','w') as z:
                z.writestr('nexus/core/server_config.json','default config')
                z.writestr('nexus/client/index.html','new interface')
            with patch('sys._MEIPASS', str(bundle), create=True):
                deploy_runtime(target, overwrite=True)
            self.assertEqual((target/'nexus/core/server_config.json').read_text(),'local config')
            self.assertEqual((target/'nexus/client/index.html').read_text(),'new interface')

    def test_development_install_blocked(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            (root/'.nexus-development').touch()
            with zipfile.ZipFile(root/'runtime.zip','w'): pass
            with patch('sys._MEIPASS', str(root), create=True), self.assertRaises(ValueError):
                deploy_runtime(root, overwrite=True)

    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            with zipfile.ZipFile(root/'runtime.zip','w') as z: z.writestr('../escape.py','bad')
            with patch('sys._MEIPASS', str(root), create=True), self.assertRaises(ValueError):
                deploy_runtime(root/'app')
            self.assertFalse((root/'escape.py').exists())
