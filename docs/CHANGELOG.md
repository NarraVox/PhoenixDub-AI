# Changelog

Todas as mudanÃ§as notÃ¡veis neste projeto serÃ£o documentadas neste arquivo.

## [0.02.0] - A Trava de Ouro (app_jogos)

AtualizaÃ§Ã£o massiva de estabilidade, sincronia de Ã¡udio e inteligÃªncia do pipeline `app_jogos.py`:

### ðŸš€ Novidades (Features)
- **Instalador Supremo (`setup.py`)**: AutomaÃ§Ã£o total. Download autÃ´nomo do modelo de traduÃ§Ã£o (Gemma 3 4B) e verificaÃ§Ã£o inteligente via *Smart Cache* (pula download se o arquivo de 4.5GB jÃ¡ existir).
- **Audio Sync Absoluto (Fim do "Pitch Lento")**: Injetada uma trava de exportaÃ§Ã£o rÃ­gida de `44.1kHz` (PadrÃ£o de CD) para arquivos `native_wav`. Impede matematicamente que misturas de vozes geradas em 24kHz e ruÃ­dos originais de 48kHz corrompam a velocidade ao passarem pelo `concat` final do FFmpeg.
- **Micro-Chunking Elevado (25s)**: O limite de particionamento dinÃ¢mico do Whisper foi cravado oficialmente em 25.0 segundos. A IA agora respeita o fÃ´lego humano longo e para de quebrar bruscamente em palavras soltas.
- **PreservaÃ§Ã£o Direta (Original Audio Bypass)**: Se o texto for idÃªntico ao original (ex: "Papa Soochong!" ou rugidos de monstros), o motor ignora o Chatterbox e clona a mesma voz do ator americano direto da raiz, repassada para 24.000Hz (fim das faixas mudas criadas indevidamente na versÃ£o anterior).

### ðŸ› CorreÃ§Ãµes (Bugfixes)
- **Filtro Anti-Frenagem Chatterbox (O Truque da VÃ­rgula)**: Para extinguir o famigerado bug de "Gritos e Ecos" (`aaaaa`) e o corte agudo abrupto do Ã¡udio no fim das palavras, o pipeline injeta as falas num Filtro Regex que altera todos os Pontos Finais soltos (`.`) por VÃ­rgulas (`,`), mantendo reticÃªncias (`...`) intactas. O Chatterbox agora exala a respiraÃ§Ã£o adequadamente.
- **Blindagem do Windows Defender**: Implementado um loop robusto de *Exponential Backoff* (5 tentativas) nas transferÃªncias de fase final, aniquilando os crashes por "Acesso Negado/PermissionError" gerados pelas varreduras silenciosas do antivÃ­rus no Windows.

---

## [0.03.0] - Gema 4 & Sincronia Inteligente

AtualizaÃ§Ã£o de peso focada na migraÃ§Ã£o para o motor **Gema 4**, naturalidade extrema da voz e inteligÃªncia tÃ¡tica de traduÃ§Ã£o:

### ðŸš€ Novidades (Features)
- **Upgrade Gema 4**: TransiÃ§Ã£o completa do motor de raciocÃ­nio (Gemini 4). Melhora drÃ¡stica na compreensÃ£o de contextos complexos, tom de voz e adaptaÃ§Ã£o cultural de gÃ­rias.
- **Silence Auto-Trimming (`App_videos`)**: Injetado filtro `silenceremove` que corta cirurgicamente respiraÃ§Ãµes e ar morto nas pontas dos Ã¡udios gerados pelo XTTS. Isso libera espaÃ§o precioso para a fala sem precisar acelerar o Ã¡udio.
- **ProteÃ§Ã£o de Sujeito (Hardened Sync)**: Novo algoritmo de "Prompt Shield" que impede o Gema de remover o sujeito principal da frase (ex: "A cidade") durante simplificaÃ§Ãµes de sincronia.
- **ErradicaÃ§Ã£o do "TraduquÃªs"**: Novas diretrizes de traduÃ§Ã£o que priorizam expressÃµes idiomÃ¡ticas curtas em PT-BR (ex: "Antes" em vez de "Uma vez") para melhor fluxo vocal.
- **Perfilador de Jogos (XCOM Support)**: LanÃ§amento do sistema de perfis dinÃ¢micos. InclusÃ£o do perfil *The Bureau: XCOM Declassified* com volume de cinema (-16 LUFS) e glossÃ¡rio tÃ¡tico dos anos 60.
- **Smart Merge Nativo**: A lÃ³gica de mesclagem inteligente agora Ã© embutida no nÃºcleo do script (`App_videos.py`), eliminando dependÃªncias externas e aumentando a estabilidade.

