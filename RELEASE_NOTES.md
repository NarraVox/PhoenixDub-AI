# ⚡ PhoenixDub AI v0.6.0 - "The Stage Batch & Security Update" 🛡️

* 📌 **Versão:** v0.6.0 (Beta)
* 🎯 **Hardware Alvo:** NVIDIA RTX 3050 (6GB VRAM)
* 📜 **Licença:** Apache 2.0 (Open-Source Livre)

Esta atualização traz recursos monumentais focados em **produtividade em lote para modders**, **performance extrema de VRAM (6GB)** e **reforço de segurança no ecossistema NarraVox**.

---

### 🌟 O que há de novo (Highlights):

#### ⚡ 1. Fila de Dublagem por Estágios de IA (Stage Batch Queue)
- **Otimização de VRAM:** Execute múltiplas pastas de áudio em lote! O sistema roda o Whisper em todas as pastas (Estágio 1), depois a Tradução LLM (Estágio 2), depois o Qwen3-TTS (Estágio 3) e finaliza na Masterização (Estágio 4).
- **Economia de Tempo:** Cada modelo de IA é carregado na VRAM apenas **1 vez por lote**, economizando memória e acelerando o processamento em GPUs modestas (RTX 3050 6GB Target).
- ⚠️ **Nota Experimental (Beta):** Recurso implementado recentemente! Como é um motor recém-lançado nesta versão v0.6.0, ainda está em fase de validação e pode apresentar instabilidades em cenários específicos. Pedimos a ajuda da comunidade para testar e reportar eventuais bugs na nossa aba de Issues!

#### 📂 2. Múltipla Seleção de Pastas Sem Alterar Estrutura de Modding
- **Suporte a Ctrl/Shift:** Escolha várias pastas simultaneamente no seletor nativo do Windows.
- **100% Compatível com Repack:** Nenhuma pasta do seu jogo é alterada ou movida. A estrutura original de diretórios permanece intacta para você recriar os arquivos `.pak`, `.pck`, `.vpk` ou `.bank` sem erros.

#### ⏱️ 3. Correção do Cronômetro de Sessão Ativa
- Medição exata do tempo real em que a GPU/CPU esteve trabalhando em memória (`_session_progress_state`), ignorando totalmente as horas em que o programa esteve fechado.

#### 🛡️ 4. Blindagem de Segurança (Security Hardening)
- **Anti-Command Injection:** Sanitização de títulos no `os.system` para evitar injeção de comandos CMD.
- **Proteção Total de API:** Binding em `127.0.0.1`, monkeypatch `SecuredFlask` contra CSRF/Path Traversal e travas atômicas de gravação (`safe_json_write`).

#### 🔄 5. Checagem Automática de Atualizações por Build Hash (Git SHA)
- Endpoint `/api/check-update` para comparação de impressões digitais de código entre a build local e o GitHub.

---

### 📥 Executáveis da Release (Download Direto):
- **`Setup_Nexus.exe`** (Instalador Automático 1-Clique)
- **`Nexus_AI_Pro.exe`** (Executável da Aplicação Principal)
