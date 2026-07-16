# 📜 Escopo do Projeto — NarraVox Studios Premium

Este documento estabelece os limites, os módulos oficiais e o propósito de cada componente da suíte **NarraVox Studios Premium**, uma plataforma completa de dublagem, edição e criação de conteúdo com Inteligência Artificial, executada **100% localmente** em hardware consumer (RTX 3050 / i5-6400).

---

## 🎯 Missão e Filosofia NarraVox

### Missão
Democratizar a produção profissional de conteúdo audiovisual em Português do Brasil, eliminando barreiras de custo e conhecimento técnico via automação por IA, sem depender de serviços de nuvem.

### Filosofia da Otimização Local (Hardware Acessível)
Enquanto a indústria foca em nuvens caras ou modelos gigantescos que exigem GPUs industriais (24GB+ VRAM), a filosofia do NarraVox é **ocupar o espaço do hardware de consumo em massa**. Nosso alvo é entregar dublagem, tradução, clonagem de voz e geração multimídia local de alta qualidade rodando em GPUs acessíveis de **6GB VRAM (como a RTX 3050/4050)**.

Nossa engenharia apoia-se em dois pilares:
1. **Pipeline Modular Sequencial (Handoff de VRAM):** Em vez de modelos multimodais gigantes, orquestramos modelos menores altamente especializados que são carregados, executados e descarregados em sequência (*lazy loading* e *aggressive unloading*), liberando VRAM de forma dinâmica.
2. **Consistência sobre Resolução:** Priorizamos a consistência narrativa e a identidade de personagens (como a tecnologia de IP-Lock para consistência de rostos e consistência de timbres no TTS) e a velocidade, em vez de perseguir resoluções puras e modelos pesados ineficientes.

---

## ✅ Módulos Oficiais do Núcleo (Produção)

Estes módulos fazem parte do fluxo de trabalho primário e são críticos para o funcionamento da aplicação.

### 🎮 Titan Games — Dublagem de Jogos
- **Localização:** `nexus/dub/nexus_dub_games.py` + `nexus/core/orchestrator_jobs_games.py`
- **Porta:** 5002
- **Propósito:** Dublar áudios de jogos em lote (WAV → WAV PT-BR).
- **Pipeline:** Auto-Diarização → Transcrição → Tradução com Gemma 4 → TTS com Qwen3 → Mixagem.
- **Features:** Perfis por jogo, glossário personalizado, volume boost, auto-purge de defeituosos, retomada automática.

### 🎬 Titan Video — Dublagem de Vídeos
- **Localização:** `nexus/dub/video_routes.py` + `nexus/dub/video_pipeline.py`
- **Porta:** 5004
- **Propósito:** Dublar arquivos de vídeo completos (MP4/MKV → MP4 PT-BR).
- **Pipeline:** Extração de Áudio → Separação de Stems (OpenUnmix) → Diarização + Transcrição → Geração de Lore → Tradução com Gemma 4 → TTS com Qwen3 → Mixagem com Ducking Engine.
- **Features:** Safety Gate de qualidade (90%), HALLUCINATION_BREAKER, suporte a múltiplos falantes com Super Ref.

### 🌪️ Vortex DJ — Mixagem Automática de DJ
- **Localização:** `nexus/dj/vortex_dj.py`
- **Porta:** 5005
- **Propósito:** Criar sets de DJ automáticos com transições profissionais.
- **Pipeline:** Análise de BPM/Energia → Curadoria de Setlist → Auto-FX → Mixagem → Super-Resolução de Áudio.
- **Features:** Personalidades de set (Festival, Agressivo, Suave), Super Mix épico, separação de stems, ACE Music Generation, AudioSR Upscaling.

### 🌪️ Vortex Editor — Edição Criativa de Vídeo
- **Localização:** `nexus/editor/narravox_editor.py`
- **Porta:** 5003
- **Propósito:** Edição de vídeos com VFX cinematográfico, corte e montagem.
- **Features:** Parallax 3.5D para fotos, LUTs de cinema, corte acelerado por GPU (NVENC), multi-corte em lote, geração de Shorts/TikTok, legendas via Whisper.

