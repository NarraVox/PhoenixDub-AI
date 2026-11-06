import json
import re
import tempfile
import unittest
from pathlib import Path

from flask import Flask

from nexus.dj.arranger import build_arrangement, compile_arrangement_abc
from nexus.dj.style_routes import register_style_routes


def sample_style():
    return {
        "style_version": "0.2", "algorithm_version": "0.3.0", "name": "Forró teste",
        "source_analysis": {"bpm": 96.0, "meter": "2/4", "duration": 74.0},
        "rhythm_consensus": {"bpm": 95.5, "meter": "2/4"},
        "drums": {"patterns": [
            {"label": "MAIN A", "length_bars": 8, "occurrences": 4},
            {"label": "MAIN B", "length_bars": 2, "occurrences": 2},
        ]},
        "harmony": {
            "key": {"symbol": "D#m", "root": "D#", "mode": "minor"},
            "key_changes": [{"key": "Em"}],
            "chord_progression": [{"bar": 1, "chord": "D#m"}, {"bar": 2, "chord": "F#"}],
            "melody_notes": [{"midi_pitch": 71, "start_seconds": 0.1}],
        },
        "sections": [], "capabilities": {"rhythm": True},
        "style_pack": {"version": "1.0", "patterns": [
            {"id": "P001", "label": "MAIN A", "length_bars": 8, "confidence": 0.91,
             "roles": {"drums": {"stem": "drums", "steps_per_bar": 16, "length_bars": 8,
                                   "step_energy": [0.2] * 128, "attack_steps": [
                                       {"bar_offset": 1, "step": 0, "probability": .9, "substep": 0, "bands": ["low"]}]},
                       "bass": {"stem": "bass", "steps_per_bar": 16, "length_bars": 8,
                                "step_energy": [0.4] * 128,
                                "attack_probability": [1.0] + [0.0] * 127,
                                "attack_strength": [1.0] + [0.0] * 127, "attack_substep": [0] * 128}}},
            {"id": "P002", "label": "MAIN B", "length_bars": 2, "confidence": 0.82,
             "roles": {"drums": {"stem": "drums", "steps_per_bar": 16, "length_bars": 2,
                                   "step_energy": [0.3] * 32, "attack_steps": [
                                       {"bar_offset": 1, "step": 0, "probability": .9, "substep": 0, "bands": ["mid"]}]}}},
        ], "form": [
            {"type": kind, "start_bar": i * 2 + 1, "bars": bars, "status": "detected", "confidence": .8}
            for i, (kind, bars) in enumerate([
                ("INTRO", 4), ("MAIN A", 8), ("FILL A", 1), ("MAIN A", 8),
                ("MAIN B", 2), ("FILL B", 1), ("BREAK", 4), ("MAIN B", 2),
                ("MAIN A", 8), ("ENDING", 4),
            ])
        ], "grid_steps_per_bar": 16},
    }


