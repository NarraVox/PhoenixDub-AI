import unittest
from pathlib import Path
import numpy as np
from tests import test_corrections as fixtures
from nexus.correction_service import read_audio, read_json, write_json
from nexus.correction_search import search_uploads
from nexus.correction_timing import original_duration


class TimingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.CorrectionTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.service = self.fixture.service

    def test_original_duration_metadata_and_search(self):
        self.assertEqual(original_duration({'duration':3.5},'games'),3.5)
        self.assertEqual(original_duration({'start_time':2,'end_time':6},'games'),4)
        self.assertEqual(original_duration({'start':1,'end':4.5,'duration':99},'video'),3.5)
        self.assertIsNone(original_duration({'duration':float('nan')},'games'))
        items = search_uploads(self.service)['items']
        self.assertTrue(all(i['original_duration']==2 for i in items))

    def test_long_text_is_allowed_speed_capped_and_audio_not_cut(self):
        metadata = self.fixture.game / 'project_data.json'
        segments = read_json(metadata); segments[0]['duration']=1
        write_json(metadata,segments)
        def long_voice(text, ref, output, duration, emotion):
            self.assertEqual(duration,1)  # Uses original window, not existing 2s dubbed file.
            self.fixture.tone(output,4,600)
        self.service.synthesizer=long_voice
        key=self.fixture.keys['games']
        info=self.service.preview(key,'seg_0','Uma correção bem maior do que o tempo recomendado para esta fala.')
        self.assertEqual(info['speed'],1.2)
        self.assertGreater(info['generated_duration'],3.2)
        self.assertEqual(info['original_duration'],1)
        self.assertGreater(info['overrun_seconds'],2)
        path,_=self.service.preview_file(key,info['token'])
        audio=read_audio(path).set_channels(1)
        samples=np.asarray(audio.get_array_of_samples(),dtype=float)
        peak=np.argmax(abs(np.fft.rfft(samples))) * audio.frame_rate/len(samples)
        self.assertAlmostEqual(peak,600,delta=3)  # Tempo change preserves pitch.
        self.service.apply(key,info['token'])
        item=self.service.search(key)['items'][0]
        self.assertEqual(item['translated'],'Uma correção bem maior do que o tempo recomendado para esta fala.')

    def test_short_audio_is_not_accelerated(self):
        info=self.service.preview(self.fixture.keys['games'],'seg_0','Fala curta')
        self.assertEqual(info['speed'],1)
        self.assertAlmostEqual(info['generated_duration'],2,delta=.03)

    def test_video_preserves_long_corrected_audio_past_original_end(self):
        self.service.synthesizer=lambda text,ref,out,duration,emotion:self.fixture.tone(out,6,600)
        key=self.fixture.keys['video']
        info=self.service.preview(key,'seg_1','Uma fala longa')
        self.service.apply(key,info['token'])
        result=self.service.export(key)
        master=read_audio(Path(result['folder'])/'vozes_corrigidas.wav')
        self.assertGreater(len(master),6900)
        self.assertGreater(master[6500:6800].rms,0)


if __name__=='__main__':
    unittest.main()
