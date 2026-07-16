# 👨‍💻 Guia do Desenvolvedor — NarraVox Studios Premium

Este documento serve como guia de boas práticas, convenções e arquitetura interna para qualquer desenvolvedor (humano ou IA) que venha integrar, depurar ou expandir o sistema NarraVox. O objetivo é manter a coesão técnica e funcional em todos os módulos.

---

## 📂 1. Estrutura de Pastas

```
C:/IA_dublagem/
├── nexus/                      ← Código-fonte principal
│   ├── nexus_app.py            ← Hub Central (Launcher + Porta 5000)
│   ├── core/                   ← Inteligência: IA, Áudio, Orquestração
│   │   ├── orchestrator_jobs_games.py
│   │   ├── orchestrator_jobs_core.py
│   │   ├── model_loader.py     ← Ciclo de vida dos modelos de IA
│   │   ├── translation.py      ← Motor de Tradução Consolidado
│   │   ├── tts.py              ← Motor Qwen3-TTS
│   │   ├── whisper.py          ← Motor faster-whisper
│   │   ├── vocals.py           ← OpenUnmix / DeepFilterNet
│   │   ├── diarization.py      ← Pyannote 3.1 & Clustering
│   │   └── utils.py            ← Utilitários de I/O, áudio, sistema, telemetry
│   ├── dub/                    ← Motores de Dublagem (Jogos + Vídeo)
│   │   └── dubbing.py          ← Servidor e Pipeline Consolidado (Porta 5002 / 5004)
│   ├── dj/                     ← Motor Vortex DJ (Porta 5005)
│   │   └── vortex_dj.py
│   ├── editor/                 ← Motor Vortex Editor (Porta 5003)
│   │   └── narravox_editor.py
│   ├── cine/                   ← Motor Cine-Gen (Porta 5006 alt.)
│   │   └── nexus_cine_gen.py
│   └── client/                 ← UI (HTML/CSS/JS — Servidas pelo Hub)
│       ├── nexus_premium.html  ← Hub Principal
│       ├── games_studio.html   ← Estúdio de Jogos
│       ├── video_studio.html   ← Estúdio de Vídeo
│       ├── dj_studio.html      ← Estúdio DJ
│       └── vortex_editor.html  ← Editor Criativo
├── nexus_godogen/              ← Módulo Experimental Godogen
├── _MODELS_/                   ← Modelos de IA (GGUF, Qwen3, etc.)
├── uploads/                    ← Projetos e arquivos de trabalho
│   ├── [job_id]/               ← Pasta de projeto individual
│   │   ├── job_status.json     ← Status em tempo real
│   │   ├── project_data.json   ← Dados mestre de transcrição/tradução
│   │   ├── _1_MOVER_OS_FICHEIROS_DAQUI/  ← Áudios de entrada (jogos)
│   │   ├── _2_PARA_AS_PASTAS_DE_VOZ/     ← Áudios separados por falante
│   │   ├── _backup_transcricao/          ← Cache de transcrições
│   │   ├── _backup_texto_final/          ← Cache de traduções (1 JSON por seg.)
│   │   ├── _dubbed_audio/                ← Áudios dublados (jogos)
│   │   └── _saida_final/                 ← Saída final mixada
│   └── dj_projects/            ← Projetos do Vortex DJ
├── docs/documentação/          ← Documentação do projeto (AQUI)
├── env/                        ← Ambiente Python isolado
└── requirements.txt            ← Dependências do projeto
```

> **Regra de Ouro de Diretórios:**  
> Código de produção vai em `nexus/*`. Protótipos, testes e scripts auxiliares vão em `scratch/`. A pasta `nexus_godogen/` tem seu próprio ciclo de vida.

---

## 🚀 2. Como Executar o Sistema

O sistema é iniciado pelo arquivo `nexus_app.py`:

```bash
cd C:/IA_dublagem
python -m nexus.nexus_app
# OU via o arquivo .bat
TESTAR_AGORA.bat
```

O Hub sobe na porta 5000 e a janela do PyWebView abre automaticamente. Os motores restantes são iniciados **sob demanda** (lazy loading) quando o usuário navega para o estúdio correspondente.

### Portas do Sistema

| Motor | Porta | Quando Ativa |
|---|---|---|
| Hub Central | 5000 | Sempre |
| Titan Games | 5002 | Ao acessar games_studio.html |
| Vortex Editor | 5003 | Ao acessar vortex_editor.html |
| Titan Video | 5004 | Ao acessar video_studio.html |
| Vortex DJ | 5005 | Ao acessar dj_studio.html |
| Docs | 5006 | Ao acessar nexus_docs.html |

---

## ✨ 3. Como Adicionar Novos Módulos

Para adicionar uma nova funcionalidade ao core oficial:

1. **Planejamento:**
   - Documente o propósito, inputs, outputs e regras em `BUSINESS_RULES.md`.
   - Registre o novo módulo em `PROJECT_SCOPE.md`.

2. **Criação do Servidor Flask:**
   - Crie o arquivo em `nexus/[novo_modulo]/`.
   - Implemente as rotas `/api/health` e `/api/is_busy` obrigatoriamente (são usadas pelo Hub para gerenciamento de ciclo de vida).

3. **Registro no Hub (`nexus_app.py`):**
   - Adicione o motor ao dicionário `active_engines` com porta única.
   - Crie a página HTML em `nexus/client/`.
   - Mapeie a página ao motor no dicionário `page_to_engine`.

4. **Integração com o Core:**
   - Importe o `nexus.core` como `core` para acessar modelos e utilitários.
   - Use `core.safe_json_read/write` para persistência.
   - Use `core.get_optimal_device()` para detecção de hardware.

