# -*- coding: utf-8 -*-
# Testes do Conversor de Mídias (Áudio 160k padrão & Vídeo H.265 na resolução original)
# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo

import os
import sys
import time
import json
import shutil
import tempfile
import unittest
import subprocess
from unittest.mock import patch
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from nexus.editor.media_converter import MediaConverter, ConversionBatchQueue, is_nvenc_hevc_available
from nexus.editor.narravox_editor import app, batch_queue

class TestMediaConverter(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="vortex_test_")
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_audio_command_default_160k(self):
        """Valida se o bitrate padrão de áudio é rigorosamente 160k."""
        cmd = MediaConverter.build_audio_command("input.wav", "output.mp3")
        self.assertIn("-b:a", cmd)
        idx = cmd.index("-b:a")
        self.assertEqual(cmd[idx + 1], "160k")
        self.assertIn("libmp3lame", cmd)

    def test_audio_command_custom_bitrate_and_formats(self):
        """Valida bitrates customizados e formatos diferentes."""
        cmd_320 = MediaConverter.build_audio_command("input.wav", "output.mp3", bitrate="320k")
        idx_320 = cmd_320.index("-b:a")
        self.assertEqual(cmd_320[idx_320 + 1], "320k")

        cmd_aac = MediaConverter.build_audio_command("input.wav", "output.m4a", target_format="aac", bitrate="128k")
        self.assertIn("aac", cmd_aac)
        self.assertEqual(cmd_aac[cmd_aac.index("-b:a") + 1], "128k")

        cmd_wav = MediaConverter.build_audio_command("input.mp3", "output.wav", target_format="wav")
        self.assertIn("pcm_s16le", cmd_wav)

    def test_video_h265_command_specs(self):
        for gpu in (False, True):
            with self.subTest(gpu=gpu), patch(
                "nexus.editor.media_converter.is_nvenc_hevc_available", return_value=gpu
            ):
                cmd = MediaConverter.build_video_h265_command("input.mp4", "output.mp4")
                self.assertNotIn("-maxrate:v", cmd)
                self.assertNotIn("scale=", " ".join(cmd))
                self.assertEqual(cmd[cmd.index("-b:a") + 1], "160k")
                flag = "-cq" if gpu else "-crf"
                self.assertEqual(cmd[cmd.index(flag) + 1], "23")
                if gpu:
                    self.assertEqual(cmd[cmd.index("-b:v") + 1], "0")
                else:
                    self.assertNotIn("-b:v", cmd)
        cmd = MediaConverter.build_video_h265_command(
            "in.mp4", "out.mp4", video_bitrate="2500k", force_cpu=True)
        self.assertEqual(cmd[cmd.index("-b:v") + 1], "2500k")

    def test_real_audio_conversion_160k(self):
        """Gera áudio de teste sintético de 1s e converte para MP3 160k."""
        raw_wav = self.temp_path / "test_tone.wav"
        out_mp3 = self.temp_path / "test_out_160k.mp3"

        # Gera tom senoidal de 1s via lavfi
        cmd_gen = ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=1", str(raw_wav)]
        res_gen = subprocess.run(cmd_gen, capture_output=True, text=True)
        self.assertEqual(res_gen.returncode, 0, f"Falha ao gerar WAV de teste: {res_gen.stderr}")

        # Converte para MP3 160k
        cmd_conv = MediaConverter.build_audio_command(raw_wav, out_mp3, target_format="mp3", bitrate="160k")
        res_conv = subprocess.run(cmd_conv, capture_output=True, text=True)
        self.assertEqual(res_conv.returncode, 0, f"Falha ao converter áudio: {res_conv.stderr}")
        self.assertTrue(out_mp3.exists(), "Arquivo MP3 deve existir.")

        # Inspeciona bitrate com ffprobe
        cmd_probe = [
            "ffprobe", "-v", "error", "-show_entries", "format=bit_rate",
            "-of", "default=noprint_wrappers=1:nokey=1", str(out_mp3)
        ]
        out_br = subprocess.check_output(cmd_probe).decode().strip()
        br_int = int(out_br)
        # MP3 160k fica em torno de 160.000 bps (tolerância de ±10% do cabeçalho)
        self.assertTrue(140000 <= br_int <= 175000, f"Bitrate esperado ~160k, obtido: {br_int}")

    def test_real_video_h265_conversion(self):
        """Verifica resolução, proporção e FPS em conversões reais CPU/GPU."""
        gpu_available = is_nvenc_hevc_available()
        for width, height in [(640, 480), (1280, 720), (1920, 1080), (480, 640)]:
            for force_cpu in ([True, False] if gpu_available else [True]):
                with self.subTest(width=width, height=height, cpu=force_cpu):
                    src = self.temp_path / "source.mp4"
                    dst = self.temp_path / "output.mp4"
                    subprocess.run([
                        "ffmpeg", "-y", "-f", "lavfi", "-i",
                        f"testsrc2=size={width}x{height}:rate=25",
                        "-t", "0.2", "-c:v", "libx264", str(src)
                    ], capture_output=True, check=True, timeout=30)
                    cmd = MediaConverter.build_video_h265_command(src, dst, force_cpu=force_cpu)
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    data = json.loads(subprocess.check_output([
                        "ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=codec_name,width,height,r_frame_rate,sample_aspect_ratio",
                        "-of", "json", str(dst)
                    ]))["streams"][0]
                    self.assertEqual(data["codec_name"], "hevc")
                    self.assertEqual((data["width"], data["height"]), (width, height))
                    self.assertEqual(data["r_frame_rate"], "25/1")
                    self.assertEqual(data["sample_aspect_ratio"], "1:1")

    def test_batch_queue_execution(self):
        """Valida enfileiramento e conclusão de lote na ConversionBatchQueue."""
        q_dir = self.temp_path / "batch_out"
        queue = ConversionBatchQueue(output_dir=q_dir)

        # Gera 2 áudios sintéticos
        f1 = self.temp_path / "song1.wav"
        f2 = self.temp_path / "song2.wav"
        for f in (f1, f2):
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=800:duration=1", str(f)], capture_output=True)

        added = queue.add_items([
            {"input_path": str(f1), "mode": "audio", "format": "mp3", "audio_bitrate": "160k"},
            {"input_path": str(f2), "mode": "audio", "format": "mp3", "audio_bitrate": "160k"}
        ])
        self.assertEqual(len(added), 2)

        started = queue.start_batch()
        self.assertTrue(started)

        # Aguarda término
        for _ in range(30):
            time.sleep(0.5)
            status = queue.get_status()
            if not status["is_running"] and status["queue_count"] == 0:
                break

        final_status = queue.get_status()
        self.assertFalse(final_status["is_running"])
        self.assertEqual(len(final_status["history"]), 2)
        self.assertEqual(final_status["history"][0]["status"], "done")
        self.assertEqual(final_status["history"][1]["status"], "done")

    def test_flask_routes(self):
        """Valida as rotas HTTP de conversão no Flask do Editor."""
        client = app.test_client()

        # Health
        resp_health = client.get('/api/health')
        self.assertEqual(resp_health.status_code, 200)
        self.assertTrue(resp_health.json.get("hevc_nvenc") is not None)

        # Status
        resp_status = client.get('/api/conversion_status')
        self.assertEqual(resp_status.status_code, 200)
        self.assertIn("overall_progress", resp_status.json)

        # Pasta de saída
        with patch("nexus.editor.narravox_editor.subprocess.Popen") :
            resp_folder = client.post('/api/open_output_folder')
        self.assertEqual(resp_folder.status_code, 200)
        self.assertTrue(resp_folder.json.get("success"))

if __name__ == "__main__":
    unittest.main()