### 🧠 Nexus Core — Biblioteca de IA
- **Localização:** `nexus/core/`
- **Propósito:** Biblioteca central compartilhada por todos os motores. Não tem porta própria.
- **Componentes:** Gerenciamento de modelos (model_loader), Tradução (translation_core), TTS (tts), Diarização (diarization_*), Transcrição (whisper), Separação Vocal (vocals), Utilitários (utils_*), Telemetria (telemetry).

### 🖥️ Hub Central — Launcher e Gerenciador
- **Localização:** `nexus/nexus_app.py`
- **Porta:** 5000
- **Propósito:** Interface central que gerencia o ciclo de vida de todos os motores e serve a UI via PyWebView.
- **Features:** Gerenciamento dinâmico de motores (lazy load/unload), streaming de mídia com Range Requests, limpeza de cache, auditoria de segurança.

---

## 🧪 Módulos Experimentais / Em Desenvolvimento

Estes módulos estão em desenvolvimento e não fazem parte do fluxo de trabalho principal de produção.

### 🎬 Nexus Cine-Gen
- **Localização:** `nexus/cine/nexus_cine_gen.py`
- **Status:** Funcional (pipeline simulado para Wan 2.2)
- **Propósito:** Gerar curtas-metragens com IA generativa (Wan 2.2 + Gemma 4 como Diretor).
- **Restrição:** O motor Wan 2.2 real ainda não está integrado à produção. As cenas são geradas como placeholder.

### 🧪 Nexus Godogen
- **Localização:** `nexus_godogen/`
- **Status:** Módulo paralelo com ciclo de vida próprio.
- **Propósito:** Pipeline de geração e gestão de conteúdo com interface web própria.
- **Restrição:** Não deve ser modificado sem autorização explícita.

### 🗂️ Scratch
- **Localização:** `scratch/`
- **Status:** Diretório de prototipagem — código não garantido para produção.
- **Propósito:** Scripts auxiliares ad-hoc, análise de PDFs, testes rápidos.

---

## 🔧 Dependências Externas de Produção

Estas ferramentas devem estar instaladas e disponíveis no PATH:

| Ferramenta | Uso | Obrigatório |
|---|---|---|
| **FFmpeg** (Full) | Extração de áudio, remux de vídeo, corte, mixagem | ✅ Sim |
| **Python 3.10+** | Runtime do sistema | ✅ Sim |
| **NVIDIA Driver** + CUDA | Aceleração de GPU para todos os modelos | ✅ Sim |
| **LM Studio** (opcional) | Motor externo alternativo para Gemma 4 via porta 1234 | ⚪ Opcional |

---

## 📦 Modelos de IA Necessários

Devem estar em `C:/IA_dublagem/_MODELS_/`:

| Modelo | Arquivo | Uso |
|---|---|---|
| **Gemma 4 E4B** | `gemma-4-E4B-it-Q4_K_M.gguf` (ou variante) | Tradução e Cine-Gen |
| **Qwen3-TTS 0.6B** | `_MODELS_/qwen3_0.6b/model.safetensors` | Síntese de voz |
| **Wan 2.2 5B** | `wan2.2-5b-ti2v-Q4_K_M.gguf` | Cine-Gen (experimental) |

---

## 🚫 O que está FORA do Escopo

- Serviços de nuvem (AWS, GCP, Azure) — o sistema é **100% local**.
- APIs pagas de terceiros (OpenAI, ElevenLabs, Google TTS).
- Modificação de módulos experimentais sem justificativa documentada.
- Código de produção na pasta `scratch/`.

---

**Regra de Ouro:** Qualquer funcionalidade nova deve ser mapeada para um módulo oficial (`nexus/*`) ou justificada explicitamente como extensão do escopo neste documento antes de ser implementada.