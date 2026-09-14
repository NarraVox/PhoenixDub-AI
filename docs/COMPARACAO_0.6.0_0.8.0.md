# Comparação do código — v0.6.0 → v0.8.0

Revisão realizada em 2026-09-10. Base pública: `f13937f0f858cfd3ff4c87da1bca6a97616c6897` (tag v0.6.0). HEAD local: `7990a72520494e1c92970cfe2a9a9e5ecffab180`, com 11 commits posteriores à base, mais alterações locais e arquivos novos ainda sem commit.

O levantamento compara o comportamento escrito no código, incluindo as ligações entre interfaces e rotas. Não certifica instalação, qualidade da IA ou execução em GPU. As datas individuais das alterações locais não podem ser reconstruídas com segurança apenas pelo Git. Backups, áudios do usuário e scripts específicos de revisão de dublagens não são novidades do produto.

## Principais mudanças confirmadas

| Área | Mudança desde a base pública | Evidência no código atual |
|---|---|---|
| Correção manual | O fluxo antigo de busca/redublagem era fixo em uma pasta de Call of Duty e sobrescrevia o áudio. Foi substituído por serviço compartilhado de projetos de jogos e vídeos; rotas antigas retornam orientação para recarregar a página. | `nexus/nexus_routes.py`, `nexus/nexus_app.py`, `nexus/correction_routes.py` |
| Busca global | Busca nos projetos de uploads, por original, tradução e identificadores, com filtro de projeto, paginação, normalização de acentos e aproximação por palavra. | `nexus/correction_search.py`, `nexus/client/js/corrections/template.js` |
| Rascunhos | Edições persistidas em disco, revisões e separação entre o texto atual e a cópia enviada à fila. | `nexus/correction_service.py`, `nexus/client/js/corrections/persistence.js` |
| Prévia | Síntese com referência individual, remoção de silêncio nas extremidades, rejeição de prévia silenciosa e aplicação de prévia identificada por token. | `nexus/correction_preview.py`, `nexus/correction_service.py` |
| Correção em grupo | Seleção de página ou resultados, tradução compartilhada e envio agrupado por projeto, validando revisões antes de enfileirar. | `nexus/correction_batch.py`, `nexus/client/js/corrections/batch*.js` |
| Tempo da fala | Indicador de 18 caracteres/s baseado na duração original. É orientação, sem bloquear textos longos. A prévia acelera até 1,20× e preserva a fala que ainda exceder a janela. | `nexus/correction_timing.py`, `nexus/correction_preview.py`, `nexus/client/js/corrections/timing.js` |
| Fila de correções | Tarefas em segundo plano, progresso com concluídas/falhas, registro de processamento e reaproveitamento de prévias em retomadas. Jogos enfileiram a geração ao salvar; vídeos aguardam o início do processamento. | `nexus/correction_jobs.py`, `nexus/correction_queue_runner.py`, `nexus/correction_routes.py` |
| Exportação de jogos corrigidos | Saída em `_correcoes/exportacoes/jogos`, mantendo arquivos originais do projeto; verifica se a fonte mudou desde a prévia. | `nexus/correction_export.py` |
| Exportação de vídeos corrigidos | Remonta falas, conserva áudio de fundo separado e gera `video_corrigido.mp4`, copiando o vídeo sem recodificá-lo. Requer os arquivos fonte e pode haver sobreposição quando falas excedem suas janelas. | `nexus/correction_video_export.py` |
| Saídas de State of Decay | Regra específica de cópia por jogo/personagem em uploads, tanto na saída completa quanto nas correções. Não generalizar essa regra a todos os jogos. | `nexus/correction_game_output.py`, `nexus/game_full_export.py` |
| Formatos de áudio | Finalização consulta a extensão da fonte, escolhe codecs conforme o formato e remove WAV antigo conflitante quando a saída possui outra extensão. | `nexus/core/orchestrator_jobs_games.py` |
| Lote por estágios | Ajustados parâmetros de parada/início por estágio, acompanhamento da pasta ativa, estado global e manifesto do último lote para retomada. A arquitetura de lote já existia. | `nexus/core/batch_orchestrator.py`, `nexus/core/orchestrator_jobs_games.py`, `nexus/core/orchestrator_routes.py` |
| Entrada de jogos | Cópia paralela com até 16 workers, contagem acumulada das pastas e tentativa de recuperar arquivos da pasta original quando a entrada está vazia. Sem benchmark de ganho nesta revisão. | `nexus/core/orchestrator_routes.py`, `nexus/core/diarization.py`, `nexus/client/js/games_studio.js` |
| Preparação de áudio | Pré-conversão paralela para WAV mono de 16 kHz antes do fluxo de diarização de lotes. | `nexus/core/audio_batch_preparer.py`, `nexus/core/diarization.py` |
| Painel de jogos | Botão de início unificado, cartões de projetos, atualização da seleção/progresso e botão para retomar a última fila; rotas de status registradas no motor. | `nexus/client/js/games_studio.js`, `nexus/client/games_studio.html`, `nexus/core/orchestrator_routes.py` |
| Transcrição — experimento não adotado | O responsável esclareceu em 2026-09-10 que Qwen ASR foi testado e considerado mais lento, mantendo-se Whisper. A revisão encontrou uma seleção padrão residual de Qwen, agora removida junto dos imports na inicialização normal. O carregador experimental permanece como arquivo de estudo, sem ser novidade da v0.8.0. | `nexus/core/orchestrator_jobs_core.py`, `nexus/core/model_loader.py`, `nexus/core/__init__.py`, `nexus/core/qwen_asr_loader.py` |
| Tradução | Limpeza de metadados dos prompts, mudanças na preservação de reações isoladas, novas tentativas quando a tradução fica vazia/igual ao original e uma tentativa de condensação ao ultrapassar 18 caracteres/s. Regras do corretor passaram a enfatizar contexto e linguagem falada. | `nexus/core/translation_processors.py`, `nexus/core/translation_corrector.py`, `nexus/core/translation_utils.py` |
| Dicionário tático | Lógica retirada do módulo de processamento e organizada em módulo próprio. A tradução tática já existia; não anunciar sua criação nesta versão. | `nexus/core/tactical_dict.py`, comparação com `translation_processors.py` da v0.6.0 |
| Modelos e memória | Carregador Qwen unificado, descoberta de variantes 9B/4B em MODELS, preparação das DLLs CUDA no Windows, mudanças no contexto/cache e descarga explícita do CTranslate2 no Whisper. | `nexus/core/qwen_loader.py`, `nexus/core/whisper_loader.py` |
| Silêncio em vídeos | Novo tratamento com Silero VAD, margens conservadoras e alternativa por energia; preserva áudio quando a detecção é incerta. Cache passa a considerar a versão do tratamento e mudanças na fonte. | `nexus/dub/speech_trim.py`, `nexus/dub/dubbing.py` |
| Fatiador de vídeo | Interface e rota para dividir arquivos com FFmpeg em blocos configuráveis, de 5 s a 2 h. Usa stream copy: cortes dependem dos quadros-chave. | `nexus/core/video_slicer_route.py`, `nexus/client/js/vortex_editor.js`, `nexus/client/vortex_editor.html` |
| Reinicialização | Nova instância aguarda liberação da porta 5000; o Hub responde antes de encerrar e reabrir o aplicativo. | `Nexus_AI_Pro.py`, `nexus/nexus_routes.py` |
| Instalador e apresentação | Ajustes de diretório MODELS/download, detecção de modelo 9B, retirada da opção de instalação generativa e título da release baseado na tag; widget de apoio nas interfaces. | `nexus/build_tools/nexus_setup.py`, `nexus/client/js/installer_ui.js`, `.github/workflows/build_and_release.yml`, `nexus/client/js/donation_widget.js` |
| Remoções e documentação | Removidos motores antigos Cine Gen/GodoGen, painel Aider e forge local; documentação reorganizada e criado o histórico de atualizações. Ainda existem interfaces e dependências remanescentes. | Diff dos arquivos removidos, `docs/ATUALIZACOES.md`, `docs/documentacao/` |

