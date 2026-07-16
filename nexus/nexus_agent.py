import os
import sys
import json
import requests
from pathlib import Path

# Configurações do Servidor Local de IA
API_URL = "http://localhost:1234/v1/chat/completions"
HEADERS = {"Content-Type": "application/json"}

def ask_gemma(prompt, system_prompt="Você é um assistente de programação útil."):
    """Envia uma requisição para o servidor local do Gemma."""
    payload = {
        "model": "openai/gemma-4",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    try:
        response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Erro do Servidor: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Falha na conexão com o servidor local (certifique-se de que o bat do servidor está rodando): {e}"

def chunk_file(file_path, chunk_size=150, overlap=30):
    """Lê o arquivo e divide em linhas com sobreposição."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    chunks = []
    total_lines = len(lines)
    start = 0
    while start < total_lines:
        end = min(start + chunk_size, total_lines)
        chunk_lines = lines[start:end]
        chunks.append({
            "start_line": start + 1,
            "end_line": end,
            "content": "".join(chunk_lines),
            "lines": chunk_lines
        })
        if end == total_lines:
            break
        start += (chunk_size - overlap)
    return chunks, lines

def scan_file_for_query(file_path, query, mode="explicar"):
    """Varre o arquivo segmento por segmento usando o Gemma."""
    print(f"\n🔍 [Agente] Carregando e fatiando {Path(file_path).name}...")
    chunks, original_lines = chunk_file(file_path)
    total_chunks = len(chunks)
    print(f"📦 [Agente] Arquivo dividido em {total_chunks} segmentos.")
    
    found_segments = []
    
    for idx, chunk in enumerate(chunks):
        print(f"⏳ Analisando segmento {idx+1}/{total_chunks} (Linhas {chunk['start_line']} a {chunk['end_line']})...", end="\r")
        
        system_prompt = (
            "Você é um analisador de código estrito. Sua tarefa é responder se o trecho de código fornecido "
            "contém o assunto ou a função solicitada pelo usuário. Responda estritamente iniciando com 'SIM' ou 'NÃO', "
            "seguido de uma justificativa muito curta de 1 frase."
        )
        
        prompt = (
            f"O usuário quer: {query}\n\n"
            f"Analise o seguinte trecho de código (Linhas {chunk['start_line']} a {chunk['end_line']}):\n"
            f"```python\n{chunk['content']}\n```"
        )
        
        veredicto = ask_gemma(prompt, system_prompt)
        
        if "SIM" in veredicto.upper() or "FOUND" in veredicto.upper():
            print(f"\n✨ [Agente] Encontrado contexto relevante no Segmento {idx+1}!")
            print(f"📝 Justificativa da IA: {veredicto}")
            found_segments.append((idx, chunk))
            
            # Pergunta o que fazer
            opcao = input("\n[Opções] (1) Explicar trecho (2) Editar trecho (3) Continuar procurando: ")
            
            if opcao == "1":
                # Modo Explicação
                print("\n🧠 [Gemma] Explicando o trecho:\n")
                explicacao_prompt = f"Explique o funcionamento detalhado do seguinte trecho de código em português:\n\n```python\n{chunk['content']}\n```"
                print(ask_gemma(explicacao_prompt))
                input("\nPressione Enter para continuar a busca...")
            
            elif opcao == "2":
                # Modo Edição
                instrucao = input("\n✍️ Digite as alterações que você quer fazer nesse trecho: ")
                print("\n⚙️ [Gemma] Gerando alteração para este segmento...")
                
                edit_system_prompt = (
                    "Você é um refatorador de código. Reescreva o trecho de código fornecido aplicando as alterações solicitadas. "
                    "ATENÇÃO: Mantenha as mesmas assinaturas e lógica geral, alterando apenas o necessário. "
                    "Retorne APENAS o código Python atualizado dentro de uma tag de código ```python ... ```, sem texto adicional antes ou depois."
                )
                
                edit_prompt = (
                    f"Código Original (Linhas {chunk['start_line']} a {chunk['end_line']}):\n"
                    f"```python\n{chunk['content']}\n```\n\n"
                    f"Instrução de Alteração: {instrucao}"
                )
                
                novo_codigo = ask_gemma(edit_prompt, edit_system_prompt)
                
                # Extrai o código de dentro das tags markdown
                if "```python" in novo_codigo:
                    novo_codigo = novo_codigo.split("```python")[1].split("```")[0]
                elif "```" in novo_codigo:
                    novo_codigo = novo_codigo.split("```")[1].split("```")[0]
                
                print("\n📝 [Código Proposto]:\n")
                print(novo_codigo)
                
                confirmar = input("\n💾 Deseja aplicar essa alteração no arquivo real? (S/N): ")
                if confirmar.lower() == 's':
                    # Aplica a alteração nas linhas originais
                    novas_linhas = [line + "\n" for line in novo_codigo.strip().splitlines()]
                    
                    # Substitui as linhas no array original
                    slice_start = chunk['start_line'] - 1
                    slice_end = chunk['end_line']
                    
                    original_lines[slice_start:slice_end] = novas_linhas
                    
                    # Grava de volta no arquivo
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.writelines(original_lines)
                    
                    print("✅ Arquivo atualizado com sucesso! Salvando alterações.")
                    break
            
            elif opcao == "3":
                continue
    
    print("\n🏁 [Agente] Busca concluída.")

if __name__ == "__main__":
    print("==================================================")
    print("      NEXUS SEGMENT AGENT - MOTOR LOCAL GEMMA      ")
    print("==================================================")
    
    # Verifica se o servidor local está de fato ativo
    teste = ask_gemma("Oi", "Responda apenas 'Olá'")
    if "Falha na conexão" in teste:
        print("\n❌ ERRO: O servidor local do Gemma não está respondendo.")
        print("Certifique-se de que o arquivo 'ABRIR_AIDER_LOCAL.bat' está rodando.")
        sys.exit(1)
        
    arquivo = input("📁 Caminho do arquivo a ser analisado (ex: nexus_core.py): ").strip()
    if not arquivo:
        arquivo = "nexus_core.py"
        
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo '{arquivo}' não encontrado.")
        sys.exit(1)
        
    pergunta = input("💡 O que você deseja procurar, entender ou editar no código? ")
    if pergunta:
        scan_file_for_query(arquivo, pergunta)
