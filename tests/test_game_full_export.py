import tempfile
import unittest
from pathlib import Path
from nexus.correction_service import read_json, write_json
from nexus.game_full_export import copy_full_output


class FullExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()

    def project(self, character):
        folder = self.base / 'uploads' / ('PROJETO_123_' + character)
        write_json(folder / 'job_status.json', {
            'game_profile': 'state_of_decay', 'original_folder_name': character,
            'project_name': 'nome_interno', 'status': 'completed'})
        final = folder / '_saida_final'
        final.mkdir()
        (final / 'fala.mp3').write_bytes(character.encode())
        (final / 'outra.wav').write_bytes(b'another voice line')
        return folder

    def test_complete_characters_gather_in_one_game_directory(self):
        for character in ['ALN', 'ED', 'SAM']:
            folder = self.project(character)
            count, target = copy_full_output(folder, folder.name)
            self.assertEqual(count, 2)
            self.assertEqual(target, self.base / 'uploads/State of Decay' / character)
            self.assertEqual((target / 'fala.mp3').read_bytes(), character.encode())
            self.assertEqual((folder / '_saida_final/fala.mp3').read_bytes(), character.encode())
            self.assertEqual(read_json(folder / 'job_status.json')['status'], 'completed')

    def test_existing_game_folder_merges_without_removing_other_character(self):
        aln = self.project('ALN'); ed = self.project('ED')
        _, aln_target = copy_full_output(aln, aln.name)
        copy_full_output(ed, ed.name)
        (aln / '_saida_final/fala.mp3').write_bytes(b'updated ALN')
        copy_full_output(aln, aln.name)
        self.assertEqual((aln_target / 'fala.mp3').read_bytes(), b'updated ALN')
        self.assertEqual((aln_target.parent / 'ED/fala.mp3').read_bytes(), b'ED')

    def test_other_game_keeps_previous_project_layout(self):
        folder = self.project('ALN')
        status = read_json(folder / 'job_status.json')
        status.update(game_profile='cod', game_name='Call of Duty')
        write_json(folder / 'job_status.json', status)
        _, target = copy_full_output(folder, folder.name)
        self.assertEqual(target, self.base / 'uploads/Call of Duty/nome_interno')

    def test_original_file_names_extensions_and_subfolders_preserved(self):
        folder = self.project('ALN')
        nested = folder / '_saida_final/dialogue'
        nested.mkdir()
        (nested / 'dx_original_010_b.ogg').write_bytes(b'original structure')
        count, target = copy_full_output(folder, folder.name)
        self.assertEqual(count, 3)
        source_paths = sorted(str(p.relative_to(folder / '_saida_final')) for p in (folder / '_saida_final').rglob('*') if p.is_file())
        target_paths = sorted(str(p.relative_to(target)) for p in target.rglob('*') if p.is_file())
        self.assertEqual(source_paths, target_paths)


if __name__ == '__main__':
    unittest.main()
