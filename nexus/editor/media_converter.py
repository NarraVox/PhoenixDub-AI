# -*- coding: utf-8 -*-
"""Módulo de conversão de mídia com suporte a HEVC/H.264 NVENC, detecção de resolução (4K -> 1080p),
cópia inteligente de stream (remux) e estimativa de tamanho pré-conversão.
Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
"""

import logging
import subprocess
import json
import re
import threading
from pathlib import Path

from nexus.editor.tv_compat import is_tv_codec, is_tv_ready, plan_when_bigger

# ─── INICIALIZAÇÃO GLOBAL ───────────────────────────────────────────────────
FFMPEG = "ffmpeg"
logger = logging.getLogger(__name__)


# ─── FUNÇÕES UTILITÁRIAS DE PROBE E TELEMETRIA ──────────────────────────────

def probe_media_file(input_path: str) -> dict:
    """Extrai metadados completos de um arquivo de mídia (resolução, codec, duração, taxa e tamanho)."""
    p = Path(input_path)
    info = {
        'path': str(input_path),
        'filename': p.name,
        'size_bytes': 0,
        'size_mb': 0.0,
        'duration': 0.0,
        'width': 0,
        'height': 0,
        'resolution_label': 'Áudio / Desconhecido',
        'codec': '',
        'fps': 0.0,
        'is_video': False,
        'ext': p.suffix.lower(),
    }
    if not p.exists():
        return info

    try:
        info['size_bytes'] = p.stat().st_size
        info['size_mb'] = round(info['size_bytes'] / (1024 * 1024), 2)
    except Exception:
        pass

    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height,codec_name,r_frame_rate,codec_type:format=duration,size",
            "-of", "json",
            str(input_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            fmt = data.get('format', {})
            try:
                info['duration'] = float(fmt.get('duration', 0.0))
            except (ValueError, TypeError):
                info['duration'] = 0.0

            streams = data.get('streams', [])
            vstream = next((s for s in streams if s.get('codec_type') == 'video'), None)
            if vstream:
                info['is_video'] = True
                info['width'] = int(vstream.get('width', 0))
                info['height'] = int(vstream.get('height', 0))
                info['codec'] = (vstream.get('codec_name') or '').lower()
                r_fps = vstream.get('r_frame_rate', '0/1')
                try:
                    num, den = map(int, r_fps.split('/'))
                    info['fps'] = round(num / den, 2) if den > 0 else 0.0
                except Exception:
                    info['fps'] = 0.0

                w, h = info['width'], info['height']
                max_dim = max(w, h)
                if max_dim >= 3800:
                    info['resolution_label'] = f"4K ({w}×{h})"
                elif max_dim >= 2500:
                    info['resolution_label'] = f"1440p 2K ({w}×{h})"
                elif max_dim >= 1800:
                    info['resolution_label'] = f"1080p Full HD ({w}×{h})"
                elif max_dim >= 1200:
                    info['resolution_label'] = f"720p HD ({w}×{h})"
                elif max_dim > 0:
                    info['resolution_label'] = f"{w}×{h}"
                else:
                    info['resolution_label'] = "Vídeo"
            else:
                info['resolution_label'] = "Áudio"
    except Exception as e:
        logger.warning("Falha ao analisar metadados de %s: %s", input_path, e)

    return info


def calculate_conversion_plan(info: dict, target_codec: str = 'h265', max_res: str = '1080p',
                              audio_bitrate: str = '160k', skip_if_less_10_pct: bool = True) -> dict:
    """Calcula tamanho estimado, ação ideal (remux, encode, skip) e explica por que demora ou economiza."""
    if not info.get('is_video'):
        # Áudio
        abr_num = 160
        try:
            abr_num = int(re.sub(r'\D', '', audio_bitrate) or 160)
        except Exception:
            abr_num = 160
        dur = info.get('duration', 0.0)
        est_bytes = int((abr_num * 1000 * dur) / 8) if dur > 0 else 0
        est_mb = round(est_bytes / (1024 * 1024), 2)
        return {
            'action': 'encode_audio',
            'orig_size_mb': info.get('size_mb', 0.0),
            'estimated_size_mb': est_mb,
            'savings_pct': round(((info.get('size_bytes', 1) - est_bytes) / max(1, info.get('size_bytes', 1))) * 100, 1),
            'target_res_label': 'Áudio',
            'target_codec': 'aac/mp3',
            'explanation': f"Conversão de áudio para {audio_bitrate}."
        }

    w, h = info.get('width', 0), info.get('height', 0)
    max_dim = max(w, h)
    codec = (info.get('codec') or '').lower()
    ext = (info.get('ext') or '').lower()
    dur = info.get('duration', 0.0)
    orig_bytes = info.get('size_bytes', 0)
    orig_mb = info.get('size_mb', 0.0)

    # 1. Verifica se precisa de escala para resolução máxima
    needs_scale = False
    target_res_label = info.get('resolution_label', '')
    if max_res == '1080p':
        if w > 1920 or h > 1080:
            needs_scale = True
            target_res_label = "1080p Full HD"
    elif max_res == '720p':
        if w > 1280 or h > 720:
            needs_scale = True
            target_res_label = "720p HD"

    # 2. Verifica se o codec já é o mesmo desejado
    is_same_codec = False
    if target_codec == 'h265' and codec in ['hevc', 'h265']:
        is_same_codec = True
    elif target_codec == 'h264' and codec in ['h264', 'avc', 'avc1']:
        is_same_codec = True

    # 3. Estimativa de Bitrate e Tamanho Final
    if target_res_label.startswith("720p"):
        v_kbps = 1500
    elif target_res_label.startswith("1080p"):
        v_kbps = 2800
    elif max_dim >= 3800:
        v_kbps = 6000
    else:
        v_kbps = 2500

    abr_num = 160
    try:
        abr_num = int(re.sub(r'\D', '', audio_bitrate) or 160)
    except Exception:
        abr_num = 160

    total_kbps = v_kbps + abr_num
    est_bytes = int((total_kbps * 1000 * dur) / 8) if dur > 0 else 0
    est_mb = round(est_bytes / (1024 * 1024), 2)

    if orig_bytes > 0 and est_bytes > 0:
        savings_pct = round(((orig_bytes - est_bytes) / orig_bytes) * 100, 1)
    else:
        savings_pct = 0.0

    # 4. Decisão de Ação Inteligente
    is_mkv_to_mp4 = (ext != '.mp4')

    # Caso B: a conversão deixaria o arquivo mais pesado. Se o vídeo já toca na TV,
    # pula (ou só troca o contêiner); só recodifica se o codec for incompatível.
    if est_bytes > 0 and orig_bytes > 0 and est_bytes >= orig_bytes:
        alt = plan_when_bigger(info, est_mb, savings_pct)
        if alt:
            return alt

    # Caso A: Vídeo já é do mesmo codec e já respeita a resolução máxima
    if is_same_codec and not needs_scale:
        if savings_pct >= 10.0:
            # A nova codificação diminuirá o tamanho em 10% ou mais: realmente converte!
            return {
                'action': 'encode',
                'orig_size_mb': orig_mb,
                'estimated_size_mb': est_mb,
                'savings_pct': savings_pct,
                'target_res_label': target_res_label,
                'target_codec': target_codec.upper(),
                'explanation': f"🎬 Otimizando compressão para {target_codec.upper()} ({target_res_label}) via GPU NVENC • Redução estimada de tamanho: -{savings_pct:.0f}%."
            }
        else:
            # A economia seria menor que 10%
            if is_mkv_to_mp4:
                # Muda de formato (ex: .mkv para .mp4): Stream Copy instantâneo em ~5s!
                return {
                    'action': 'remux',
                    'orig_size_mb': orig_mb,
                    'estimated_size_mb': orig_mb,
                    'savings_pct': 0.0,
                    'target_res_label': info.get('resolution_label', ''),
                    'target_codec': f"{codec.upper()} (Cópia)",
                    'explanation': f"⚡ Troca rápida de formato ({ext.upper()} ➔ MP4): A economia seria < 10%, portanto aplicando Cópia Direta (Stream Copy) em ~5 segundos sem perda de qualidade e sem aquecer a GPU."
                }
            elif skip_if_less_10_pct:
                # Já é MP4 e economia < 10%: pula a conversão
                return {
                    'action': 'skip',
                    'orig_size_mb': orig_mb,
                    'estimated_size_mb': est_mb,
                    'savings_pct': savings_pct,
                    'target_res_label': info.get('resolution_label', ''),
                    'target_codec': codec.upper(),
                    'explanation': f"⏭️ Pulado: O vídeo já é MP4 {codec.upper()} ({info.get('resolution_label')}) e a redução de tamanho estimada seria de apenas {max(0.0, savings_pct):.1f}% (< 10%). Conversão desnecessária evitada."
                }

    # Caso C: Vídeo é 4K (ou maior que o limite) e será reduzido para Full HD 1080p
    if needs_scale:
        return {
            'action': 'encode',
            'orig_size_mb': orig_mb,
            'estimated_size_mb': est_mb,
            'savings_pct': savings_pct,
            'target_res_label': target_res_label,
            'target_codec': target_codec.upper(),
            'explanation': f"🎬 Vídeo {info.get('resolution_label')} detectado. Redimensionando para {target_res_label} via GPU NVENC para máxima velocidade e economia de espaço (estimativa: -{max(0.0, savings_pct):.0f}%)."
        }

    # Caso D: Re-codificação padrão para o codec alvo
    return {
        'action': 'encode',
        'orig_size_mb': orig_mb,
        'estimated_size_mb': est_mb,
        'savings_pct': savings_pct,
        'target_res_label': target_res_label,
        'target_codec': target_codec.upper(),
        'explanation': f"🎬 Recodificando para {target_codec.upper()} ({target_res_label}) via GPU NVENC • Redução estimada: {max(0.0, savings_pct):.1f}%."
    }


def detect_nvenc_hevc(ffmpeg_path: str = None) -> bool:
    """Verifica se o binário lista HEVC NVENC e consegue iniciar uma codificação."""
    try:
        cmd = [ffmpeg_path, "-encoders"] if ffmpeg_path else ["ffmpeg", "-encoders"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and "hevc_nvenc" in result.stdout:
            probe_cmd = [cmd[0], "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                         "color=c=black:s=320x240:d=0.2", "-frames:v", "1", "-c:v", "hevc_nvenc",
                         "-f", "null", "-"]
            probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
            return probe.returncode == 0
        return False
    except Exception:
        return False


def detect_nvenc_h264(ffmpeg_path: str = None) -> bool:
    """Verifica se o binário suporta codificação H.264 NVENC via hardware."""
    try:
        cmd = [ffmpeg_path, "-encoders"] if ffmpeg_path else ["ffmpeg", "-encoders"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and "h264_nvenc" in result.stdout:
            probe_cmd = [cmd[0], "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                         "color=c=black:s=320x240:d=0.2", "-frames:v", "1", "-c:v", "h264_nvenc",
                         "-f", "null", "-"]
            probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
            return probe.returncode == 0
        return False
    except Exception:
        return False


is_nvenc_hevc_available = detect_nvenc_hevc


def detect_orientation_auto(width: int, height: int) -> str:
    """Detecta a orientação automática baseada na proporção."""
    if height == 0:
        return "auto"
    aspect_ratio = width / height
    tolerance = 0.05
    if abs(aspect_ratio - 16 / 9) < tolerance:
        return "horizontal"
    elif abs(aspect_ratio - 9 / 16) < tolerance:
        return "vertical"
    elif abs(aspect_ratio - 4 / 3) < tolerance:
        return "43"
    elif abs(aspect_ratio - 2.35) < tolerance:
        return "cine"
    elif abs(aspect_ratio - 1) < tolerance:
        return "square"
    return "auto"


def get_media_duration(input_path: str) -> float:
    """Obtém a duração do arquivo em segundos usando ffprobe."""
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", "-i", str(input_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            return float(data.get('format', {}).get('duration', 0.0))
    except Exception:
        pass
    return 0.0


# ─── CLASSE PRINCIPAL MEDIACONVERTER ────────────────────────────────────────

class MediaConverter:
    """Conversor de mídia com suporte a HEVC/H.264 NVENC, redimensionamento automático de 4K para 1080p e remux."""

    def __init__(self, ffmpeg_path: str = None):
        self.FFMPEG = ffmpeg_path or FFMPEG
        self._nvenc_hevc_available = None
        self._nvenc_h264_available = None
        self._nvdec_available = None

    def _check_nvenc(self, codec: str = "h265") -> bool:
        if codec == "h264":
            if self._nvenc_h264_available is None:
                self._nvenc_h264_available = detect_nvenc_h264(self.FFMPEG)
            return self._nvenc_h264_available
        if self._nvenc_hevc_available is None:
            self._nvenc_hevc_available = detect_nvenc_hevc(self.FFMPEG)
        return self._nvenc_hevc_available

    def _check_nvdec(self) -> bool:
        if self._nvdec_available is not None:
            return self._nvdec_available
        try:
            res = subprocess.run([self.FFMPEG, "-hide_banner", "-hwaccels"],
                                 capture_output=True, text=True, timeout=10)
            self._nvdec_available = res.returncode == 0 and "cuda" in res.stdout.lower()
        except Exception:
            self._nvdec_available = False
        return self._nvdec_available

    @staticmethod
    def build_audio_command(input_path, output_path, target_format="mp3", bitrate="160k"):
        """Gera comando FFmpeg para conversão de áudio mantendo compatibilidade com testes."""
        cmd = [FFMPEG, "-y", "-hide_banner", "-i", str(input_path), "-vn"]
        if target_format == "mp3":
            cmd.extend(["-c:a", "libmp3lame", "-b:a", str(bitrate)])
        elif target_format in ["aac", "m4a"]:
            cmd.extend(["-c:a", "aac", "-b:a", str(bitrate)])
        elif target_format == "wav":
            cmd.extend(["-c:a", "pcm_s16le"])
        elif target_format == "flac":
            cmd.extend(["-c:a", "flac"])
        else:
            cmd.extend(["-b:a", str(bitrate)])
        cmd.append(str(output_path))
        return cmd

    @staticmethod
    def build_video_h265_command(input_path, output_path, video_bitrate=None, force_cpu=False):
        """Compatibilidade com testes legados de comando de vídeo."""
        cmd = [FFMPEG, "-y", "-hide_banner", "-i", str(input_path)]
        use_gpu = is_nvenc_hevc_available() and not force_cpu
        if use_gpu:
            cmd.extend(["-c:v", "hevc_nvenc", "-cq", "23", "-b:v", "0"])
        else:
            cmd.extend(["-c:v", "libx265", "-crf", "23"])
            if video_bitrate:
                cmd.extend(["-b:v", str(video_bitrate)])
        cmd.extend(["-c:a", "aac", "-b:a", "160k", str(output_path)])
        return cmd

    def _video_command(self, input_path, output_path, vf_filter=None, bitrate=3000, max_bitrate=5000,
                       audio_bitrate="160k", force_cpu=False, target_codec="h265", max_res="1080p"):
        """Monta comando de vídeo com suporte a GPU NVENC, escolha de codec e limite de resolução (ex: 4K -> 1080p)."""
        target_codec = target_codec.lower() if target_codec else "h265"
        use_nvenc = self._check_nvenc(target_codec) and not force_cpu

        cmd = [self.FFMPEG, "-y", "-hide_banner", "-nostdin"]
        if use_nvenc and self._check_nvdec():
            cmd.extend(["-hwaccel", "cuda"])

        cmd.extend(["-i", str(input_path)])

        # Monta os filtros de vídeo (orientação + escala máxima)
        filters = []
        if vf_filter:
            filters.append(vf_filter)

        if max_res == "1080p":
            filters.append("scale='min(1920,iw)':'min(1080,ih)':force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2")
        elif max_res == "720p":
            filters.append("scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2")

        if filters:
            cmd.extend(["-vf", ",".join(filters)])

        # Seleciona encoder
        if target_codec == "h264":
            encoder = "h264_nvenc" if use_nvenc else "libx264"
        else:
            encoder = "hevc_nvenc" if use_nvenc else "libx265"

        cmd.extend(["-c:v", encoder])

        if use_nvenc:
            cmd.extend([
                "-preset", "p4", "-tune", "hq", "-rc", "vbr",
                "-spatial-aq", "1",
                "-b:v", f"{bitrate}k", "-maxrate", f"{max_bitrate}k",
                "-bufsize", f"{max_bitrate * 2}k"
            ])
        else:
            cmd.extend([
                "-preset", "fast",
                "-b:v", f"{bitrate}k", "-maxrate", f"{max_bitrate}k",
                "-bufsize", f"{max_bitrate * 2}k"
            ])

        cmd.extend([
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", str(audio_bitrate),
            "-movflags", "+faststart",
            str(output_path)
        ])
        return cmd

    def detect_orientation(self, input_path: str) -> str:
        """Detecta a orientação original do vídeo usando ffprobe."""
        try:
            cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
                   "-show_entries", "stream=width,height", "-of", "json", "-i", str(input_path)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if res.returncode == 0:
                meta = json.loads(res.stdout)
                streams = meta.get('streams', [])
                if streams:
                    w = int(streams[0].get('width', 0))
                    h = int(streams[0].get('height', 0))
                    return detect_orientation_auto(w, h)
        except Exception as e:
            logger.warning("Erro na detecção de orientação: %s", e)
        return "auto"


# ─── FILA DE CONVERSÃO EM LOTE (CONVERSION BATCH QUEUE) ─────────────────────

class ConversionBatchQueue:
    """Fila de conversão em lote inteligente com remux automático, limite 1080p e telemetria detalhada."""

    AUDIO_EXTS = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'}
    VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm', '.flv',
                  '.mpeg', '.mpg', '.ts', '.mts', '.m2ts', '.3gp', '.ogv',
                  '.m4v', '.vob', '.divx', '.asf', '.rm', '.rmvb', '.mxf',
                  '.y4m', '.nut', '.h264', '.h265', '.hevc'}

    def __init__(self, max_workers: int = 4, output_dir: str = None):
        self.max_workers = max_workers
        self._output_dir = Path(output_dir) if output_dir else Path('uploads/conversoes')
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._queue = []
        self._history = []
        self._current = None
        self._item_progress = 0
        self._lock = threading.Lock()
        self._running = False
        self._cancel_flag = False
        self._thread = None
        self._converter = MediaConverter()

    @property
    def is_running(self) -> bool:
        return self._running

    def add_items(self, items: list) -> list:
        """Adiciona itens à fila e pré-calcula informações e planos de conversão."""
        added = []
        with self._lock:
            for it in items:
                path = it.get('input_path', '')
                if not path:
                    continue
                info = probe_media_file(path)
                target_codec = it.get('target_codec', 'h265')
                max_res = it.get('max_res', '1080p')
                abr = it.get('audio_bitrate', '160k')
                skip_less_10 = it.get('skip_if_less_10_pct', True)

                plan = calculate_conversion_plan(
                    info,
                    target_codec=target_codec,
                    max_res=max_res,
                    audio_bitrate=abr,
                    skip_if_less_10_pct=skip_less_10
                )

                entry = {
                    'input_path': path,
                    'filename': Path(path).name,
                    'mode': it.get('mode', 'video' if info.get('is_video') else 'music'),
                    'format': it.get('format', 'mp4' if info.get('is_video') else 'mp3'),
                    'audio_bitrate': abr,
                    'orientation': it.get('orientation', 'auto'),
                    'target_codec': target_codec,
                    'max_res': max_res,
                    'skip_if_less_10_pct': skip_less_10,
                    'status': 'pending',
                    'info': info,
                    'plan': plan,
                    'explanation': plan.get('explanation', '')
                }
                self._queue.append(entry)
                added.append(entry)
        return added

    def start_batch(self) -> bool:
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._cancel_flag = False
        self._thread = threading.Thread(target=self._run_batch, daemon=True)
        self._thread.start()
        return True

    def _run_batch(self):
        try:
            while True:
                with self._lock:
                    if self._cancel_flag or not self._queue:
                        break
                    item = self._queue.pop(0)
                    self._current = item
                    self._item_progress = 0

                self._process_item(item)

                with self._lock:
                    self._history.append(item)
                    self._current = None
                    self._item_progress = 0
        finally:
            with self._lock:
                self._running = False
                self._current = None

    def _process_item(self, item: dict):
        """Executa a conversão inteligente de um único item (remux, encode com 1080p ou skip)."""
        input_path = item['input_path']
        fmt = item['format']
        abr = item['audio_bitrate']
        target_codec = item.get('target_codec', 'h265')
        max_res = item.get('max_res', '1080p')
        out_stem = Path(input_path).stem
        ext = Path(input_path).suffix.lower()

        try:
            # 1. Garante metadados e plano atualizados
            info = item.get('info') or probe_media_file(input_path)
            item['info'] = info
            plan = item.get('plan') or calculate_conversion_plan(
                info, target_codec=target_codec, max_res=max_res, audio_bitrate=abr,
                skip_if_less_10_pct=item.get('skip_if_less_10_pct', True)
            )
            item['plan'] = plan
            item['explanation'] = plan.get('explanation', '')

            # 2. Se a ação for PULAR (Skip):
            if plan.get('action') == 'skip':
                logger.info("Conversão pulada para %s: %s", input_path, plan.get('explanation'))
                item['status'] = 'skipped'
                item['skip_reason'] = plan.get('explanation')
                self._item_progress = 100
                return

            item['status'] = 'converting'

            # 3. Conversão de Áudio
            if item['mode'] == 'music' or ext in self.AUDIO_EXTS or not info.get('is_video'):
                item['mode'] = 'audio'
                out_path = self._output_dir / f"{out_stem}.{fmt}"
                cmd = [
                    'ffmpeg', '-y', '-hide_banner', '-nostdin',
                    '-i', str(input_path),
                    '-b:a', abr,
                    '-vn',
                    str(out_path)
                ]
            # 4. Remux Ultrarrápido de Vídeo (Stream Copy)
            elif plan.get('action') == 'remux':
                item['mode'] = 'video'
                out_path = self._output_dir / f"{out_stem}.mp4"
                cmd = self._remux_command(input_path, out_path, abr, info)
            # 5. Codificação Completa com Redimensionamento se necessário (4K -> 1080p)
            else:
                item['mode'] = 'video'
                out_path = self._output_dir / f"{out_stem}.mp4"
                cmd = self._converter._video_command(
                    input_path, out_path,
                    audio_bitrate=abr,
                    target_codec=target_codec,
                    max_res=max_res
                )

            total_duration = info.get('duration') or get_media_duration(input_path) or 0.0

            proc = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            time_pat = re.compile(r'time=(\d+):(\d+):(\d+\.\d+)')
            speed_pat = re.compile(r'speed=\s*([\d.]+)x')
            fps_pat = re.compile(r'fps=\s*([\d.]+)')

            for line in proc.stderr:
                if self._cancel_flag:
                    proc.kill()
                    break
                m = time_pat.search(line)
                if m and total_duration > 0:
                    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
                    elapsed = h * 3600 + mi * 60 + s
                    self._item_progress = min(99, int(elapsed / total_duration * 100))
                ms = speed_pat.search(line)
                if ms:
                    item['speed'] = float(ms.group(1))
                mf = fps_pat.search(line)
                if mf:
                    item['fps'] = float(mf.group(1))

            proc.wait()
            if proc.stderr:
                try:
                    proc.stderr.close()
                except Exception:
                    pass

            # Fallback em caso de erro no encoder da GPU
            if item['mode'] == 'video' and proc.returncode != 0 and plan.get('action') == 'encode':
                logger.warning("Falha na GPU para %s; tentando CPU: %s", input_path, out_path)
                cpu_cmd = self._converter._video_command(
                    input_path, out_path,
                    audio_bitrate=abr,
                    target_codec=target_codec,
                    max_res=max_res,
                    force_cpu=True
                )
                proc = subprocess.Popen(cpu_cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                        text=True, encoding='utf-8', errors='replace')
                for line in proc.stderr:
                    m = time_pat.search(line)
                    if m and total_duration > 0:
                        elapsed = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
                        self._item_progress = min(99, int(elapsed / total_duration * 100))
                proc.wait()
            if proc.stderr:
                try:
                    proc.stderr.close()
                except Exception:
                    pass

            item['status'] = 'done' if proc.returncode == 0 else 'error'
            if item['status'] == 'done' and item['mode'] == 'video' and plan.get('action') == 'encode':
                self._discard_if_bigger(item, info, out_path, abr)
            self._item_progress = 100

        except Exception as e:
            logger.error('[CONVERTER] Erro ao processar %s: %s', input_path, e)
            item['status'] = 'error'

    @staticmethod
    def _remux_command(input_path, out_path, abr, info) -> list:
        """Troca o contêiner para MP4 sem recodificar o vídeo."""
        cmd = ['ffmpeg', '-y', '-hide_banner', '-nostdin', '-i', str(input_path), '-c:v', 'copy']
        if (info.get('codec') or '').lower() in ('hevc', 'h265'):
            cmd.extend(['-tag:v', 'hvc1'])  # HEVC em MP4 reconhecido por TVs/Apple
        cmd.extend(['-c:a', 'aac', '-b:a', str(abr), '-movflags', '+faststart', str(out_path)])
        return cmd

    def _discard_if_bigger(self, item: dict, info: dict, out_path: Path, abr: str):
        """Se a recodificação ficou mais pesada que o original e o vídeo já tocava na TV,
        descarta o resultado: pula (MP4 pronto) ou apenas troca o contêiner."""
        orig_bytes = info.get('size_bytes', 0)
        try:
            new_bytes = Path(out_path).stat().st_size
        except OSError:
            return
        if orig_bytes <= 0 or new_bytes < orig_bytes or not is_tv_codec(info.get('codec')):
            return
        growth = (new_bytes - orig_bytes) / orig_bytes * 100
        try:
            Path(out_path).unlink()
        except OSError as e:
            logger.warning("Não foi possível remover conversão maior %s: %s", out_path, e)
            return
        if is_tv_ready(info):
            item['status'] = 'skipped'
            item['skip_reason'] = (f"⏭️ Conversão descartada: o resultado ficou ~{growth:.0f}% mais pesado "
                                   f"e o original já é compatível com TV.")
            item['explanation'] = item['skip_reason']
            logger.info("Conversão descartada (maior que o original): %s", item['input_path'])
            return
        res = subprocess.run(self._remux_command(item['input_path'], out_path, abr, info),
                             capture_output=True, text=True, encoding='utf-8', errors='replace')
        item['status'] = 'done' if res.returncode == 0 else 'error'
        item['explanation'] = (f"⚡ Recodificação ficou ~{growth:.0f}% mais pesada; feita só a troca "
                               f"de formato para MP4 (cópia direta).")

    def get_status(self) -> dict:
        """Retorna telemetria completa da fila para o frontend."""
        with self._lock:
            queue_count = len(self._queue)
            history_count = len(self._history)
            total = queue_count + history_count + (1 if self._current else 0)
            overall = int(history_count / total * 100) if total > 0 else 0
            current_snap = dict(self._current) if self._current else None
            history_snap = [
                {
                    'input_path': h['input_path'],
                    'status': h['status'],
                    'skip_reason': h.get('skip_reason', ''),
                    'explanation': h.get('explanation', ''),
                    'plan': h.get('plan')
                }
                for h in self._history
            ]
            item_prog = self._item_progress

        return {
            'is_running': self._running,
            'overall_progress': overall,
            'queue_count': queue_count,
            'history_count': history_count,
            'item_progress': item_prog,
            'current_item': current_snap,
            'history': history_snap,
        }

    def cancel_batch(self):
        with self._lock:
            self._cancel_flag = True

    def clear_queue(self) -> bool:
        with self._lock:
            if self._running:
                return False
            self._queue.clear()
            self._history.clear()
            return True

    def get_stats(self) -> dict:
        with self._lock:
            return {
                'total': len(self._history),
                'success': sum(1 for h in self._history if h['status'] == 'done'),
                'failed': sum(1 for h in self._history if h['status'] == 'error'),
                'skipped': sum(1 for h in self._history if h['status'] == 'skipped'),
                'queue_size': len(self._queue),
            }
