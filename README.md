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

> [!IMPORTANT]
> ### 💖 Ajude a Financiar a Versão 1.0 e o Cine Gen! (Apoia.se)
> O PhoenixDub é um projeto monumental feito de forma independente (*Bootstrapping*). Nosso foco não é pagar servidores na nuvem, e sim **rodar IAs pesadas localmente no seu computador**.
> * Com a sua ajuda, vamos financiar a **Versão 1.0** (experiência definitiva de dublagem local e a versão beta do gerador de músicas por IA) e a pesquisa futura do projeto **Cine Gen** (gerador de vídeos via IA para PCs modestos).
> * **Sustentabilidade do Projeto:** Hoje me dedico 100% vivendo de economias passadas, mas essa reserva vai acabar em alguns meses. Sem apoiadores suficientes, precisarei assumir um emprego de mercado (44 horas semanais de trabalho pesado) ou um estágio (30 horas semanais), fazendo o ritmo de desenvolvimento do projeto cair 10x ou mais devido ao cansaço e falta de tempo. O seu apoio é o que garante dedicação integral de 100% e atualizações constantes!
> * Apoiadores ganham **Poder de Voto** nas decisões de desenvolvimento, **Suporte VIP** no Discord e **Vídeos de Bastidores**.
> 
> 👉 **[Apoie a NarraVox Studios no Apoia.se clicando aqui!](https://apoia.se/narravox_studios)**

> [!NOTE]
> ### 📢 O Futuro da Dublagem: A Grande Evolução v1.0 está Chegando! 🚀
> O PhoenixDub AI está atualmente na **versão 0.5** (The Sentinel Update). Esta versão é o resultado de 3 meses de intenso desenvolvimento e reescrita total a partir da v0.1 anterior.
> 
> 💡 *Por que saltamos direto para a v0.5?* Focamos em reconstruir o software do zero para entregar estabilidade e usabilidade incomparáveis. O antigo motor Gemma (via LM Studio) foi substituído pelo avançado **Qwen 3.5** local (Qwen3-TTS), e todo o processo de instalação foi automatizado!
> 
> Esta nova versão mudará absolutamente tudo e trará:
> *   📦 **Instalação Descomplicada**: Chega de terminais e linhas de comando! Novo instalador inteligente portátil `.exe` nativo com configuração quase 100% automática em um duplo clique.
> *   🎨 **Interface Premium Ultra-Moderna**: Painel visual espetacular totalmente redesenhado, com layout moderno, micro-animações dinâmicas e controles altamente intuitivos.
> *   🧠 **Revolução na Síntese de Voz**: Migração do antigo motor Chatterbox TTS para o avançado **Qwen3-TTS**, entregando dublagens muito mais naturais, fluidas e expressivas.
> *   🎬 **Editor de Vídeo Integrado**: Foco 100% no fluxo de trabalho de dubladores, com ferramentas nativas para cortar, juntar e sincronizar trechos diretamente na tela.
> *   🎵 **Gerador de Músicas (Vortex Beta)**: Primeira versão experimental do gerador de trilhas e sets musicais assistidos por IA.
> *   ⚡ **Performance RTX Otimizada**: Motores atualizados para extrair o máximo poder de processamento e VRAM de placas como a RTX 3050 com agendamento inteligente.

> [!IMPORTANTE]
> ### 🖥️ Requisitos do Sistema (Atualizado)
> * **Processador**: Compatível com Intel (6ª geração ou superior) ou equivalente AMD
> * **Placa de Vídeo (OBRIGATÓRIA)**: GPU dedicada com suporte a CUDA
>   * *Recomendado*: NVIDIA RTX 3050 (6GB) ou superior
> * **Memória RAM**: Mínimo de 16 GB

### ⚠️ Suporte de Hardware (Aviso Importante)
*   **Exclusivo NVIDIA**: O sistema foi exaustivamente testado, otimizado e usado diariamente na **RTX 3050** (plataforma oficial do fundador). Por conta disso, **não garanto que funcionará em placas AMD** ou Apple M-Series.
*   **Aceleração de IA**: Uma placa de vídeo dedicada NVIDIA RTX é absolutamente obrigatória. O sistema NÃO roda apenas no processador (CPU).

### 🚀 Tutorial de Instalação (Passo a Passo)

> [!TIP]
> ### 📦 Versão Portátil Independente (.EXE) - (Disponível na v0.5!)
> **Atenção:** A partir desta atualização (**Versão 0.5**), você conta com o instalador automatizado. Siga os passos simplificados:
> 1. Acesse as **Releases** do projeto no GitHub.
> 2. Baixe o instalador `Setup_Nexus.exe` da v0.5.
> 3. Execute o instalador para configurar toda a suíte de forma automática no Windows.
> 4. Abra a suite executando o **Nexus AI Pro**!

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
*   **Vortex DJ (`vortex_dj.py`)**: *(🚧 Em Breve)* O futuro motor de inteligência artificial voltado a músicas e sets, atualmente em fase de planejamento e desenvolvimento inicial.

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
> ### 💖 Help Finance Version 1.0 and Cine Gen! (Sponsor Us)
> PhoenixDub is a monumental independent project (bootstrapped). Our goal is not to rely on cloud servers, but to **run heavy AI locally on your PC**.
> * With your help, we will fund **Version 1.0** (the ultimate local dubbing experience and a beta of the AI music generator) and future research for the **Cine Gen** project (local AI video generator).
> * **Project Sustainability:** Today I dedicate 100% of my time living off past savings, but this reserve will run out in a few months. Without enough supporters, I will have to take a traditional job (44 hours/week of demanding work) or an internship (30 hours/week), causing the project's development pace to drop 10x or more due to fatigue. Your support guarantees 100% full-time dedication and constant updates!
> * Sponsors get **Voting Power** on development decisions, **VIP Support** on Discord, and **Behind-the-Scenes Videos**.
> 
> 👉 **[Support NarraVox Studios on Apoia.se by clicking here!](https://apoia.se/narravox_studios)**

> [!NOTE]
> ### 📢 The Future of Dubbing: The Great v1.0 Evolution is Coming! 🚀
> PhoenixDub AI is currently in **version 0.5** (The Sentinel Update). This release is the result of 3 months of intense development and a complete rewrite starting from the previous v0.1.
> 
> 💡 *Why did we leap directly to v0.5?* We focused on completely rewriting the codebase to deliver unmatched stability and usability. The old Gemma engine (via LM Studio) was replaced by the advanced local **Qwen 3.5** (Qwen3-TTS), and the installation process is now fully automated!
> 
> This upcoming release changes absolutely everything and will deliver:
> *   📦 **Super-Easy Installation**: No more terminal inputs! A new smart portable `.exe` installer with near 100% automated setup with a simple double click.
> *   🎨 **Stunning Premium Interface**: A gorgeous, fully redesigned visual control panel with smooth dynamic micro-animations and sleek, intuitive controls.
> *   🧠 **Voice Synthesis Revolution**: Migrating from the old Chatterbox TTS engine to the advanced **Qwen3-TTS**, ensuring far more natural, fluid, and expressive dubbed voices.
> *   🎬 **Integrated Video Editor**: 100% focused on the dubbing experience, with native tools to cut, join, and synchronize tracks directly within the studio.
> *   🎵 **Music Generator (Vortex Beta)**: The first experimental version of our integrated AI music and set generator.
> *   ⚡ **Dedicated RTX Power**: Updated engines optimized to leverage the absolute maximum performance and VRAM of GPUs like the RTX 3050 with smart scheduling.

> [!IMPORTANT]
> ### 🖥️ System Requirements (Updated)
> * **Processor**: Compatible with Intel (6th Gen or newer) or AMD equivalent
> * **Graphics Card (MANDATORY)**: Dedicated GPU with CUDA support
>   * *Recommended*: NVIDIA RTX 3050 (6GB) or higher
> * **System Memory (RAM)**: Minimum of 16 GB

### ⚠️ Hardware Support (Important Notice)
*   **NVIDIA Exclusive**: The system was exhaustively tested, optimized, and used daily on the founder's **RTX 3050**. Because of this, **I do not guarantee it will work on AMD** or Apple M-Series GPUs.
*   **AI Acceleration**: A dedicated NVIDIA RTX GPU is absolutely mandatory. It does NOT run on CPU-only.

### 🚀 Installation Tutorial (Step-by-Step)

> [!TIP]
> ### 📦 Standalone Portable Version (.EXE) - (Available in v0.5!)
> **Note:** Starting with this update (**Version 0.5**), the automated installer is ready. Follow these simplified steps:
> 1. Go to the project's **Releases** page on GitHub.
> 2. Download the `Setup_Nexus.exe` installer for v0.5.
> 3. Run the installer to automatically configure the entire suite on Windows.
> 4. Launch the suite by running **Nexus AI Pro**!

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
*   **Vortex DJ (`vortex_dj.py`)**: *(🚧 Coming Soon)* The future AI-driven music curation engine, currently in the early planning and development phase.

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
