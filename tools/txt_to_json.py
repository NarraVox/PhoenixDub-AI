import re
import json
from pathlib import Path

txt_path = Path("C:/IA_dublagem/scratch/transcricao_video_editado_2.txt")
json_path = Path("C:/IA_dublagem/scratch/transcricao_video_editado_2.json")

if not txt_path.exists():
    print(f"Erro: {txt_path} não existe.")
    sys.exit(1)

segments = []
pattern = re.compile(r"\[([\d.]+)s -> ([\d.]+)s\]: (.*)")

with open(txt_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        match = pattern.match(line)
        if match:
            start = float(match.group(1))
            end = float(match.group(2))
            text = match.group(3).strip()
            segments.append({
                "start": start,
                "end": end,
                "text": text
            })

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(segments, f, ensure_ascii=False, indent=2)

print(f"Sucesso! JSON gerado em: {json_path} com {len(segments)} segmentos.")
