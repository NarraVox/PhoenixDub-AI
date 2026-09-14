# Atualizações — Diário de evolução do PhoenixDub AI

Este é o mapa cronológico das mudanças do projeto. Consulte-o no início do trabalho e atualize-o ao concluir cada sessão com alterações, para que o fechamento do dia já esteja registrado.

## Como registrar

- Use a data real no formato AAAA-MM-DD, no horário de Brasília, e coloque as entradas mais recentes primeiro.
- O marco atual é 0.8.0, escolhido pelo responsável para o próximo lançamento. Nos próximos dias com mudanças, avance para 0.8.1, 0.8.2 etc., salvo nova decisão de versão. No mesmo dia, complemente a entrada existente. Não crie entradas para dias sem alterações.
- Esses números identificam marcos internos de desenvolvimento. Eles não significam uma release, tag ou executável publicado. A versão pública será escolhida pelo responsável no lançamento.
- Registre o que mudou, por quê, os arquivos principais, a validação realmente executada e as pendências. Não declare testes ou recursos como validados sem evidência.
- Preserve as entradas anteriores. Registre correções posteriores em novas entradas, sem reescrever a história.
- Ao preparar um lançamento, reúna todas as entradas ainda não publicadas em NOTAS_PARA_GITHUB.md e depois em ../RELEASE_NOTES.md. Após a publicação, registre aqui a versão pública, a data, o link e os marcos internos incluídos.

## 0.8.2 — 2026-09-14 — Desenvolvimento / não publicada

### Publicação confirmada — v0.8.1

