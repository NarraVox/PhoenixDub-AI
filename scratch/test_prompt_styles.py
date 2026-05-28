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
    "Thank god you're alive",
    "It's just a small scratch I'll be okay",
    "IA initiate AI transfer sequence"
]

for txt_en in txt_en_list:
    print("\n" + "="*50)
    print(f"INPUT: {txt_en}")
    
    # 1. Simple Prompt
    prompt_1 = f"Translate from English to Brazilian Portuguese: {txt_en}\nTranslation:"
    out_1 = llm(prompt_1, max_tokens=100, temperature=0.1)
    print(f"STYLE 1 (Simple) RAW: {repr(out_1['choices'][0]['text'])}")
    
    # 2. Gemma Chat Instruct Template
    prompt_2 = (
        "<start_of_turn>user\n"
        "Você é um tradutor profissional de filmes. "
        "Traduza o seguinte texto do Inglês para o Português Brasileiro de forma natural. "
        "Responda APENAS com a tradução limpa, sem aspas extras, sem explicações e sem justificativas.\n"
        f"Texto: \"{txt_en}\"<end_of_turn>\n"
        "<start_of_turn>model\n"
    )
    out_2 = llm(prompt_2, max_tokens=100, temperature=0.1)
    print(f"STYLE 2 (Instruct Template) RAW: {repr(out_2['choices'][0]['text'])}")
    
    # 3. Current prompt style
    prompt_3 = (
        f"Traduza o seguinte texto do Inglês ou do Russo para o Português Brasileiro: \"{txt_en}\"\n"
        "REGRA 1: Se você mantiver termos em inglês ou russo, coloque-os entre aspas simples.\n"
        "REGRA 2: Se o texto já estiver em Português Brasileiro, apenas repita o texto exatamente como ele está.\n"
        "REGRA 3: Não explique o texto, não adicione legendas explicativas, e não escreva análises. Responda APENAS com a tradução limpa.\n"
        "Tradução:"
    )
    out_3 = llm(prompt_3, max_tokens=100, temperature=0.1)
    print(f"STYLE 3 (Current) RAW: {repr(out_3['choices'][0]['text'])}")