### ðŸ› CorreÃ§Ãµes (Bugfixes)
- **Trava de Velocidade Natural (Max 1.20x)**: Reduzido o teto de aceleraÃ§Ã£o no App_videos de 30% para 20%, garantindo que nenhuma voz soe como "esquilo", aproveitando o tempo ganho com o Silence Trimming.
- **Threshold de DiarizaÃ§Ã£o (0.65)**: Refinamento da separaÃ§Ã£o de vozes agora que o Ã¡udio Ã© prÃ©-limpo. Impede a fusÃ£o indesejada de vozes masculinas e femininas.
- **Reference Gen Finalization**: A geraÃ§Ã£o do arquivo unificado de referÃªncia (`_REF_VOZ_UNIFICADA.wav`) agora ocorre estritamente apÃ³s todas as consolidaÃ§Ãµes de orador.
---

## [v2026.11.2] - Cofre de Ferro & Turbo Hardware (v2026.11.2)

Esta atualizaÃ§Ã£o foca na seguranÃ§a absoluta dos dados editados pelo usuÃ¡rio e na performance mÃ¡xima para placas de vÃ­deo com 6GB de VRAM (RTX 2060).

### ðŸš€ Novidades (Features)
- **Cofre de Ferro (Manual Edit Iron Vault):** ProteÃ§Ã£o multinÃ­vel para o campo `manual_edit_text`.
    - **Re-Sync Reverso:** O sistema agora detecta se a pasta de backups foi limpa e reconstrÃ³i os arquivos vitais automaticamente a partir do que estiver salvo no `project_data.json`.
    - **FusÃ£o Inteligente (Intelligent Merge):** Impede que backups vazios ou antigos sobrescrevam ediÃ§Ãµes manuais recentes. A memÃ³ria do programa agora Ã© a "Fonte da Verdade".
- **OtimizaÃ§Ã£o R-3000/RTX-2060 (Hardware Proativo):**
    - **Ajuste de VRAM Permissivo:** O "Modo Turbo" (CUDA) agora aceita rodar com apenas **800MB** livres na GPU (antes exigia 1.5GB).
    - **DiagnÃ³stico Inicial:** Agora o programa avisa logo na Etapa 1 se o LM Studio estÃ¡ pesando na placa, sugerindo o fechamento para acelerar a TranscriÃ§Ã£o e DiarizaÃ§Ã£o em atÃ© 20x.

### ðŸ› CorreÃ§Ãµes (Bugfixes)
- **ProteÃ§Ã£o contra Overwrite Silencioso:** Removida a lÃ³gica que "limpava" segmentos quando o arquivo de backup fÃ­sico estava ausente.
- **Fix NameError `backup_path`:** Corrigido erro de execuÃ§Ã£o que ocorria ao tentar retomar trabalhos com as novas travas de seguranÃ§a ativas.

---

## [0.09] - PHOENIX-STABLE-TIME (O OdÃ´metro de PrecisÃ£o)

Esta atualizaÃ§Ã£o traz o controle total de tempo de engenharia e a eliminaÃ§Ã£o definitiva de erros de escopo que causavam travamentos silenciosos no pipeline.