- Publicada em **2026-09-14 00:35:46 (Brasília)**: [PhoenixDub AI v0.8.1](https://github.com/NarraVox/PhoenixDub-AI/releases/tag/v0.8.1). Commit da tag: `0bea94de00c4305eeaa0be4ed144636891ebcc4f`. Consolida os marcos internos 0.8.0, 0.8.1 e 0.8.2; numeração interna e versão pública são independentes.
- GitHub Actions: [validação prévia](https://github.com/NarraVox/PhoenixDub-AI/actions/runs/34802937966) e [publicação](https://github.com/NarraVox/PhoenixDub-AI/actions/runs/34803042393) concluídas com sucesso. Confirmados build dos dois executáveis, testes de inicialização fora do checkout e pacote de atualização.
- Anexos conferidos pela API: `Nexus_AI_Pro.exe` (14.867.405 bytes), `Setup_Nexus.exe` (28.084.512 bytes) e `PhoenixDub_Update.zip` (14.995.920 bytes), todos em estado uploaded, com SHA-256 informado pelo GitHub.
- Revisão final excluiu `nexus/test_api.py`, `nexus/test_api_simple.py` e `nexus/dj/vortex_music_fixed.py`: scripts experimentais/cópia alternativa sem referências no código ativo. Preservados no desenvolvimento e incluídos nas exclusões de `release/policy.json`. Limpeza de espaços feita somente na cópia de release, sem alteração da AST Python.
- Desenvolvimento preservado no HEAD `096c783`; README original e `.nexus-development` intactos. Nenhum atualizador aplicado. Instalação completa com modelos e dublagem real em GPU não foram executadas nesta publicação.

### Mudanças desta sessão

- Correção do setup em preparação para v0.8.2: BAT com diretório fixo e checagem de erros; dependências centralizadas, matriz de Qwen3-TTS/WhisperX reconciliada; FFmpeg/ffprobe locais com SHA-256; corrigido import local de subprocess que interrompia downloads. Nenhum ambiente de desenvolvimento foi reinstalado.
- Privacidade: Git local configurado com noreply da conta; AGENTS.md e assistente passam a impedir e-mail pessoal em novas preparações. Histórico antigo não reescrito; aguardando decisão sobre alcance dessa limpeza.
- Validação até aqui: 89 testes Python aprovados (52,735 s), oito específicos do setup; download real e execução de FFmpeg/ffprobe aprovados em pasta temporária. Resolução de dependências revelou MixingBear 0.1.2 indisponível; retirado da instalação obrigatória, mantendo fallback FFmpeg existente. Nova resolução e validação de instalação limpa no CI em andamento.


- Publicação da v0.8.1 autorizada pelo responsável. Worktree revisado inclui o assistente de preparação; passaram 80 testes Python em 43,075 s, três arquivos JavaScript, análise de sintaxe/padrões de credenciais e git diff --check. Base remota 692bd6e reconferida. Build em nuvem e publicação ainda pendentes neste registro.

- Criada a entrada `PREPARAR_RELEASE.py` na raiz para preparação guiada por IA local. Aceita a versão escolhida, verifica pré-requisitos e metadados, fixa a base remota e usa o preparador existente em destino novo. Modos `--check-only` e `--offline` explícitos; sem carregamento de modelos, instalação, commit, push, tag ou publicação.
- Relatórios resumidos em `_updates/release-assistant/LEIA_PRIMEIRO.txt` e `ULTIMO_RESULTADO.json`, com histórico de logs por execução, códigos de saída e próximo passo. Falhas, timeout, conflito e divergência de hash interrompem o fluxo. Os testes automáticos escolhidos cobrem preparação, assistente, atualização, distribuição e JavaScript; não substituem testes funcionais em GPU.
- Guia curto em `docs/PREPARAR_RELEASE_IA.md`, referenciado por `AGENTS.md`, `docs/PUBLICAR_RELEASE.md` e `docs/documentacao/CONTEXTO_IA.md`. Entrada adicionada à política de distribuição. Implementação em `release/release_assistant.py` e regressões em `tests/test_release_assistant.py`.

### Validação efetivamente realizada

- Sete testes do novo assistente aprovados, incluindo argumento inválido, leitura da versão sem executar código, hash divergente, bloqueio antes da preparação, check-only, erro/timeout e fluxo offline simulado com base fixa.
- Execução real de pré-requisitos: solicitação 0.8.1 bloqueada porque a cópia de desenvolvimento declara 0.8.0; solicitação 0.8.0 retornou PASSOU_PRE_REQUISITOS. Nenhuma dessas verificações criou worktree, acessou a rede ou executou modelos.

### Pendências

- Não foi executada uma nova preparação completa com este assistente no projeto real; o fluxo de sucesso foi testado com comandos simulados e arquivos temporários. A cópia v0.8.1 preparada anteriormente permanece independente e não foi modificada nesta sessão.
- Revisar versão e notas antes da próxima preparação. Build, instalação real, testes em GPU e publicação continuam sendo etapas posteriores. Este marco interno não altera a versão pública escolhida nem significa release publicada.

## 0.8.1 — 2026-09-11 — Desenvolvimento / não publicada

### Mudanças desta sessão

- Por solicitação do responsável, removidos painel, rotas, worker e cache ativo de OpenUnmix adicionados nesta tarefa. Projetos/áudios já salvos foram preservados no disco e ocultados da listagem do Hub. Removida a separação automática da mixagem legada; sem stems previamente disponíveis, ela usa a mixagem comum. Nenhuma desinstalação de dependências compartilhadas foi realizada.
- Extended passa a exportar somente a continuação após o fim do áudio de referência, antes de AudioSR/MP3. O contexto original e a sobreposição de repaint ficam fora da saída final. Se não houver continuação suficiente, o fluxo informa erro em vez de entregar o original como resultado. Interface descreve “Extended — somente a parte nova”.
- Investigado relato de referência errada: último log disponível registra origem e referência de 492,04 s, compatíveis com o Djavu completo (arquivo de 492,016 s), não a bateria do Forró Perfeito de cerca de 74 s. Não foi comprovada reutilização incorreta nessa execução. Para evitar seleção antiga quando um arquivo foi apenas escolhido e não enviado, Gerar agora envia o arquivo pendente antes da síntese, aborta se o upload falhar, limpa a seleção de arquivo após sucesso e mostra/loga a referência ativa. Músicas já enviadas passam a aparecer no seletor; cópias antigas `separated_*` ficam fora dessa lista.
- Arquivos: `nexus/dj/music_request.py`, `vortex_music.py`, `vortex_app.py`, `vortex_dj.py`, `vortex_utils.py`, `vortex_mix.py`, `nexus/nexus_routes.py`, interface/CSS/JS do DJ; removidos `stem_projects.py`, `stem_routes.py`, `stem_worker.py`, `dj_stems.js` e seus testes específicos. Novos testes de referência em `tests/test_music_source.mjs` e recorte em `tests/test_music_request.py`.
- Validação desta mudança: dez testes Python e dois testes JavaScript aprovados, incluindo exclusão do original, rejeição de extensão ausente, upload do Djavu substituindo bateria antiga e falha de upload sem geração. Recorte real de `temp_0_1789104295.wav` produziu `test-output/extended_somente_parte_nova.wav` com exatamente 30 s estéreo. Não foi feita nova síntese em GPU nem teste de mixagem legada nesta etapa; a validação real reutilizou áudio já gerado.

- Adicionados projetos permanentes de separação OpenUnmix (`umxhq`) no Vortex DJ. Quatro WAVs preservados: bateria, baixo, voz e outros instrumentos. Projeto identificado pelo SHA-256 do arquivo original; reutilização confere receita, presença, tamanho e hash das saídas. Mesmo conteúdo renomeado reutiliza o projeto; conteúdo diferente ou saídas incompletas/corrompidas não são aceitos como cache válido. Originais e tentativas anteriores preservados.
- Novo painel “Projetos de instrumentos — OpenUnmix”: selecionar/enviar música, separar e salvar, consultar estado, ouvir/baixar cada faixa e usá-la como referência em Cover/Extended. Seleção da referência preservada ao trocar de modo. Projetos persistem em `uploads/dj_projects/separated_<sha256>/job_status.json` e entram na listagem de projetos Vortex do Hub. Reutilizar como referência não trava bateria/baixo na síntese do ACE-Step.
- Separação roda em processo isolado, com blocos de 10 s e contexto lateral de 1 s para limitar memória. Integração antiga de mixagem passa a reutilizar esses projetos e exportar os MP3s de compatibilidade sem apagar as quatro faixas. Erros e separações interrompidas são identificados; solicitações novas são recusadas enquanto o Vortex está ocupado. Escrita dos registros usa `safe_json_write`.
- Arquivos: `nexus/dj/stem_projects.py`, `stem_worker.py`, `stem_routes.py`, `vortex_app.py`, `vortex_utils.py`, `nexus/nexus_routes.py`, `nexus/client/dj_studio.html`, `nexus/client/js/dj_stems.js`, `dj_studio.js`, `nexus/client/css/dj_studio.css`, `tests/test_stem_projects.py`.
- Validação: seis testes automatizados aprovados (cache após reinício/renomeação, arquivo alterado, reconstrução por faixa ausente, falha do separador, caminhos e rotas/listagem/download/reuso/bloqueio ocupado). Execução real de trecho de 10 s e da música completa `Solos_Forro_Perfeito_-_As_Melhores.mp3` na instalação local: oito blocos e quatro WAVs em 44,1 kHz estéreo. Segunda chamada, com nova instância do serviço, retornou cache sem executar o separador. Interface verificada em navegador: projeto salvo visível após recarga, quatro faixas com áudio/download e seleção de bateria como referência. Sintaxe Python/JavaScript e diff conferidos.
- Pendências específicas: avaliar vazamento/qualidade auditiva da separação; saxofone, guitarra e teclado permanecem juntos em “outros”. Geração de novos solos/voz sincronizados com base preservada ainda não implementada. Sem publicação de release nem execução de nova geração ACE-Step nesta etapa.

- Implementado Cover fiel experimental a pedido do responsável: modo Cover passa a usar `cover-nofsq`, remove códigos semânticos herdados e envia o mesmo arquivo em `audio` e `ref_audio`, com streams independentes abertos até terminar o envio. Interface identifica a variante experimental. O motor instalado aceitou a tarefa e registrou codificação da referência de timbre.
- No teste, a análise automática chamou o forró de metal. Para evitar essa influência incorreta, Cover fiel usa instrução neutra para preservar ritmo/instrumentos/timbres, mantendo o campo de estilo ignorado e a letra fornecida. Essa decisão substitui para o Cover fiel o uso anterior da descrição inferida. AudioSR continua desativado por padrão.
- Arquivos: `nexus/dj/music_request.py`, `nexus/dj/vortex_music.py`, `nexus/client/dj_studio.html`, `tests/test_music_request.py`, `docs/documentacao/CONTEXTO_IA.md`. Validação: oito testes de regressão aprovados, sintaxe Python e diff sem erros. Teste real na RTX 3050 com trecho de 30 s do forró, letra curta de teste, força 0,8, oito passos, guidance 1 e sem AudioSR. Primeira execução com descrição automática gerou 30 s; repetição com instrução neutra registrada em `test-output/music_smoke/faithful_neutral_caption.log`. Avaliação de fidelidade da batida e qualidade dos solos/canto permanece auditiva, sem alegação de preservação exata.

- Por nova decisão do responsável, Cover volta a ignorar totalmente o campo de estilo: interface desativa o campo e envia estilo vazio; o motor preserva a descrição extraída do áudio mesmo se a API receber texto de estilo. Letra e força do Cover continuam aplicadas. Esta decisão substitui somente para Cover o envio de estilo descrito anteriormente neste mesmo dia. Arquivos: `nexus/client/js/dj_studio.js`, `nexus/dj/vortex_music.py`. Validação: sintaxe Python/JavaScript e `git diff --check` aprovados; sem nova geração em GPU.

- A pedido do responsável, masterização/AudioSR desativada por padrão no Vortex DJ: checkbox inicialmente desmarcado, opções de upscale ocultas até ativação e padrões do JavaScript, API e motor Python definidos como falso. Ativação manual preservada. Arquivos: `nexus/client/dj_studio.html`, `nexus/client/js/dj_studio.js`, `nexus/dj/vortex_app.py`, `nexus/dj/vortex_dj.py`, `nexus/dj/vortex_music.py`. Validação desta alteração: sintaxe Python/JavaScript e `git diff --check` aprovados; não houve nova geração de áudio nem execução de AudioSR.

- Corrigida a geração musical do Vortex DJ após `UnboundLocalError` em `json`: removido o import local que ocultava o módulo e corrigida a leitura JSON no fallback de duração por FFprobe.
- Restaurado o envio de síntese em Normal, Cover e Extended. Áudio de referência permanece aberto durante upload multipart; parâmetros são enviados como JSON uma única vez, sem fallback silencioso para geração sem referência. Cover passa a declarar sua tarefa e enviar o áudio original.
- Extended usa a duração medida do áudio, preserva a duração total solicitada e envia fim explícito da região de continuação. O teste real inicial revelou que contar tokens concatenados como palavras reduzia incorretamente a extensão; a correção foi validada em nova geração.
- Corrigidos os nomes dos parâmetros de passos e guidance usados pelo motor C++; o estilo digitado passa a ser enviado também em Cover/Extended. Campo vazio mantém a descrição extraída da referência. Falha na exportação FFmpeg agora interrompe o fluxo em vez de registrar sucesso.
- Arquivos relevantes: `nexus/dj/vortex_music.py`, `nexus/dj/music_request.py`, `nexus/client/js/dj_studio.js`, `tests/test_music_request.py`.

### Validação efetivamente realizada

- Sete testes de regressão aprovados: vínculo global de JSON, upload com arquivo aberto, serialização, envio normal, falha de rede/arquivo ausente e duração da extensão. Sintaxe JavaScript e `git diff --check` dos arquivos alterados aprovados.
- Gerações reais com `env/Scripts/python.exe`, motor instalado `acestep.cpp 4922ed1`, modelo `acestep-v15-xl-sftturbo50-Q4_K_M.gguf` e RTX 3050: Cover de 10,008 s e Extended de 20,016 s a partir de trecho de 10 s de `Solos_Forro_Perfeito_-_As_Melhores.mp3`. Arquivos decodificados e verificados quanto a duração, amostras finitas e sinal não silencioso. O primeiro Extended de 10,176 s falhou na verificação de duração e foi corrigido antes da segunda execução.
- Modo Normal também concluiu geração real e exportação: `smoke_text2music_103729.mp3`, 19,2 s, sinal finito e não silencioso. Limitação observada: solicitação de 10 s produziu 19,2 s porque o motor priorizou 96 códigos de áudio gerados pelo LM; duração exata do modo Normal permanece pendente. Logs de síntese dos três modos preservados na pasta dos ensaios.
- Ensaios isolados em `test-output/music_smoke/`, sem alterar o áudio original nem o histórico musical do usuário; oito passos, guidance 1, uma saída por execução e masterização desativada.

### Pendências

- Validação auditiva de qualidade musical, aderência da letra, fidelidade de instrumentos e batida; faixas longas, lotes e AudioSR/masterização não foram testados nesta sessão.
- O fluxo proposto de preservar a base e recriar solos/voz separadamente ainda não foi implementado. O modelo instalado é SFT/Turbo; o modo Lego documentado pelo motor requer modelo Base, ausente nesta instalação. Não confundir a correção do Cover/Extended com essa funcionalidade futura.
- Nenhuma release, tag ou atualização do checkout foi publicada ou instalada nesta sessão.

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
