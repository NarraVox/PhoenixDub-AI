# Atualizações — Diário de evolução do PhoenixDub AI

Este é o mapa cronológico das mudanças do projeto. Consulte-o no início do trabalho e atualize-o ao concluir cada sessão com alterações, para que o fechamento do dia já esteja registrado.

## Como registrar

- Use a data real no formato AAAA-MM-DD, no horário de Brasília, e coloque as entradas mais recentes primeiro.
- O marco atual é 0.8.0, escolhido pelo responsável para o próximo lançamento. Nos próximos dias com mudanças, avance para 0.8.1, 0.8.2 etc., salvo nova decisão de versão. No mesmo dia, complemente a entrada existente. Não crie entradas para dias sem alterações.
- Esses números identificam marcos internos de desenvolvimento. Eles não significam uma release, tag ou executável publicado. A versão pública será escolhida pelo responsável no lançamento.
- Registre o que mudou, por quê, os arquivos principais, a validação realmente executada e as pendências. Não declare testes ou recursos como validados sem evidência.
- Preserve as entradas anteriores. Registre correções posteriores em novas entradas, sem reescrever a história.
- Ao preparar um lançamento, reúna todas as entradas ainda não publicadas em NOTAS_PARA_GITHUB.md e depois em ../RELEASE_NOTES.md. Após a publicação, registre aqui a versão pública, a data, o link e os marcos internos incluídos.

## 0.8.0 — 2026-09-10 — Em preparação para lançamento / não publicada

### Mudanças desta sessão

- Preparação da publicação v0.8.0 autorizada pelo responsável: política de seleção em `release/policy.json`, preparo isolado em `release/prepare_release.py` e procedimento em `docs/PUBLICAR_RELEASE.md`. Preservadas as alterações remotas do README; excluídos dados locais e experimentos. Corrigido o empacotamento do código/interface, mantendo configurações existentes e bloqueando instalação sobre desenvolvimento. Release aguardando validação do GitHub Actions.

- Reforçada a proteção da cópia de desenvolvimento após solicitação do responsável: marcador local `.nexus-development` preservado fora do Git e dos pacotes, detecção também nas pastas ancestrais, indicação no Hub e bloqueio de instalação automática independentemente da versão pública. Versões iguais/anteriores são recusadas novamente pelo aplicador antes de qualquer substituição, incluindo leitura da versão local no disco.
- Validação do atualizador: suíte geral de 44 testes aprovada antes do reforço; depois, 20 testes específicos de atualização aprovados. Conferidos a interface em navegador com release simulada, pacote/manifesto em pasta temporária e consulta real (0.8.0 local > 0.6.0 pública, desenvolvimento protegido, atualização automática desativada). Nenhum código local foi atualizado por pacote e nenhum executável real foi reiniciado.
- Adicionado ao HTML do Hub o botão **Verificar atualizações**, versão instalada e painel com notas, estado da consulta e ação **Atualizar e reiniciar**, conforme escolha do responsável. Nova versão central em `nexus/version.py`; comparação numérica substitui a comparação por desigualdade da rota antiga e falha de rede não é tratada como versão atualizada.
- Implementados `nexus/updates.py`, `update_manager.py` e `update_worker.py`: pacote oficial, SHA-256, manifesto, backup, restauração em erro de cópia e processo externo de reinício. Dados, modelos e configurações locais ficam fora do pacote. Atualização automática bloqueada em checkout Git, motores abertos e mudanças de dependências que exijam instalador.
- Workflow preparado para anexar `PhoenixDub_Update.zip`, gerado por `build_update_package.py`. Procedimento e limites documentados em [ATUALIZACAO_AUTOMATICA.md](ATUALIZACAO_AUTOMATICA.md). O ciclo real com executáveis ainda não foi validado nem publicado.
- Esclarecimento do responsável: Qwen ASR foi somente um teste e ficou mais lento; a decisão é manter Whisper. Retirado das novidades da v0.8.0. Restaurado Whisper em `nexus/core/orchestrator_jobs_core.py` e removidos imports de Qwen ASR da inicialização em `model_loader.py` e `__init__.py`; os arquivos experimentais foram preservados. O benchmark não foi repetido nesta sessão.
- Validação dessa correção: análise de sintaxe dos três módulos Python e busca de referências confirmaram a retirada da seleção/imports de Qwen ASR do fluxo normal; `git diff --check` desses módulos passou. Sem execução de modelo ou teste em GPU.
- Definida a versão pública alvo **0.8.0**, substituindo o marco provisório 0.6.1, por decisão do responsável. Lançamento previsto para 2026-09-10, reunindo as mudanças acumuladas desde a v0.6.0, com destaque para a edição e correção manual de vídeos e jogos. Atualizados o título das notas para o GitHub e as regras de sequência; publicação ainda não realizada.
- Renomeado `RELEASE_DRAFT.md` para `NOTAS_PARA_GITHUB.md`, destinado a preparar o texto de atualização para colar na release do GitHub. Atualizadas as referências e delimitada a seção de publicação.
- Renomeado CHANGELOG.md para ATUALIZACOES.md, com o nome “Atualizações — Diário de evolução do PhoenixDub AI”. O histórico anterior foi preservado abaixo.
- Definido o registro diário de mudanças, validações e pendências, com marcos internos sequenciais.
- Adicionada a regra permanente em ../AGENTS.md e os links de consulta na documentação.

