import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

from flask import Flask
from nexus.correction_service import CorrectionService, CorrectionError, read_json, write_json


class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nexus_correction_test_")
        self.base = Path(self.temp.name)
        self.calls = []
        self.service = CorrectionService(self.base, self.synth)
        self.game = self.make_project("jogo", "games")
        self.video = self.make_project("video", "video")
        self.keys = {p["kind"]: p["id"] for p in self.service.discover()}

    def tearDown(self):
        self.temp.cleanup()

    def tone(self, output, duration=1, frequency=600):
        output.parent.mkdir(parents=True, exist_ok=True)
        self.service.run_ffmpeg(["-f", "lavfi", "-i", f"sine=frequency={frequency}:duration={duration}", "-ar", "24000", output])

    def synth(self, text, ref, output, duration, emotion):
        self.calls.append(text)
        self.tone(output, min(1, duration), 900)

    def make_project(self, name, kind):
        folder = self.base / "uploads" / name
        folder.mkdir(parents=True)
        segments = [{"id": f"seg_{i}", "speaker": "voz1", "original_text": 'A "quoted" <line> ' + str(i),
                     "translated_text": "Fala antiga", "text_pt": "Fala antiga", "file_name": f"seg_{i}.wav",
                     "start": i * 2, "end": i * 2 + 2} for i in range(2)]
        write_json(folder / "project_data.json", {"segments": segments} if kind == "video" else segments)
        for i in range(2):
            self.tone(folder / "_2_PARA_AS_PASTAS_DE_VOZ" / "voz1" / f"seg_{i}.wav")
            self.tone(folder / ("_dubbed_segments" if kind == "video" else "_saida_final") / f"seg_{i}.wav", 2)
        if kind == "video":
            self.tone(folder / "vocals.wav", 6)
            self.tone(folder / "instrumental.wav", 6, 200)
            self.service.run_ffmpeg(["-f", "lavfi", "-i", "color=c=blue:s=160x90:r=10:d=6", "-c:v", "libx264", folder / "original.mp4"])
            write_json(folder / "job_status.json", {"video_path": str(folder / "original.mp4")})
        return folder

    def save(self, kind, sid="seg_0", text="Texto corrigido", revision=1):
        return self.service.save_draft(self.keys[kind], sid, text, revision)

    def test_autosave_does_not_start_or_enqueue_and_survives_restart(self):
        self.save("video")
        self.save("video", "seg_1", "Outra fala", 2)
        self.assertEqual(len(list((self.video / "_correcoes/segmentos").glob("*.json"))), 2)
        restarted = CorrectionService(self.base, self.synth)
        queue = restarted.queue(self.keys["video"])
        self.assertEqual(queue["drafts"], 2)
        self.assertEqual(queue["pending"], 0)
        self.assertEqual(self.calls, [])
        self.assertEqual(restarted.search(self.keys["video"])["items"][0]["translated"], "Texto corrigido")

    def test_out_of_order_autosave_and_saved_snapshot(self):
        self.save("video", text="Texto novo", revision=20)
        self.save("video", text="Texto antigo", revision=10)
        self.service.enqueue(self.keys["video"], "seg_0")
        self.save("video", text="Rascunho ainda não enviado", revision=21)
        draft = self.service.queue(self.keys["video"])["items"][0]
        self.assertEqual(draft["text"], "Rascunho ainda não enviado")
        self.assertEqual(draft["queued"]["text"], "Texto novo")
        self.assertEqual(self.calls, [])

    def test_twenty_drafts_survive_restart_and_failed_atomic_write(self):
        metadata = self.video / "project_data.json"
        data = read_json(metadata)
        sample = data["segments"][0]
        data["segments"] = [{**sample, "id": f"seg_{i}"} for i in range(20)]
        write_json(metadata, data)
        for i in range(20):
            self.save("video", f"seg_{i}", f"Edição protegida {i}", i + 1)
        draft_path = self.service.draft_path(self.video, "seg_0")
        before = draft_path.read_bytes()
        with patch('nexus.correction_service.os.replace', side_effect=OSError('Interrupção simulada')):
            with self.assertRaises(OSError):
                self.save("video", "seg_0", "Escrita interrompida", 100)
        self.assertEqual(draft_path.read_bytes(), before)
        restarted = CorrectionService(self.base, self.synth)
        self.assertEqual(restarted.queue(self.keys["video"])["drafts"], 20)
        self.assertEqual(len(list(draft_path.parent.glob('*.json'))), 20)
        self.assertEqual(self.calls, [])

    def test_mp3_game_keeps_format_and_sample_rate(self):
        key = self.keys["games"]
        source = self.game / "_saida_final/seg_0.mp3"
        self.tone(source, 2)
        write_json(self.game / "job_status.json", {"file_format_map": {"seg_0": ".mp3"}})
        self.save("games")
        self.service.enqueue(key, "seg_0")
        result = self.service.process_queue(key, "seg_0")
        output = Path(result["folder"]) / source.name
        self.assertTrue(output.is_file())
        from nexus.correction_service import read_audio
        self.assertEqual(read_audio(output).frame_rate, read_audio(source).frame_rate)
        self.assertAlmostEqual(len(read_audio(output)), len(read_audio(source)), delta=100)

    def test_game_export_preserves_original_and_metadata(self):
        source = self.game / "_saida_final/seg_0.wav"
        metadata = self.game / "project_data.json"
        before = (source.read_bytes(), metadata.read_bytes())
        self.save("games")
        self.service.enqueue(self.keys["games"], "seg_0")
        result = self.service.process_queue(self.keys["games"], "seg_0")
        self.assertTrue((Path(result["folder"]) / source.name).exists())
        self.assertEqual(before, (source.read_bytes(), metadata.read_bytes()))
        self.assertEqual(result["queue"]["pending"], 0)
        self.assertEqual(self.calls, ["Texto corrigido"])

    def test_video_generates_all_then_exports_once_and_retries_no_tts(self):
        key = self.keys["video"]
        for i in range(2):
            self.save("video", f"seg_{i}", f"Correção {i}", i + 1)
            self.service.enqueue(key, f"seg_{i}")
        source_hash = hashlib.sha256((self.video / "original.mp4").read_bytes()).hexdigest()
        self.assertEqual(self.calls, [])
        with patch.object(self.service, "export_video", wraps=self.service.export_video) as render:
            result = self.service.process_queue(key)
            self.assertEqual(render.call_count, 1)
        final = Path(result["folder"]) / "video_corrigido.mp4"
        self.assertTrue(final.exists())
        self.assertEqual(source_hash, hashlib.sha256((self.video / "original.mp4").read_bytes()).hexdigest())
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(final)], capture_output=True, text=True, check=True)
        self.assertAlmostEqual(float(json.loads(probe.stdout)["format"]["duration"]), 6, delta=.2)
        self.assertEqual(self.calls, ["Correção 0", "Correção 1"])
        restarted = CorrectionService(self.base, self.synth)
        restarted.process_queue(key)
        self.assertEqual(len(self.calls), 2)

    def test_failure_then_restart_only_retries_unfinished_segment(self):
        key = self.keys["games"]
        for i in range(2):
            self.save("games", f"seg_{i}", f"Correção {i}", i + 1)
            self.service.enqueue(key, f"seg_{i}")
        def fail_second(text, *args):
            if text.endswith("1"):
                raise RuntimeError("GPU indisponível")
            self.synth(text, *args)
        self.service.synthesizer = fail_second
        result = self.service.process_queue(key)
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(result["queue"]["pending"], 1)
        restarted = CorrectionService(self.base, self.synth)
        resumed = restarted.process_queue(key)
        self.assertEqual(resumed["queue"]["pending"], 0)
        self.assertEqual(self.calls, ["Correção 0", "Correção 1"])

    def test_stale_preview_and_path_traversal_rejected(self):
        key = self.keys["games"]
        info = self.service.preview(key, "seg_0", "Nova fala")
        self.tone(self.game / "_saida_final/seg_0.wav", 1)
        with self.assertRaises(CorrectionError):
            self.service.apply(key, info["token"])
        with self.assertRaises(CorrectionError):
            self.service.preview_file(key, "../../project_data.json")
        with self.assertRaises(CorrectionError):
            self.service.segment(key, "../seg_0")

    def test_api_games_save_starts_queue_video_save_only_stages(self):
        from nexus import correction_routes as routes
        app = Flask("correction_tests")
        app.register_blueprint(routes.correction_blueprint)
        client = app.test_client()
        jobs = []
        fake_executor = types.SimpleNamespace(submit=lambda callback: jobs.append(callback))
        fake_hub = types.SimpleNamespace(is_engine_busy=lambda name: False)
        with patch.object(routes, "service", self.service), patch.object(routes, "executor", fake_executor), patch.object(routes, "tasks", {}), patch.dict("sys.modules", {"nexus.nexus_routes": fake_hub}):
            for kind in ("video", "games"):
                response = client.post('/api/corrections/draft', json={"project_id": self.keys[kind], "segment_id": "seg_0", "text": "Teste", "revision": 5})
                self.assertEqual(response.status_code, 200)
            self.assertEqual(jobs, [])
            video = client.post('/api/corrections/enqueue', json={"project_id": self.keys["video"], "segment_id": "seg_0"})
            self.assertEqual(video.status_code, 200)
            self.assertEqual(jobs, [])
            game = client.post('/api/corrections/enqueue', json={"project_id": self.keys["games"], "segment_id": "seg_0"})
            self.assertEqual(game.status_code, 202)
            self.save("games", "seg_1", "Outra fala", 6)
            second = client.post('/api/corrections/enqueue', json={"project_id": self.keys["games"], "segment_id": "seg_1"})
            self.assertEqual(second.status_code, 202)
            self.assertEqual(len(jobs), 2)
            self.assertEqual(self.calls, [])
            for callback in jobs:
                callback()
            self.assertEqual(self.calls, ["Teste", "Outra fala"])
            self.assertTrue(all(task["status"] == "done" for task in routes.tasks.values()))


if __name__ == "__main__":
    unittest.main()