## O que já existia na v0.6.0

Fila por estágios, seleção múltipla de pastas, cronômetro de sessão, proteções locais e consulta de atualização por hash constam do código/notas da base. Qwen para tradução e TTS, tradução tática e ferramentas de correção anteriores também não devem ser apresentados como inteiramente novos. O destaque da v0.8.0 é a ampliação e reestruturação dos fluxos, junto das correções posteriores.

## Limites e pontos para a preparação do lançamento

- `character_voice_shield.py` está presente como arquivo novo, mas a busca por referências não encontrou integração dele no fluxo do programa. Não anunciar proteção universal de voz com base apenas nesse arquivo.
- `system_guard.py` tem chamadas no worker de correções e no tratamento de silêncio; isso não comprova cobertura de todos os motores ou prevenção de todos os travamentos.
- Qwen ASR não foi adotado: o resultado de maior lentidão foi informado pelo responsável, sem repetir o benchmark nesta revisão. Whisper permanece como motor de transcrição. Não anunciar Qwen ASR nas novidades.
- Permanecem caminhos absolutos e dependências de geração de imagem/vídeo. É necessário revisar a instalação limpa e o empacotamento dos módulos novos.
- Os testes de correções usam projetos temporários e síntese substituta; resultados não medem qualidade de voz, tradução nem memória em GPU.
- Não foram executados instalação limpa, build dos executáveis, teste visual completo ou dublagem real nesta revisão. Não há comprovação de ganhos percentuais de desempenho.

## Validação desta revisão

- Comparados os 11 commits posteriores à tag, os diffs locais das principais áreas e os novos módulos de correção, exportação, áudio e transcrição.
- JavaScript: `node --test tests/test_correction_progress.mjs tests/test_correction_timing.mjs` passou nos dois arquivos, com 5 cenários de progresso e 9 verificações de contagem.
- Python 3.12: `python -m unittest discover -s tests -p 'test_*.py'` passou 31 testes em 41,546 s. Houve aviso de depreciação de `audioop` pelo pydub, sem falhas. A execução cobriu correções, busca, grupos, duração, progresso e exportação com dados temporários e síntese substituta.
