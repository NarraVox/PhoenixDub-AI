# 🤖 NarraVox Studios Premium — Central Core Summary (NEXUS_CORE_SUMMARY)
# =====================================================================
# Este documento centraliza o propósito, arquitetura e regras críticas
# do sistema. Serve como o "Contexto Supremo" otimizado para IAs locais.

# =====================================================================
# 🎙️ 0. PROPÓSITO E ESCOPO DO PROGRAMA
# =====================================================================
O **NarraVox Studios Premium** (incorporando PhoenixDub AI e Cine Gen) é uma suíte local e independente de automação de mídia por IA para criadores de conteúdo, modders de jogos e comunidades.
*   **Propósito:** Oferecer dublagem automatizada de vídeos/jogos (inglês/russo para português brasileiro), edição e mixagem de áudio sem depender de nuvens corporativas.
*   **Filosofia de Hardware:** Otimizado estritamente para rodar localmente com alta performance em GPUs de consumo de entrada, visando o hardware alvo de **NVIDIA RTX 3050 (6GB VRAM)**.


# =====================================================================
# 📦 1. ARQUITETURA E PORTAS DOS MOTORES
# =====================================================================
O NarraVox é uma suíte local composta por múltiplos motores Flask coordenados
por um Hub Central (PyWebView na porta 5000). Os motores rodam em portas dedicadas:

*   **Porta 5000:** Hub Central / Launcher (`nexus/nexus_app.py`) - PyWebView & Streaming.
*   **Porta 5002:** Titan Games (`nexus/dub/dubbing.py` + `orchestrator_jobs_games.py`).
*   **Porta 5003:** Vortex Editor (`nexus/editor/narravox_editor.py`) - VFX e corte.
*   **Porta 5004:** Titan Video (`nexus/dub/dubbing.py` + pipeline_video_master).
*   **Porta 5005:** Vortex DJ (`nexus/dj/vortex_dj.py`) - Mixagem automática.
*   **Porta 5006:** Docs (`nexus/docs/nexus_docs.py`) - Documentação local do desenvolvedor.
*   **Porta 5006 (Alt):** Cine-Gen (`nexus/cine/nexus_cine_gen.py`) - WAN 2.2 placeholder.

# =====================================================================
# 📁 2. MAPA DE MÓDULOS (CORE ENGINE)
# =====================================================================
Todo o código de produção fica em `nexus/`. Módulos experimentais: `nexus_godogen/` e `nexus/cine/`.
*   `nexus/core/model_loader.py`: **Gerenciador de Modelos**. Carrega/descarrega modelos na GPU (RTX 3050 6GB) de forma sequencial. Controla o lock global `gema_lock` e garante limite de 5.0GB de VRAM.
*   `nexus/core/translation.py`: **Motor de Tradução**. Roda tradução estruturada via llama-cpp-python, controla velocidade (16 CPS máx) e realiza LQA (validação de qualidade) e Lore Global.
*   `nexus/core/tts.py`: **Motor Qwen3-TTS**. Geração de voz (0.6B) na GPU com clonagem via áudio de referência e modo Turbo (CUDA Graphs).
*   `nexus/core/whisper.py`: **Transcrição**. Usa `faster-whisper` (modelo `small`) com `Smart Trim` (cortador de alucinações de silêncio) sem VAD filter.
*   `nexus/core/diarization.py`: **Diarização**. Executa **Pyannote 3.1** na GPU para clusterização temporal de falantes.
*   `nexus/core/vocals.py`: **Isolamento Vocal**. Separa vozes e trilha sonora via DeepFilterNet/OpenUnmix.
*   `nexus/core/utils.py`: **Utilitários**. Escrita/leitura JSON atômica segura, FFmpeg/Pydub (speedup/normalização/mixagem) e callbacks de telemetria.

# =====================================================================
# 📂 3. ESTRUTURA DE PASTAS DE TRABALHO
# =====================================================================
Cada projeto gera uma pasta em `uploads/[job_id]/`:
*   `job_status.json`: Status e progresso (0-100%) em tempo real.
*   `project_data.json`: Arquivo mestre de dados de transcrição, tradução e áudio.
*   `_1_MOVER_OS_FICHEIROS_DAQUI/`: Pasta de entrada com os WAVs originais (Jogos).
*   `_2_PARA_AS_PASTAS_DE_VOZ/SPEAKER_XX/`: Pasta de referências de voz. Contém o arquivo `_ref_titan_22k.wav` para clonagem.
*   `_backup_transcricao/`: Cache individual das transcrições de segmentos.
*   `_backup_texto_final/`: Cache individual das traduções (1 JSON por segmento).
*   `_saida_final/`: Arquivos resultantes mixados e prontos para uso.

# =====================================================================
# 🛡️ 4. REGRAS CRÍTICAS E INVIOLÁVEIS
# =====================================================================
1.  **LOCK DO GEMMA (Thread-Safety):** Toda chamada de tradução ao modelo Gemma/Qwen deve usar `with gema_lock:` importado de `model_loader.py`.
2.  **HANDOFF DE VRAM (GPU de 6GB):** Nunca carregue dois modelos de IA pesados ao mesmo tempo. Execute `unload_[modelo]()`, limpe cache com `gc.collect()` e `torch.cuda.empty_cache()` antes do próximo carregamento.
3.  **ESCRITA ATÔMICA JSON:** Nunca use `json.dump` direto em arquivos cruciais. Sempre use `safe_json_write(dados, caminho)` de `utils.py` para evitar corrupção por queda de energia.
4.  **EDIÇÃO MANUAL SAGRADA:** O campo `manual_edit_text` de qualquer segmento é absoluto. Se preenchido, ignora a IA e nunca é sobrescrito.
5.  **CACHE GRANULAR:** Nunca delete a pasta `_backup_texto_final/` inteira. Delete arquivos JSON individuais para forçar a re-tradução de segmentos específicos.
6.  **AMBIENTE WINDOWS (BARRAS E COMANDOS):** O projeto roda estritamente no CMD clássico. Sempre use barras invertidas (`\`) nos comandos de terminal. Nunca use `ls`, use `dir`. Use caminhos nativos no Python (`os.path.join`).
7.  **PATCHES DE SEGURANÇA:** Os orquestradores pesados devem declarar patches no topo: `np.NAN = np.nan` (compatibilidade Numpy 2.0 com Pyannote), `HF_HUB_DISABLE_SYMLINKS = "1"`, e `GGML_CUDA_NO_PINNED = "1"`.

# =====================================================================
# 🔊 5. REGRAS DE NEGÓCIO (ÁUDIO E DIÁLOGO)
# =====================================================================
*   **Tratamento de Silêncios:** Se o Whisper transcrever texto vazio mas o segmento durar mais de 0.5s, ele falhou. O segmento deve ser re-transcrito, nunca apagado.
*   **Gemidos e Não-Verbais (<0.5s):** Áudios muito curtos ou que contenham apenas palavras da lista `SONS_A_IGNORAR` (ah, oh, hmm, yeah, etc.) são marcados como `Copiado Diretamente (Som Não-Verbal)` e o áudio original é copiado sem dublagem.
*   **Quebra de Cantoria:** Se o Whisper repetir a mesma frase 4x ou mais em sequência (alucinação por música), marque a emoção como `CANTORIA` e ignore a dublagem de IA.
*   **Filtro de PT-BR:** Se `detected_language` for `pt`, ignore a tradução e defina a tradução diretamente como o original limpo.
*   **Safety Gate (Vídeo):** Se menos de 90% dos segmentos forem dublados com sucesso, a masterização do vídeo final é abortada para evitar cortes mudos.
