import sys
from pathlib import Path
import os

project_root = Path("C:/IA_dublagem")
sys.path.insert(0, str(project_root))

base_env = Path(sys.executable).parent.parent
local_site = base_env / "Lib" / "site-packages"
sys.path = [p for p in sys.path if not ("AppData" in p and "site-packages" in p)]
if str(local_site) not in sys.path:
    sys.path.insert(0, str(local_site))

# Forçar DLLs da NVIDIA
site_packages = base_env / "Lib" / "site-packages"
dll_paths = [
    site_packages / "llama_cpp" / "lib",
    site_packages / "nvidia" / "cublas" / "bin",
    site_packages / "nvidia" / "cuda_runtime" / "bin",
    site_packages / "nvidia" / "cuda_nvrtc" / "bin"
]
for p in dll_paths:
    if p.exists():
        os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try: os.add_dll_directory(str(p))
            except: pass

import torch
from faster_whisper import WhisperModel
import json

scratch_dir = Path("C:/IA_dublagem/scratch")
config_file = scratch_dir / "video_editor_config.json"

# Valores padrão
video_path = "C:/IA_dublagem/uploads/VID_editado.mp4"
if config_file.exists():
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            video_path = cfg.get("output_path", video_path)
    except Exception as e:
        print(f"Aviso ao carregar config: {e}")

output_path = "C:/IA_dublagem/scratch/transcricao_video_editado.txt"

print(f"Inicializando o modelo Whisper 'small' na GPU...")
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "int8_float16" if device == "cuda" else "int8"

model = WhisperModel("small", device=device, compute_type=compute_type)

print(f"Transcrevendo o vídeo editado {video_path}...")
segments, info = model.transcribe(
    video_path,
    language="pt",
    beam_size=1,
    condition_on_previous_text=False
)

print("Iniciando escrita da transcrição do vídeo editado...")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(f"Transcrição do Vídeo Editado: {Path(video_path).name}\n")
    f.write(f"Idioma: {info.language}\n\n")
    for segment in segments:
        line = f"[{segment.start:.2f}s -> {segment.end:.2f}s]: {segment.text}"
        print(line)
        f.write(line + "\n")

print(f"Concluído! Salvo em: {output_path}")