class ArrangementPlannerTests(unittest.TestCase):
    def test_creates_new_key_harmony_and_full_section_plan_deterministically(self):
        style = sample_style()
        first = build_arrangement(style, seed=1234)
        second = build_arrangement(style, seed=1234)
        self.assertEqual(first, second)
        self.assertEqual(first["tempo_bpm"], 95.5)
        self.assertEqual(first["meter"], "2/4")
        self.assertNotEqual(first["harmony"]["root"], "D#")
        self.assertNotEqual(first["harmony"]["root"], "E")
        self.assertEqual(first["total_bars"], sum(s["bars"] for s in first["sections"]))
        self.assertEqual(first["sections"][0]["type"], "INTRO")
        self.assertEqual(first["sections"][-1]["type"], "ENDING")
        self.assertIn("MAIN A", [s["type"] for s in first["sections"]])
        self.assertIn("MAIN B", [s["type"] for s in first["sections"]])
        self.assertIn("FILL A", [s["type"] for s in first["sections"]])
        self.assertIn("FILL B", [s["type"] for s in first["sections"]])
        self.assertIn("BREAK", [s["type"] for s in first["sections"]])
        self.assertFalse(first["reference_melody_copied"])
        self.assertFalse(first["provenance"]["source_chord_progression_used"])
        self.assertFalse(first["provenance"]["source_melody_or_note_events_used"])
        self.assertNotIn("melody_notes", json.dumps(first))
        self.assertTrue(all(len(s["harmony_by_bar"]) == s["bars"] for s in first["sections"]))
        self.assertEqual(next(s for s in first["sections"] if s["type"] == "MAIN A")["style_pattern_id"], "P001")
        self.assertEqual(first["drums"]["patterns"][0]["id"], "P001")
        self.assertEqual(len(first["melody_by_bar"]), first["total_bars"])
        self.assertEqual(first["melody_source"], "new_deterministic_chord_tone_motif")

    def test_new_song_reuses_observed_drum_steps_and_revoices_bass(self):
        arrangement = build_arrangement(sample_style(), seed=8, song_plan={
            "key": "G", "sections": [{"type": "MAIN A", "bars": 1, "chords": ["G"]}],
        })
        section = arrangement["sections"][0]
        bar = section["performance_by_bar"][0]
        self.assertEqual(bar["drums"][0]["step"], 0)
        self.assertEqual(bar["drums"][0]["bands"], ["low"])
        self.assertEqual(bar["bass"][0]["pitch_midi"], 43)
        self.assertEqual(bar["bass"][0]["source"], "root_only_unconfirmed_fallback")
        score = compile_arrangement_abc(arrangement)
        self.assertIn("[V: Vocal]", score)
        self.assertIn("[V: Ins]", score)
        self.assertNotIn("[V:Drums]", score)
        self.assertNotIn("[V:Bass]", score)
        self.assertNotIn("[V:Comp]", score)
        self.assertIn("L:1/32", score)
        self.assertIn("G,,", score)

    def test_no_detected_form_requires_user_supplied_sections(self):
        style = sample_style()
        style["style_pack"]["form"] = []
        with self.assertRaisesRegex(ValueError, "não contém seções detectadas"):
            build_arrangement(style, seed=12)

    def test_legacy_energy_only_template_is_not_claimed_as_learned_rhythm(self):
        style = sample_style()
        for pattern in style["style_pack"]["patterns"]:
            for profile in pattern["roles"].values():
                profile.pop("attack_probability", None)
                profile.pop("attack_steps", None)
        arrangement = build_arrangement(style, seed=4, song_plan={
            "sections": [{"type": "MAIN A", "bars": 1, "chords": ["G"]}],
        })
        self.assertEqual(arrangement["sections"][0]["pattern_origin"], "not_observed_in_source")
        self.assertEqual(arrangement["sections"][0]["performance_by_bar"][0]["drums"], [])

    def test_new_song_harmony_lyrics_and_melody_override_automatic_composition(self):
        song = {"title": "Canção nova", "key": "G", "lyrics": "[verse]\nTexto original",
                "sections": [{"type": "MAIN A", "bars": 2, "chords": ["G", "D"]}],
                "melody_by_bar": [[{"pitch": 67, "duration_eighths": 4}],
                                   [{"pitch": 69, "duration_eighths": 4}]]}
        result = build_arrangement(sample_style(), seed=1, song_plan=song)
        self.assertEqual(result["harmony"]["key"], "G")
        self.assertEqual([x["chord"] for x in result["sections"][0]["harmony_by_bar"]], ["G", "D"])
        self.assertEqual(result["lyrics"], song["lyrics"])
        self.assertEqual(result["melody_by_bar"], song["melody_by_bar"])

    def test_duration_and_section_bars_follow_tempo_meter_and_phrase_evidence(self):
        arrangement = build_arrangement(sample_style(), seed=77)
        expected = arrangement["total_bars"] * 2 * 60 / 95.5
        self.assertAlmostEqual(arrangement["duration_estimate_seconds"], expected, places=2)
        main_a = next(s for s in arrangement["sections"] if s["type"] == "MAIN A")
        self.assertEqual(main_a["bars"], 8)
        self.assertEqual(arrangement["duration_reference_seconds"], 74.0)

    def test_invalid_style_and_seed_are_rejected(self):
        with self.assertRaises(ValueError):
            build_arrangement({"style_version": "9"})
        with self.assertRaises(ValueError):
            build_arrangement(sample_style(), seed=-1)

    def test_abc_carries_new_song_tempo_meter_chords_and_melody(self):
        song = {"key": "G", "sections": [{"type": "MAIN A", "bars": 1, "chords": ["G"]}],
                "melody_by_bar": [[{"pitch": 67, "duration_eighths": 2},
                                   {"pitch": 71, "duration_eighths": 2}]]}
        score = compile_arrangement_abc(build_arrangement(sample_style(), seed=7, song_plan=song))
        self.assertIn("M:2/4", score)
        self.assertIn("Q:1/4=96", score)
        self.assertNotIn("95.5", score)
        self.assertIn('"G"', score)
        self.assertIn('"G" G8 B8', score)
        self.assertNotIn("[G", score)
        lengths = [int(x) for x in re.findall(r"(?:[A-Ga-g][,']*|z)(\d+)", score)]
        self.assertTrue(lengths)
        self.assertTrue(set(lengths).issubset({1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48}))

    def test_native_abc_uses_exact_2_4_bar_lengths_and_voice_blocks(self):
        song = {"key": "G", "sections": [{"type": "MAIN A", "bars": 2, "chords": ["G", "D"]}],
                "melody_by_bar": [[{"pitch": 67, "duration_eighths": 2}],
                                   [{"pitch": 69, "duration_eighths": 4}]]}
        score = compile_arrangement_abc(build_arrangement(sample_style(), seed=7, song_plan=song))
        blocks = re.findall(r"\[V: (Vocal|Ins)\] ([^\n]+)", score)
        self.assertEqual([voice for voice, _ in blocks], ["Vocal", "Ins"])
        for _, content in blocks:
            bars = content.split("|")[:-1]
            self.assertEqual(len(bars), 2)
            for bar in bars:
                durations = [int(value) for value in re.findall(r"(?:[A-Ga-g][,']*|z)(\d+)", bar)]
                self.assertEqual(sum(durations), 16)
        self.assertEqual(score.count("V: Vocal"), 2)  # declaration plus score block


