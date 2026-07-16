# Codebase Map — NarraVox Studios Premium Engine

Este arquivo é o mapa de referência rápida para desenvolvedores e IAs localizarem módulos, editarem funcionalidades e compreenderem as responsabilidades de cada arquivo de forma cirúrgica.

> **Última atualização baseada em inspeção real do código-fonte.**

---

## 📂 Estrutura de Diretórios e Arquivos

---

### 🌐 Raiz do Nexus (`/nexus`)

* [nexus_app.py](file:///c:/IA_dublagem/nexus/nexus_app.py): **Hub Central (Porta 5000)**. Inicia e gerencia o ciclo de vida de todos os motores via `active_engines`. Serve a UI via PyWebView. Rotas: `/api/engine_status`, `/api/restart_motors`, `/api/clear_cache`, `/api/list_project_files`, `/api/security_audit`, `/stream_media`.
* [nexus_agent.py](file:///c:/IA_dublagem/nexus/nexus_agent.py): Lógica de agentes autônomos.
* [nexus_local_forge.py](file:///c:/IA_dublagem/nexus/nexus_local_forge.py): Motor local do Forge.

---

### 🧠 Core Engine (`/nexus/core`)

Biblioteca central compartilhada por todos os motores. Não tem porta própria.

#### 🎙️ Diarização e Análise de Voz
* [diarization.py](file:///c:/IA_dublagem/nexus/core/diarization.py): **Diarização Consolidada**. Pipeline Pyannote 3.1 (GPU/CUDA) e fallback SpeechBrain para embeddings. Mapeia e clusteriza os trechos de fala por personagem em lote, organizando as pastas de vozes e limpando a VRAM.

#### 📝 Transcrição e Tradução
* [whisper.py](file:///c:/IA_dublagem/nexus/core/whisper.py): Transcrição com `faster-whisper` (modelo `small`, sem VAD Filter). Função `Smart Trim` para cortar alucinações e silêncio.
* [translation.py](file:///c:/IA_dublagem/nexus/core/translation.py): **Motor de Tradução Consolidado (Gemma 4 / Qwen 3.5)**. Inclui a orquestração de tradução em lote estruturada (JSON), adaptação de silêncio e limites de caracteres por segundo (CPS = 16), validação de qualidade (LQA), vocabulário de combate (DJ), sanitização de opções e geração de Lore global.

#### 🧠 Modelos e Orquestração
* [model_loader.py](file:///c:/IA_dublagem/nexus/core/model_loader.py): **Gerenciador de Modelos de IA**. Controla Whisper, Gemma/Qwen (llama-cpp-python / LM Studio) e Qwen3-TTS. Funções: `get_optimal_device`, `ensure_vram_safety` (limite 5GB), `wait_for_vram_release`, `unload_*`, `get_qwen3_engine`. Lock global: `gema_lock`.
* [orchestrator_jobs_games.py](file:///c:/IA_dublagem/nexus/core/orchestrator_jobs_games.py): **Orquestrador Titan Games**. Pipeline completo de dublagem de jogos. Features: retomada inteligente (resume), auto-purge de defeituosos, volume boost por perfil, glossário personalizado, tradução paralela com ThreadPoolExecutor.
* [orchestrator_jobs_core.py](file:///c:/IA_dublagem/nexus/core/orchestrator_jobs_core.py): Orquestrador base de jobs gerais.
* [orchestrator_routes.py](file:///c:/IA_dublagem/nexus/core/orchestrator_routes.py): Rotas de API do orquestrador.
* [utils.py](file:///c:/IA_dublagem/nexus/core/utils.py): **Utilitários Consolidados do Core**. Junção das ferramentas de sistema (prioridade de processos, UTF-8, detecção de VRAM), manipulação de áudio via FFmpeg/Pydub (`get_audio_duration`, `speedup_audio`, mixagem), telemetria (`set_progress`) e I/O de JSON com escrita atômica com locks (Phoenix Recovery).

#### 🔊 Áudio e Sintetizadores
* [tts.py](file:///c:/IA_dublagem/nexus/core/tts.py): Motor Qwen3-TTS-0.6B (GPU BFloat16 Ampere). Clonagem de voz via referência, injeção de emoção, modo FasterQwen3TTS com CUDA Graphs. Fallback para modo seguro `Qwen3TTSModel`.
* [vocals.py](file:///c:/IA_dublagem/nexus/core/vocals.py): Isolamento de voz (DeepFilterNet/OpenUnmix). Função `separar_vocal_instrumental`. Gera `vocals.wav` e `instrumental.wav`.

---

### 🎮 Dublagem Games e Vídeo (`/nexus/dub`)

* [dubbing.py](file:///c:/IA_dublagem/nexus/dub/dubbing.py): **Motor Dubbing Consolidado (Porta 5002 / 5004)**. Une o servidor Titan Games e o Titan Video. Executa as APIs de upload e o pipeline unificado de vídeo: extração de áudio, stems, diarização, geração de Lore, tradução estruturada, TTS com Super Ref, mixagem de áudio com Ducking Engine e remux final por FFmpeg (RTX NVENC / Intel QQS). Aceita argumento dinâmico de porta CLI.

---

### 🌪️ Vortex DJ (`/nexus/dj`)

* [vortex_dj.py](file:///c:/IA_dublagem/nexus/dj/vortex_dj.py): **Motor Vortex DJ Completo (Porta 5005)**. Classe `VortexDJ`. Métodos: `transcribe_lot` (Whisper Worker), `analyze_lot` (Análise de Espectro), `curate_set_fast` (Curadoria e Auto-FX), `ignite_mix_lot` (Mixagem Profissional com FFmpeg). Features: Super Mix, Separação de Stems (OpenUnmix), Super-Resolução Áudio (AudioSR em chunks de 10s com crossfade), ACE Music Generation, checkpointing.

---

### 🌪️ Vortex Editor (`/nexus/editor`)

* [narravox_editor.py](file:///c:/IA_dublagem/nexus/editor/narravox_editor.py): **Motor Vortex Editor (Porta 5003)**. Classes: `VortexDirector` (filtros FFmpeg de cinema: Parallax 3.5D, Bokeh, Grain, Vignette, LUTs), `VortexAI` (orquestração de ferramentas). Ferramentas: `trim` (corte acelerado RTX NVENC), `multi_trim` (multi-corte em lote), `merge` (junção de clipes), `parallax` (VFX cinema), `captions` (legendas Whisper), `studio_sound` (OpenUnmix + DeepFilter).

---

### 🎬 Cine-Gen (`/nexus/cine`)

* [nexus_cine_gen.py](file:///c:/IA_dublagem/nexus/cine/nexus_cine_gen.py): **Motor Cine-Gen**. Pipeline: Gemma 4 roteiriza em cenas JSON → Wan 2.2 gera os vídeos → TangoFlux gera SFX/música → NVENC monta → Real-ESRGAN faz upscale. IP-Lock de atores via fotos de referência.

---

### 🖥️ UI — Interface do Usuário (`/nexus/client`)

| Arquivo | Módulo | Porta |
|---|---|---|
| `nexus_premium.html` | Hub Central | 5000 |
| `games_studio.html` | Titan Games | 5002 |
| `vortex_editor.html` | Vortex Editor | 5003 |
| `video_studio.html` | Titan Video | 5004 |
| `dj_studio.html` | Vortex DJ | 5005 |
| `nexus_docs.html` | Documentação | 5006 |
| `installer_ui.html` | Setup/Instalação | – |
| `nexus_cine_gen.html` | Cine-Gen | – |

---

## 🔄 Pipelines em Diagrama

### Pipeline Titan — Jogos
```
dubbing.py (API - Porta 5002)
  → orchestrator_jobs_games.py (Thread)
    → diarization.py (Pyannote & Clustering)
    → whisper.py (Transcrição)
    → translation.py (Gemma 4 / Qwen 3.5)
    → tts.py (Qwen3-TTS)
    → utils.py (Mixagem Final & Telemetria)
```

### Pipeline Cinema — Vídeos
```
dubbing.py (API - Porta 5004)
  → dubbing.py (Thread pipeline_video_master)
    → vocals.py (OpenUnmix)
    → diarization.py (Pyannote)
    → whisper.py (Transcrição)
    → translation.py (Gemma 4 / Qwen 3.5 + Lore)
    → tts.py (Qwen3-TTS + Super Ref)
    → utils.py (Remux FFmpeg / Mixagem)
```

### Pipeline Vortex DJ
```
vortex_dj.py (API + Classe VortexDJ)
  → transcribe_lot() → Whisper Worker
  → analyze_lot() → Analysis Worker
  → curate_set_fast() → Auto-FX + Setlist
  → ignite_mix_lot() → Mixagem FFmpeg
  → process_upscale() → AudioSR Chunked
```

---

## 💾 Estrutura de um Projeto de Job (Pasta `uploads/[job_id]/`)

```
uploads/
└── [job_id]/
    ├── job_status.json               ← Status em tempo real (polling UI)
    ├── project_data.json             ← Dados mestre de todos os segmentos
    ├── relatorio_processamento.json  ← Relatório LQA final
    ├── lore_global.json              ← Lore Global gerada pelo Gemma (Vídeo)
    ├── durations_cache.json          ← Cache de durações de áudio
    ├── mastering_cache.json          ← Cache de masterização
    ├── volume_boost.txt              ← Configuração de volume (+dB)
    ├── _1_MOVER_OS_FICHEIROS_DAQUI/ ← Entrada: WAVs originais (Jogos)
    ├── _2_PARA_AS_PASTAS_DE_VOZ/    ← Áudios separados por falante
    │   └── SPEAKER_XX/
    │       ├── seg_0.wav, seg_1.wav, ...
    │       └── _ref_titan_22k.wav    ← Super Ref para clonagem de voz
    ├── _backup_transcricao/          ← Cache de transcrição (1 JSON/seg)
    ├── _backup_texto_final/          ← Cache de tradução (1 JSON/seg)
    ├── _dubbed_audio/                ← Áudios dublados finais (Jogos)
    ├── _dubbed_segments/             ← Áudios dublados por segmento (Vídeo)
    ├── _saida_final/                 ← Saída final mixada (Jogos)
    ├── vocals.wav                    ← Vocais isolados (Vídeo)
    ├── instrumental.wav              ← Trilha instrumental (Vídeo)
    └── dubbed_audio_clean/           ← Segmentos dublados normalizados (Vídeo)
```
