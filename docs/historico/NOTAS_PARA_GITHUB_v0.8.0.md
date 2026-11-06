# Notas de atualização para o GitHub — v0.8.0

O registro contínuo de trabalho está em [Atualizações — Diário de evolução](ATUALIZACOES.md). Ao preparar a publicação, consolide aqui os marcos internos ainda não lançados. A numeração interna não define automaticamente a versão pública.

Versão escolhida: **v0.8.0**, com lançamento previsto para **2026-09-10**. Comparação inicial com a tag v0.6.0. Publicação autorizada com instaladores e pacote de atualização gerados pelo GitHub Actions. Este documento não indica que o lançamento já foi validado ou publicado.

## Texto para colar na release do GitHub

> Antes de publicar, atualize esta seção a partir de ATUALIZACOES.md e revise as validações. Copie o texto a partir do título abaixo, até o início de "Antes de publicar". O conteúdo ainda é um rascunho.

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

### Pendências específicas

- Avaliar vazamento/qualidade auditiva da separação; saxofone, guitarra e teclado permanecem juntos em "outros". Geração de novos solos/voz sincronizados com base preservada ainda não implementada. Sem publicação de release nem execução de nova geração ACE-Step nesta etapa.
