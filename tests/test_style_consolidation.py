import unittest

from nexus.dj.style_analyzer.consolidation import apply_rhythm_consensus, consolidate_rhythm, _chord_classes
from nexus.dj.style_analyzer.rhythm import bar_features
import numpy as np


class StyleConsolidationTests(unittest.TestCase):
    def _grid(self):
        return {
            "bpm": None, "tempo_estimate": 174.0, "tempo_ambiguous": True,
            "meter": "4/4", "grid_confidence": 0.5,
            "duration": 100,
            "bars": [{"bar": i + 1, "start_seconds": i * 1.38,
                      "end_seconds": (i + 1) * 1.38} for i in range(100)],
            "tempo_hypotheses": [
                {"bpm": 175.0, "measured_bpm": 174.0, "score": 0.99,
                 "meter_hypotheses": [{"meter": 2, "phase": 1, "accent_score": 0.05},
                                      {"meter": 4, "phase": 3, "accent_score": 0.06}],
                 "beat_times": [i * 60 / 175 for i in range(800)]},
                {"bpm": 87.5, "measured_bpm": 87.0, "score": 0.98,
                 "meter_hypotheses": [{"meter": 2, "phase": 0, "accent_score": 0.01},
                                      {"meter": 4, "phase": 2, "accent_score": 0.0}],
                 "beat_times": [i * 60 / 87.5 for i in range(400)]},
            ],
        }

    def test_sheet_sage_resolves_equivalent_half_tempo_meter(self):
        grid = self._grid()
        result = consolidate_rhythm(grid, {"model_tempo_bpm": 91, "meter": "2/4"})
        self.assertEqual(result["status"], "corroborated_interpretation")
        self.assertEqual(result["bpm"], 87.0)
        self.assertEqual(result["meter"], "2/4")
        self.assertAlmostEqual(result["bar_duration_seconds"], 120 / 87.0, places=5)

    def test_consensus_keeps_drum_derived_bar_phase(self):
        grid = self._grid()
        consensus = consolidate_rhythm(grid, {"model_tempo_bpm": 91, "meter": "2/4"})
        grid["downbeats"] = [0.5, 1.88, 3.26]
        grid["beats"] = [i * 0.345 for i in range(200)]
        grid["tempo_tracker_hypothesis"] = 175.0
        grid["bars"] = [{"bar": 1, "start_seconds": 0.5, "end_seconds": 1.88},
                        {"bar": 2, "start_seconds": 1.88, "end_seconds": 3.26}]
        updated = apply_rhythm_consensus(grid, consensus)
        self.assertAlmostEqual(updated["bars"][0]["start_seconds"], 0.5, places=6)
        self.assertAlmostEqual(updated["bars"][0]["end_seconds"], 0.5 + 120 / 87.0, delta=0.02)
        self.assertEqual(updated["bpm"], 87.0)
        self.assertEqual(updated["meter"], "2/4")
        self.assertFalse(updated["tempo_ambiguous"])

    def test_explicit_user_meter_constrains_consensus_candidates(self):
        result = consolidate_rhythm(self._grid(), {"model_tempo_bpm": 91, "meter": "2/4"}, meter_hint=4)
        self.assertEqual(result["status"], "user_constrained_interpretation")
        self.assertEqual(result["meter"], "4/4")
        self.assertIsNone(result["candidate_margin"])
        self.assertTrue(all(item["meter"] == "4/4" for item in result["candidates"]))

    def test_parses_major_minor_and_flat_chords(self):
        self.assertEqual(_chord_classes("Gm"), {7, 10, 2})
        self.assertEqual(_chord_classes("D#"), {3, 7, 10})
        self.assertEqual(_chord_classes("Bb"), {10, 2, 5})

    def test_bar_feature_resolution_does_not_depend_on_equivalent_meter_label(self):
        sr = 22050
        y = np.sin(2 * np.pi * 110 * np.arange(sr * 2, dtype=np.float32) / sr)
        bars = [{"start_seconds": 0.0, "end_seconds": 2.0}]
        meter_two = bar_features(y, sr, bars, 2)[0]["vector"]
        meter_four = bar_features(y, sr, bars, 4)[0]["vector"]
        self.assertEqual(len(meter_two), len(meter_four))
        np.testing.assert_allclose(meter_two, meter_four)


if __name__ == "__main__":
    unittest.main()
