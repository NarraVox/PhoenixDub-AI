import tempfile
import unittest
from pathlib import Path
from nexus.correction_service import CorrectionService, CorrectionError, write_json


class GameOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.service = CorrectionService(self.base)
        self.folder = self.base / 'uploads/PROJETO_SAM'
        write_json(self.folder / 'project_data.json', [{'id': 'fala', 'file_name': 'fala.wav'}])
        source = self.folder / '_saida_final/fala.wav'
        source.parent.mkdir(); source.write_bytes(b'original')
        corrected = self.folder / '_correcoes/previas/fala.wav'
        corrected.parent.mkdir(parents=True); corrected.write_bytes(b'corrected')
        write_json(self.folder / '_correcoes/correcoes.json', {
            'fala': {'path': '_correcoes/previas/fala.wav', 'fingerprint': self.service.fingerprint(self.folder, source)}})
        self.key = self.service.discover()[0]['id']

    def status(self, **extra):
        write_json(self.folder / 'job_status.json', {'game_name': 'State of Decay', 'original_folder_name': 'SAM', **extra})

    def test_export_copies_both_and_updates_same_filename(self):
        self.status()
        result = self.service.export(self.key, 'fala')
        target = self.base / 'uploads/State of Decay/SAM/fala.wav'
        self.assertEqual(Path(result['folder']), target.parent.resolve())
        self.assertEqual(target.read_bytes(), b'corrected')
        self.assertEqual((Path(result['corrections_folder']) / 'fala.wav').read_bytes(), b'corrected')
        (target.parent / 'another.wav').write_bytes(b'keep')
        (self.folder / '_correcoes/previas/fala.wav').write_bytes(b'new correction')
        self.service.export(self.key)
        self.assertEqual(target.read_bytes(), b'new correction')
        self.assertEqual((target.parent / 'another.wav').read_bytes(), b'keep')
        self.assertEqual((self.folder / '_saida_final/fala.wav').read_bytes(), b'original')

    def test_sam_infers_game_from_shared_original_source(self):
        self.status(game_name=None, game_profile='padrao', original_folder_path=r'C:\source\dialog\sam')
        write_json(self.base / 'uploads/PROJETO_HRO/job_status.json', {
            'game_profile': 'state_of_decay', 'original_folder_path': r'C:\source\dialog\hro'})
        result = self.service.export(self.key)
        self.assertEqual(Path(result['folder']).parent.name, 'State of Decay')

    def test_missing_identity_preserves_regular_export(self):
        result = self.service.export(self.key)
        self.assertIsNone(result['game_folder'])
        self.assertTrue((Path(result['folder']) / 'fala.wav').exists())

    def test_path_escape_rejected(self):
        self.status(original_folder_name='../outside')
        with self.assertRaises(CorrectionError):
            self.service.export(self.key)


if __name__ == '__main__':
    unittest.main()
