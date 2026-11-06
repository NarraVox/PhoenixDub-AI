import json
import tempfile
import unittest
from pathlib import Path

from nexus.dj.style_analyzer.adapters.sheetsage import _event_payload, _parse_score, _unwrap_artifact


class SheetSageAdapterTests(unittest.TestCase):
    def test_parses_key_chords_sections_and_timed_melody(self):
        abc = """X:1
M:4/4
Q:1/4=128
K:Am
% intro
K:Am
V: Vocal
"Am"C2D2|"F"E2G2|
V: Ins
A2B2|c2d2|
K:Gm
K:Gm
"""
        events = {"events": [{"time": 0.5, "notes": [{"pitch": 60, "track": 0, "end_time": 0.75},
                                                         {"pitch": 48, "track": 1, "end_time": 0.9}]}]}
        summary = _parse_score(abc, events)
        self.assertEqual(summary["key"], {"symbol": "Am", "root": "A", "mode": "minor"})
        self.assertEqual(summary["key_changes"], [{"after_bar": 0, "key": "Am"}, {"after_bar": 2, "key": "Gm"}])
        self.assertEqual(summary["model_tempo_bpm"], 128.0)
        self.assertEqual(summary["meter"], "4/4")
        self.assertEqual(summary["chord_progression"], [{"bar": 1, "chord": "Am"}, {"bar": 2, "chord": "F"}])
        self.assertEqual(summary["structure_sections"], [{"start_bar": 1, "label": "intro"}])
        self.assertEqual(summary["melody_profiles"]["vocal"]["note_count"], 1)
        self.assertEqual(summary["melody_profiles"]["instrumental_melody"]["pitch_min"], 48)

    def test_unwraps_audio_cpp_hex_json_artifact(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "events.json"
            payload = json.dumps({"events": [{"time": 0.0, "notes": []}]})
            wrapper = {"id": "events", "payload_hex": payload.encode().hex()}
            path.write_text(json.dumps(wrapper), encoding="utf-8")
            self.assertEqual(json.loads(_unwrap_artifact(path)), {"events": [{"time": 0.0, "notes": []}]})
            self.assertEqual(_event_payload(folder), {"events": [{"time": 0.0, "notes": []}]})


if __name__ == "__main__":
    unittest.main()