### ðŸš€ Novidades (Features)
- **OdÃ´metro de Tempo (Cumulative Timing):** O tempo total do projeto agora Ã© persistente. Se vocÃª fechar o programa e retomar o trabalho amanhÃ£, o cronÃ´metro continua exatamente de onde parou (ex: de 53:40 em diante), registrando o custo real de tempo do seu projeto.
- **Painel de Monitoramento High-Fidelity:** Todas as barras de progresso (Whisper, Gema e Chatterbox) agora exibem:
    - **RelÃ³gio de Parede `[HH:MM:SS]`:** A hora exata em que aquele segmento foi processado.
    - **CronÃ´metro por Segmento `(0.0s)`:** Quanto tempo de hardware cada arquivo levou individualmente.
    - **Tempo Total da Jornada:** ExibiÃ§Ã£o clara do tempo acumulado total na barra.
- **Recibo de TraduÃ§Ã£o Minimalista:** SubstituiÃ§Ã£o dos logs volumosos por uma linha Ãºnica e elegante `âœ… [Hora] Segmento Traduzido`, mantendo o terminal limpo para apresentaÃ§Ãµes.

### ðŸ› CorreÃ§Ãµes (Bugfixes)
### ðŸ › CorreÃ§Ãµes (Bugfixes)
- **ErradicaÃ§Ã£o de UnboundLocalError (`time`):** RefatoraÃ§Ã£o atÃ´mica do escopo de variÃ¡veis. Removidos todos os imports locais de `time` que causavam conflitos no Python 3.x, garantindo que o cronÃ´metro nunca mais trave a thread de traduÃ§Ã£o.
- **EstabilizaÃ§Ã£o de Workers Silenciosos:** Corrigido o bug onde os tradutores "morriam" no final da tarefa por falta de referÃªncia ao relÃ³gio, o que deixava a barra de progresso congelada.
- **Bypass de Cache Corrompido:** OtimizaÃ§Ã£o na triagem de segmentos russos para ignorar resquÃ­cios de texto antigo na pasta de backups em projetos reiniciados do zero.

---

## [0.5.0] - A Grande Reconstrução (The Sentinel Update) - v0.5.0

A maior atualização da história do projeto, representando o salto após 3 meses de desenvolvimento intensivo desde a v0.10 anterior. O **Nexus AI** agora é a suíte **NarraVox Sentinel**, profissional e distribuível, contendo os módulos Games, Vídeos, Vortex Music e Cine Gen.

### ðŸš€ Novidades (Features)
- **Unificao 'Nexus Core':** Fuso atmica dos scripts. No existe mais diviso entre 'Jogos' e 'Vdeos' no cdigo base; tudo agora roda sob o motor unificado 'nexus_core.py'.
- **Interface Premium Webview:** Substituio do terminal/navegador comum por uma janela nativa moderna (Neon Dark Design). O programa agora se comporta como um aplicativo Windows real.
- **Web Installer Inteligente ('Setup_Nexus.exe'):** O instalador agora baixa automaticamente apenas o necessÃ¡rio, cria o ambiente virtual isolado e configura a GPU RTX ou CPU sem interveno do usuÃ¡rio.
- **Diarizao Cirrgica v10.60:** Implementado o sistema de corte por silncio preservado (0.3s padding), eliminando respiraes cortadas no meio e garantindo um fluxo de fala ultra-natural.
- **Auto-Update de Ativos:** O executvel agora extrai os arquivos de interface ('client/') e recursos ('resources/') automaticamente na primeira execuo.

### ðŸ›¡ï¸ Segurana e Integridade
- **Verificao SHA256:** Cada release agora acompanha um selo de integridade matemtica.
- **Hash SHA256 (v2026.Pro):** 65767AC8017181B5A46B8D9AA59930AEA91B82FEC5E515752034D38AD3CB93FD
- **Isolamento de Ambiente:** O sistema agora roda 100% dentro da pasta local ('env'), sem poluir o Python global do Windows.

### ðŸ› Correes (Bugfixes)
- **Fim das Importaes Fantasmas:** Resolvido o erro 'Falha ao importar App_videos'. Todas as referncias legadas foram migradas para o novo motor 'nexus_video_engine'.
- **Correo de Loop Circular:** Resolvido o conflito onde o Core e o Motor de Vdeo tentavam se carregar mutuamente, causando crash no servidor.
- **Estabilizao de Rotas Flask:** Removidas rotas duplicadas ('/dublar') que causavam comportamentos imprevisveis na UI.
