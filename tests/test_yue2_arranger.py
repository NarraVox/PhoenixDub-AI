import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from flask import Flask

from nexus.dj.arranger import build_arrangement, compile_arrangement_abc, compile_yue2_request, qwen_enrich_prompt
from nexus.dj.style_routes import register_style_routes
from tests.test_arranger_mvp import sample_style
from nexus.dj.yu_backend import YuE2Backend


class Yue2ArrangementTests(unittest.TestCase):
    def setUp(self):
        self.arrangement = build_arrangement(sample_style(), seed=27)

    def test_compiler_preserves_plan_and_marks_prompt_steering(self):
        request = compile_yue2_request(self.arrangement)
        prompt = request["style_prompt"]
        self.assertIn("96 BPM", prompt)
        self.assertIn("2/4", prompt)
        self.assertIn("Tempo 96 BPM", prompt)
        self.assertIn("meter 2/4", prompt)
        self.assertEqual(request["lyrics"], "[instrumental]")
        self.assertEqual(request["target_tokens"], round(self.arrangement["duration_estimate_seconds"] * 25))
        self.assertIn("meter", request["score_conditioned"])
        self.assertIn("key", request["score_conditioned"])
        self.assertIn("Vocal melody", request["score_conditioned"])
        self.assertIn("exact drum hits", request["not_directly_supported"])
        self.assertIn("X:1", compile_arrangement_abc(self.arrangement))
        self.assertEqual(request["direct_controls"]["semantic_min_tokens"], int(request["target_tokens"] * .9))

    def test_cli_preview_uses_only_supported_direct_parameters(self):
        request = compile_yue2_request(self.arrangement)
        with tempfile.TemporaryDirectory() as tmp:
            abc_path = Path(tmp) / "new score.abc"
            abc_path.write_text(compile_arrangement_abc(self.arrangement), encoding="utf-8")
            command = YuE2Backend().prepare_command(request["lyrics"], request["style_prompt"], request["target_tokens"], seed=9,
                                                    abc_file=str(abc_path), cot="full")
        self.assertIn("--lyrics", command)
        self.assertEqual(command[command.index("--lyrics") + 1], "[instrumental]")
        self.assertIn("cot=full", command)
        self.assertIn(f"abc_file={abc_path}", command)
        self.assertIn("--request-option", command)
        self.assertIn(f"semantic_max_tokens={max(round(request['target_tokens'] * 6), request['target_tokens'] + 512)}", command)
        self.assertFalse(any(arg in {"--bpm", "--meter", "--key", "--sections"} for arg in command))

    def test_qwen_prompt_adapter_enforces_noncopying_guardrails(self):
        captured = {}
        def fake(system, user):
            captured["system"] = system
            captured["user"] = user
            return "Original instrumental prompt with all sections and instrumentation preserved in detail."
        draft = compile_yue2_request(self.arrangement)["style_prompt"]
        result = qwen_enrich_prompt(self.arrangement, draft, generator=fake)
        self.assertIn("Do not invent exact note sequences", captured["system"])
        self.assertIn("Tempo 96 BPM", captured["user"])
        self.assertTrue(result.startswith("Original instrumental"))
        self.assertIn("96 BPM", result)

    def test_style_project_preview_returns_cli_request_without_audio_generation(self):
        class FakeDJ:
            worker_busy = False
            generating_music = False
            run_music_generation_flow = Mock()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sid = "c" * 24
            project = root / "uploads" / "dj_styles" / sid
            project.mkdir(parents=True)
            (project / "job_status.json").write_text(json.dumps({"status": "completed"}), encoding="utf-8")
            (project / "style.json").write_text(json.dumps(sample_style()), encoding="utf-8")
            app = Flask(__name__)
            dj = FakeDJ()
            register_style_routes(app, dj, root / "uploads")
            client = app.test_client()
            planned = client.post(f"/api/styles/{sid}/arrangement", json={
                "seed": 27,
                "song": {"title": "Nova", "lyrics": "[verse]\\nLetra inédita", "key": "Gm",
                         "sections": [{"type": "MAIN A", "bars": 2, "chords": ["Gm", "Eb"]}]},
            })
            self.assertEqual(planned.status_code, 201, planned.get_json())
            response = client.post(f"/api/styles/{sid}/generate", json={})
            self.assertEqual(response.status_code, 200, response.get_json())
            data = response.get_json()
            self.assertTrue(data["dry_run"])
            self.assertFalse(data["request"]["audio_generation_started"])
            self.assertIn("--task", data["request"]["cli_command_preview"])
            preview_command = data["request"]["cli_command_preview"]
            self.assertIn("cot=full", preview_command)
            self.assertTrue(any(arg.startswith("abc_file=") and arg.endswith("arrangement.abc") for arg in preview_command))
            self.assertIn("Gm", (project / "arrangement.abc").read_text(encoding="utf-8"))
            self.assertTrue((project / "generation_preview.json").is_file())
            dj.run_music_generation_flow.assert_not_called()


if __name__ == "__main__":
    unittest.main()