class ArrangementRouteTests(unittest.TestCase):
    def test_post_writes_arrangement_and_get_downloads_it(self):
        class FakeDJ:
            worker_busy = False
            generating_music = False

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_id = "a" * 24
            project = root / "uploads" / "dj_styles" / project_id
            project.mkdir(parents=True)
            (project / "style.json").write_text(json.dumps(sample_style()), encoding="utf-8")
            (project / "job_status.json").write_text(json.dumps({"status": "completed"}), encoding="utf-8")
            app = Flask(__name__)
            register_style_routes(app, FakeDJ(), root / "uploads")
            client = app.test_client()

            response = client.post(f"/api/styles/{project_id}/arrangement", json={"seed": 19})
            self.assertEqual(response.status_code, 201)
            self.assertTrue((project / "arrangement.json").is_file())
            self.assertTrue((project / "arrangement.abc").is_file())
            saved = json.loads((project / "arrangement.json").read_text(encoding="utf-8"))
            self.assertEqual(saved, response.get_json()["arrangement"])

            download = client.get(f"/api/styles/{project_id}/arrangement.json")
            self.assertEqual(download.status_code, 200)
            self.assertIn("arrangement.json", download.headers["Content-Disposition"])
            download.close()
            score = client.get(f"/api/styles/{project_id}/arrangement.abc")
            self.assertEqual(score.status_code, 200)
            score.close()

    def test_route_rejects_incomplete_analysis(self):
        class FakeDJ:
            worker_busy = False
            generating_music = False

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_id = "b" * 24
            project = root / "uploads" / "dj_styles" / project_id
            project.mkdir(parents=True)
            (project / "job_status.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
            app = Flask(__name__)
            register_style_routes(app, FakeDJ(), root / "uploads")
            response = app.test_client().post(f"/api/styles/{project_id}/arrangement", json={})
            self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
