"""DJ-owned worker lifecycle with CPU/GPU resource caps."""
import atexit
import logging
import subprocess
import sys
import threading
import time
from pathlib import Path

from nexus.json_io import safe_json_read, safe_json_write
from .store import cache_key, digest, write_json
from .safety import (MAX_SYSTEM_USAGE_PERCENT, MAX_VRAM_USAGE_PERCENT, MAX_WORKER_RSS_BYTES,
                     preflight)
from .safety import vram_usage_percent


def parse_options(data):
    """Prefer CUDA for supported analysis stages; CPU remains an explicit fallback."""
    import math
    
    options = {
        "device": str(data.get("device", "gpu")).lower(),
        "separator": str(data.get("separator", "openunmix")).lower(),
        "sheetsage": str(data.get("sheetsage", "false")).lower() == "true",
        "sheetsage_backend": str(data.get("sheetsage_backend",
                                    "cuda" if str(data.get("sheetsage", "false")).lower() == "true" else "cpu")).lower()
    }
    if options["device"] not in {"cpu", "gpu"}:
        raise ValueError("device deve ser gpu ou cpu")
    if options["separator"] != "openunmix":
        raise ValueError("O Analyzer aceita somente Open-Unmix")
    if options["sheetsage_backend"] not in {"cpu", "cuda"}:
        raise ValueError("backend SheetSage2 deve ser cpu ou cuda")
    
    for key, low, high in [("bpm", 40, 240), ("meter", 2, 7), ("offset", 0, 30)]:
        value = data.get(key)
        if value not in (None, ""):
            number = float(value)
            if not math.isfinite(number) or not low <= number <= high or (key == "meter" and not number.is_integer()):
                raise ValueError(f"Valor inválido para {key}")
            options[key] = int(number) if key == "meter" else number
    
    return options


