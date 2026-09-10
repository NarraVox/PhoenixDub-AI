# PhoenixDub AI 🚀🔥

![Status](https://img.shields.io/badge/Status-Beta_em_desenvolvimento-E11D48?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square)
![PyTorch](https://img.shields.io/badge/PyTorch-2.6.0_CUDA_12.4-EE4C2C?style=flat-square)
![GPU Target](https://img.shields.io/badge/GPU_Target-RTX_3050_6GB-76B900?style=flat-square)
![Licença](https://img.shields.io/badge/Licen%C3%A7a-Apache_2.0-16A34A?style=flat-square)

[Português](#português) | [English](#english)

## Português

**PhoenixDub AI**, da NarraVox Studios, é uma suíte desktop para dublagem de jogos e vídeos em português brasileiro, edição de mídia e criação de músicas com IA. O processamento de IA foi desenvolvido para execução local, com gerenciamento de memória voltado a GPUs como a NVIDIA RTX 3050 de 6 GB.

> [!NOTE]
> Este README descreve o código em desenvolvimento. A v0.6.0 é a referência das notas de lançamento existentes; o número da próxima versão ainda não foi definido. Recursos posteriores podem não estar nos executáveis publicados. Consulte as [notas da v0.6.0](https://github.com/NarraVox/PhoenixDub-AI/releases/tag/v0.6.0).

### 🎥 Demonstração

[Assista à demonstração de dublagem de Call of Duty: Modern Warfare 3](https://youtu.be/E3HuG6ju7W8).

[Bio e portfólio do autor](https://narravox.github.io/bio/).

### Recursos

- **Titan Games:** dublagem de áudios em lote, seleção de múltiplas pastas e processamento por estágios de transcrição, tradução, síntese e finalização.
- **Titan Video:** dublagem de vídeos, acompanhamento de filas e tratamento de silêncio nas falas.
- **Painel de correção:** busca de segmentos, rascunhos persistentes, prévia de áudio, fila de redublagem e exportação de jogos e vídeos.
- **Vortex Editor:** edição de mídia e fatiador de vídeos com duração configurável. O corte sem recodificação depende dos quadros-chave do arquivo.
- **Vortex DJ (Beta):** criação de músicas com IA usando ACE-Step/ACE-Step 1.5.
- **Gerenciamento de VRAM:** carregamento e liberação dos modelos por estágio para reduzir o consumo de memória. A capacidade necessária depende do modelo e da tarefa.
- **Sincronização:** ajustes de duração para aproximar a fala dublada do tempo original; os resultados precisam de revisão.

Os antigos motores Cine Gen/GodoGen foram removidos desta distribuição. Arquivos de interface e dependências remanescentes não indicam disponibilidade desses motores.

### Stack tecnológica

| Área | Implementação atual |
|---|---|
| Linguagem | Python; os requisitos e o instalador devem ser conferidos para a versão escolhida |
| Transcrição | faster-whisper 1.2.1 |
| Síntese de voz | Qwen3-TTS, com modelos locais de 1.7B/0.6B conforme disponibilidade |
| Diarização | Biblioteca pyannote.audio 3.3.1; o código referencia o modelo speaker-diarization-3.1 |
| Tradução | Modelos GGUF locais via llama-cpp-python e integração com servidor local |
| Aceleração | PyTorch 2.6.0, torchaudio 2.6.0 e torchvision 0.21.0 com CUDA 12.4 |
| Interface | Flask, Flask-Cors, HTML/CSS/JavaScript e janela pywebview |
| Mídia | FFmpeg, librosa, soundfile e pydub |

As versões declaradas estão em [requirements.txt](../requirements.txt). O arquivo ainda inclui dependências de geração de imagem/vídeo que precisam de revisão, e não lista o `pywebview` usado pela aplicação desktop.

### Arquitetura e portas locais

A entrada na raiz é [`Nexus_AI_Pro.py`](../Nexus_AI_Pro.py), que chama `nexus.nexus_app.main()`. O Hub inicia os motores em processos separados.

| Serviço | Porta | Módulo |
|---|---:|---|
| Sentinel Hub | 5000 | `nexus.nexus_app` |
| Titan Games | 5002 | `nexus.dub.dubbing` |
| Vortex Editor | 5003 | `nexus.editor.narravox_editor` |
| Titan Video | 5004 | `nexus.dub.dubbing` |
| Vortex DJ | 5005 | `nexus.dj.vortex_dj` |

Games e Video compartilham o módulo de dublagem, com modos e processos distintos. O Hub fica disponível em `http://127.0.0.1:5000` enquanto a aplicação está aberta.

### Requisitos e preparação

- **Windows de 64 bits**, ambiente principal desta distribuição.
- **GPU NVIDIA com CUDA** para os fluxos acelerados. A RTX 3050 de 6 GB é o alvo de otimização, sem garantia de que qualquer modelo caiba nessa VRAM.
- **16 GB de RAM como referência inicial**; modelos maiores podem exigir mais RAM e memória virtual.
- **Python e Git** para execução pelo código-fonte.
- **FFmpeg e ffprobe no PATH** para processamento de mídia.
- **Microsoft Edge WebView2 Runtime** para a janela desktop com backend Edge Chromium.
- Internet para instalação e download inicial dos modelos. Modelos restritos de diarização exigem aceitar os termos no Hugging Face e configurar `HF_TOKEN` com acesso autorizado.

### Instalação e execução pelo código-fonte

Os comandos abaixo usam PowerShell e pressupõem que o repositório já está em `C:\IA_dublagem`. Há caminhos absolutos de modelos no código atual; mudar a pasta exige revisar essas configurações.

**1. Crie um ambiente somente se ainda não existir um ambiente preparado.**

```powershell
Set-Location C:\IA_dublagem
python -m venv env
.\env\Scripts\python.exe -m pip install --upgrade pip
.\env\Scripts\python.exe -m pip install -r requirements.txt
.\env\Scripts\python.exe -m pip install pywebview
```

Esses comandos preparam as dependências declaradas e a janela desktop; a instalação limpa completa ainda é uma pendência da próxima versão. Se já usa Conda, ative o ambiente existente e use o `python` correspondente, sem recriar `env`.

**2. Prepare os modelos e a tradução.**

- O instalador possui rotina de download de modelos. Os pesos não são fornecidos pelo `pip install`.
- O carregador de voz procura `MODELS/qwen3_1.7b_pytorch` e `MODELS/qwen3_0.6b` sob `C:/IA_dublagem`.
- Para tradução, confira o modelo GGUF e os caminhos em `nexus/core/server_config.json`. O código oferece carregamento local com llama-cpp-python e um inicializador de servidor em `nexus/build_tools/run_llama_server.py`.
- Caso utilize LM Studio, carregue o modelo compatível escolhido e inicie o servidor local na porta configurada (1234 na configuração atual). LM Studio é uma opção de backend.
- Para diarização, configure `HF_TOKEN` no ambiente e autorize o acesso ao modelo solicitado pelo carregador. Nunca publique seu token.

**3. Inicie o Hub.**

```powershell
Set-Location C:\IA_dublagem
.\env\Scripts\python.exe Nexus_AI_Pro.py
```

Para um ambiente Conda já preparado:

```powershell
conda activate C:\IA_dublagem\env
Set-Location C:\IA_dublagem
python Nexus_AI_Pro.py
```

### Downloads publicados e estado beta

- [Setup_Nexus.exe — instalador](https://github.com/NarraVox/PhoenixDub-AI/releases/latest/download/Setup_Nexus.exe)
- [Nexus_AI_Pro.exe — aplicação](https://github.com/NarraVox/PhoenixDub-AI/releases/latest/download/Nexus_AI_Pro.exe)
- [Página de releases](https://github.com/NarraVox/PhoenixDub-AI/releases)

Os links apontam para os artefatos da release marcada como mais recente no GitHub, quando disponíveis. Confira as notas dessa release para saber quais recursos estão incluídos. O projeto permanece em beta; a validação completa de instalação e dublagem em GPU da próxima publicação ainda está pendente.

### Solução de problemas

| Problema | O que verificar |
|---|---|
| FFmpeg ausente, erro MP3 ou fluxo de áudio inválido | Execute `ffmpeg -version` e `ffprobe -version`; confira o PATH e o arquivo de entrada. |
| CUDA indisponível | Confira o driver NVIDIA, o ambiente Python ativo e a instalação de PyTorch com CUDA. |
| Falta de VRAM | Feche outros processos que usam a GPU, libere modelos anteriores e reduza o tamanho do modelo. |
| Erro 1455 no Windows | Confira RAM e memória virtual/arquivo de paginação; esse erro não significa apenas falta de VRAM. |
| Conexão recusada na porta 1234 | Confira o backend de tradução selecionado, o servidor iniciado e a porta configurada. |
| `No module named webview` | Instale `pywebview` no mesmo ambiente usado para iniciar o aplicativo. |
| Falha na diarização | Confira acesso ao modelo, termos aceitos e `HF_TOKEN`, sem expor o token nos logs. |
| Modelo de voz não encontrado | Confira os diretórios de pesos em `MODELS` e os caminhos utilizados pelo carregador. |

### Documentação, comunidade e apoio

- [Contexto técnico](documentacao/CONTEXTO_IA.md) e [guia de manutenção](documentacao/GUIA_DE_MANUTENCAO.md).
- [Organização das saídas de jogos](GAME_OUTPUT_LAYOUTS.md).
- [Créditos](../CREDITS.md).
- [Discussões](https://github.com/NarraVox/PhoenixDub-AI/discussions) e [relatos de problemas](https://github.com/NarraVox/PhoenixDub-AI/issues).
- [Apoie o desenvolvimento independente no Apoia.se](https://apoia.se/narravox_studios).

## English

**PhoenixDub AI**, by NarraVox Studios, is a desktop suite for Brazilian Portuguese game and video dubbing, media editing and AI music creation. Its AI pipeline is designed for local processing, with memory management targeting GPUs such as the NVIDIA RTX 3050 with 6 GB VRAM.

> [!NOTE]
> This README describes the development code. Existing release notes use v0.6.0 as their reference; the next version number has not been assigned. Newer features may not be included in published executables. See the [v0.6.0 release notes](https://github.com/NarraVox/PhoenixDub-AI/releases/tag/v0.6.0).

### Demo and features

[Watch the Call of Duty: Modern Warfare 3 dubbing demo](https://youtu.be/E3HuG6ju7W8).

- **Titan Games:** batch dubbing with multiple input folders and staged transcription, translation, synthesis and finalization.
- **Titan Video:** video dubbing, queue tracking and speech silence handling.
- **Correction panel:** segment search, persistent drafts, audio previews, redubbing queue and game/video export.
- **Vortex Editor:** media editing and configurable video splitting. Cuts without re-encoding depend on source keyframes.
- **Vortex DJ (Beta):** AI music creation using ACE-Step/ACE-Step 1.5.
- **Memory and timing management:** models are loaded and released across stages; speech duration is adjusted toward the original timing. Memory usage varies by model and results require review.

The old Cine Gen/GodoGen engines were removed from this distribution. Remaining interface files and dependencies do not indicate working engines.

### Technology and architecture

The stack includes faster-whisper 1.2.1, Qwen3-TTS, pyannote.audio 3.3.1, llama-cpp-python, PyTorch 2.6.0 with CUDA 12.4, Flask, pywebview and FFmpeg. The diarization code references the `speaker-diarization-3.1` model; its version differs from the library version.

[`Nexus_AI_Pro.py`](../Nexus_AI_Pro.py) starts the Hub and desktop window. The Hub manages separate engine processes:

| Service | Port | Module |
|---|---:|---|
| Sentinel Hub | 5000 | `nexus.nexus_app` |
| Titan Games | 5002 | `nexus.dub.dubbing` |
| Vortex Editor | 5003 | `nexus.editor.narravox_editor` |
| Titan Video | 5004 | `nexus.dub.dubbing` |
| Vortex DJ | 5005 | `nexus.dj.vortex_dj` |

### Requirements and source installation

Use 64-bit Windows, Python, Git, FFmpeg/ffprobe on PATH and the Microsoft Edge WebView2 Runtime. An NVIDIA GPU with CUDA is required for accelerated processing. The hardware target is an RTX 3050 with 6 GB VRAM and 16 GB system RAM as an initial reference; larger models may need more memory. Internet access is needed for installation and initial model downloads.

With the repository already at `C:\IA_dublagem`, run in PowerShell. Create the environment only if a prepared one does not already exist:

```powershell
Set-Location C:\IA_dublagem
python -m venv env
.\env\Scripts\python.exe -m pip install --upgrade pip
.\env\Scripts\python.exe -m pip install -r requirements.txt
.\env\Scripts\python.exe -m pip install pywebview
```

The requirements still contain image/video generation dependencies and omit the desktop `pywebview` dependency. Full clean-install validation for the next release is pending.

Model weights require separate preparation. The installer includes download routines. The voice loader looks for `MODELS/qwen3_1.7b_pytorch` and `MODELS/qwen3_0.6b` under `C:/IA_dublagem`. Review hardcoded paths before relocating the project.

For translation, check the GGUF model and paths in `nexus/core/server_config.json`. Local llama-cpp-python loading and the `nexus/build_tools/run_llama_server.py` server launcher are available. LM Studio is an alternative: load a compatible model and start its local server on the configured port (currently 1234). For restricted diarization models, accept the required terms and configure an authorized `HF_TOKEN`; keep it private.

Start the application:

```powershell
Set-Location C:\IA_dublagem
.\env\Scripts\python.exe Nexus_AI_Pro.py
```

For an existing Conda environment, activate it and run `python Nexus_AI_Pro.py` from the project root. The Hub is available at `http://127.0.0.1:5000` while the application is running.

### Published downloads and beta status

- [Setup_Nexus.exe — installer](https://github.com/NarraVox/PhoenixDub-AI/releases/latest/download/Setup_Nexus.exe)
- [Nexus_AI_Pro.exe — application](https://github.com/NarraVox/PhoenixDub-AI/releases/latest/download/Nexus_AI_Pro.exe)
- [Release history](https://github.com/NarraVox/PhoenixDub-AI/releases)

These links target the GitHub release marked as latest, when its assets are available. Check that release's notes for included features. The project remains in beta; complete installation and real GPU dubbing validation for the next release is pending.

### Troubleshooting

| Issue | Check |
|---|---|
| Missing FFmpeg or invalid audio stream | Run `ffmpeg -version` and `ffprobe -version`; check PATH and the source file. |
| CUDA unavailable | Check the NVIDIA driver, active Python environment and CUDA-enabled PyTorch installation. |
| Out of VRAM | Close other GPU workloads, unload previous models and choose a smaller model. |
| Windows error 1455 | Check system RAM and virtual memory/page file settings. |
| Connection refused on port 1234 | Check the selected translation backend, running server and configured port. |
| `No module named webview` | Install `pywebview` in the environment running the app. |
| Diarization failure | Check model access, accepted terms and `HF_TOKEN`; do not expose the token. |
| Missing voice model | Check downloaded weights and loader paths under `MODELS`. |

### Documentation and community

[Technical context](documentacao/CONTEXTO_IA.md), [maintenance guide](documentacao/GUIA_DE_MANUTENCAO.md), [game output layouts](GAME_OUTPUT_LAYOUTS.md) and [credits](../CREDITS.md).

[Discussions](https://github.com/NarraVox/PhoenixDub-AI/discussions) · [Issues](https://github.com/NarraVox/PhoenixDub-AI/issues) · [Support on Apoia.se](https://apoia.se/narravox_studios) · [Author portfolio](https://narravox.github.io/bio/).

---

*Developed with ❤️ by Paulo Henrik Carvalho de Araújo.*
