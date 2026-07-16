import os
import sys
import json
import re
import subprocess
import requests
from pathlib import Path

# Configurações padrão do Servidor Local
API_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "gemma-4-E4B-it-Q4_K_M"
AIDER_EXE = r"C:\aider_env\Scripts\aider.exe"

def ask_gemma_local(system_prompt, prompt, try_json=False):
    """Envia requisição direta para o servidor llama.cpp/LM Studio local."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "openai/gemma-4",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    if try_json:
        # Alguns servidores locais aceitam response_format
        payload["response_format"] = {"type": "json_object"}
        
    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=90)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"⚠️ Erro do servidor local ({response.status_code}): {response.text}")
            return None
    except Exception as e:
        print(f"❌ Falha de conexão com o servidor local em {API_URL}: {e}")
        return None

def extract_json(text):
    """Extrai e valida um JSON de um bloco de texto que pode conter markdown."""
    if not text:
        return None
    # Procura por blocos de código markdown ```json ... ```
    match = re.search(r"```json(.*?)```", text, re.DOTALL)
    if match:
        content = match.group(1).strip()
    else:
        # Fallback para procurar a partir do primeiro '{' até o último '}'
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            content = text[start:end+1]
        else:
            content = text.strip()
    try:
        return json.loads(content)
    except Exception as e:
        print(f"⚠️ Erro ao decodificar JSON: {e}\nTexto original:\n{text}")
        return None

def create_tasks_markdown(project_dir, tasks):
    """Cria um arquivo task_local.md para o usuário acompanhar o progresso (estilo Antigravity)."""
    md_content = "# Plano de Desenvolvimento Local - Forge\n\n"
    md_content += "Este arquivo mostra o progresso do desenvolvimento sequencial do projeto.\n\n"
    for t in tasks:
        status = "[x]" if t.get("status") == "completed" else "[ ]"
        md_content += f"- {status} **Tarefa {t['id']}: {t['title']}**\n"
        md_content += f"  - **Arquivos**: {', '.join(t.get('files', []))}\n"
        md_content += f"  - **Descrição**: {t['description']}\n\n"
        
    with open(project_dir / "task_local.md", "w", encoding="utf-8") as f:
        f.write(md_content)

def run_aider_on_task(project_dir, task):
    """Invoca o Aider passando apenas os arquivos específicos da tarefa para economizar contexto."""
    print(f"\n==================================================")
    print(f"🚀 Executando Tarefa {task['id']}: {task['title']}")
    print(f"📁 Arquivos: {', '.join(task['files'])}")
    print(f"📝 Descrição: {task['description']}")
    print(f"==================================================")

    cmd = [
        AIDER_EXE,
        "--openai-api-base", "http://localhost:1234/v1",
        "--openai-api-key", "fake-key",
        "--model", "openai/gemma-4",
        "--yes"
    ]

    # Adiciona os arquivos à sessão do Aider para que o Gemma tenha apenas esse contexto
    for f in task.get("files", []):
        file_path = project_dir / f
        # Garante que o arquivo exista ou pelo menos o diretório pai exista
        file_path.parent.mkdir(exist_ok=True, parents=True)
        if not file_path.exists():
            # Cria arquivo vazio para o Aider conseguir adicionar
            with open(file_path, "w", encoding="utf-8") as empty_f:
                empty_f.write("")
        cmd.extend(["--file", str(file_path.resolve())])

    # Comando de teste automático se houver
    test_cmd = Path(project_dir) / "testar_imports.bat"
    if not test_cmd.exists():
        test_cmd = Path(r"C:\IA_dublagem\tools\testar_imports.bat")
    if test_cmd.exists():
        cmd.extend(["--test-cmd", str(test_cmd)])

    # Mensagem de instrução específica para a tarefa
    prompt_msg = (
        f"INSTRUÇÃO DA TAREFA:\n"
        f"Sua missão é realizar estritamente as alterações descritas abaixo.\n"
        f"Foque APENAS nesta tarefa e não tente criar outras funcionalidades.\n\n"
        f"Tarefa: {task['title']}\n"
        f"Descrição detalhada: {task['description']}\n"
    )
    cmd.extend(["--message", prompt_msg])

    try:
        # Executa em tempo real exibindo a saída no terminal do usuário
        process = subprocess.Popen(
            cmd,
            cwd=str(project_dir.resolve()),
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        process.wait()
        return process.returncode == 0
    except Exception as e:
        print(f"❌ Erro ao rodar o Aider: {e}")
        return False

def main():
    print("==================================================")
    print("      NEXUS LOCAL FORGE - AUTOMATION SYSTEM      ")
    print("        (Substituto Local do Antigravity)         ")
    print("==================================================")

    # 1. Verifica Aider e Conexão
    if not os.path.exists(AIDER_EXE):
        print(f"❌ Erro: Executável do Aider não encontrado em: {AIDER_EXE}")
        sys.exit(1)

    print("🔌 Testando comunicação com o Llama Server local na porta 1234...")
    teste = ask_gemma_local("Você é um assistente", "Diga 'OK'")
    if not teste:
        print("⚠️ Servidor não detectado. Iniciando servidor de IA local integrado (llama-cpp-python)...")
        # Inicia o servidor em um novo console
        creationflags = 0
        if os.name == 'nt':
            creationflags = subprocess.CREATE_NEW_CONSOLE
            
        import sys
        import time
        server_path = os.path.join(os.path.dirname(__file__), "tools", "run_local_server.py")
        # Fallback if running from a nested directory
        if not os.path.exists(server_path):
            server_path = os.path.join(os.path.dirname(__file__), "..", "tools", "run_local_server.py")
        subprocess.Popen([sys.executable, server_path], creationflags=creationflags)
        
        print("⏳ Aguardando inicialização do servidor...")
        for i in range(15):
            time.sleep(1)
            teste = ask_gemma_local("Você é um assistente", "Diga 'OK'")
            if teste:
                break
                
        if not teste:
            print("\n❌ ERRO: Não foi possível iniciar o servidor local automaticamente.")
            print("Certifique-se de carregar o modelo de IA ou iniciar o Llama Server manual na porta 1234.")
            sys.exit(1)
            
    print("✅ Servidor local conectado com sucesso!\n")

    # 2. Pasta do Projeto
    proj_input = input("📁 Digite o caminho da pasta do projeto (Enter para a pasta atual): ").strip()
    if not proj_input:
        project_dir = Path.cwd()
    else:
        project_dir = Path(proj_input)
    
    project_dir.mkdir(exist_ok=True, parents=True)
    print(f"📂 Diretório de trabalho: {project_dir.resolve()}")

    # 3. Verifica se há progresso salvo
    save_file = project_dir / "tasks_forge.json"
    tasks = []
    
    if save_file.exists():
        confirmar = input("💾 Encontrado plano de tarefas anterior. Deseja continuar dele? (S/N): ").strip().lower()
        if confirmar == 's':
            try:
                with open(save_file, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                print(f"📋 Retomando plano com {len(tasks)} tarefas carregadas.")
            except Exception as e:
                print(f"⚠️ Falha ao ler arquivo de progresso: {e}. Criando novo plano.")
    
    # 4. Criação de Novo Plano de Tarefas
    if not tasks:
        meta_prompt = input("\n💡 Qual o objetivo ou programa que você deseja construir localmente? ")
        if not meta_prompt:
            print("❌ Objetivo vazio. Encerrando.")
            sys.exit(0)

        planner_system = (
            "Você é o Nexus-Forge Planner (Gemma). Sua missão é receber o objetivo do usuário e criar um plano "
            "de desenvolvimento extremamente segmentado e modular em arquivos. Cada tarefa deve ser minúscula, "
            "focando em no máximo 1 ou 2 arquivos por vez, para que cada execução caiba em menos de 4.000 tokens.\n\n"
            "Você DEVE retornar OBRIGATORIAMENTE um objeto JSON contendo a lista de tarefas organizadas sequencialmente.\n"
            "As tarefas devem seguir dependências de baixo para cima (ex: arquivos de configuração e utilitários primeiro, lógica depois).\n\n"
            "Modelo de Retorno JSON:\n"
            "{\n"
            "  \"tasks\": [\n"
            "    {\n"
            "      \"id\": 1,\n"
            "      \"title\": \"Configurar banco de dados\",\n"
            "      \"description\": \"Crie a conexão sqlite e crie as tabelas necessárias no db.py\",\n"
            "      \"files\": [\"db.py\"]\n"
            "    },\n"
            "    {\n"
            "      \"id\": 2,\n"
            "      \"title\": \"Implementar lógica do usuário\",\n"
            "      \"description\": \"Crie funções para adicionar e autenticar usuários baseando-se no db.py\",\n"
            "      \"files\": [\"auth.py\", \"db.py\"]\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        print("\n🧠 [Planner - Gemma] Analisando objetivo e dividindo em subtarefas de baixo contexto...")
        planner_resp = ask_gemma_local(planner_system, f"Objetivo: {meta_prompt}")
        
        plan_data = extract_json(planner_resp)
        if not plan_data or "tasks" not in plan_data:
            print("❌ Falha na geração do plano de tarefas estruturado pela IA local. Tente simplificar o prompt.")
            sys.exit(1)
            
        tasks = plan_data["tasks"]
        # Marca todas como pendentes
        for t in tasks:
            t["status"] = "pending"
            
        # Salva o plano inicial
        with open(save_file, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=4)
        print(f"📋 Novo plano gerado com sucesso contendo {len(tasks)} tarefas!")

    # 5. Loop de Execução
    create_tasks_markdown(project_dir, tasks)
    
    for idx, task in enumerate(tasks):
        if task.get("status") == "completed":
            print(f"⏭️ Tarefa {task['id']} já concluída. Pulando.")
            continue

        # Executa a tarefa via Aider
        sucesso = run_aider_on_task(project_dir, task)
        
        if sucesso:
            print(f"✅ Tarefa {task['id']} executada com sucesso!")
            task["status"] = "completed"
            
            # Salva o progresso
            with open(save_file, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=4)
            create_tasks_markdown(project_dir, tasks)
            
            # Pergunta se quer pausar ou continuar
            if idx < len(tasks) - 1:
                resposta = input("\n[Menu] Pressione Enter para ir à próxima tarefa ou digite (P) para Pausar: ").strip().lower()
                if resposta == 'p':
                    print("⏸️ Execução pausada pelo usuário. Você pode retomar depois rodando o Forge novamente.")
                    break
        else:
            print(f"\n❌ A execução da Tarefa {task['id']} retornou um erro (linter ou teste falhou).")
            print("Você tem as seguintes opções:")
            print("(1) Tentar rodar a tarefa novamente (a IA receberá o prompt de novo)")
            print("(2) Corrigir o erro manualmente e marcar como concluída")
            print("(3) Pausar para inspecionar os arquivos")
            
            opcao = input("\nEscolha uma opção (1/2/3): ").strip()
            if opcao == "1":
                # Volta o índice do loop para tentar a mesma tarefa de novo
                # Como o loop for itera sobre 'tasks', vamos rodar uma recursão rápida ou apenas repetir
                print("🔄 Tentando novamente...")
                # Repete a execução manualmente fora do fluxo normal
                sucesso_retry = run_aider_on_task(project_dir, task)
                if sucesso_retry:
                    print(f"✅ Tarefa {task['id']} resolvida na re-tentativa!")
                    task["status"] = "completed"
                    with open(save_file, "w", encoding="utf-8") as f:
                        json.dump(tasks, f, indent=4)
                    create_tasks_markdown(project_dir, tasks)
                else:
                    print("❌ Falhou novamente. Pausando para segurança.")
                    break
            elif opcao == "2":
                print("📝 Marcada como concluída manualmente.")
                task["status"] = "completed"
                with open(save_file, "w", encoding="utf-8") as f:
                    json.dump(tasks, f, indent=4)
                create_tasks_markdown(project_dir, tasks)
            else:
                print("⏸️ Pausado. Inspecione o código e rode o Forge quando estiver pronto.")
                break

    # Verifica se concluímos tudo
    pendentes = [t for t in tasks if t["status"] == "pending"]
    if not pendentes:
        print("\n🎉 PARABÉNS! Todas as tarefas do plano foram executadas com sucesso.")
        # Limpa o arquivo de tarefas para não ficar incomodando na próxima execução do diretório
        if save_file.exists():
            save_file.unlink()
    else:
        print(f"\n🏁 Execução finalizada. Ainda restam {len(pendentes)} tarefas pendentes.")

if __name__ == "__main__":
    main()
