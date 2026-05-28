import sys
import os
from pathlib import Path

# Add parent dir to sys.path
sys.path.append(str(Path(__file__).parent.parent))

import nexus_core as core

def test():
    print("Carregando motor Gemma...")
    engine = core.get_local_gemma_engine()
    if not engine:
        print("Erro: nao foi possivel carregar o motor Gemma local.")
        return

    test_batch = [
        {
            "id": "seg_test_1", 
            "text": "I need you to tell me everything that happened.", 
            "speaker": "voz_SPEAKER_01", 
            "start": 0.0, 
            "end": 1.8 # dur = 1.8s, limit = 28
        },
        {
            "id": "seg_test_2", 
            "text": "Are you out of your mind?", 
            "speaker": "voz_SPEAKER_02", 
            "start": 10.0, 
            "end": 11.0 # dur = 1.0s, limit = 16
        },
        {
            "id": "seg_test_3", 
            "text": "We have to get out of here right now!", 
            "speaker": "voz_SPEAKER_01", 
            "start": 20.0, 
            "end": 21.5 # dur = 1.5s, limit = 24
        }
    ]

    context = "Dois personagens em uma situacao de extrema urgencia e perigo em uma nave."

    print("Traduzindo lote com limites dinamicos de 16 CPS...")
    results = core._process_with_local_engine(engine, test_batch, context, {}, "pt")
    
    print("\nResultados da Traducao (Geral sem exemplos explicitos):")
    print("=" * 70)
    for seg in test_batch:
        res = results.get(seg["id"])
        dur = seg["end"] - seg["start"]
        limit = max(12, int(dur * 16.0))
        print(f"EN: {seg['text']}")
        if res:
            text_pt = res['text']
            cps = len(text_pt) / dur
            print(f"PT: {text_pt}")
            print(f"Letras: {len(text_pt)} | Limite Permitido: {limit} | CPS Efetivo: {cps:.1f}")
            print(f"Emocao: {res['emotion']}")
        else:
            print("PT: FALHOU")
        print("-" * 70)

if __name__ == "__main__":
    test()
