CONTEXTO DO PROJETO — NarraVox Studios Premium

Leia este arquivo inteiro antes de qualquer tarefa. É o mapa completo do projeto.

O QUE É O PROJETO

Suíte de dublagem e edição de conteúdo com IA, 100% local. Hardware alvo: RTX 3050 (6GB VRAM) + i5-6400 + 16GB RAM. Roda no Windows via Python + PyWebView.

MOTORES E PORTAS

Motor

Porta

Arquivo Principal

Hub Central (Launcher)

5000

nexus\nexus_app.py

Titan Games (Dublagem de Jogos)

5002

nexus\dub\dubbing.py

Vortex Editor (Edição de Vídeo)

5003

nexus\editor\narravox_editor.py

Titan Video (Dublagem de Vídeo)

5004

nexus\dub\dubbing.py

Vortex DJ (Mixagem Automática)

5005

nexus\dj\vortex_dj.py

Documentação

5006

nexus\docs\nexus_docs.py

ARQUIVOS-CHAVE POR FUNÇÃO

Função

Arquivo

Gerenciar modelos de IA (carregar/descarregar)

nexus\core\model_loader.py

Pipeline completo de jogos

nexus\core\orchestrator_jobs_games.py

Pipeline completo de vídeo

nexus\dub\dubbing.py

Tradução com Gemma 4 / Qwen 3.5

nexus\core\translation.py

Síntese de voz (TTS)

nexus\core\tts.py

Transcrição (Whisper)

nexus\core\whisper.py

Diarização (Pyannote) & Clusterização

nexus\core\diarization.py

Isolamento vocal (OpenUnmix)

nexus\core\vocals.py

Utilitários (JSON, Áudio, Sistema, Telemetria)

nexus\core\utils.py

Filtragem de reações/ruídos

nexus\dub\dubbing.py

Motor Vortex DJ completo

nexus\dj\vortex_dj.py

Editor criativo de vídeo

nexus\editor\narravox_editor.py

UI (HTMLs servidos pelo Hub)

nexus\client\

ESTRUTURA DE PASTAS DE PROJETO (uploads)

uploads\[job_id]\
├── job_status.json            ← Status em tempo real (polling da UI)
├── project_data.json          ← Dados mestre de todos os segmentos
├── _1_MOVER_OS_FICHEIROS_DAQUI\ ← Entrada: WAVs originais
├── _2_PARA_AS_PASTAS_DE_VOZ\    ← Áudios por falante (SPEAKER_XX\)
│   └── SPEAKER_XX\
│       └── _ref_titan_22k.wav  ← Referência de clonagem de voz
├── _backup_transcricao\         ← Cache: 1 JSON por segmento transcrito
├── _backup_texto_final\         ← Cache: 1 JSON por segmento traduzido
├── _dubbed_audio\               ← Áudios dublados (jogos)
├── _dubbed_segments\            ← Áudios dublados (vídeo)
└── _saida_final\                ← Saída final mixada


REGRAS CRÍTICAS — NUNCA VIOLAR

1. LOCK DO GEMMA (Thread-Safety)

Toda chamada ao Gemma 4 DEVE usar o lock global:

from nexus.core.model_loader import gema_lock
with gema_lock:
    resultado = gema_batch_processor_v2(...)


2. HANDOFF SEQUENCIAL DE VRAM

Nunca carregue dois modelos grandes ao mesmo tempo. Padrão obrigatório:

core.unload_whisper_model()   # ou unload_gema_model() / unload_qwen3_model()
import gc, torch
gc.collect()
if torch.cuda.is_available(): torch.cuda.empty_cache()
# Só depois carrega o próximo modelo


3. ESCRITA SEGURA DE JSON

NUNCA use json.dump() direto em arquivos críticos. Use sempre:

from nexus.core.utils import safe_json_write, safe_json_read
safe_json_write(dados, caminho)


4. EDIÇÃO MANUAL É SAGRADA

O campo manual_edit_text de qualquer segmento é intocável. Nunca sobrescreva, limpe ou ignore esse campo. Se ele existe, ele tem prioridade absoluta sobre qualquer tradução de IA.

5. CACHE GRANULAR — NÃO APAGAR A PASTA INTEIRA

A pasta _backup_texto_final\ nunca deve ser deletada inteira. Para forçar re-tradução de um segmento, apague apenas o .json individual daquele segmento.

6. PATCHES DE COMPATIBILIDADE (Obrigatórios no topo de orquestradores)

import numpy as np
if not hasattr(np, 'NAN'):
    np.NAN = np.nan  # Fix Numpy 2.0+ com Pyannote

os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"        # Fix WinError 1314
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["GGML_CUDA_NO_PINNED"] = "1"             # Estabilidade VRAM llama-cpp


7. AMBIENTE WINDOWS (BARRAS INVERTIDAS E TERMINAL)

Este projeto roda estritamente no Windows usando o prompt de comando (CMD) clássico do sistema operacional.

NUNCA use barras normais (/) para caminhos no terminal ou comandos (ex: dir nexus/dub/ ou ls causarão falhas graves no CMD).

SEMPRE use barras invertidas (\) para todos os comandos de terminal (ex: dir nexus\dub\).

NUNCA execute o comando ls. O comando correto para listar conteúdos no Windows é estritamente dir.

Ao programar ou manipular scripts de terminal em Python, use caminhos nativos do Windows (os.path.join ou caminhos com duas barras invertidas \\ para evitar problemas de escape).

REGRAS DE NEGÓCIO ESSENCIAIS

Segmento com texto vazio + duração > 0.5s → Whisper falhou. Re-transcrever, NÃO descartar.

Sons curtos < 0.5s ("ah", "oh", "hmm") → Copiar áudio original sem dublar (status: Copiado Diretamente (Som Não-Verbal)).

Mesma frase repetida 4x seguidas → Marcar como CANTORIA (alucinação do Whisper sobre música). Não dublar.

Segmento com detected_language: pt → Não enviar ao Gemma. Preservar original como sanitized_text.

VRAM limite: 5.0 GB. Verificar com ensure_vram_safety() antes de carregar modelos.

Safety Gate (Pipeline Vídeo): Se menos de 90% dos segmentos foram dublados com sucesso, a masterização é abortada.

MODELOS DE IA UTILIZADOS

Modelo

Localização

Uso

Gemma 4 E4B (GGUF)

_MODELS_\gemma-4-E4B-it-*.gguf

Tradução, LQA, Lore, Cine-Gen

Qwen3-TTS 0.6B

_MODELS_\qwen3_0.6b\

Síntese de voz com clonagem

faster-whisper small

Download automático

Transcrição de áudio

Pyannote 3.1

HuggingFace (token necessário)

Diarização por falante

OpenUnmix (umxhq)

Download automático

Separação vocal/instrumental

CONVENÇÕES DE CÓDIGO

snake_case para variáveis e funções

PascalCase para classes

Use logging.info/warning/error — nunca print em produção

Progresso via callback cb(progresso_0_100, indice_etapa, mensagem_str)

Status persistido in job_status.json via safe_json_write

O QUE NÃO MODIFICAR SEM AUTORIZAÇÃO

nexus_godogen\ — módulo experimental com ciclo de vida próprio

nexus\cine\ — motor Cine-Gen em desenvolvimento

scratch\ — não é código de produção

Qualquer arquivo com # Copyright (c) 2026 Paulo Henrik no topo — verificar antes