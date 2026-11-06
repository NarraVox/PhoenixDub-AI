import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np
import soundfile as sf

from nexus.dj.arranger import build_arrangement
from nexus.dj.arranger.renderer import render_arrangement
from nexus.dj.style_analyzer.style_pack import apply_manual_drum_review
from tests.test_arranger_mvp import sample_style


class ArrangementRendererTests(unittest.TestCase):
    def test_renders_learned_main_a_b_drums_bass_and_new_chord_comp(self):
        style = sample_style()
        for pattern in style["style_pack"]["patterns"]:
            pattern["roles"]["drums"]["attack_steps"].append({
                "bar_offset": 1, "step": 8, "probability": 0.5,
                "substep": 0, "bands": ["mid"],
            })
            count = pattern["length_bars"] * 16
            attacks = [0.0] * count
            for step in (3, 11):
                if step < count:
                    attacks[step] = 0.9
            pattern["roles"]["accompaniment"] = {
                "stem": "other", "length_bars": pattern["length_bars"],
                "attack_probability": attacks, "attack_strength": attacks,
                "attack_substep": [0] * count,
            }
        arrangement = build_arrangement(style, seed=31, song_plan={
            "key": "Gm",
            "sections": [
                {"type": "MAIN A", "bars": 2, "chords": ["Gm", "Eb"]},
                {"type": "MAIN B", "bars": 2, "chords": ["Bb", "F"]},
            ],
        })
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "renderer.wav"
            result = render_arrangement(arrangement, output, max_bars_per_section=2,
                                        sample_rate=8000, tail_seconds=0.1)
            self.assertEqual(result["sections"], ["MAIN A", "MAIN B"])
            self.assertEqual(result["bars"], 4)
            self.assertGreater(result["drum_attacks"], 0)
            self.assertGreater(result["bass_notes"], 0)
            self.assertGreater(result["accompaniment_stabs"], 0)
            self.assertEqual(len(result["bar_event_counts"]), 4)
            self.assertEqual(result["minimum_drum_probability"], 0.6667)
            self.assertEqual(result["bar_event_counts"][0]["drums"], 1)
            with wave.open(str(output), "rb") as wav:
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getframerate(), 8000)
                self.assertAlmostEqual(wav.getnframes() / 8000, result["duration_seconds"], places=3)
                samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
            self.assertGreater(np.max(np.abs(samples)), 0)
            self.assertLessEqual(np.max(np.abs(samples)), 32767)
            second = Path(tmp) / "renderer_repeat.wav"
            render_arrangement(arrangement, second, max_bars_per_section=2,
                               sample_rate=8000, tail_seconds=0.1)
            self.assertEqual(output.read_bytes(), second.read_bytes())

    def test_main_a_uses_relative_root_third_fifth_and_minor_flat_third(self):
        style = sample_style()
        for pattern in style["style_pack"]["patterns"]:
            if pattern.get("label") == "MAIN A":
                pattern["roles"]["bass"]["relative_pattern"] = {
                    "status": "confirmed", "events": [
                        {"step": 2, "substep": 2, "degree": 1, "octave_offset": 0, "duration_seconds": .30},
                        {"step": 9, "substep": 2, "degree": 3, "octave_offset": -1, "duration_seconds": .09},
                        {"step": 13, "substep": 1, "degree": 5, "octave_offset": -1, "duration_seconds": .12},
                    ]}
            elif pattern.get("label") == "MAIN B":
                pattern["roles"].setdefault("bass", {})["relative_pattern"] = {"status": "unconfirmed", "events": []}
        arrangement = build_arrangement(style, seed=101, song_plan={
            "key": "Gm", "sections": [{"type": "MAIN A", "bars": 2, "chords": ["G", "Gm"]}],
        })
        main_a = arrangement["sections"][0]["performance_by_bar"]
        self.assertEqual([e["degree"] for e in main_a[0]["bass"]], [1, 3, 5])
        self.assertEqual([e["pitch_midi"] for e in main_a[0]["bass"]], [43, 35, 38])
        self.assertEqual([e["pitch_midi"] for e in main_a[1]["bass"]], [43, 34, 38])
        self.assertEqual([e["duration_seconds"] for e in main_a[0]["bass"]], [.30, .09, .12])
        self.assertEqual(main_a[0]["bass"][1]["source"], "learned_relative_chord_degree")

    def test_does_not_invent_unobserved_sections(self):
        arrangement = build_arrangement(sample_style(), seed=32, song_plan={
            "key": "Gm", "sections": [{"type": "MAIN A", "bars": 1, "chords": ["Gm"]}],
        })
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "MAIN A/B aprendidos"):
                render_arrangement(arrangement, Path(tmp) / "no-fill.wav", section_types=("FILL A",))

    def test_can_use_short_hits_from_reference_drum_stem_at_learned_steps(self):
        style = sample_style()
        style["style_pack"]["patterns"][0]["occurrence_bars"] = [1]
        arrangement = build_arrangement(style, seed=33, song_plan={
            "key": "Gm", "sections": [{"type": "MAIN A", "bars": 1, "chords": ["Gm"]}],
        })
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = np.zeros(8000, dtype=np.float32)
            t = np.arange(1200, dtype=np.float32) / 8000
            source[20:1220] = np.sin(2 * np.pi * 90 * t) * np.exp(-t * 16)
            stem = tmp / "drums.wav"
            sf.write(stem, source, 8000)
            rendered = tmp / "sampled.wav"
            result = render_arrangement(
                arrangement, rendered, section_types=("MAIN A",), max_bars_per_section=1,
                sample_rate=8000, reference_drum_stem=stem, reference_grid_start_seconds=0,
            )
            self.assertEqual(result["drum_source"], "reference stem one-shots at corresponding learned grid positions")
            self.assertGreater(result["drum_attacks"], 0)
            self.assertEqual(result["reference_samples_used"], result["drum_attacks"])
            self.assertEqual(result["synthetic_drum_attacks"], 0)
            self.assertGreater(rendered.stat().st_size, 1000)

    def test_repeats_continuous_drum_loop_with_bass_and_no_accompaniment(self):
        style = sample_style()
        arrangement = build_arrangement(style, seed=34, song_plan={
            "key": "Gm", "sections": [{"type": "MAIN A", "bars": 8, "chords": ["Gm"]}],
        })
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sr = 8000
            bar_samples = round(120 / arrangement["tempo_bpm"] * sr)
            loop = np.zeros((bar_samples * 4, 2), dtype=np.float32)
            tone = np.sin(2 * np.pi * 160 * np.arange(240) / sr).astype(np.float32) * 0.4
            for bar in range(4):
                loop[bar * bar_samples:bar * bar_samples + len(tone)] = tone[:, None]
            source = root / "drum_loop.wav"
            sf.write(source, loop, sr)
            output = root / "main_a.wav"
            result = render_arrangement(
                arrangement, output, section_types=("MAIN A",), max_bars_per_section=8,
                sample_rate=sr, tail_seconds=0, reference_drum_loop=source,
                drum_loop_bars=4, include_accompaniment=False,
            )
            rendered, output_rate = sf.read(output, always_2d=True)
            self.assertEqual(output_rate, sr)
            self.assertEqual(rendered.shape[1], 2)
            self.assertEqual(result["drum_loop_repetitions"], 2)
            self.assertEqual(result["accompaniment_stabs"], 0)
            self.assertEqual(result["drum_attacks"], 0)
            self.assertGreater(np.max(np.abs(rendered[:120])), 0.05)
            self.assertGreater(np.max(np.abs(rendered[4 * bar_samples:4 * bar_samples + 120])), 0.05)

    def test_reviewed_main_a_alternates_stable_a_c_and_never_uses_b(self):
        style = sample_style()
        pattern = style["style_pack"]["patterns"][0]
        pattern["occurrence_bars"] = [1, 9]
        sr = 8000
        bpm = style["rhythm_consensus"]["bpm"]
        seconds_per_bar = 120 / bpm
        bar_edges = [round(i * seconds_per_bar * sr) for i in range(17)]
        bars = [{"bar": i + 1, "start_seconds": bar_edges[i] / sr,
                 "end_seconds": bar_edges[i + 1] / sr} for i in range(16)]
        review = {"version": 1, "pattern_id": "P001", "loop_bars": 4,
                  "stable_loops": [{"id": "A", "start_bar": 1, "bars": 4},
                                   {"id": "C", "start_bar": 9, "bars": 4}],
                  "transition_candidates": [{"id": "B", "start_bar": 5, "bars": 4}]}
        apply_manual_drum_review(style["style_pack"], review, bars)
        source_audio = np.zeros((bar_edges[-1], 2), dtype=np.float32)
        for first, last, hz in ((1, 4, 100), (5, 8, 500), (9, 12, 200)):
            left, right = bar_edges[first - 1], bar_edges[last]
            tone = 0.35 * np.sin(2 * np.pi * hz * np.arange(right - left) / sr)
            source_audio[left:right] = tone[:, None]
        arrangement = build_arrangement(style, seed=35, song_plan={
            "key": "Gm", "sections": [{"type": "MAIN A", "bars": 16, "chords": ["Gm"]}],
        })
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stem = root / "drums.wav"
            sf.write(stem, source_audio, sr)
            output = root / "stable_main_a.wav"
            result = render_arrangement(
                arrangement, output, section_types=("MAIN A",), max_bars_per_section=16,
                sample_rate=sr, tail_seconds=0, reference_drum_loop_stem=stem,
                include_bass=False, include_accompaniment=False,
            )
            self.assertEqual([item["id"] for item in result["reviewed_drum_sequence"]],
                             ["A", "C", "A", "C"])
            self.assertEqual(result["drum_attacks"], 0)
            audio, _ = sf.read(output, always_2d=True)
            target_block = round(4 * seconds_per_bar * sr)
            for index, frequency in enumerate((100, 200, 100, 200)):
                middle = index * target_block + target_block // 2
                excerpt = audio[middle:middle + sr // 2, 0]
                spectrum = np.abs(np.fft.rfft(excerpt))
                actual = np.fft.rfftfreq(len(excerpt), 1 / sr)[int(np.argmax(spectrum))]
                self.assertAlmostEqual(actual, frequency, delta=3)

    def test_single_entry_and_bass_share_the_drum_bar_grid(self):
        style = sample_style()
        pattern = style["style_pack"]["patterns"][0]
        pattern["occurrence_bars"] = [1, 9]
        pattern["roles"]["bass"]["relative_pattern"] = {
            "status": "confirmed", "events": [
                {"step": step, "substep": 0, "degree": degree,
                 "octave_offset": 0, "duration_grid_steps": 2}
                for step, degree in ((0, 1), (8, 3), (12, 5))
            ],
        }
        sr = 8000
        seconds_per_bar = 120 / style["rhythm_consensus"]["bpm"]
        edges = [round(i * seconds_per_bar * sr) for i in range(17)]
        bars = [{"bar": i + 1, "start_seconds": edges[i] / sr,
                 "end_seconds": edges[i + 1] / sr} for i in range(16)]
        review = {"version": 1, "pattern_id": "P001", "loop_bars": 4,
                  "stable_loops": [{"id": "A", "start_bar": 1, "bars": 4},
                                   {"id": "C", "start_bar": 9, "bars": 4}],
                  "transition_candidates": [{"id": "B", "start_bar": 5, "bars": 4}],
                  "initial_turn_excerpt": {"id": "B-entry", "start_bar": 5, "bars": 2}}
        apply_manual_drum_review(style["style_pack"], review, bars)
        arrangement = build_arrangement(style, seed=36, song_plan={
            "key": "Gm", "sections": [
                {"type": "INTRO", "bars": 2, "chords": ["Gm", "Eb"]},
                {"type": "MAIN A", "bars": 8, "chords": ["Gm", "Eb", "Bb", "F"] * 2},
            ],
        })
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stem = root / "drums.wav"
            sf.write(stem, np.ones((edges[-1], 2), dtype=np.float32) * 0.05, sr)
            result = render_arrangement(
                arrangement, root / "entry.wav", section_types=("INTRO", "MAIN A"),
                max_bars_per_section=8, sample_rate=sr, tail_seconds=0,
                reference_drum_loop_stem=stem, include_accompaniment=False,
            )
        self.assertEqual([row["id"] for row in result["reviewed_drum_sequence"]],
                         ["B-entry", "A", "C"])
        self.assertEqual(result["reviewed_drum_sequence"][0]["target_bars"], [1, 2])
        self.assertEqual(result["reviewed_drum_sequence"][1]["target_bars"], [3, 6])
        self.assertEqual(result["synthetic_drum_attacks"], 0)
        self.assertEqual(result["bass_notes"], 30)
        grid = result["bass_attack_grid"]
        edges = result["shared_timeline"]["bar_edges_samples"]
        for bar in range(10):
            self.assertEqual([hit["step"] for hit in grid[bar * 3:bar * 3 + 3]],
                             [0, 8, 12])
            self.assertEqual(grid[bar * 3]["sample"], edges[bar])
            for hit in grid[bar * 3:bar * 3 + 3]:
                expected = round(((bar * 16) + hit["step"]) *
                                 seconds_per_bar / 16 * sr)
                self.assertEqual(hit["sample"], expected)


if __name__ == "__main__":
    unittest.main()
