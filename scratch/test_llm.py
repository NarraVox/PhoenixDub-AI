import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from llama_cpp import Llama

model_path = "C:/IA_dublagem/_MODELS_/gemma-4-E4B-it-Q4_K_M.gguf"
if not Path(model_path).exists():
    print("Model not found")
    sys.exit(1)

print("Loading LLM...")
llm = Llama(
    model_path=model_path,
    n_gpu_layers=43,
    n_ctx=2048,
    verbose=False
)

txt_en_list = [
    "Dad dad please dad please don't leave me dad please no",
    "Thank god you're alive",
    "It's just a small scratch I'll be okay"
]

for txt_en in txt_en_list:
    prompt_tradutor = (
        f"Traduza o seguinte texto do Inglês ou do Russo para o Português Brasileiro: \"{txt_en}\"\n"
        "REGRA 1: Se você mantiver termos em inglês ou russo, coloque-os entre aspas simples.\n"
        "REGRA 2: Se o texto já estiver em Português Brasileiro, apenas repita o texto exatamente como ele está.\n"
        "REGRA 3: Não explique o texto, não adicione legendas explicativas, e não escreva análises. Responda APENAS com a tradução limpa.\n"
        "Tradução:"
    )
    
    print("\n" + "="*40)
    print(f"INPUT: {txt_en}")
    
    # Test 1: with stop=["\n\n"]
    out_trad = llm(prompt_tradutor, max_tokens=256, temperature=0.1, stop=["\n\n", "EN:", "###"])
    raw_1 = out_trad['choices'][0]['text']
    print(f"TEST 1 (stop=[\\n\\n]) RAW: {repr(raw_1)}")
    
    # Test 2: without stop
    out_trad_2 = llm(prompt_tradutor, max_tokens=256, temperature=0.1)
    raw_2 = out_trad_2['choices'][0]['text']
    print(f"TEST 2 (no stop) RAW: {repr(raw_2)}")