### Levantamento do código concluído em 2026-09-10

- Comparada a tag v0.6.0 com o HEAD local (11 commits posteriores), alterações sem commit e módulos novos. A evidência por área está em [COMPARACAO_0.6.0_0.8.0.md](COMPARACAO_0.6.0_0.8.0.md).
- Ampliadas as notas em [NOTAS_PARA_GITHUB.md](NOTAS_PARA_GITHUB.md): edição manual e em grupo, busca aproximada, rascunhos, prévias, duração das falas, fila e exportação; retomada de lotes, formatos de áudio, saída de State of Decay, preparação de áudio, transcrição, tradução, modelos, fatiador e reinicialização.
- Separados recursos já existentes na v0.6.0, alterações confirmadas no código e módulos sem integração encontrada. Este registro documenta a revisão de hoje; não atribui a implementação das mudanças acumuladas a esta data.

### Situação inicial herdada

A release pública mais recente consultada hoje é a [v0.6.0](https://github.com/NarraVox/PhoenixDub-AI/releases/tag/v0.6.0), publicada em 2026-07-31 no horário de Brasília.

O [rascunho existente](NOTAS_PARA_GITHUB.md) já descrevia alterações posteriores à v0.6.0: painel de correção e redublagem de jogos/vídeos, ajustes de processamento em lote, tratamento de silêncio, carregamento de modelos, organização das saídas, interface, fatiador de vídeos, remoção de motores antigos e ajustes no instalador. Este é um inventário herdado, não uma afirmação de que essas mudanças foram feitas hoje ou validadas nesta sessão. Suas datas individuais ainda não foram reconstruídas.

### Validação

- Nesta sessão: conferência documental, consulta das releases do GitHub e verificação da renomeação, dos links e da preservação do histórico anterior.
- Nenhum teste funcional ou de GPU executado nesta sessão. O rascunho anterior relata 9 testes aprovados; esse resultado é histórico e não foi reexecutado hoje.

Atualização após a revisão de código desta mesma data: `python -m unittest discover -s tests -p 'test_*.py'` passou **31 testes em 41,546 s** com Python 3.12. `node --test tests/test_correction_progress.mjs tests/test_correction_timing.mjs` passou os dois arquivos (5 cenários de progresso e 9 verificações de contagem). São testes com projetos temporários e síntese substituta; nenhuma dublagem real em GPU, instalação limpa ou build foi executada. O resultado anterior de 9 testes foi substituído por esta execução mais abrangente nas notas para publicação.

### Pendências

- Revisar o código e os arquivos novos antes do lançamento, incluindo dependências e configurações locais.
- Validar instalação, executáveis e um fluxo real de dublagem; consultar a lista completa em NOTAS_PARA_GITHUB.md.
- Consolidar as mudanças acumuladas nas notas da v0.8.0 e concluir a preparação e publicação no GitHub.

---

## Histórico anterior — preservado do CHANGELOG.md

As numerações, textos e eventuais problemas de codificação abaixo foram mantidos como estavam. Entradas sem data não receberam datas estimadas. Este histórico não é uma lista completa das releases do GitHub.

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
