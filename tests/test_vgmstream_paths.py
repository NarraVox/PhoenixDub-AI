import tempfile
import unittest
from pathlib import Path

from nexus.runtime_paths import resolve_vgmstream_path


class VgmstreamPathTests(unittest.TestCase):
    def test_prefers_environment_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            installed = root / "env" / "tools_vgmstream" / "vgmstream-cli.exe"
            installed.parent.mkdir(parents=True)
            installed.touch()
            legacy = root / "tools" / "vgmstream-cli" / "vgmstream-cli.exe"
            legacy.parent.mkdir(parents=True)
            legacy.touch()

            self.assertEqual(resolve_vgmstream_path(root), installed)

    def test_falls_back_to_legacy_release_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "tools" / "vgmstream-cli" / "vgmstream-cli.exe"
            legacy.parent.mkdir(parents=True)
            legacy.touch()

            self.assertEqual(resolve_vgmstream_path(root), legacy)

    def test_reports_expected_environment_path_when_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = root / "env" / "tools_vgmstream" / "vgmstream-cli.exe"

            self.assertEqual(resolve_vgmstream_path(root), expected)


if __name__ == "__main__":
    unittest.main()
