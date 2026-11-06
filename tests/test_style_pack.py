import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from nexus.dj.style_analyzer.style_pack import apply_manual_drum_review, build_style_pack


class StylePackTests(unittest.TestCase):
    def test_auditory_review_keeps_stable_main_loops_separate_from_unlocalized_turn(self):
        pack = {"version": "2.1", "patterns": [{
            "id": "P1", "label": "MAIN A", "length_bars": 4,
            "occurrence_bars": [1, 5, 9], "roles": {"drums": {"stem": "drums"},
                                                "bass": {"stem": "bass"}},
        }]}
        bars = [{"bar": i, "start_seconds": i - 1.0, "end_seconds": float(i)}
                for i in range(1, 13)]
        review = {"version": 1, "pattern_id": "P1", "loop_bars": 2,
                  "source": "user_auditory_validation",
                  "stable_loops": [{"id": "A", "start_bar": 1, "bars": 2},
                                   {"id": "C", "start_bar": 9, "bars": 2}],
                  "transition_candidates": [{"id": "B", "start_bar": 5, "bars": 2}],
                  "bass_relative_pattern": {"status": "confirmed", "events": [
                      {"degree": 1}, {"degree": 3}, {"degree": 5}]}}
        result = apply_manual_drum_review(pack, review, bars)
        loops = result["patterns"][0]["roles"]["drums"]["audited_continuous_loops"]
        self.assertEqual(result["version"], "2.2")
        self.assertEqual([item["id"] for item in loops["stable_main_a"]], ["A", "C"])
        self.assertEqual(loops["transition_candidates"][0]["status"],
                         "contains_turn_location_unresolved")
        self.assertEqual(loops["transition_candidates"][0]["source_end_seconds"], 6.0)
        self.assertEqual(result["patterns"][0]["roles"]["bass"]["relative_pattern"]["events"][1]["degree"], 3)

    def test_extracts_reusable_attacks_role_rhythms_and_detected_form(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sr = 16000
            # Four four-second bars; repeat the same three attacks in bars 1 and 3.
            envelope = np.zeros(sr * 4, dtype=np.float32)
            for step, frequency in ((0, 80), (4, 420), (8, 5200)):
                left = int(step * sr * 4 / 16)
                count = int(.04 * sr)
                t = np.arange(count) / sr
                envelope[left:left + count] += np.sin(2 * np.pi * frequency * t).astype(np.float32) * np.exp(-t * 80)
            envelope = np.tile(envelope, 4)
            stem_paths = {}
            for name, scale in (("drums", 1.0), ("bass", 0.6), ("other", 0.3)):
                path = root / f"{name}.wav"
                sf.write(path, envelope * scale, sr)
                stem_paths[name] = path
            bars = [{"bar": i + 1, "start_seconds": i * 4.0, "end_seconds": (i + 1) * 4.0}
                    for i in range(4)]
            patterns = [{"id": "P01", "label": "MAIN A", "length_bars": 1,
                         "occurrence_bars": [1, 3], "confidence": 0.9}]
            sections = [{"candidate_type": "FILL A", "start_bar": 2, "duration_bars": 1,
                         "pattern_id": None, "confidence": 0.7, "status": "detected"},
                        {"candidate_type": "BREAK", "start_bar": 4, "duration_bars": 1,
                         "pattern_id": None, "confidence": 0.3, "status": "candidate"}]
            pack = build_style_pack(patterns, sections, bars, stem_paths)
            main_a = pack["patterns"][0]
            self.assertEqual(main_a["occurrence_bars"], [1, 3])
            self.assertEqual(main_a["roles"]["drums"]["observations"], 2)
            self.assertEqual(len(main_a["roles"]["drums"]["step_energy"]), 16)
            attacks = main_a["roles"]["drums"]["attack_steps"]
            self.assertEqual([event["step"] for event in attacks], [0, 4, 8])
            self.assertTrue(all(event["probability"] == 1.0 for event in attacks))
            self.assertEqual(pack["form"][0]["type"], "FILL A")
            self.assertIn("roles", pack["form"][0])
            self.assertNotIn("roles", pack["form"][1])
            self.assertIn("bass", main_a["roles"])
            self.assertEqual(pack["version"], "2.1")


if __name__ == "__main__":
    unittest.main()