class StyleService:
    def __init__(self, root, dj):
        self.root = Path(root)
        self.projects = self.root / "uploads/dj_styles"
        self.projects.mkdir(parents=True, exist_ok=True)
        self.dj = dj
        self.lock = threading.RLock()
        self.process = None
        self.active_id = None
        self.cancelled = False
        self._monitor = None
        
        # Process cannot survive previous app shutdown as a valid current job.
        for path in self.projects.glob("*/job_status.json"):
            old = safe_json_read(path) or {}
            if old.get("status") in ("running", "queued"):
                safe_json_write({"status": "interrupted", "error": "Sessão interrompida; reenviar referência retoma o cache."}, path)
        
        atexit.register(self.cancel)

    def get_projects_list(self):
        """Return list of all projects with their metadata."""
        projects = []
        for project_path in self.projects.iterdir():
            if not project_path.is_dir():
                continue
            
            # Get project info from source.json or style.json
            source = safe_json_read(project_path / "source.json") or {}
            style = safe_json_read(project_path / "style.json") or {}
            
            project_info = {
                "id": str(project_path.relative_to(self.projects)),
                "name": source.get("name", "Projeto"),
                "file_reference": source.get("path", "Arquivo não encontrado"),
                "has_analysis": bool(style),
                "algorithm_version": style.get("algorithm_version", None) if style else None,
            }
            
            projects.append(project_info)
        
        return sorted(projects, key=lambda p: p["name"])

    def list_projects(self):
        """Return project names for UI display."""
        projects = []
        for project_path in self.projects.iterdir():
            if not project_path.is_dir():
                continue
            
            source = safe_json_read(project_path / "source.json") or {}
            style = safe_json_read(project_path / "style.json") or {}
            
            name = source.get("name", f"Projeto {len(projects)+1}")
            
            projects.append({
                "id": str(project_path.relative_to(self.projects)),
                "name": name[:100],
                "has_analysis": bool(style),
            })
        
        return projects

    def open_project(self, project_id):
        """Open an existing project without reprocessing."""
        project_path = self.projects / project_id
        
        source = safe_json_read(project_path / "source.json") or {}
        style = safe_json_read(project_path / "style.json") or {}
        
        # Check if stems exist
        stem_files = [project_path / f"{target}.wav" for target in ("drums", "bass", "vocals", "other")]
        stems_exist = all(p.is_file() for p in stem_files)
        
        return {
            "source": source,
            "style": style if not source.get("path") else None,  # Only include style if source exists
            "stems_exist": stems_exist,
            "project_path": str(project_path),
        }

    def start(self, source, name, options):
        with self.lock:
            if self.active_id or self.dj.worker_busy or self.dj.generating_music:
                raise RuntimeError("Nexus DJ ocupado; aguarde a tarefa atual")

            preflight(source, self.projects, sheetsage=options.get("sheetsage", False),
                      require_gpu=options.get("device") == "gpu" or options.get("sheetsage_backend") == "cuda")
            
            source_hash = digest(source)
            
            # Check for existing project (avoid duplicates)
            existing_project = None
            for p in self.projects.iterdir():
                if not p.is_dir():
                    continue
                proj_source = safe_json_read(p / "source.json") or {}
                if proj_source.get("sha256") == source_hash:
                    existing_project = str(p)
                    break
            
            if existing_project and options.get("force_reprocess", False):
                # User wants to reprocess - delete old project
                import shutil
                shutil.rmtree(existing_project, ignore_errors=True)

            sid = cache_key(source_hash, options)
            project = self.projects / sid
            
            # Create project structure
            project.mkdir(exist_ok=True)
            
            # Save source reference (persistent)
            safe_json_write({
                "sha256": source_hash,
                "path": str(Path(source).resolve()),
                "name": name[:100],
                "options": options,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S") if False else None
            }, project / "source.json")
            
            # Initialize job status
            safe_json_write({
                "status": "queued",
                "stage": "preparing",
                "fraction": 0,
                "project_id": sid
            }, project / "job_status.json")
            self.active_id = sid
            self.cancelled = False
            try:
                import os
                env = os.environ.copy()
                for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                            "NUMBA_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
                    env[key] = "2"
                env["OMP_WAIT_POLICY"] = "PASSIVE"
                log = (project / "supervisor.log").open("a", encoding="utf-8")
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                self.process = subprocess.Popen(
                    [sys.executable, "-m", "nexus.dj.style_analyzer.worker",
                     str(self.root), str(project)],
                    cwd=str(self.root), stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, env=env,
                    creationflags=flags)
                log.close()
                self._lower_worker_priority(self.process.pid)
            except Exception as exc:
                self.active_id = None
                self.process = None
                safe_json_write({"status": "failed", "error": f"Não foi possível iniciar o worker: {exc}"}, project / "job_status.json")
                raise
            self._monitor = threading.Thread(target=self._watch_worker, args=(sid, project, self.process), daemon=True)
            self._monitor.start()
            return sid

    def _watch_worker(self, sid, project, process):
        import psutil
        unsafe_count = 0
        safety_reason = None
        while process.poll() is None:
            try:
                proc = psutil.Process(process.pid)
                tree = [proc, *proc.children(recursive=True)]
                rss = sum(p.memory_info().rss for p in tree if p.is_running())
                memory = psutil.virtual_memory()
                try:
                    vram_percent = vram_usage_percent()
                    vram_unreadable = False
                except Exception:
                    vram_percent = None
                    vram_unreadable = True
                unsafe_count = unsafe_count + 1 if (
                    rss > MAX_WORKER_RSS_BYTES or memory.percent >= MAX_SYSTEM_USAGE_PERCENT
                    or vram_unreadable or vram_percent >= MAX_VRAM_USAGE_PERCENT) else 0
                if unsafe_count >= 3:
                    if rss > MAX_WORKER_RSS_BYTES:
                        safety_reason = "Interrompido: memória do worker acima de 3,5 GiB"
                    elif memory.percent >= MAX_SYSTEM_USAGE_PERCENT:
                        safety_reason = "Interrompido: uso total da RAM atingiu 90%"
                    elif vram_unreadable:
                        safety_reason = "Interrompido: não foi possível verificar o limite de VRAM"
                    else:
                        safety_reason = "Interrompido: ocupação da VRAM atingiu 90%"
                    self._terminate_tree(process)
                    write_json(project / "job_status.json", {"status": "safety_abort", "error": safety_reason})
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            time.sleep(1)
        code = process.wait()
        with self.lock:
            state = safe_json_read(project / "job_status.json") or {}
            if safety_reason:
                pass
            elif code != 0 and state.get("status") not in ("failed", "cancelled"):
                safe_json_write({"status": "failed", "error": f"Worker terminou com código {code}"}, project / "job_status.json")
            elif self.cancelled:
                safe_json_write({"status": "cancelled", "error": "Análise cancelada"}, project / "job_status.json")
            if self.active_id == sid:
                self.active_id = None
                self.process = None

    def cancel(self):
        with self.lock:
            if self.process and self.process.poll() is None:
                self.cancelled = True
                self._terminate_tree(self.process)

    @staticmethod
    def _lower_worker_priority(pid):
        try:
            import psutil
            process = psutil.Process(pid)
            process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if sys.platform == "win32" else 10)
            cores = psutil.cpu_count(logical=True) or 1
            process.cpu_affinity(list(range(max(1, cores // 2))))
        except Exception:
            logging.getLogger("style_analyzer").warning("Não foi possível limitar prioridade/afinidade do worker")

    @staticmethod
    def _terminate_tree(process):
        import psutil
        try:
            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except psutil.Error:
                    pass
            parent.terminate()
            _, alive = psutil.wait_procs([*children, parent], timeout=3)
            for item in alive:
                try:
                    item.kill()
                except psutil.Error:
                    pass
        except psutil.Error:
            if process.poll() is None:
                process.kill()
