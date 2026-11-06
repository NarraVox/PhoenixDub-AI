import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from nexus.dj.style_analyzer.fills import detect_fills


class FillDetectorTests(unittest.TestCase):
    def test_groups_matching_partial_bar_fills_and_rejects_ending(self):
        sample_rate = 8000
        bar_count = 32
        audio = np.zeros(sample_rate * bar_count, dtype=np.float32)

        def hit(bar, step, frequency, amplitude=0.3):
            first = round(((bar - 1) + step / 16) * sample_rate)
            t = np.arange(280) / sample_rate
            audio[first:first + len(t)] += (amplitude * np.sin(2 * np.pi * frequency * t)
                                             * np.exp(-t * 100))

        for bar in range(1, bar_count + 1):
            for step, frequency in ((0, 90), (4, 500), (8, 90), (12, 500),
                                    (2, 3500), (6, 3500), (10, 3500), (14, 3500)):
                hit(bar, step, frequency)
        for bar in (4, 12):
            for step in (1, 3, 5, 9, 11, 13, 15):
                hit(bar, step, 1300, 1.5)
        for step in (1, 3, 5, 7, 9, 11, 13):
            hit(17, step, 2000, 1.5)
            hit(32, step, 1500, 1.5)
        bars = [{"bar": index, "start_seconds": float(index - 1),
                 "end_seconds": float(index)} for index in range(1, bar_count + 1)]
        with tempfile.TemporaryDirectory() as tmp:
            stem = Path(tmp) / "drums.wav"
            sf.write(stem, audio, sample_rate)
            result = detect_fills(stem, bars, [])

        self.assertEqual([[item["start_bar"] for item in cluster["occurrences"]]
                          for cluster in result["clusters"]], [[4, 12], [17]])
        self.assertEqual([cluster["id"] for cluster in result["clusters"]],
                         ["FILL_A", "FILL_B"])
        self.assertGreater(result["fills"][0]["start_step"], 0)
        self.assertLess(result["fills"][0]["duration_seconds"], 1)
        self.assertIn({"bars": [32, 32], "reason": "no_prompt_main_return"},
                      result["rejected_candidates"])
        self.assertEqual(len(result["bar_signatures"][3]["band_onsets"]), 3)

    def test_short_tail_reuses_fill_type_and_human_review_can_confirm_ending(self):
        sample_rate = 8000
        audio = np.zeros(sample_rate * 32, dtype=np.float32)

        def hit(bar, step, frequency, amplitude=0.3):
            first = round(((bar - 1) + step / 16) * sample_rate)
            t = np.arange(280) / sample_rate
            audio[first:first + len(t)] += (amplitude * np.sin(2 * np.pi * frequency * t)
                                             * np.exp(-t * 100))

        for bar in range(1, 33):
            for step, frequency in ((0, 90), (4, 500), (8, 90), (12, 500),
                                    (2, 3500), (6, 3500), (10, 3500), (14, 3500)):
                hit(bar, step, frequency)
        for bar in (4, 12):
            for step in (1, 3, 5, 9, 11, 13, 15):
                hit(bar, step, 1300, 1.5)
        for bar in (5, 13, 21):
            for step in (1, 3, 5, 13):
                hit(bar, step, 1700, 1.5)
        for step in (1, 3, 5, 7, 9, 11, 13):
            hit(32, step, 2000, 1.5)
        bars = [{"bar": index, "start_seconds": float(index - 1),
                 "end_seconds": float(index)} for index in range(1, 33)]
        with tempfile.TemporaryDirectory() as tmp:
            stem = Path(tmp) / "drums.wav"
            sf.write(stem, audio, sample_rate)
            automatic = detect_fills(stem, bars, [])
            reviewed = detect_fills(stem, bars, [], review={
                "version": 1, "source": "listening_test",
                "confirmed_regions": [{"start_bar": 32, "end_bar": 32}],
            })

        main_cluster = next(cluster for cluster in automatic["clusters"]
                            if cluster["occurrences"][0]["start_bar"] == 4)
        self.assertEqual([item["start_bar"] for item in main_cluster["occurrences"]],
                         [4, 12, 21])
        self.assertEqual(main_cluster["occurrences"][-1]["variant"], "tail_only")
        self.assertTrue(any(row["bars"] == [32, 32] for row in automatic["rejected_candidates"]))
        ending = next(row for row in reviewed["fills"] if row["start_bar"] == 32)
        self.assertTrue(ending["human_confirmed"])
        self.assertIsNone(ending["main_returns_at_bar"])
        self.assertEqual(reviewed["unmatched_review_regions"], [])


if __name__ == "__main__":
    unittest.main()
