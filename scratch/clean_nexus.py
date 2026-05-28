
import sys
from pathlib import Path

file_path = Path(r"c:\IA_dublagem\nexus_core.py")

if not file_path.exists():
    print("Arquivo não encontrado!")
    sys.exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Localiza o início da função master
start_idx = -1
for i, line in enumerate(lines):
    if "def transcrever_e_diarizar" in line:
        start_idx = i
        break

if start_idx == -1:
    print("Função não encontrada!")
    sys.exit(1)

# Mantém as primeiras 6849 linhas (até antes da função)
clean_lines = lines[:start_idx]

# Adiciona a versão definitiva e limpa da função
new_code = [
    'def transcrever_e_diarizar(audio_path, job_dir=None, cb=None, source_lang="auto"):\n',
    '    """[v2026.SYNC_ELITE] Diarização -> Whisper."""\n',
    '    cleanup_on_exit() \n',
    '    if not Path(audio_path).exists(): return []\n',
    '    \n',
    '    if cb: cb(10, 1, "[Diarização] Mapeando vozes originais...")\n',
    '    diarization_segments = []\n',
    '    try:\n',
    '        diarizer = PyannoteDiarizer(device="cuda" if torch.cuda.is_available() else "cpu")\n',
    '        annotation = diarizer.diarize(audio_path, progress_cb=cb)\n',
    '        if annotation:\n',
    '            for segment, _, speaker in annotation.itertracks(yield_label=True):\n',
    '                diarization_segments.append({\'start\': segment.start, \'end\': segment.end, \'speaker\': f"voz_{speaker}"})\n',
    '    except Exception as e:\n',
    '        logging.error(f"Erro Diarização: {e}")\n',
    '\n',
    '    if cb: cb(50, 1, "[Whisper AI] Transcrevendo falas detectadas...")\n',
    '    w_model = get_whisper_model()\n',
    '    whisper_lang = source_lang if source_lang != "auto" else None\n',
    '    \n',
    '    results = []\n',
    '    for i, d_seg in enumerate(diarization_segments):\n',
    '        try:\n',
    '            res = w_model.transcribe(str(audio_path), clip_timestamps=[d_seg[\'start\'], d_seg[\'end\']], language=whisper_lang, beam_size=1)\n',
    '            text = "".join([s.text for s in res[0]])\n',
    '            text = text.replace("A seguir uma dublagem profissional, sem gagueira e sem cortes bruscos.", "").strip()\n',
    '            if text and len(text) > 2:\n',
    '                results.append({\n',
    '                    "id": f"seg_{len(results)}",\n',
    '                    "start": max(0, d_seg[\'start\'] - 0.1),\n',
    '                    "end": d_seg[\'end\'] + 0.3,\n',
    '                    "text": text,\n',
    '                    "speaker": d_seg[\'speaker\']\n',
    '                })\n',
    '        except: continue\n',
    '        if cb: cb(50 + (i / len(diarization_segments) * 45), 1, f"[Whisper] {i+1}/{len(diarization_segments)}")\n',
    '\n',
    '    if job_dir:\n',
    '        job_dir = Path(job_dir)\n',
    '        with open(job_dir / "transcription.json", "w", encoding="utf-8") as f:\n',
    '            json.dump(results, f, ensure_ascii=False, indent=4)\n',
    '            \n',
    '    return results\n',
    '\n',
    'def gerar_audio_chatterbox(text, prompt_audio, output_path, language_id="pt", **kwargs):\n',
    '    """Ponte Chatterbox com proteção de VRAM."""\n',
    '    if not ensure_vram_safety("Chatterbox"): return False\n',
    '    tts = get_chatterbox_model()\n',
    '    if not tts or not os.path.exists(str(prompt_audio)): return False\n',
    '    try:\n',
    '        import re, soundfile as sf\n',
    '        from concurrent.futures import ThreadPoolExecutor\n',
    '        clean_text = re.sub(r\'[^\\w\\s.,!?\\\'"-]\', "", text).strip()\n',
    '        wav = tts.generate(clean_text, language_id=language_id, audio_prompt_path=str(prompt_audio), temperature=0.50, inference_steps=35)\n',
    '        if not hasattr(get_chatterbox_model, "_writer_pool"):\n',
    '            get_chatterbox_model._writer_pool = ThreadPoolExecutor(max_workers=2)\n',
    '        wav_data = wav.cpu().numpy().squeeze()\n',
    '        get_chatterbox_model._writer_pool.submit(lambda p, d: sf.write(str(p), d, 24000), output_path, wav_data)\n',
    '        return True\n',
    '    except Exception as e:\n',
    '        logging.error(f"Erro Chatterbox: {e}"); return False\n',
    '\n',
    'if __name__ == "__main__":\n',
    '    check_ffmpeg()\n',
    '    host, port = "0.0.0.0", 5001\n',
    '    url = f"http://127.0.0.1:{port}"\n',
    '    import threading\n',
    '    def open_browser():\n',
    '        import time; time.sleep(1.5)\n',
    '        import webbrowser\n',
    '        webbrowser.open_new(url)\n',
    '    threading.Thread(target=open_browser).start()\n',
    '    app.run(host=host, port=port, debug=False, threaded=True)\n',
    '\n',
    'import atexit\n',
    'atexit.register(cleanup_on_exit)\n'
]

clean_lines.extend(new_code)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(clean_lines)

print("✅ nexus_core.py LIMPO E REESTRUTURADO!")
