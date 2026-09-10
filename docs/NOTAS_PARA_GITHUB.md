# Notas de atualização para o GitHub — v0.8.0

O registro contínuo de trabalho está em [Atualizações — Diário de evolução](ATUALIZACOES.md). Ao preparar a publicação, consolide aqui os marcos internos ainda não lançados. A numeração interna não define automaticamente a versão pública.

Versão escolhida: **v0.8.0**, com lançamento previsto para **2026-09-10**. Comparação inicial com a tag v0.6.0. Publicação autorizada com instaladores e pacote de atualização gerados pelo GitHub Actions. Este documento não indica que o lançamento já foi validado ou publicado.

## Texto para colar na release do GitHub

> Antes de publicar, atualize esta seção a partir de ATUALIZACOES.md e revise as validações. Copie o texto a partir do título abaixo, até o início de “Antes de publicar”. O conteúdo ainda é um rascunho.

### PhoenixDub AI v0.8.0 — Edição manual de vídeos e jogos

### Principais mudanças

Esta atualização reúne as mudanças posteriores à v0.6.0, com destaque para a edição manual das dublagens de jogos e vídeos.

#### Edição e correção manual

- Painel compartilhado para encontrar e corrigir falas de diferentes projetos de jogos e vídeos, ampliando o antigo fluxo limitado a uma pasta específica.
- Busca por texto original, tradução ou identificador, com filtro por projeto, paginação e tolerância a pequenas diferenças de escrita.
- Rascunhos salvos automaticamente e controle de revisões para preservar o texto durante o processamento.
- Correção de várias falas de uma vez: selecione resultados, escreva a tradução e gere cada fala com sua referência individual de voz.
- Prévia de áudio, fila de redublagem em segundo plano, progresso geral e registro de falhas. As falas concluídas ficam salvas para permitir tentar novamente as pendentes.
- Indicador de caracteres baseado na duração original, com referência de 18 caracteres por segundo. Textos maiores continuam permitidos; a prévia usa aceleração de até 1,20× e preserva falas que ainda excederem a duração original.
- Exportação dos áudios corrigidos dos jogos e de uma nova cópia do vídeo com vozes corrigidas e fundo separado. Falas longas podem se sobrepor e precisam de revisão.

#### Processamento e organização de jogos

- Ajustes no lote por estágios, rotas de acompanhamento, identificação da pasta ativa e recuperação do último lote salvo.
- Contagem acumulada dos áudios selecionados, cópia paralela dos arquivos e recuperação da pasta original quando a entrada do projeto está vazia.
- Preparação paralela de áudios em WAV mono de 16 kHz para o fluxo de diarização em lote.
- Botão de início unificado, cartões de projetos e atualização de progresso e estado na interface.
- Ajustes na preservação da extensão e na escolha do codec de saída, evitando WAV antigo conflitante com o formato final.
- Organização específica das saídas de State of Decay por jogo e personagem dentro de uploads, incluindo as correções.

#### Áudio, tradução e modelos

- Tratamento de silêncio nas falas de vídeo com detecção de voz e margens conservadoras; cache renovado quando a fonte ou a versão do tratamento muda.
- Revisão dos prompts de tradução, limpeza de metadados e nova tentativa de condensação quando a tradução ultrapassa a referência de 18 caracteres por segundo.
- Ajustes na preservação de reações isoladas e no tratamento de traduções vazias, repetitivas ou iguais ao original. A qualidade continua dependente do modelo e da revisão humana.
- Carregamento unificado do Qwen, reconhecimento de variantes 9B/4B, ajustes das DLLs CUDA no Windows e liberação explícita do motor CTranslate2 usado pelo Whisper.

#### Editor, aplicativo e instalação

- Botão **Verificar atualizações** no Hub: mostra a versão instalada, consulta releases do GitHub e informa quando há uma nova versão. Para pacotes compatíveis, **Atualizar e reiniciar** baixa e verifica os arquivos, guarda uma cópia de recuperação e reabre o aplicativo. Checkouts Git e versões que alteram dependências exigem atualização pelo procedimento correspondente. O ciclo com executáveis empacotados ainda está em validação.
- Proteção de desenvolvimento e contra regressão: cópias Git ou marcadas como desenvolvimento permitem somente consulta; pacotes com versão igual ou anterior à local são bloqueados antes da instalação.
- Fatiador de vídeos com duração configurável e divisão via FFmpeg sem recodificação; os cortes efetivos dependem dos quadros-chave do arquivo.
- Ajustes na reinicialização para reabrir a janela após a liberação da porta do Hub.
- Ajustes no diretório de modelos e na detecção de modelos pelo instalador; título da release associado à tag de publicação.
- Inclusão de acesso ao apoio do projeto nas interfaces.
- Remoção de motores antigos de Cine Gen/GodoGen, painel Aider e forge local desta distribuição. Ainda existem interfaces e dependências remanescentes que precisam de revisão.
- Documentação reorganizada e histórico contínuo em ATUALIZACOES.md.

### Validação realizada na preparação

- Em 2026-09-10, passaram **57 testes Python**, incluindo correções, busca, fila em grupo, duração, progresso, exportação, atualização, distribuição e política de publicação.
- Passaram também os **2 arquivos de testes JavaScript**, com 5 cenários de progresso e 9 verificações de contagem de caracteres.
- Os testes usam projetos temporários, áudio de teste e síntese substituta. Instalação limpa, executáveis, qualidade dos modelos e dublagem completa em GPU não foram validados nesta revisão.

## Antes de publicar

Base do levantamento: [comparação do código v0.6.0 → v0.8.0](COMPARACAO_0.6.0_0.8.0.md), incluindo commits, alterações locais e novos módulos. Revisar o escopo final antes de copiar as notas para a release.

### Recursos que já existiam na v0.6.0

A fila por estágios, a seleção múltipla de pastas, o cronômetro de sessão, as proteções locais e a verificação de atualização por hash não devem ser anunciados como novidades desta versão. As mudanças posteriores devem ser descritas como correções ou aprimoramentos desses recursos.

### Pendências

- Escopo definido: v0.8.0 com Setup_Nexus.exe, Nexus_AI_Pro.exe e PhoenixDub_Update.zip; aguardando validação do build.
- Revisar os arquivos novos: incluir os módulos necessários e testes; deixar backups, resultados de testes e scripts de trabalho específicos fora do lançamento.
- Conferir as dependências de instalação: requirements.txt ainda contém componentes de geração de imagem/vídeo, embora os motores correspondentes tenham sido removidos.
- Conferir configurações locais de modelos, especialmente o caminho absoluto em nexus/core/server_config.json.
- Atualizar README.md e RELEASE_NOTES.md para a versão escolhida; atualmente há referências misturadas a v0.5 e v0.6.0.
- Validar instalação limpa, inicialização dos executáveis e ao menos um fluxo real de dublagem antes de anunciar estabilidade.

## Publicação existente

O workflow .github/workflows/build_and_release.yml gera Setup_Nexus.exe e Nexus_AI_Pro.exe. Uma tag iniciada por v dispara a criação de uma Release pública automaticamente; a tag só deve ser enviada depois da preparação e validação.
