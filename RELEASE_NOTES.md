# ⚡ PHOENIXDUB AI v0.6.0 :: NEXUS PROTOCOL 🛡️

> [!NOTE]
> ### 🌌 O FUTURO DA DUBLAGEM LOCAL CHEGOU
> Esta versão introduz a **Arquitetura por Estágios de IA**, reduzindo drasticamente o consumo de VRAM e trazendo **blindagem de segurança de nível industrial** para criadores e modders.

---

### 🌟 🌟 🌟 HIGHLIGHTS TECNOLÓGICOS :: NOVIDADES DA v0.6.0 🌟 🌟 🌟

---

#### ⚡ 1. FILA EM LOTE POR ESTÁGIOS (STAGE BATCH ENGINE)
* 🧠 **Otimização Extrema de VRAM:** Execute múltiplas pastas de áudio em lote! O motor processa o Whisper em todas as pastas (**Estágio 1**), depois o LLM Gemma/Qwen3.5 (**Estágio 2**), depois o Qwen3-TTS Titan (**Estágio 3**) e finaliza na Masterização (**Estágio 4**).
* ⏱️ **Recarga Zero de Modelo:** Cada modelo de IA é carregado na placa de vídeo apenas **1 vez por lote**, economizando memória e acelerando o processamento em GPUs de 6GB (**RTX 3050 Target**).
* ⚠️ **Aviso de Recurso Experimental (Beta):** Recurso de ponta recém-implementado nesta versão v0.6.0. Como está em fase de validação, pedimos o feedback da comunidade para reportar eventuais bugs na nossa aba de Issues!

---

#### 📂 2. SELEÇÃO MÚLTIPLA DE PASTAS PARA MODDING (.PAK / .PCK)
* 🎮 **Suporte a Ctrl / Shift:** Escolha várias pastas simultaneamente na janela nativa do Windows.
* 🛡️ **Preservação de Árvore de Diretórios:** Nenhuma pasta do seu jogo é alterada ou movida. A estrutura original de diretórios permanece 100% intacta para recriação direta de arquivos `.pak`, `.pck`, `.vpk` ou `.bank` sem erros.

---

#### ⏱️ 3. CRONÔMETRO DE SESSÃO ATIVA (SEM DRIFT)
* 🛰️ **Precisão Cirúrgica:** Medição exata do tempo real em que a GPU/CPU esteve trabalhando em memória (`_session_progress_state`), ignorando totalmente as horas em que o programa esteve fechado.

---

#### 🛡️ 4. BLINDAGEM DE SEGURANÇA E PROTEÇÃO DE DADOS
* 🔐 **Anti-Command Injection:** Sanitização de títulos no `os.system` para evitar injeção de comandos CMD.
* 🌐 **Isolamento Local (Localhost):** Binding local protegido, monkeypatch `SecuredFlask` contra CSRF/Path Traversal e travas atômicas de gravação (`safe_json_write`).

---

#### 🔄 5. VERIFICAÇÃO AUTOMÁTICA DE ATUALIZAÇÕES (BUILD HASH)
* 🧬 **Impressão Digital Git SHA:** Endpoint `/api/check-update` para comparação automática de hashes de código entre a build local e o GitHub.

---

> [!TIP]
> ### 📦 DOWNLOAD DIRETO DOS EXECUTÁVEIS (1-CLIQUE)
> * 📥 **Setup_Nexus.exe** (Instalador Automático 1-Clique)
> * 🚀 **Nexus_AI_Pro.exe** (Executável da Aplicação Principal)

---
*NarraVox Studios Premium Suite // Powered by Qwen3-TTS, Whisper ASR & CUDA*
