"""Instrument Discovery framing and temporal grouping tests."""
import unittest

import numpy as np

from nexus.dj.style_analyzer.adapters.instrument_worker import mel_patches, summarize
from nexus.dj.style_analyzer.instrument_validation import prepare_instrument_validation


class InstrumentDiscoveryTests(unittest.TestCase):
    def test_model_labels_remain_unconfirmed_and_stems_authoritative(self):
        raw = {"status": "detected", "classes": ["accordion", "synthesizer", "bass", "drums"],
               "windows": [{"scores": {"accordion": .05, "synthesizer": .52}}],
               "detected": [{"instrument": label, "confidence": .5} for label in
                            ("synthesizer", "bass", "drums")]}
        result = prepare_instrument_validation(raw)
        self.assertEqual(result["raw_predictions"], raw)
        self.assertEqual(result["confirmed_instruments"], [])
        self.assertEqual(result["ambiguous_instruments"][1]["dedicated_stem_authority"], "bass.wav")
        self.assertEqual(result["ambiguous_instruments"][2]["dedicated_stem_authority"], "drums.wav")
        self.assertIn("accordion", result["ambiguous_instruments"][0]["possible_confusion"])

    def test_mel_patches_match_official_model_shape_and_hop(self):
        silence = np.zeros(16000 * 5, dtype=np.float32)
        patches, starts = mel_patches(silence)
        self.assertEqual(patches.shape[1:], (128, 96))
        self.assertGreaterEqual(len(patches), 3)
        self.assertAlmostEqual(starts[1] - starts[0], 62 * 256 / 16000)
        self.assertTrue(np.isfinite(patches).all())
        self.assertTrue(np.allclose(patches, 0))

    def test_single_window_spike_is_candidate_not_instrument_region(self):
        starts = [0, .992, 1.984, 2.976]
        scores = np.array([[.05, .05], [.7, .05], [.05, .4], [.05, .4]], dtype=np.float32)
        result = summarize(scores, starts, 5.0, ["spike", "sustained"])
        self.assertEqual([item["instrument"] for item in result["detected"]], ["sustained"])
        self.assertEqual(result["detected"][0]["regions"][0]["start_seconds"], 1.984)
        self.assertEqual(result["detected"][0]["regions"][0]["end_seconds"], 5.0)
        self.assertEqual(result["candidates"][0]["instrument"], "spike")


if __name__ == "__main__":
    unittest.main()
