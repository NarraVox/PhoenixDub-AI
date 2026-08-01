Esta versão introduz a **Arquitetura de Fila por Estágios de IA**, otimizando a memória VRAM e trazendo **blindagem de segurança de nível industrial** para criadores e modders.

## 🌟 O que há de novo na v0.6.0:

### ⚡ 1. Fila de Dublagem por Estágios de IA (Stage Batch Queue)
- **Otimização Extrema de VRAM:** Execute múltiplas pastas de áudio em lote! O motor processa o Whisper em todas as pastas (Estágio 1), a Tradução LLM (Estágio 2), o Qwen3-TTS Titan (Estágio 3) e finaliza na Masterização (Estágio 4).
- **Recarga Zero de Modelo:** Cada modelo de IA é carregado na placa de vídeo apenas **1 vez por lote**, economizando memória e acelerando o processamento em GPUs de 6GB (RTX 3050 Target).
- ⚠️ **Nota Experimental (Beta):** Recurso de ponta recém-implementado nesta versão v0.6.0. Como está em fase de validação, pedimos a ajuda da comunidade para testar e reportar eventuais bugs na nossa aba de Issues!

### 📂 2. Múltipla Seleção de Pastas Sem Alterar Estrutura de Modding (.pak / .pck)
- **Suporte a Ctrl / Shift:** Escolha várias pastas simultaneamente no seletor nativo do Windows.
- **100% Compatível com Repack:** Nenhuma pasta do seu jogo é alterada ou movida. A estrutura original de diretórios permanece intacta para você recriar os arquivos `.pak`, `.pck`, `.vpk` ou `.bank` sem erros.

### ⏱️ 3. Cronômetro de Sessão Ativa (Sem Drift)
- **Precisão Cirúrgica:** Medição exata do tempo real em que a GPU/CPU esteve trabalhando em memória (`_session_progress_state`), ignorando totalmente as horas em que o programa esteve fechado.

### 🛡️ 4. Blindagem de Segurança e Proteção de Dados
- **Anti-Command Injection:** Sanitização de títulos no `os.system` para evitar injeção de comandos CMD.
- **Isolamento Local (Localhost):** Binding local protegido, monkeypatch `SecuredFlask` contra CSRF/Path Traversal e travas atômicas de gravação (`safe_json_write`).

### 🔄 5. Verificação Automática de Atualizações por Build Hash
- **Impressão Digital Git SHA:** Endpoint `/api/check-update` para comparação automática de hashes de código entre a build local e o GitHub.

> [!TIP]
> ### 📦 Download Direto dos Executáveis (1-Clique)
> - 📥 **Setup_Nexus.exe** (Instalador Automático 1-Clique)
> - 🚀 **Nexus_AI_Pro.exe** (Executável da Aplicação Principal)

---
*NarraVox Studios Premium Suite // Powered by Qwen3-TTS, Whisper ASR & CUDA*
