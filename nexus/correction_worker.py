"""Executa TTS em processo próprio e libera a GPU ao terminar."""
import json
from pathlib import Path
import sys


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    from nexus.core.system_guard import check_system_safety
    check_system_safety()
    from nexus.core.tts import gerar_audio_qwen3
    # O orçamento do motor acompanha textos longos; a janela original é
    # usada depois, apenas para ajustar a velocidade até o teto de 1,20x.
    generation_window = max(request['duration'], len(request['text']) / 18)
    ok = gerar_audio_qwen3(text=request["text"], ref_audio_path=request["reference"],
                          output_path=request["output"], language="Portuguese",
                          emotion=request.get("emotion", "NORMAL"), max_duration=generation_window)
    if not ok:
        raise RuntimeError("O motor Qwen3 não conseguiu gerar a voz.")


if __name__ == "__main__":
    main()
