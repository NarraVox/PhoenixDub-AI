import ast
import json
from pathlib import Path
import symtable
import tempfile
import unittest
from unittest.mock import Mock

from nexus.dj.music_request import submit_synthesis, configure_extension, extract_continuation, choose_reference_start


class MusicRequestTests(unittest.TestCase):
    def test_reference_window_excludes_both_ends(self):
        for total in (40, 74.47, 180, 492):
            for choose in (lambda low, high: low, lambda low, high: high):
                start = choose_reference_start(total, choose)
                self.assertGreaterEqual(start, 5)
                self.assertLessEqual(start + 30, total - 5)

    def test_short_reference_is_rejected_instead_of_using_ending(self):
        for total in (10, 30, 39.9, float('nan')):
            with self.assertRaises(ValueError):
                choose_reference_start(total)

    def test_three_minutes_is_new_audio_plus_thirty_seconds_context(self):
        parameters = {}
        configure_extension(parameters, 30, 180)
        self.assertEqual(parameters['duration'], 210)
        self.assertEqual(parameters['repainting_end'], 210)
        self.assertEqual(parameters['repainting_start'], 28.5)

    def test_continuation_excludes_original_and_keeps_only_new_duration(self):
        import numpy as np
        import soundfile as sf
        with tempfile.TemporaryDirectory() as directory:
            source, dest = Path(directory) / 'whole.wav', Path(directory) / 'new.wav'
            sr = 8000
            samples = np.concatenate([np.full((sr * 2, 2), 0.1), np.full((sr, 2), 0.7)])
            sf.write(source, samples, sr, subtype='FLOAT')
            extract_continuation(source, dest, 2, 1)
            result, rate = sf.read(dest)
            self.assertEqual(len(result), sr)
            self.assertEqual(rate, sr)
            self.assertTrue(np.allclose(result, 0.7, atol=1e-6))

    def test_missing_extension_does_not_export_original(self):
        import numpy as np
        import soundfile as sf
        with tempfile.TemporaryDirectory() as directory:
            source, dest = Path(directory) / 'whole.wav', Path(directory) / 'new.wav'
            sf.write(source, np.zeros((8000, 2)), 8000)
            with self.assertRaises(ValueError):
                extract_continuation(source, dest, 1, 1)
            self.assertFalse(dest.exists())

    def test_faithful_cover_sends_full_source_and_independent_timbre_stream(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'base.wav'
            source.write_bytes(b'RIFF-reference')
            client = Mock()
            handles = []

            def post(url, **kwargs):
                self.assertEqual(json.loads(kwargs['data']['request'])['task_type'], 'cover-nofsq')
                for key in ('audio', 'ref_audio'):
                    handle = kwargs['files'][key][1]
                    self.assertEqual(handle.read(), b'RIFF-reference')
                    handles.append(handle)
                self.assertIsNot(handles[0], handles[1])

            client.post.side_effect = post
            submit_synthesis(client, {'task_type': 'cover-nofsq'}, source)
            self.assertTrue(all(handle.closed for handle in handles))

    def test_extension_uses_measured_seconds_not_concatenated_tokens(self):
        parameters = {'audio_codes': '<|audio_1|><|audio_2|>', 'duration': 75}
        configure_extension(parameters, 74.48, 30)
        self.assertAlmostEqual(parameters['duration'], 104.48)
        self.assertAlmostEqual(parameters['repainting_end'], 104.48)
        self.assertAlmostEqual(parameters['repainting_start'], 72.98)
        self.assertEqual(parameters['task_type'], 'repaint')

    def test_extension_rejects_invalid_durations(self):
        for source, extra in [(0, 10), (10, -1), (float('nan'), 10), (10, float('inf'))]:
            with self.subTest(source=source, extra=extra), self.assertRaises(ValueError):
                configure_extension({}, source, extra)

    def test_source_upload_is_open_and_json_is_not_double_encoded(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'base.wav'
            source.write_bytes(b'RIFF-test')
            parameters = {'task_type': 'repaint', 'repainting_end': 20, 'caption': 'forró'}
            client = Mock()
            captured = []

            def post(url, **kwargs):
                self.assertNotIn('json', kwargs)
                self.assertEqual(json.loads(kwargs['data']['request']), parameters)
                name, handle, mime = kwargs['files']['audio']
                self.assertEqual(handle.read(), b'RIFF-test')
                self.assertEqual(name, 'base.wav')
                self.assertTrue(mime.startswith('audio/'))
                captured.append(handle)
                return 'ok'

            client.post.side_effect = post
            self.assertEqual(submit_synthesis(client, parameters, source), 'ok')
            self.assertTrue(captured[0].closed)

    def test_text_generation_posts_parameters_directly(self):
        client = Mock()
        parameters = {'caption': 'forro', 'duration': 10}
        submit_synthesis(client, parameters)
        client.post.assert_called_once_with(
            'http://127.0.0.1:8085/synth', json=parameters, timeout=300)

    def test_missing_source_does_not_fall_back_to_text_generation(self):
        client = Mock()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                submit_synthesis(client, {}, Path(directory) / 'missing.wav')
        client.post.assert_not_called()

    def test_network_failure_closes_reference_and_is_not_silently_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'base.mp3'
            source.write_bytes(b'audio')
            client = Mock()
            handles = []

            def post(url, **kwargs):
                handles.append(kwargs['files']['audio'][1])
                raise RuntimeError('offline')

            client.post.side_effect = post
            with self.assertRaisesRegex(RuntimeError, 'offline'):
                submit_synthesis(client, {}, source)
            self.assertTrue(handles[0].closed)
            self.assertEqual(client.post.call_count, 1)

    def test_generation_json_binding_is_global(self):
        path = Path(__file__).resolve().parents[1] / 'nexus/dj/vortex_music.py'
        code = path.read_text(encoding='utf-8')
        ast.parse(code)
        function = next(child for child in symtable.symtable(code, str(path), 'exec').get_children()
                        if child.get_name() == 'run_music_generation_flow_logic')
        self.assertTrue(function.lookup('json').is_global())


if __name__ == '__main__':
    unittest.main()
