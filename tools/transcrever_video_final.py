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

# Forçar DLLs da NVIDIA para garantir execução CUDA
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

import glob
matching_files = glob.glob("C:/Users/Paulo Henrik/Videos/*editado.mp4")
if not matching_files:
    raise FileNotFoundError("Não foi possível encontrar o arquivo de vídeo editado na pasta Videos.")
video_path = matching_files[0]
scratch_dir = Path("C:/IA_dublagem/scratch")
scratch_dir.mkdir(exist_ok=True)
output_txt = scratch_dir / "transcricao_video_final_editado.txt"

print("Inicializando o modelo Whisper 'small'...")
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "int8_float16" if device == "cuda" else "int8"
print(f"Dispositivo selecionado: {device} | Tipo de computação: {compute_type}")

model = WhisperModel("small", device=device, compute_type=compute_type)

print(f"\n--- Iniciando transcrição de {Path(video_path).name} ---")
try:
    segments, info = model.transcribe(
        video_path,
        language="pt",
        beam_size=1,
        condition_on_previous_text=False
    )
    
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(f"Transcrição do Vídeo Final Editado: {Path(video_path).name}\n")
        f.write(f"Idioma detectado: {info.language} (probabilidade: {info.language_probability:.2f})\n\n")
        for segment in segments:
            line = f"[{segment.start:.2f}s -> {segment.end:.2f}s]: {segment.text}"
            print(line)
            f.write(line + "\n")
    print(f"Concluído! Salvo em: {output_txt}")
except Exception as e:
    print(f"Erro ao transcrever o vídeo final: {e}")
