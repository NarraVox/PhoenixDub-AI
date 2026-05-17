# PhoenixDub AI 🚀🔥

[Português](#português) | [English](#english)

---

### 🗨️ Participe da nossa Comunidade! / Join our Community!
**Queremos ouvir você!** Se você baixou o projeto, por favor, deixe seu feedback, sugestões ou poste seus resultados na nossa aba de [**Discussões (Discussions)**](https://github.com/rick60496/PhoenixDub-AI/discussions). Sua opinião é fundamental para a evolução do PhoenixDub!

---

## Português

**PhoenixDub AI** é uma solução completa de **edição de vídeo e dublagem automatizada** de nível profissional. Projetado para alta precisão, fluxo natural e extrema resiliência, o PhoenixDub utiliza IAs de última geração para processar, editar e sincronizar vídeos e jogos em Português (PT-BR) de forma inteligente.

Meu site que tem todos os projetos que fiz até o momento
https://narravox.github.io/bio/



> [!IMPORTANTE]
> ### 🖥️ Requisitos do Sistema (Atualizado)
> * **Processador**: Compatível com Intel (6ª geração ou superior) ou equivalente AMD
> * **Placa de Vídeo (OBRIGATÓRIA)**: GPU dedicada com suporte a CUDA
>   * *Recomendado*: NVIDIA RTX 3050 (6GB) ou superior
> * **Memória RAM**: Mínimo de 16 GB

### 🌟 O que há de novo na Versão 0.10 (TURBO-PATCH-UNLEASHED)
*   **Modo Turbo Ativado**: Desativamos o raciocínio interno da IA para aumentar a velocidade em até 10x em CPUs i5/i7.
*   **Universal Hardware Support**: Detecção inteligente e automática de NVIDIA (CUDA), AMD (ROCm), Apple (MPS) e CPU.
*   **AI Video Editing**: O motor `App_videos` agora conta com o **Magic Cut**, que remove silências e falhas de gravação automaticamente via IA.
*   **Thinking Scrubber**: Filtro que elimina "vazamentos" de pensamentos da IA nas traduções.
*   **Web Interface Auto-Detect**: Opções de idioma e vozes agora começam em "Auto-Detectar" por padrão.

### 🚀 Tutorial de Instalação (Passo a Passo)

> [!TIP]
> ### 📦 Versão Portátil Independente (.EXE) - Recomendado!
> Se você prefere **não instalar Python, Anaconda ou Git manualmente**, pode baixar o instalador único executável compilado automaticamente pelo nosso GitHub Release:
> 1. Acesse as **Releases** do projeto no GitHub.
> 2. Baixe o arquivo `setup.exe` mais recente.
> 3. Execute o instalador para configurar toda a suíte de forma automática no Windows.
> 4. Abra o estúdio instantaneamente clicando no atalho do **NarraVox Sentinel** criado na sua Área de Trabalho!

#### Passo 1: Ferramentas de Base (Obrigatório)
1.  **Git para Windows**: [Baixe Aqui](https://git-scm.com/download/win). (Essencial para baixar a IA).
2.  **Anaconda (ou Miniconda)**: [Baixe Aqui](https://www.anaconda.com/download). **Marque "Add to PATH"** durante a instalação.
3.  **eSpeak-NG**: [Baixe o .msi X64 Aqui](https://github.com/espeak-ng/espeak-ng/releases). **VITAL**: O motor de voz não funciona no Windows sem ele.

#### Passo 2: O Cérebro de Tradução (LM Studio)
1.  Instale o **LM Studio** ([lmstudio.ai](https://lmstudio.ai)).
2.  Pesquise e baixe: `unsloth/gemma-4-E4B-it-GGUF` (Recomendado: Q4_K_M).
3.  Em **Local Server**, clique em **Start Server** na porta **1234**.
4.  > [!CAUTION]
    > **USUÁRIOS NVIDIA RTX**: Após a fase de tradução, o programa pedirá para você **FECHAR O LM STUDIO**. Isso é obrigatório para liberar a memória (VRAM) para o motor de voz.

#### Passo 3: Token HuggingFace (Opcional, mas Recomendado)
1.  No terminal (Anaconda Prompt), digite: `huggingface-cli login`.
2.  Cole seu Token de acesso (gerado no site huggingface.co).

#### Passo 4: Rodando o Instalador/Reparador
Na pasta do projeto, você pode rodar o setup inteligente diretamente:
*   **Via Windows (Duplo Clique - Altamente Recomendado)**: Rode o arquivo `TESTAR_SETUP.bat` para iniciar o instalador e verificar os requisitos.
*   **Via Terminal (Anaconda Prompt)**:
    ```bash
    python build_tools/nexus_setup.py
    ```
*   **Em caso de erros graves de arquivos travados**: Execute o arquivo `REPARAR_TOTAL.bat`. Ele vai fechar todos os processos fantasmas do Python, limpar a pasta do ambiente virtual `env` e reinstalar do zero de forma limpa!

#### Passo 5: Como Rodar e Usar (A Hora da Verdade) 🎮
Agora que tudo está instalado, veja como abrir a suíte completa de aplicativos pelo **Anaconda Prompt**:

1. **Ative o ambiente virtual** (VITAL):
   ```bash
   conda activate C:\IA_dublagem\env
   ```
2. Entre na pasta do projeto:
   ```bash
   cd C:\IA_dublagem
   ```
3. Digite o comando único para abrir a Central NarraVox:
   ```bash
   python nexus_app.py
   ```
4. **Pronto!** O aplicativo mestre **NarraVox Studios Sentinel** abrirá em uma janela desktop dedicada e bonita, iniciando automaticamente todos os motores em segundo plano (Dublagem de Jogos, Vídeos, Editor de Áudio e Vortex DJ).
5. Se preferir abrir manualmente no navegador (Chrome ou Edge), acesse: `http://localhost:5000`

---

### 🛠️ Configuração do FFmpeg FULL (Obrigatório)

Diferente do FFmpeg comum, você precisa da versão **completa** para gerar arquivos MP3 e vídeos de alta qualidade:

1. Acesse: [Gyan.dev (FFmpeg Full)](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z)
2. Baixe o arquivo `ffmpeg-release-full.7z`.
3. Extraia e copie o arquivo `ffmpeg.exe` (da pasta `bin`) para:
   - `C:\IA_dublagem\env\Library\bin\ffmpeg.exe`
   - (Substitua o arquivo que já estiver lá).

---

### 🕹️ Os Motores do Ecossistema NarraVox

O NarraVox Sentinel centraliza 5 motores de ponta em uma única interface inteligente:

*   **Central de Controle (`nexus_app.py`)**: O aplicativo desktop principal que inicializa todos os sub-motores em portas isoladas e exibe a interface unificada na porta 5000.
*   **Dublagem de Jogos (`nexus_dub_games.py`)**: Especialista em traduzir e dublar centenas de arquivos de áudio de games em lote na porta 5002. Possui sistema de threads paralelas CUDA e respeito rigoroso ao tempo original.
*   **Dublagem de Vídeos (`nexus_dub_video.py`)**: Dublador completo de vídeos e trailers longos na porta 5004, com orquestração inteligente de Pyannote 3.1 para vozes nativas e Whisper para transcrição ultrarrápida.
*   **Editor Portátil (`narravox_editor.py`)**: Editor visual de ondas de áudio na porta 5003 para refinar ou cortar trechos gerados com facilidade.
*   **Vortex DJ (`vortex_dj.py`)**: O motor avançado de inteligência artificial voltado a músicas e sets na porta 5005, com análise técnica (BPM, tom e espectro) e mixagem profissional via comandos complexos de FFmpeg.

---

### 🛠️ Solução de Problemas (FAQ)

| Problema | Solução |
| :--- | :--- |
| **"Invalid audio stream" ou erro MP3** | Você está usando o FFmpeg básico. Instale o **FFmpeg FULL** como descrito acima. |
| **"Out of Memory" or Error 1455** | Você não fechou o LM Studio quando o programa pediu. Feche-o para liberar VRAM. |
| **"espeak-ng not found"** | Você esqueceu o Passo 1. Instale o eSpeak-NG e reinicie o PC. |
| **O som da dublagem sai mudo** | Verifique se o eSpeak-NG está instalado corretamente. |
| **Erro 1234 (Connection Refused)** | O LM Studio não está com o "Start Server" ligado. |

### 🎖️ Créditos e Agradecimentos
Para conhecer todas as pessoas e tecnologias envolvidas no PhoenixDub, veja o arquivo [CREDITS.md](CREDITS.md).

---

## English

**PhoenixDub AI** is a complete **AI Video Editing and automated dubbing** solution for professional-grade media projects. Designed for high precision and natural flow, it uses state-of-the-art AI to edit and synchronize videos and games into Portuguese (PT-BR).

> [!IMPORTANT]
> ### 🖥️ System Requirements (Updated)
> * **Processor**: Compatible with Intel (6th Gen or newer) or AMD equivalent
> * **Graphics Card (MANDATORY)**: Dedicated GPU with CUDA support
>   * *Recommended*: NVIDIA RTX 3050 (6GB) or higher
> * **System Memory (RAM)**: Minimum of 16 GB

### 🌟 What's New in v0.10 (TURBO-PATCH-UNLEASHED)
*   **Turbo Mode Activated**: Disabled internal AI reasoning for up to 10x speed boost on i5/i7 CPUs.
*   **Universal Hardware Support**: Smart auto-detection for NVIDIA (CUDA), AMD (ROCm), Apple (MPS), and CPU.
*   **AI Video Editing**: The `App_videos` engine now features **Magic Cut**, automatically removing silences and recording errors.
*   **Thinking Scrubber**: Filter to eliminate AI "thought leaks" in translations.
*   **Web Interface Auto-Detect**: Language and speaker options now default to "Auto-Detect".

### 🚀 Installation Tutorial (Step-by-Step)

> [!TIP]
> ### 📦 Standalone Portable Version (.EXE) - Recommended!
> If you prefer **not to install Python, Anaconda, or Git manually**, you can download the consolidated single-executable installer generated automatically via our GitHub Releases:
> 1. Go to the project's **Releases** page on GitHub.
> 2. Download the latest `setup.exe` file.
> 3. Run the installer to automatically configure the entire suite on Windows.
> 4. Launch the studio instantly using the **NarraVox Sentinel** shortcut created on your Desktop!

#### Step 1: Base Tools (Mandatory)
1.  **Git for Windows**: [Download Here](https://git-scm.com/download/win). (Essential for downloading the AI models).
2.  **Anaconda (or Miniconda)**: [Download Here](https://www.anaconda.com/download). **Check "Add to PATH"** during installation.
3.  **eSpeak-NG**: [Download .msi X64 Here](https://github.com/espeak-ng/espeak-ng/releases). **VITAL**: The voice engine will NOT work on Windows without it.

#### Step 2: The Translation Brain (LM Studio)
1.  Install **LM Studio** ([lmstudio.ai](https://lmstudio.ai)).
2.  Search and download: `unsloth/gemma-4-E4B-it-GGUF` (Recommended: Q4_K_M).
3.  In **Local Server**, click **Start Server** on port **1234**.
4.  > [!CAUTION]
    > **NVIDIA RTX USERS**: After the translation phase, the program will ask you to **CLOSE LM STUDIO**. This is mandatory to free up VRAM for the voice engine.

#### Step 3: HuggingFace Token (Optional, but Recommended)
1.  In your terminal (Anaconda Prompt), type: `huggingface-cli login`.
2.  Paste your access Token (generated at huggingface.co).

#### Step 4: Running the Installer/Repair Tool
In the project folder, you can run the intelligent setup utility directly:
*   **Via Windows (Double Click - Highly Recommended)**: Run the `TESTAR_SETUP.bat` file to launch the setup interface and verify all dependencies.
*   **Via Terminal (Anaconda Prompt)**:
    ```bash
    python build_tools/nexus_setup.py
    ```
*   **In case of locked files or critical errors**: Run `REPARAR_TOTAL.bat`. It will forcefully terminate any frozen Python instances, clean up the virtual environment directory (`env`), and reinstall a clean copy from scratch!

#### Step 5: How to Run and Use 🎮
Now that everything is installed, here's how to launch the complete application suite via **Anaconda Prompt**:

1. **Activate the virtual environment** (VITAL):
   ```bash
   conda activate C:\IA_dublagem\env
   ```
2. Navigate to the project folder:
   ```bash
   cd C:\IA_dublagem
   ```
3. Type the single master command to launch the NarraVox Hub:
   ```bash
   python nexus_app.py
   ```
4. **Done!** The master **NarraVox Studios Sentinel** app will open directly in a dedicated, beautiful desktop window, automatically initializing all background engines (Games, Videos, Audio Editor, and Vortex DJ).
5. If you prefer to access it manually via web browser (Chrome or Edge), navigate to: `http://localhost:5000`

---

### 🛠️ FFmpeg FULL Setup (Mandatory)

Unlike basic FFmpeg, you need the **Full** build to support MP3 encoding and high-quality video:

1. Visit: [Gyan.dev (FFmpeg Full)](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z)
2. Download `ffmpeg-release-full.7z`.
3. Extract and copy the `ffmpeg.exe` file (from the `bin` folder) to:
   - `C:\IA_dublagem\env\Library\bin\ffmpeg.exe`
   - (Overwrite the existing file).

---

### 🕹️ The NarraVox Ecosystem Engines

The NarraVox Sentinel centralizes 5 cutting-edge AI engines within a single unified control panel:

*   **Master Sentinel Hub (`nexus_app.py`)**: The core desktop app that initializes all sub-services on isolated ports and coordinates the unified user interface on port 5000.
*   **Game Dubbing (`nexus_dub_games.py`)**: Highly optimized batch processor on port 5002 for gaming audio assets. Utilizes concurrent multithreaded CUDA queues and strict time preservation logic.
*   **Video Dubbing (`nexus_dub_video.py`)**: End-to-end translation and voice cloning for movies and trailers on port 5004. Orchestrates Pyannote 3.1 speaker tracking and GPU-accelerated Whisper transcription.
*   **Audio Editor (`narravox_editor.py`)**: A portable visual audio workspace on port 5003 for real-time waveform edits and fine-tuning.
*   **Vortex DJ (`vortex_dj.py`)**: Advanced AI-driven music curation and analysis assistant on port 5005, supporting technical audits (BPM, key, energy profiling) and professional mix renders.

---

### 🛠️ Troubleshooting (FAQ)

| Issue | Solution |
| :--- | :--- |
| **"Invalid audio stream" or MP3 error** | You are using basic FFmpeg. Install **FFmpeg FULL** as described above. |
| **"Out of Memory" or Error 1455** | You didn't close LM Studio when prompted. Close it to free up VRAM. |
| **"espeak-ng not found"** | You missed Step 1. Install eSpeak-NG and restart your terminal/PC. |
| **Dubbed audio is silent** | Ensure eSpeak-NG is correctly installed. |
| **Error 1234 (Connection Refused)** | LM Studio "Start Server" is not toggled on. |

---

### 🎖️ Credits and Acknowledgments
To meet the incredible people and technologies behind PhoenixDub, check the [CREDITS.md](CREDITS.md) file.

---
*Developed with ❤️ by Paulo Henrik Carvalho de Araújo.*
