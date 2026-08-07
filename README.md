# PhoenixDub AI 🚀🔥

![Versão](https://img.shields.io/badge/Vers%C3%A3o-v0.6.0-E11D48?style=flat-square&labelColor=1E293B)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&labelColor=1E293B&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-CUDA_Accelerated-EE4C2C?style=flat-square&labelColor=1E293B&logo=pytorch&logoColor=white)
![GPU Target](https://img.shields.io/badge/GPU_Target-RTX_3050_6GB-76B900?style=flat-square&labelColor=1E293B&logo=nvidia&logoColor=white)
![Licença](https://img.shields.io/badge/Licen%C3%A7a-Apache_2.0-16A34A?style=flat-square&labelColor=1E293B)
[![Apoia.se](https://img.shields.io/badge/Apoia.se-NarraVox_Studios-E11D48?style=flat-square&labelColor=1E293B&logo=patreon)](https://apoia.se/narravox_studios)
[![Baixar Setup](https://img.shields.io/badge/%F0%9F%93%A5_1._Setup_Nexus.exe-Download-0284C7?style=flat-square&labelColor=1E293B)](https://github.com/NarraVox/PhoenixDub-AI/releases/latest/download/Setup_Nexus.exe)
[![Baixar Executável](https://img.shields.io/badge/%F0%9F%9A%80_2._Nexus_AI_Pro.exe-Download-16A34A?style=flat-square&labelColor=1E293B)](https://github.com/NarraVox/PhoenixDub-AI/releases/latest/download/Nexus_AI_Pro.exe)

[Português](#português) | [English](#english)

---

## Português

**PhoenixDub AI** é uma solução completa de **engenharia de software e inteligência artificial** voltada para **edição, sincronização e dublagem automatizada** de vídeos e jogos para Português (PT-BR). 

O diferencial técnico core do projeto é a **extrema eficiência de hardware**: pipelines complexos de IA (síntese de voz, transcrição ASR e diarização) otimizados para rodar **100% localmente em GPUs de entrada (NVIDIA RTX 3050 6GB VRAM)**, dispensando dependências ou custos com APIs pagas na nuvem.

👉 **Bio & Portfólio do Autor:** [https://narravox.github.io/bio/](https://narravox.github.io/bio/)

---

### 🎥 Demonstração Visual & Interface (Showcase)

![NarraVox Sentinel Dashboard](assets/Image_fx_1.jpg)

🎬 **[Clique Aqui para Assistir à Dublagem do Call of Duty: MW3 no YouTube (1 Minuto)](https://youtu.be/E3HuG6ju7W8)**  
*(Demonstração real de uma cutscene do Call of Duty: Modern Warfare 3 dublada automaticamente pelo PhoenixDub AI em Português PT-BR)*

---

### 🛠️ Stack Tecnológica & IAs Utilizadas

* **Linguagem Principal:** Python 3.10+
* **Modelos de IA & Transcrição:** OpenAI Whisper (ASR), Qwen3-TTS (Síntese de Voz), Pyannote.audio 3.1 (Diarização de Locutores)
* **Aceleração por Hardware:** PyTorch com suporte nativo CUDA, Gestão Dinâmica de Memória VRAM (Offloading)
* **Interface & Orquestração Desktop:** Flask, WebSockets, HTML5/CSS3 (Design Premium Glassmorphism), Suíte Multiprocesso
* **Processamento de Áudio e Mídia:** FFmpeg Full Build Core, eSpeak-NG engine

---

### 🧠 💡 Destaques de Engenharia & Decisões Técnicas

1. ⚡ **VRAM Management & Memory Offloading (Target 6GB):**
   - Arquitetura de agendamento de recursos que gerencia a alocação e liberação de modelos pesados em VRAM (ex: descarregando instâncias de LLM antes de iniciar o motor de voz), prevenindo erros de *Out-Of-Memory (OOM)* em GPUs modestas.
2. 🔄 **Pipeline Concorrente com Preservação de Tempo (Time Preservation):**
   - Sistema de filas de tarefas concorrentes em CUDA que processa centenas de áudios de jogos em lote, aplicando algoritmos de ajuste de *pitch* e *speed* para alinhar a dublagem perfeitamente ao tempo original.
3. 🏛️ **Arquitetura Desktop Modular baseada em Microsserviços:**
   - A central mestre (`nexus_app.py`) gerencia e orquestra 4 subsistemas isolados rodando em portas locais dedicadas:
     - **Porta 5000:** Dashboard Principal (Sentinel Hub)
     - **Porta 5002:** Engine de Dublagem de Jogos em Lote (`nexus_dub_games.py`)
     - **Porta 5003:** Editor Portátil de Ondas de Áudio (`narravox_editor.py`)
     - **Porta 5004:** Engine de Dublagem de Vídeos Longos & Trailers (`nexus_dub_video.py`)

---

> [!TIP]
> ### 📥 DOWNLOAD DIRETO DOS 2 ARQUIVOS DO PROJETO (1-CLIQUE)
> Baixe os 2 executáveis da versão v0.5 direto para o seu PC sem precisar procurar no GitHub:  
> 1. 👉 [**[Passo 1] Baixar Instalador Automático: Setup_Nexus.exe (225 MB)**](https://github.com/NarraVox/PhoenixDub-AI/releases/latest/download/Setup_Nexus.exe)  
> 2. 👉 [**[Passo 2] Baixar Executável Principal: Nexus_AI_Pro.exe (213 MB)**](https://github.com/NarraVox/PhoenixDub-AI/releases/latest/download/Nexus_AI_Pro.exe)

---

### 🗨️ Participe da nossa Comunidade!
**Queremos ouvir você!** Deixe seu feedback, sugestões ou poste seus resultados na aba de [**Discussões (Discussions)**](https://github.com/NarraVox/PhoenixDub-AI/discussions).

---

> [!WARNING]
> ### ⚠️ Aviso de Versão Beta (v0.5 - The Sentinel Update)
> Esta versão é fruto de uma reescrita completa do software para automação e estabilidade. Por ser um release Beta, os executáveis podem apresentar instabilidades. Caso encontre algum problema, por favor reporte na aba de [Issues](https://github.com/NarraVox/PhoenixDub-AI/issues).

---

> [!IMPORTANT]
> ### 💖 Ajude a Financiar a Versão 1.0 e o Cine Gen! (Apoia.se)
> O PhoenixDub é um projeto independente (*Bootstrapping*). Nosso foco é **rodar IAs pesadas localmente no seu computador**.
> * Com o seu apoio, financiamos a **Versão 1.0** (dublagem local definitiva e gerador de músicas por IA) e a pesquisa do **Cine Gen** (gerador de vídeos via IA para PCs modesto).
> 👉 **[Apoie a NarraVox Studios no Apoia.se clicando aqui!](https://apoia.se/narravox_studios)**

---

### 🖥️ Requisitos do Sistema & Suporte de Hardware
* **Processador:** Intel (6ª geração ou superior) ou AMD equivalente
* **Placa de Vídeo (OBRIGATÓRIA):** GPU dedicada NVIDIA com suporte a CUDA
  * *Recomendado:* NVIDIA RTX 3050 (6GB VRAM) ou superior
* **Memória RAM:** Mínimo de 16 GB

---

### 🚀 Tutorial de Instalação (Para Desenvolvedores & Execução Local)

#### Passo 1: Ferramentas de Base (Obrigatório)
1. **Git para Windows:** [Baixe Aqui](https://git-scm.com/download/win)
2. **Anaconda / Miniconda:** [Baixe Aqui](https://www.anaconda.com/download)
3. **eSpeak-NG:** [Baixe o .msi X64 Aqui](https://github.com/espeak-ng/espeak-ng/releases) *(Essencial para síntese de voz no Windows)*

#### Passo 2: O Cérebro de Tradução (LM Studio)
1. Instale o **LM Studio** ([lmstudio.ai](https://lmstudio.ai)).
2. Baixe o modelo: `unsloth/gemma-4-E4B-it-GGUF` (Recomendado: Q4_K_M).
3. Em **Local Server**, clique em **Start Server** na porta **1234**.

#### Passo 3: Execução via Anaconda Prompt
```bash
# 1. Ative o ambiente virtual
conda activate C:\IA_dublagem\env

# 2. Acesse a pasta do projeto
cd C:\IA_dublagem

# 3. Inicie o aplicativo central
python nexus_app.py
```
Acesse a interface unificada pelo navegador em `http://localhost:5000` ou pela janela desktop nativa.

---

### 🛠️ Solução de Problemas (FAQ)

| Problema | Solução |
| :--- | :--- |
| **"Invalid audio stream" ou erro MP3** | Instale a versão **FFmpeg FULL** (Gyan.dev). |
| **"Out of Memory" ou Error 1455** | Feche o LM Studio quando solicitado para liberar VRAM. |
| **"espeak-ng not found"** | Instale o eSpeak-NG .msi e reinicie a máquina. |
| **Erro 1234 (Connection Refused)** | Verifique se o server do LM Studio está ativo na porta 1234. |

---

### 🎖️ Créditos e Agradecimentos
Para conhecer todas as tecnologias e projetos que tornaram o PhoenixDub possível, consulte o arquivo [CREDITS.md](CREDITS.md).

---

## English

**PhoenixDub AI** is an advanced **software engineering and AI solution** designed for **automated video editing, voice synchronization, and dubbing** into Portuguese (PT-BR).

The core technical highlight of the project is its **extreme hardware efficiency**: complex AI pipelines (voice synthesis, ASR transcription, speaker diarization) optimized to run **100% locally on entry-level GPUs (NVIDIA RTX 3050 6GB VRAM)**, eliminating cloud costs and third-party API lock-in.

👉 **Author Portfolio & Bio:** [https://narravox.github.io/bio/](https://narravox.github.io/bio/)

---

### 🎥 Visual Showcase & Interface

![NarraVox Sentinel Dashboard](assets/Image_fx_1.jpg)

🎬 **[Click Here to Watch Call of Duty: MW3 Dubbing Demo on YouTube (1 Minute)](https://youtu.be/E3HuG6ju7W8)**  
*(Real video demonstration of a Call of Duty: Modern Warfare 3 cutscene automatically dubbed into Portuguese PT-BR by PhoenixDub AI)*

---

### 🛠️ Tech Stack & AI Models

* **Core Language:** Python 3.10+
* **AI Models & ASR:** OpenAI Whisper (ASR), Qwen3-TTS (Voice Synthesis), Pyannote.audio 3.1 (Speaker Diarization)
* **Hardware Acceleration:** PyTorch with CUDA backend, Dynamic VRAM Management (Offloading)
* **Desktop Interface & Orchestration:** Flask, WebSockets, HTML5/CSS3 (Glassmorphism Design), Multiprocessing Suite
* **Media & Audio Processing:** FFmpeg Full Build Core, eSpeak-NG engine

---

### 🧠 💡 Engineering Highlights & Technical Architecture

1. ⚡ **VRAM Management & Memory Offloading (Target 6GB):**
   - Resource scheduling architecture that handles memory allocation and model offloading (e.g., clearing LLM instances prior to TTS generation), preventing *Out-Of-Memory (OOM)* crashes on entry-level GPUs.
2. 🔄 **Concurrent Pipeline with Time Preservation:**
   - Multi-threaded CUDA queue manager for batch game audio dubbing, implementing automated pitch and speed adjustments to strictly match original file durations.
3. 🏛️ **Microservice-based Modular Desktop Architecture:**
   - The master controller (`nexus_app.py`) orchestrates 4 isolated sub-services running on dedicated local ports:
     - **Port 5000:** Master Sentinel Dashboard
     - **Port 5002:** Batch Game Dubbing Engine (`nexus_dub_games.py`)
     - **Port 5003:** Portable Audio Waveform Editor (`narravox_editor.py`)
     - **Port 5004:** Video & Trailer Dubbing Engine (`nexus_dub_video.py`)

---

> [!TIP]
> ### 📥 DIRECT 1-CLICK DOWNLOADS (.EXE)
> Download the 2 executables directly to your PC:  
> 1. 👉 [**[Step 1] Download Automated Installer: Setup_Nexus.exe (225 MB)**](https://github.com/NarraVox/PhoenixDub-AI/releases/latest/download/Setup_Nexus.exe)  
> 2. 👉 [**[Step 2] Download Main Suite: Nexus_AI_Pro.exe (213 MB)**](https://github.com/NarraVox/PhoenixDub-AI/releases/latest/download/Nexus_AI_Pro.exe)

---

### 🖥️ System Requirements
* **Processor:** Intel (6th Gen+) or AMD equivalent
* **Graphics Card (MANDATORY):** Dedicated NVIDIA GPU with CUDA support
  * *Recommended:* NVIDIA RTX 3050 (6GB VRAM) or higher
* **RAM:** Minimum 16 GB

---

### 🛠️ Troubleshooting (FAQ)

| Issue | Solution |
| :--- | :--- |
| **"Invalid audio stream" or MP3 error** | Install **FFmpeg FULL** build (Gyan.dev). |
| **"Out of Memory" or Error 1455** | Close LM Studio when prompted to free VRAM. |
| **"espeak-ng not found"** | Install eSpeak-NG .msi package and restart. |

---
*Developed with ❤️ by Paulo Henrik Carvalho de Araújo.*
| Ensure eSpeak-NG is correctly installed. |
| **Error 1234 (Connection Refused)** | LM Studio "Start Server" is not toggled on. |

---

### 🎖️ Credits and Acknowledgments
To meet the incredible people and technologies behind PhoenixDub, check the [CREDITS.md](CREDITS.md) file.

---
*Developed with ❤️ by Paulo Henrik Carvalho de Araújo.*
