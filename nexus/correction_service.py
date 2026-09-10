"""Correções revisáveis; os projetos e as mídias originais nunca são sobrescritos."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import uuid


class CorrectionError(ValueError):
    pass


def read_json(path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def local_file(root, path):
    root = root.resolve()
    path = Path(path).resolve()
    if not path.is_relative_to(root):
        raise CorrectionError("Caminho fora do projeto.")
    return path


def safe_name(value):
    value = str(value)
    if not value or value in {".", ".."} or any(c in value for c in '/\\:\x00'):
        raise CorrectionError("Identificador de fala inválido.")
    return value


def read_audio(path):
    from pydub import AudioSegment
    with Path(path).open("rb") as stream:
        return AudioSegment.from_file(stream)


class CorrectionService:
    def __init__(self, base_dir, synthesizer=None):
        self.base = Path(base_dir).resolve()
        self.uploads = self.base / "uploads"
        self.projects = {}
        self.synthesizer = synthesizer or self.synthesize
        self.lock = threading.RLock()

    def discover(self):
        projects = []
        for metadata in sorted(self.uploads.glob("*/project_data.json")):
            try:
                folder = local_file(self.uploads, metadata.parent)
                data = read_json(metadata)
                segments = data.get("segments") if isinstance(data, dict) else data
                if not isinstance(segments, list) or not segments:
                    continue
                kind = "video" if isinstance(data, dict) and "segments" in data else "games"
                key = hashlib.sha256(str(folder).encode()).hexdigest()[:24]
                self.projects[key] = folder
                projects.append({"id": key, "name": folder.name, "kind": kind, "count": len(segments)})
            except (OSError, ValueError, TypeError):
                continue
        return projects

    def project(self, key):
        if key not in self.projects:
            self.discover()
        folder = self.projects.get(key)
        if folder is None:
            raise CorrectionError("Projeto não encontrado. Atualize a lista de projetos.")
        folder = local_file(self.uploads, folder)
        data = read_json(folder / "project_data.json")
        kind = "video" if isinstance(data, dict) and "segments" in data else "games"
        segments = data["segments"] if kind == "video" else data
        if not isinstance(segments, list):
            raise CorrectionError("Formato de projeto não suportado.")
        return folder, kind, segments

    def segment(self, key, segment_id):
        folder, kind, segments = self.project(key)
        segment_id = safe_name(segment_id)
        matches = [s for s in segments if isinstance(s, dict) and str(s.get("id")) == segment_id]
        if len(matches) != 1:
            raise CorrectionError("Fala ausente ou com identificador duplicado no projeto.")
        return folder, kind, matches[0]

    def audio(self, folder, kind, seg):
        sid = safe_name(seg["id"])
        if kind == "video":
            candidates = [folder / "_dubbed_segments" / f"{sid}.wav"]
        else:
            status = read_json(folder / "job_status.json", {})
            ext = status.get("file_format_map", {}).get(sid) or Path(seg.get("file_name", sid + ".wav")).suffix
            ext = ext if ext in {".wav", ".mp3", ".ogg", ".flac", ".m4a"} else ".wav"
            candidates = [folder / "_saida_final" / f"{sid}{ext}"]
            output = status.get("consolidated_output_path")
            if output:
                output = Path(output)
                output = output if output.is_absolute() else self.base / output
                candidates.append(local_file(self.uploads, output / f"{sid}{ext}"))
        for path in candidates:
            if path.is_file():
                return local_file(self.uploads, path)
        raise CorrectionError("Áudio final desta fala não encontrado. Conclua a dublagem primeiro.")

    def reference(self, folder, seg):
        sid = safe_name(seg["id"])
        speaker = safe_name(seg.get("speaker", "voz1"))
        voice = folder / "_2_PARA_AS_PASTAS_DE_VOZ" / speaker
        candidates = [voice / f"{sid}.wav"]
        if voice.is_dir():
            candidates += sorted(p for p in voice.glob("*.wav") if p.name.lower().startswith("_ref"))
        for candidate in candidates:
            if candidate.is_file():
                return local_file(folder, candidate)
        raise CorrectionError("A referência da voz original não foi encontrada. Preserve as pastas de voz do projeto.")

    def manifest(self, folder):
        return read_json(folder / "_correcoes" / "correcoes.json", {})

    def draft_path(self, folder, sid):
        # Um arquivo por segmento, inclusive antes de gerar qualquer áudio.
        name = hashlib.sha256(str(sid).encode()).hexdigest() + ".json"
        return folder / "_correcoes" / "segmentos" / name

    def drafts(self, folder):
        result = {}
        for path in (folder / "_correcoes" / "segmentos").glob("*.json"):
            data = read_json(path)
            if isinstance(data, dict) and "segment_id" in data:
                result[str(data["segment_id"])] = data
        return result

    def save_draft(self, key, sid, text, revision):
        if not isinstance(text, str) or len(text) > 3000:
            raise CorrectionError("O texto deve ter até 3.000 caracteres.")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
            raise CorrectionError("Revisão inválida.")
        folder, _, _ = self.segment(key, sid)
        with self.lock:
            path = self.draft_path(folder, sid)
            previous = read_json(path, {})
            # Requisições podem chegar fora de ordem; uma antiga não apaga a nova.
            if revision <= previous.get("revision", -1):
                return previous
            data = {**previous, "segment_id": str(sid), "text": text, "revision": revision, "status": "draft"}
            write_json(path, data)
            return data

    def enqueue(self, key, sid):
        folder, _, _ = self.segment(key, sid)
        with self.lock:
            path = self.draft_path(folder, sid)
            draft = read_json(path)
            if not draft or not draft["text"].strip():
                raise CorrectionError("Digite a tradução corrigida antes de salvar na fila.")
            snapshot = {"segment_id": str(sid), "text": draft["text"], "revision": draft["revision"], "status": "queued", "queued_at": time.time_ns()}
            draft.update(queued=snapshot, status="queued", error=None)
            write_json(path, draft)
            return dict(snapshot)

    def queue(self, key):
        folder, _, _ = self.project(key)
        values = list(self.drafts(folder).values())
        return {"items": values, "pending": sum(bool(d.get("queued")) and d["queued"].get("status") != "done" for d in values),
                "drafts": sum(d.get("status") == "draft" for d in values),
                "completed": sum(d.get("queued", {}).get("status") == "done" for d in values)}

    def set_draft_status(self, folder, draft, **changes):
        with self.lock:
            path = self.draft_path(folder, draft["segment_id"])
            current = read_json(path, {})
            if current.get("queued", {}).get("revision") == draft["revision"]:
                current["queued"].update(changes)
                if current.get("revision") == draft["revision"]:
                    current.update({k: v for k, v in changes.items() if k in {"status", "error"}})
                write_json(path, current)

    def process_queue(self, key, segment_id=None, progress=None, snapshots=None):
        from nexus.correction_queue_runner import process_queue
        return process_queue(self, key, segment_id, progress, snapshots)

    def search(self, key, query="", offset=0):
        folder, kind, segments = self.project(key)
        saved = self.manifest(folder)
        drafts = self.drafts(folder)
        result = []
        query = query.casefold().strip()
        for seg in segments:
            if not isinstance(seg, dict) or "id" not in seg:
                continue
            sid = safe_name(seg["id"])
            original = str(seg.get("original_text") or seg.get("text") or "")
            translated = str(saved.get(sid, {}).get("text") or seg.get("manual_edit_text") or seg.get("text_pt") or seg.get("translated_text") or "")
            draft = drafts.get(sid)
            if draft is not None:
                translated = draft["text"]
            if query and query not in f"{sid} {original} {translated}".casefold():
                continue
            result.append({"id": sid, "original": original, "translated": translated,
                           "speaker": seg.get("speaker", ""), "start": seg.get("start"),
                           "end": seg.get("end"), "corrected": sid in saved,
                           "revision": draft.get("revision", 0) if draft else 0,
                           "draft_status": draft.get("status") if draft else None,
                           "queued_revision": draft.get("queued", {}).get("revision") if draft else None,
                           "error": draft.get("error") if draft else None,
                           "preview_token": saved.get(sid, {}).get("token")})
        return {"items": result[offset:offset + 40], "total": len(result), "kind": kind}

    def ffmpeg(self):
        for path in [self.base / "env/Library/bin/ffmpeg.exe", self.base / "ffmpeg/bin/ffmpeg.exe", self.base / "ffmpeg.exe"]:
            if path.is_file():
                return str(path)
        return shutil.which("ffmpeg") or "ffmpeg"

    def run_ffmpeg(self, args):
        proc = subprocess.run([self.ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if proc.returncode:
            raise CorrectionError("FFmpeg não conseguiu preparar a mídia: " + proc.stderr[-1000:])

    def synthesize(self, text, reference, output, duration, emotion):
        request_path = output.with_suffix(".request.json")
        write_json(request_path, {"text": text, "reference": str(reference), "output": str(output),
                                  "duration": duration, "emotion": emotion})
        python = self.base / "env/Scripts/python.exe"
        if not python.exists():
            python = Path(sys.executable)
        log = output.with_suffix(".log")
        with log.open("w", encoding="utf-8") as stream:
            proc = subprocess.run([str(python), "-m", "nexus.correction_worker", str(request_path)],
                                  cwd=self.base, stdout=stream, stderr=subprocess.STDOUT, timeout=900,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if proc.returncode or not output.is_file():
            raise CorrectionError("Falha ao gerar a voz. Consulte o registro: " + str(log))

    def fingerprint(self, folder, source):
        stat = source.stat()
        return hashlib.sha256((folder / "project_data.json").read_bytes() +
                              f"{stat.st_size}:{stat.st_mtime_ns}".encode()).hexdigest()

    def preview(self, key, sid, text):
        from nexus.correction_preview import preview
        return preview(self, key, sid, text)

    def preview_file(self, key, token):
        folder, _, _ = self.project(key)
        work = local_file(folder, folder / "_correcoes" / "previas" / safe_name(token))
        info = read_json(work / "previa.json")
        if not info:
            raise CorrectionError("Prévia não encontrada.")
        return local_file(work, work / safe_name(info["audio"])), info

    def apply(self, key, token):
        with self.lock:
            preview, info = self.preview_file(key, token)
            folder, kind, seg = self.segment(key, info["segment_id"])
            if info["fingerprint"] != self.fingerprint(folder, self.audio(folder, kind, seg)):
                raise CorrectionError("O projeto mudou depois da prévia. Gere uma nova prévia antes de salvar.")
            manifest = self.manifest(folder)
            # Arquivos de prévia são imutáveis; o manifesto é atualizado atomicamente.
            manifest[info["segment_id"]] = {**info, "path": str(preview.relative_to(folder))}
            write_json(folder / "_correcoes" / "correcoes.json", manifest)
            return {"message": "Correção salva. Exporte para gerar a mídia corrigida.", "count": len(manifest)}

    def export(self, key, segment_id=None):
        from nexus.correction_export import export_corrections
        return export_corrections(self, key, segment_id)

    def export_video(self, folder, segments, manifest, output):
        from nexus.correction_video_export import export_video
        return export_video(self, folder, segments, manifest, output)