5. **Testes:**
   - Teste o isolamento de VRAM: rode o módulo sozinho e verifique se os modelos são carregados e descarregados corretamente.

---

## 🔗 4. Comunicação entre Componentes

- **Fluxo Centralizado:** Todo pipeline principal é orquestrado por serviços dentro de `nexus/core/`. Um motor Flask chama o orquestrador, que chama os serviços individuais.
- **Modelos Compartilhados via Globals:** Os modelos de IA (`gema_instance`, `_QWEN3_INSTANCE`, `whisper_model`) são variáveis globais em `model_loader.py`, acessíveis por toda a `nexus.core`.
- **Thread-Safety:** Use o `gema_lock` (RLock) para qualquer chamada ao Gemma 4 em ambiente multi-thread.
- **Progresso via Callback:** O padrão `cb(progresso, etapa, mensagem)` é usado em todos os orquestradores. Ele chama `set_progress` que atualiza o `job_status.json`.
- **Status JSON como Estado Compartilhado:** A comunicação entre o backend e o frontend é feita via polling do `job_status.json`. O frontend lê esse arquivo periodicamente para atualizar a UI.

---

## 📚 5. Convenções de Código

### Python
- **Nomenclatura:** `snake_case` para variáveis/funções, `PascalCase` para classes.
- **Tipagem:** Use type hints em assinaturas de funções quando possível.
- **Docstrings:** Formato Google Style com `Args:`, `Returns:` e `Raises:`.
- **Logging:** Use `logging.info/warning/error` em vez de `print` para código de produção.

### Patches de Compatibilidade (Obrigatórios no Topo dos Orquestradores)
Os seguintes patches DEVEM ser mantidos no início de qualquer orquestrador que carrega modelos:

```python
import numpy as np
if not hasattr(np, 'NAN'):
    np.NAN = np.nan   # Fix para Numpy 2.0+ com Pyannote

os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"       # Fix WinError 1314
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["GGML_CUDA_NO_PINNED"] = "1"            # Estabilidade VRAM llama-cpp
```

### Gestão de VRAM — Padrão Obrigatório
Sempre use o padrão de **handoff sequencial** ao trocar de modelo:

```python
# 1. Descarregar modelo anterior
core.unload_whisper_model()
import gc, torch
gc.collect()
if torch.cuda.is_available(): torch.cuda.empty_cache()

# 2. Verificar segurança
if not core.ensure_vram_safety("Nome do Processo"):
    raise Exception("VRAM Excedida!")

# 3. Carregar próximo modelo
model = core.get_qwen3_engine()
```

---

## 🐛 6. Depuração e Diagnóstico

### Verificar VRAM em tempo real
```bash
nvidia-smi
```

### Verificar se os motores estão ativos
```
GET http://127.0.0.1:5000/api/engine_status
```

### Logs dos Motores
Todos os logs convergem para a janela do CMD do Hub (Janela Sentinela). O nível de log é `INFO` por padrão.

### Reinicialização Total
```
GET http://127.0.0.1:5000/api/restart_motors
```
Mata todos os processos filhos e faz `os.execv` para reiniciar o próprio Hub.

### Limpar Cache de um Projeto
```
POST http://127.0.0.1:5000/api/clear_cache
Body: {"job_id": "nome_do_job"}
```
Apaga as pastas `_backup_transcricao`, `_backup_texto_final`, `_dubbed_audio` e `_dubbed_segments` do projeto.

### Verificar Segurança de Dependências
```
GET http://127.0.0.1:5000/api/security_audit
```
Instala e executa `pip-audit` e retorna as vulnerabilidades encontradas em JSON.

---

## 📋 7. Fluxo de Dados de um Projeto de Jogos

```
1. Upload dos WAVs → pasta _1_MOVER_OS_FICHEIROS_DAQUI/

2. Auto-Diarização (Pyannote):
   → Separa por falante em _2_PARA_AS_PASTAS_DE_VOZ/SPEAKER_XX/

3. Transcrição (Whisper):
   → Gera backup individual em _backup_transcricao/{id}.json
   → Consolida em project_data.json

4. Tradução (Gemma 4):
   → Gera backup individual em _backup_texto_final/{id}.json
   → Atualiza project_data.json

5. TTS (Qwen3-TTS):
   → Gera _dubbed_audio/{id}_dubbed.wav para cada segmento

6. Mixagem Final:
   → Aplica volume boost, normalização e exporta para _saida_final/
   → Gera relatorio_processamento.json
```

---

## 🔒 8. Segurança e Isolamento

- **Isolamento de Ambiente:** O `sys.path` é limpo no início de cada motor pesado para remover pacotes do AppData que podem conflitar com o ambiente virtual local (`env/`).
- **DLL Injection Manual (Windows):** Os caminhos de DLL do CUDA (cublas, cuda_runtime, etc.) são adicionados ao PATH e via `os.add_dll_directory` para garantir que a RTX 3050 seja encontrada.
- **Windows Symlink Bypass:** `HF_HUB_DISABLE_SYMLINKS=1` previne o `WinError 1314` ao baixar modelos do HuggingFace sem privilégios de administrador.
- **Auditoria de Dependências:** A rota `/api/security_audit` usa `pip-audit` para verificar CVEs nas dependências. A rota `/api/security_repair` reinstala as versões seguras via `requirements.txt`.

---

*Este guia deve ser atualizado sempre que uma mudança arquitetural significativa for realizada ou um novo módulo for adicionado à suíte.*