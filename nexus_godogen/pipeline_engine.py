import os
import json
import shutil
import subprocess
import requests
import time
from pathlib import Path

# ==========================================
# CONFIGURAÇÕES E CONSTANTES
# ==========================================
SETTINGS_FILE = "settings.json"
TEMPLATES_DIR = "templates"

class PipelineEngine:
    def __init__(self, projects_dir="projects"):
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(exist_ok=True)
        self.settings = self.load_settings()

    def load_settings(self):
        default_settings = {
            "godot_path": "godot",
            "gemini_api_key": os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", "")),
            "use_local_models": True,
            "planner_model_url": "http://localhost:1234/v1/chat/completions",
            "coder_model_url": "http://localhost:1234/v1/chat/completions",
            "planner_model_name": "Qwen3.5-4B-Q4_K_M",
            "coder_model_name": "qwen2.5-coder-3b-instruct"
        }
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_settings.update(data)
            except Exception as e:
                print(f"⚠️ Erro ao ler settings.json: {e}")
        return default_settings

    def save_settings(self):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4)

    def get_godot_path(self):
        # 1. Tenta pegar das configurações e valida se é arquivo
        path = self.settings.get("godot_path", "godot")
        if os.path.isfile(path):
            return path
        
        # 2. Tenta procurar em locais comuns no Windows do usuário
        username = os.environ.get("USERNAME", "Paulo Henrik")
        common_paths = [
            rf"C:\Users\{username}\Documents\Godot_v4.6.1-stable_win64.exe\Godot_v4.6.1-stable_win64.exe",
            rf"C:\Users\{username}\Downloads\Godot_v4.6.1-stable_win64.exe\Godot_v4.6.1-stable_win64.exe",
            rf"C:\Users\{username}\Documents\Godot_v4.6.1-stable_win64.exe",
            rf"C:\Users\{username}\Downloads\Godot_v4.6.1-stable_win64.exe",
            rf"C:\Users\{username}\Documents\Godot.exe"
        ]
        for p in common_paths:
            if os.path.isfile(p):
                # Salva nas configurações para acelerar futuras execuções
                self.settings["godot_path"] = p
                self.save_settings()
                return p
        
        # 3. Fallback para command line global
        return "godot"

    def setup_project_structure(self, game_name):
        """Cria as pastas do projeto e copia os templates iniciais."""
        proj_dir = self.projects_dir / game_name
        proj_dir.mkdir(exist_ok=True)
        
        # Pastas estruturais
        (proj_dir / "builders").mkdir(exist_ok=True)
        (proj_dir / "scripts").mkdir(exist_ok=True)
        (proj_dir / "assets").mkdir(exist_ok=True)
        (proj_dir / "scenes").mkdir(exist_ok=True)

        # Copiar project.godot base
        shutil.copy(Path(TEMPLATES_DIR) / "project.godot", proj_dir / "project.godot")
        
        # Copiar screenshot helper
        shutil.copy(Path(TEMPLATES_DIR) / "screenshot_helper.gd", proj_dir / "screenshot_helper.gd")

        return proj_dir

    def call_gemini(self, system_instruction, prompt):
        """Faz a chamada direta para a API do Gemini 1.5 Flash."""
        api_key = self.settings.get("gemini_api_key", "")
        if not api_key:
            raise ValueError("API Key do Gemini não configurada! Defina a variável GEMINI_API_KEY ou configure no settings.json")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            # Extrai o texto do JSON retornado pelo Gemini
            text_response = result["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text_response)
        except Exception as e:
            print(f"❌ Erro ao chamar a API do Gemini: {e}")
            if 'response' in locals() and response:
                print(f"Detalhes do erro: {response.text}")
            raise e

    def call_local_model(self, url, model_name, system_instruction, prompt, json_mode=False):
        """Faz requisições locais compatíveis com OpenAI (LM Studio / llama.cpp)."""
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"❌ Erro ao chamar modelo local ({model_name}) em {url}: {e}")
            raise e

    def get_or_create_blueprint(self, proj_dir, game_name, initial_prompt=""):
        blueprint_path = Path(proj_dir) / "game_blueprint.md"
        if blueprint_path.exists():
            try:
                with open(blueprint_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"⚠️ Erro ao ler blueprint: {e}")
                
        # Caso não exista, cria a estrutura inicial
        concept = initial_prompt if initial_prompt else "Não definido"
        content = f"""# Blueprint do Jogo: {game_name}

## 1. Conceito Geral
- **Ideia do Jogo**: {concept}
- **Estilo de Arte**: Estilizado / Low-Poly (otimizado para VRAM)

## 2. Estrutura de Arquivos Gerados
- `builders/build_main.gd`: Script Construtor de Cena principal.
- `scripts/player.gd`: Script de controle do jogador (exemplo padrão).

## 3. Estado de Desenvolvimento
- **Objetivo Atual**: Protótipo jogável inicial básico.
- **Marcos Concluídos**: Estrutura inicial do projeto configurada.
"""
        try:
            with open(blueprint_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"⚠️ Erro ao salvar blueprint inicial: {e}")
        return content

    def update_blueprint(self, proj_dir, game_name, file_list=None, current_objective=None):
        blueprint_path = Path(proj_dir) / "game_blueprint.md"
        if not blueprint_path.exists():
            self.get_or_create_blueprint(proj_dir, game_name)
            
        try:
            with open(blueprint_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            print(f"⚠️ Erro ao ler blueprint para atualização: {e}")
            return
            
        new_lines = []
        in_files_section = False
        
        for line in lines:
            # Se for a seção de arquivos, podemos atualizar
            if line.strip().startswith("## 2. Estrutura de Arquivos Gerados"):
                in_files_section = True
                new_lines.append(line)
                if file_list:
                    for f_name in file_list:
                        new_lines.append(f"- `{f_name}`: Gerado pelo assistente.\n")
                continue
            
            if in_files_section and line.strip().startswith("## "):
                in_files_section = False
                
            if in_files_section:
                # Pula as linhas antigas da seção de arquivos, pois as reinserimos acima
                continue
                
            # Se for o objetivo atual
            if current_objective and line.strip().startswith("- **Objetivo Atual**"):
                new_lines.append(f"- **Objetivo Atual**: {current_objective}\n")
                continue
                
            new_lines.append(line)
            
        try:
            with open(blueprint_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"⚠️ Erro ao salvar blueprint atualizado: {e}")

    def get_locked_files(self, game_name):
        config_path = self.projects_dir / game_name / "nexus_config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("locked_files", [])
            except Exception as e:
                print(f"⚠️ Erro ao ler nexus_config.json: {e}")
        return []

    def toggle_file_lock(self, game_name, relative_path):
        config_path = self.projects_dir / game_name / "nexus_config.json"
        locked_files = self.get_locked_files(game_name)
        
        # Certificar diretório existe
        config_path.parent.mkdir(exist_ok=True, parents=True)
        
        if relative_path in locked_files:
            locked_files.remove(relative_path)
            status = False
        else:
            locked_files.append(relative_path)
            status = True
            
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"locked_files": locked_files}, f, indent=4)
        except Exception as e:
            print(f"⚠️ Erro ao salvar nexus_config.json: {e}")
            raise e
            
        return status

    def generate_game_files(self, game_name, prompt):
        """Orquestra as IAs locais Gemma (Planner) e Qwen (Coder) para criar o jogo."""
        proj_dir = self.setup_project_structure(game_name)
        
        # Carrega os arquivos bloqueados (que não devem ser modificados)
        locked_files = self.get_locked_files(game_name)
        
        # Carrega ou cria o blueprint do jogo para passar como contexto
        blueprint_content = self.get_or_create_blueprint(proj_dir, game_name, prompt)
        
        # Ler os templates para enviar como contexto à IA
        with open(Path(TEMPLATES_DIR) / "scene_builder_template.gd", "r", encoding="utf-8") as f:
            scene_builder_tmpl = f.read()

        use_local = self.settings.get("use_local_models", True)
        
        # ==========================================
        # 1. FASE DE PLANEJAMENTO (Gemma - Planner)
        # ==========================================
        plan_system = f"""Você é o Nexus-Godogen Planner (Gemma).
Sua missão é receber a ideia de um jogo do usuário e planejar a arquitetura de arquivos na Godot 4.
Você deve retornar OBRIGATORIAMENTE um objeto JSON válido contendo a lista de arquivos a serem gerados.

CONTEXTO ATUAL DO PROJETO:
{blueprint_content}

Exemplo de resposta:
{{
  "files": [
    "builders/build_main.gd",
    "scripts/player.gd"
  ]
}}

REGRAS:
1. O arquivo 'builders/build_main.gd' é obrigatório. Ele gerará o cenário e montará a cena 'res://main.tscn'.
2. Adicione scripts em 'scripts/' para o comportamento do jogador, inimigos ou lógica, conforme o necessário."""

        plan_prompt = f"Planeje a estrutura de arquivos para o seguinte jogo: {prompt}"
        print("🧠 [Planner - Gemma] Planejando estrutura do jogo...")
        
        files_to_generate = ["builders/build_main.gd", "scripts/player.gd"] # Fallback padrão
        
        try:
            if use_local:
                plan_resp = self.call_local_model(
                    self.settings.get("planner_model_url"),
                    self.settings.get("planner_model_name"),
                    plan_system,
                    plan_prompt,
                    json_mode=True
                )
                plan_data = json.loads(plan_resp)
            else:
                gemini_sys = plan_system + "\nRetorne no formato JSON indicado."
                plan_data = self.call_gemini(gemini_sys, plan_prompt)
                
            if "files" in plan_data:
                files_to_generate = plan_data["files"]
                print(f"📋 [Planner] Lista de arquivos a criar: {files_to_generate}")
        except Exception as e:
            print(f"⚠️ Falha no planejamento automático. Usando fallback padrão: {files_to_generate}. Erro: {e}")

        # ==========================================
        # 2. FASE DE CODIFICAÇÃO (Qwen - Coder)
        # ==========================================
        generated_files = []
        import re
        
        for filepath in files_to_generate:
            if filepath in locked_files:
                print(f"🔒 [Coder] Arquivo protegido: {filepath} está bloqueado. Pulando escrita para proteger gameplay.")
                generated_files.append(filepath)
                continue
                
            print(f"✍️ [Coder - Qwen] Escrevendo arquivo: {filepath}...")
            is_builder = filepath.startswith("builders/")
            
            if is_builder:
                coder_system = f"""Você é o Nexus-Godogen Coder (Qwen).
Sua missão é escrever o código de um Scene Builder para a Godot 4.
O script DEVE herdar de SceneTree (extends SceneTree), usar _init() para construir o cenário e chamar quit() no fim.
Você deve retornar APENAS o código GDScript final dentro de um bloco de código markdown (```gdscript ... ```). Não escreva textos ou explicações.

CONTEXTO DO JOGO:
{blueprint_content}

Use este template de SceneTree como base obrigatória para instanciamento de nós e salvamento de cena:
{scene_builder_tmpl}"""
            else:
                coder_system = f"""Você é o Nexus-Godogen Coder (Qwen).
Sua missão é escrever o script GDScript para controle de gameplay (ex: jogador, inimigo ou pontuação) na Godot 4.
O script deve herdar do nó apropriado (ex: CharacterBody3D para o jogador, Area3D para itens).
Você deve retornar APENAS o código GDScript final dentro de um bloco de código markdown (```gdscript ... ```). Não escreva textos ou explicações.

CONTEXTO DO JOGO:
{blueprint_content}"""

            coder_prompt = f"Escreva o código do arquivo '{filepath}' para o seguinte jogo: {prompt}. Lembre-se de usar apenas a sintaxe da Godot 4."
            
            try:
                if use_local:
                    code_resp = self.call_local_model(
                        self.settings.get("coder_model_url"),
                        self.settings.get("coder_model_name"),
                        coder_system,
                        coder_prompt
                    )
                else:
                    gemini_sys = coder_system + "\nRetorne um objeto JSON no formato: {{ \"code\": \"código aqui\" }}"
                    gemini_resp = self.call_gemini(gemini_sys, coder_prompt)
                    code_resp = gemini_resp.get("code", "")
                
                # Extrair código do bloco markdown
                code_match = re.search(r"```gdscript(.*?)```", code_resp, re.DOTALL)
                if code_match:
                    code_content = code_match.group(1).strip()
                else:
                    # Fallback limpo (remove tags se existirem)
                    code_content = code_resp.replace("```gdscript", "").replace("```", "").strip()
                    
                # Gravar arquivo
                file_path = proj_dir / filepath
                file_path.parent.mkdir(exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(code_content)
                generated_files.append(filepath)
                print(f"✅ Arquivo salvo: {filepath}")
            except Exception as e:
                print(f"❌ Erro ao gerar o arquivo {filepath}: {e}")
                
        # Atualiza o blueprint final com os arquivos criados
        self.update_blueprint(proj_dir, game_name, file_list=generated_files, current_objective="Arquivos de código criados. Pronto para compilação e teste.")

        # ==========================================
        # 3. FASE DE REFINAMENTO (Aider)
        # ==========================================
        non_locked_files = [f for f in generated_files if f not in locked_files]
        if not non_locked_files:
            print("🔒 [Aider] Todos os arquivos gerados estão bloqueados. Pulando fase de refinamento.")
            return proj_dir, generated_files
            
        aider_exe = r"C:\aider_env\Scripts\aider.exe"
        if os.path.exists(aider_exe):
            print("🚀 [Aider] Iniciando refinação e polimento dos scripts gerados...")
            aider_cmd = [
                aider_exe,
                "--openai-api-base", "http://localhost:1234/v1",
                "--openai-api-key", "fake-key",
                "--model", "openai/qwen-3.5",
            ]
            
            # Adiciona apenas os arquivos não bloqueados à sessão de chat do Aider
            for f in non_locked_files:
                aider_cmd.extend(["--file", f])
                
            aider_prompt = f"Revise e melhore os scripts na pasta 'scripts/' para o jogo: {prompt}. Otimize a movimentação, lógica de colisão e garanta sintaxe válida para Godot 4."
            if locked_files:
                aider_prompt += f" IMPORTANTE: Não altere de forma alguma os seguintes arquivos protegidos: {', '.join(locked_files)}."
                
            aider_cmd.extend([
                "--message", aider_prompt,
                "--yes"
            ])
            
            try:
                # Rodamos o Aider com timeout de 90 segundos para evitar travar se a IA entrar em loop
                result = subprocess.run(aider_cmd, cwd=proj_dir, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=90)
                print(f"=== LOG DO AIDER (REFINAÇÃO) ===\n{result.stdout}\n===============================")
            except subprocess.TimeoutExpired:
                print("⚠️ Aider excedeu o tempo limite na refinação.")
            except Exception as e:
                print(f"❌ Erro ao rodar Aider na refinação: {e}")
        else:
            print("⚠️ Aider não encontrado em C:\\aider_env\\Scripts\\aider.exe. Pulando fase de polimento.")
                
        return proj_dir, generated_files

    def run_scene_builder(self, proj_dir):
        """Executa o Script da Godot para compilar a cena .tscn."""
        godot_exe = self.get_godot_path()
        abs_proj_dir = os.path.abspath(proj_dir)
        
        print("⚙️ [Godot] Executando Scene Builder...")
        
        # Comando para rodar o Script de cena headlessly
        cmd = [
            godot_exe,
            "--headless",
            "--path", abs_proj_dir,
            "-s", "res://builders/build_main.gd"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=30)
            print(f"=== LOG DA GODOT (BUILD) ===\n{result.stdout}\n============================")
            if result.stderr:
                print(f"⚠️ Erros reportados:\n{result.stderr}")
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Erro ao executar Godot Scene Builder: {e}")
            return False

    def verify_game_visually(self, proj_dir):
        """Roda o jogo temporariamente com o AutoLoad de captura de tela e valida."""
        godot_exe = self.get_godot_path()
        abs_proj_dir = os.path.abspath(proj_dir)
        project_godot_path = os.path.join(abs_proj_dir, "project.godot")
        
        # 1. Injeta o AutoLoad do ScreenshotHelper temporariamente
        with open(project_godot_path, "a", encoding="utf-8") as f:
            f.write("\n[autoload]\nScreenshotHelper=\"*res://screenshot_helper.gd\"\n")
            
        print("🎮 [Godot] Iniciando validação visual (screenshot loop)...")
        
        # 2. Executa o jogo (sem --headless para renderizar o viewport e tirar a foto)
        cmd = [
            godot_exe,
            "--path", abs_proj_dir
        ]
        
        try:
            # Godot fechará sozinha por causa do ScreenshotHelper
            subprocess.run(cmd, timeout=15)
        except subprocess.TimeoutExpired:
            print("⚠️ A execução da Godot excedeu o tempo limite e foi encerrada.")
        except Exception as e:
            print(f"❌ Falha ao rodar verificação visual: {e}")
            
        # 3. Limpa o AutoLoad do project.godot para não rodar em jogadas manuais
        if os.path.exists(project_godot_path):
            with open(project_godot_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            clean_lines = []
            skip = False
            for line in lines:
                if "[autoload]" in line:
                    skip = True
                    continue
                if skip and 'ScreenshotHelper=' in line:
                    skip = False
                    continue
                clean_lines.append(line)
                
            with open(project_godot_path, "w", encoding="utf-8") as f:
                f.writelines(clean_lines)

        # 4. Verifica se a screenshot foi gerada
        screenshot_path = os.path.join(abs_proj_dir, "screenshot.png")
        if os.path.exists(screenshot_path):
            print("✅ [Validation] Visual validado com sucesso! Imagem salva.")
            return True
        else:
            print("❌ [Validation] Erro: A imagem de screenshot.png não foi encontrada.")
            return False
