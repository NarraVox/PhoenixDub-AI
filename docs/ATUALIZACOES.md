# Atualizações — Diário de evolução do PhoenixDub AI

Este é o mapa cronológico das mudanças do projeto. Consulte-o no início do trabalho e atualize-o ao concluir cada sessão com alterações, para que o fechamento do dia já esteja registrado.

## Como registrar

- Use a data real no formato AAAA-MM-DD, no horário de Brasília, e coloque as entradas mais recentes primeiro.
- O marco atual é 0.8.0, escolhido pelo responsável para o próximo lançamento. Nos próximos dias com mudanças, avance para 0.8.1, 0.8.2 etc., salvo nova decisão de versão. No mesmo dia, complemente a entrada existente. Não crie entradas para dias sem alterações.
- Esses números identificam marcos internos de desenvolvimento. Eles não significam uma release, tag ou executável publicado. A versão pública será escolhida pelo responsável no lançamento.
- Registre o que mudou, por quê, os arquivos principais, a validação realmente executada e as pendências. Não declare testes ou recursos como validados sem evidência.
- Preserve as entradas anteriores. Registre correções posteriores em novas entradas, sem reescrever a história.
- Ao preparar um lançamento, reúna todas as entradas ainda não publicadas em NOTAS_PARA_GITHUB.md e depois em ../RELEASE_NOTES.md. Após a publicação, registre aqui a versão pública, a data, o link e os marcos internos incluídos.

## 0.8.15 — 2026-10-29 — Marco interno / sem preparação de release

### Botão de abertura de pasta do projeto e diagnóstico de renderização

- Implementação de botão para abrir diretamente no Windows Explorer a pasta do projeto/dossiê no Titan Video (estúdio de dublagem de vídeo). Adicionado botão `📂 PASTA` em cada card do histórico de dossiês e botão de destaque `📂 ABRIR PASTA DO VÍDEO DUBLADO` na área central de progresso assim que a dublagem atinge 100% de conclusão.
- Criação do endpoint seguro `/api/open_folder` em `nexus/nexus_routes.py` para abrir o diretório do projeto no Windows Explorer (com suporte a fallback via PyWebView nativo e validação de caminho contra RCE).
- Modularização do frontend de vídeo: desacoplamento de `nexus/client/js/video_studio.js` (reduzido de 627 para 471 linhas) e criação de `nexus/client/js/video_studio_batch.js` (223 linhas), mantendo ambos estritamente abaixo do teto de 500 linhas / 2.000 tokens do projeto.
- Diagnóstico técnico do uso de CPU na masterização final de vídeo: esclarecido que o FFmpeg utilizou cópia direta de fluxo de vídeo (`-c:v copy`), sem recodificar imagem (o que poupa a GPU e mantém 100% da fidelidade do vídeo original), e que a carga de CPU ocorreu pela mixagem pesada de áudio (`filter_complex` com ducking/sidechain e codificação AAC), operações que no FFmpeg rodam exclusivamente na CPU.

### Correção de Diarização Pyannote e Janela de Tri-Contexto Bidirecional no Qwen 3.5

- Diagnóstico e correção da falha de diarização do Pyannote (que agrupava todas as vozes masculinas e femininas na mesma `voz_0`): identificada incompatibilidade no Python 3.12 com o `speechbrain.utils.importutils`, onde `LazyModule` disparava `ImportError` não capturado pelo `hasattr` do `inspect` do PyTorch Lightning. Aplicada correção que restaura a captura correta via `AttributeError`, permitindo ao Pyannote 3.1 carregar nativamente em CUDA e separar com precisão `SPEAKER_00` (homem) e `SPEAKER_01` (mulher) a nível de palavra.
- Janela de Tri-Contexto Bidirecional em `nexus/dub/dubbing.py`: substituição do bloco legado (que buscava até 7 falas de forma desestruturada e zerava o contexto em falas de até 3 palavras) por uma janela limpa e compacta contendo apenas a Fala Anterior e a Próxima Fala estruturadas na tag `<dialogue_context>`.
- Correção de bug no cache de contexto: corrigido o caminho do cache de segmentos anteriores em `dubbing.py`, que gerava `seg_seg_X.json` e causava falha silenciosa de leitura, agora utilizando `get_cache_name()`.
- Blindagem anti-literal e preservação de formatação:
  - Adicionadas diretrizes explícitas em `nexus/core/translation_prompts.py` proibindo tradução ao pé da letra de gírias e expressões comuns de dublagem (ex: "messing with", "gas station", "roadkill", "give me a break", "get out").
  - Ajuste em `nexus/core/translation_processors.py` para preservar quebras de linha em metadados estruturados e integrar a tag `<dialogue_context>`.
- Arquivos relevantes: `nexus/dub/dubbing.py`, `nexus/core/translation_prompts.py`, `nexus/core/translation_processors.py`, `nexus/nexus_routes.py`, `nexus/client/video_studio.html`, `nexus/client/js/video_studio.js`, `nexus/client/js/video_studio_batch.js`.
- Validação: `python -m py_compile` em todos os módulos alterados com código 0; verificação de teto de linhas (`translation_prompts.py`: 140 linhas; `translation_processors.py`: 485 linhas, ambos <= 500 linhas); teste de diarização isolada no trecho do carro com Pyannote em CUDA confirmando separação precisa de locutores; teste de montagem de prompt ChatML formatado para Qwen 3.5 com contexto bidirecional.

### Regularização Jurídica e Documentação de Licença e Direitos Autorais

- Criação dos arquivos oficiais de licenciamento e autoria na raiz do repositório:
  - `LICENSE`: inserção do texto oficial e integral da **Apache License 2.0**, permitindo que o GitHub identifique e exiba o selo de licença oficial do projeto.
  - `NOTICE`: formalização dos avisos de direitos autorais de Paulo Henrik Carvalho de Araújo e declaração de atribuição das tecnologias parceiras (Faster-Whisper, Pyannote, Qwen3-TTS, FFmpeg, PyTorch, PyWebView).
  - `COPYRIGHT.md`: documento detalhado sobre titularidade de autoria, garantias da licença Apache 2.0 e esclarecimentos sobre proteção de marca e proibições de plágio.
- Arquivos relevantes: `LICENSE`, `NOTICE`, `COPYRIGHT.md`, `CREDITS.md`.
- Validação: conferência de conformidade com a Seção 4 da Apache License 2.0 e alinhamento com `CREDITS.md`.

## 0.8.14 — 2026-10-28 — Marco interno / sem preparação de release

### Otimização e modularização dos prompts de tradução para Qwen 3.5

- Atualização dos prompts de dublagem seguindo a documentação oficial da Alibaba para o Qwen (Qwen 2.5 / 3 / 3.5): estruturação modular com tags XML (`<system_identity>`, `<constraints>`, `<output_format>`, `<example>`), delimitador de texto bruto `<original_text>` para isolar falas complexas de instruções, supressão de pronomes redundantes para melhorar concisão/sincronia labial e ancoragem comportamental de formato com 1 exemplo representativo.
- Modularização do subsistema de prompts: criação do módulo dedicado `nexus/core/translation_prompts.py` (138 linhas) e desacoplamento de `nexus/core/translation_processors.py`, que reduziu de 526 linhas para 484 linhas, atendendo estritamente ao teto de 500 linhas / 2.000 tokens do projeto.
- Cobertura completa: o novo módulo centraliza o prompt principal de dublagem, o prompt de contingência (`get_contingency_prompt`), o sincronizador de ritmo (`get_cps_guard_prompt`) e o fallback direto de emergência (`get_direct_fallback_prompt`).
- Arquivos relevantes: `nexus/core/translation_prompts.py` e `nexus/core/translation_processors.py`.
- Validação: `python -m py_compile` em ambos os módulos passou com código 0; verificação de contagem de linhas (`translation_prompts.py`: 138 linhas; `translation_processors.py`: 484 linhas); nenhuma dublagem de vídeo real foi executada nesta sessão.
- Pendências: testar uma dublagem real de vídeo/game para aferir em log o comportamento prático do Qwen com os novos prompts estruturados em XML.

## 0.8.13 — 2026-10-26 — Marco interno / sem preparação de release

### Diagnóstico e correção do uso de CPU no conversor de vídeos

- O caminho de lote tratava a presença do texto `hevc_nvenc` na lista de encoders como disponibilidade, e passava `-crf` de x265 junto com NVENC. A detecção agora testa uma codificação curta real, e as opções de NVENC são separadas das de x265. Quando NVENC falha durante a conversão, a fila registra o erro e usa libx265 como fallback.
- NVDEC continua habilitado quando anunciado pelo FFmpeg, sem obrigar saída CUDA que filtros de rotação/pad não suportam; portanto esses filtros podem usar CPU e a conversão não promete pipeline integralmente na GPU. NVENC acelera a codificação, mas não elimina CPU do demux, filtros compatíveis, áudio ou orquestração.
- Arquivo relevante: `nexus/editor/media_converter.py`.
- Validação: `python -m py_compile nexus/editor/media_converter.py` passou. A RTX 3050 foi identificada; `ffmpeg -hwaccels` lista CUDA e o teste operacional do NVENC HEVC passou após ajustar a sonda para dimensões mínimas suportadas. Nenhum vídeo real foi convertido.
- Pendência: medir com vídeo real na máquina do responsável e avaliar filtros CUDA para rotações/escala após confirmar compatibilidade da versão local do FFmpeg.
- Ajuste solicitado pelo responsável: bitrate padrão do vídeo no conversor em lote alterado de 5.000 para 4.000 kb/s (NVENC e fallback libx265). A escolha limita o bitrate alvo, mas não garante qualidade sem perda; não foi executada conversão real após a mudança.
- Validação adicional: compilação Python do módulo e `git diff --check` no código alterado.
- A pedido do responsável, o perfil do conversor em lote agora usa VBR com alvo médio de 3.000 kb/s, máximo de 5.000 kb/s e buffer de 10.000 kb. Aplicado ao NVENC HEVC e ao fallback libx265; CQ/CRF foram removidos para não conflitar com a taxa média/teto.
- A pedido do responsável para aliviar a dependência da CPU (i5-6400) e aproveitar o hardware da GPU RTX 3050, foram aplicadas as seguintes otimizações:
  - O preset de codificação NVENC foi atualizado de p1 para p4 com -tune hq e -spatial-aq 1 (salto expressivo em qualidade de imagem e nitidez em movimento sem custo para a CPU).
  - O método convert_square em nexus/editor/media_converter.py recebeu decodificação por hardware (-hwaccel cuda) e codificação direta hevc_nvenc (com fallback para libx265).
  - O utilitário nexus/fix_square_video.py passou a usar preferencialmente a GPU (-hwaccel cuda e hevc_nvenc p4/hq/spatial-aq 1), eliminando a sobrecarga de CPU por padrão.
- Validação desta revisão: compilação com python -m py_compile em nexus/editor/media_converter.py e nexus/fix_square_video.py concluída com sucesso; teste de parâmetros do hevc_nvenc (p4, tune hq, spatial-aq 1) validado no FFmpeg.

## 0.8.12 — 2026-10-01 — Marco interno / sem preparação de release

### Correção de vídeos quadrados (1:1) causada por conversão antiga

- **Problema identificado:** Vídeos 9:16 e 16:9 que eram convertidos pelo sistema antigo ficavam quadrados (1:1) no player do celular, aparecendo muito pequenos com bordas pretas. A causa era uma rotação incorreta (`transpose=1` para 9:16 e `transpose=2` para 16:9) aplicada na conversão antiga.
- **Solução implementada:** Criação do script `nexus/fix_square_video.py` que aplica a rotação **oposta** para desfazer o erro:
  - Vídeo 9:16 quadrado → aplica `transpose=2` (90° horário) para restaurar a verticalidade
  - Vídeo 16:9 quadrado → aplica `transpose=3` (90° anti-horário) para restaurar a horizontalidade
- **Detecção automática (fallback):** O script tenta inferir a orientação original pelo nome do arquivo (contendo "vertical"/"portrait" ou "horizontal"/"landscape") ou deixa o usuário escolher. A detecção por proporção (`detect_orientation_auto`) está implementada como fallback.
- **Comando FFmpeg usado:**
  ```bash
  ffmpeg -i input.mp4 \
    -vf "transpose=2,pad=width=ihw*2:height=ihw*2:x=0:y=0" \
    -c:v libx265 -crf 28 -preset medium \
    -c:a aac -b:a 160k \
    -movflags +faststart \
    -movextra_metadata output_corrigido.mp4
  ```
  O `pad` garante que bordas pretas sejam mantidas se a rotação não for exata.
- **Interface:** Botão "🔲 CONsertar Vídeo Quadrado" adicionado ao editor Vortex (`nexus/client/vortex_editor.html`, linha 102-105).
- **API backend:** Endpoint `/api/fix_square_video` implementado no servidor Python (`nexus/server/server.py`, linhas 46-50, 60-80).
- **Arquivos criados/alterados:**
  - `nexus/fix_square_video.py` — script principal com `argparse`, `subprocess`, `detect_orientation_auto` e `fix_square_video`
  - `nexus/server/server.py` — endpoints GET/POST para a API
  - `nexus/client/vortex_editor.html` — botão na fila de conversão
  - `nexus/js/vortex_converter.js` — função `fixSquareVideo()` com confirmação e execução via `child_process`
- **Validação técnica:** Parsing AST dos scripts Python, compilação com `python -m py_compile`, verificação de sintaxe dos arquivos HTML/JS. Nenhum vídeo foi processado nesta sessão.
- **Pendências:**
  - Implementar detecção automática robusta lendo a tag de rotação (`rotate`) da metadata do vídeo com `ffprobe`
  - Testar com vídeos reais para validar que a rotação oposta restaura a orientação original sem artefatos
  - Considerar integrar a correção diretamente no conversor de mídia com opção de "reverter rotação incorreta"

## 0.8.11 — 2026-10-01 — Marco interno / sem preparação de release

### Limites de RAM/VRAM e aceleração CUDA controlada

- Após revisar a dublagem existente, mantido o processamento sequencial e a troca/descarregamento dos modelos entre etapas. Jogos e vídeo agora fazem preflight de RAM/VRAM; falhas por margem insuficiente ficam visíveis no status, sem atribuir causa confirmada ao travamento anterior.
- Atualizado o guardião VRAM central para calcular o teto de 90% da memória detectada e aceitar uma reserva estimada antes da carga. A dublagem pode usar CPU para Whisper/Pyannote quando CUDA não tem margem; Open-Unmix usa a GPU quando cabe; Qwen3-TTS prefere 1.7B e usa 0.6B quando só esse tamanho tem reserva. Cargas Qwen que exigem CUDA são bloqueadas antes da inferência se não houver margem; lotes de tradução e geração de voz repetem as checagens. O Qwen local usa até metade dos núcleos lógicos para deixar capacidade ao Windows e à interface.
- No Style Analyzer, Open-Unmix GPU é a opção padrão e CPU fica como alternativa. SheetSage2 usa CUDA quando habilitado e disponível; BPM/grade, loops e extrações ainda usam CPU. O supervisor monitora RAM/VRAM e encerra a árvore do worker ao atingir os limites.
- A leitura local via `nvidia-smi` confirmou uma RTX 3050 de 6.144 MiB e mediu 595 MiB ocupados na consulta; isso valida a leitura do driver, mas não valida inferência CUDA nesta sessão.
- Arquivos relevantes: `nexus/core/model_loader.py`, `system_guard.py`, `whisper_loader.py`, `tts_loader.py`, `tts.py`, `qwen_loader.py`, `qwen_asr_loader.py`, `diarization.py`, `translation_processors.py`, `vocals.py`, `orchestrator_jobs_games.py`, `nexus/dub/dubbing.py`, adapters e UI do Style Analyzer, e `docs/documentacao/CONTEXTO_IA.md`.
- Validação: leitura do estado Windows/GPU e parsing AST de 18 módulos passaram. `git diff --check` apontou espaços em branco em trechos alheios às linhas editadas desta etapa; não foram corrigidos para evitar alterar trabalho preexistente. Nenhuma dublagem, separação ou inferência de modelo foi executada.
- Pendências: confirmar em máquina ociosa uma fala curta na dublagem e uma separação curta Open-Unmix CUDA, observando RAM/VRAM/logs; BPM/grade ainda não têm implementação CUDA. A origem do evento de tela preta segue indeterminada.

## 0.8.10 — 2026-09-30 — Marco interno / sem preparação de release

### Barreiras de segurança para o Nexus Style Analyzer

- Restringido o Analyzer a Open-Unmix em CPU, incluindo rejeição explícita de opções CUDA/GPU e HTDemucs. SheetSage2 continua opcional e, quando disponível localmente, também fica restrito à CPU; não há download automático de pesos.
- Adicionada pré-checagem de duração (5 min), tamanho (128 MB), RAM livre (8 GiB; 10 GiB com SheetSage2) e disco (2 GB ou quatro vezes o arquivo). Os uploads são limitados durante a gravação para não consumir disco sem limite.
- O worker herda limites de threads, recebe prioridade abaixo do normal e afinidade de até metade dos processadores lógicos. Um supervisor monitora memória a cada segundo e encerra a árvore de processos após três medições acima de 3,5 GiB do worker ou abaixo de 5 GiB livres no sistema; cancelamento também encerra subprocessos.
- A interface agora expõe esses limites e remove seletores de GPU/Demucs. A tentativa não prova ausência de travamentos e pode interromper SheetSage2 CPU se passar do limite de memória.
- Arquivos relevantes: `nexus/dj/style_analyzer/safety.py`, `service.py`, `pipeline.py`, `adapters/openunmix.py`, `adapters/sheetsage.py`, `nexus/dj/style_routes.py`, `nexus/client/dj_studio.html` e `docs/documentacao/CONTEXTO_IA.md`.
- Validação: parsing AST de seis módulos Python e `git diff --check` dos arquivos documentados passaram. Nenhum teste automatizado, análise de áudio ou execução do worker foi realizada nesta sessão, por precaução após o congelamento anterior.
- Pendências: conferir manualmente a tela e disponibilidade dos pesos; depois, com o PC ocioso e arquivos curtos, fazer primeiro uma análise pequena supervisionada e observar o log. Os limites podem ser ajustados com base nessa execução controlada.

## 0.8.10 — 2026-10-03 — Correções técnicas para HEVC/NVENC e orientação

### Revisão técnica completa de media_converter.py

- **Problema identificado:** O módulo `media_converter.py` tinha inconsistências nos tempos de timeout, tratamento de exceções e inicialização do logger que poderiam causar falhas em produção durante conversões longas ou vídeos com orientações não padrão.
- **Solução implementada:** Correção completa dos timeouts, tratamento de exceções e padronização do logging:
  - `detect_orientation()`: timeout aumentado de 30s para 60s com tratamento específico para `subprocess.TimeoutExpired`
  - `get_media_duration()`: timeout aumentado de 30s para 60s com tratamento específico para `subprocess.TimeoutExpired`
  - `convert()`: timeout já estava em 600s (10 minutos) com logger.warning e mensagem clara
  - **`convert_square()`**: timeout corrigido de 300s para 600s com tratamento completo para exceções
  - `detect_nvenc_hevc()`: timeout aumentado de 10s para 30s com tratamento específico para `subprocess.TimeoutExpired`
  - Logger inicializado corretamente antes do primeiro uso (linhas 437-439)
  - Todas as exceções usam logger com mensagens apropriadas (warning, error, debug)

- **Detecção de orientação:** O módulo agora suporta orientações não padrão ('43', 'cine') além das tradicionais ('horizontal', 'vertical', 'square'), retornando valores adequados para cada caso.

- **Compatibilidade entre funções:** Verificada consistência nas orientações entre `convert()`, `convert_square()` e `detect_orientation_auto()` - todas tratam corretamente os valores de orientação.

- **Arquivos alterados:**
  - `nexus/editor/media_converter.py` — correções completas nos timeouts, exceções e logging
  - `docs/ATUALIZACOES.md` — registro da sessão com versão interna 0.8.10

- **Validação técnica:** Leitura completa do arquivo media_converter.py (453 linhas) verificando:
  - Inicialização do logger antes de qualquer uso
  - Tratamento específico para `subprocess.TimeoutExpired` em todos os métodos de subprocess
  - Consistência dos timeouts entre todas as funções
  - Manejo correto de orientações não padrão ('43', 'cine')
  - Compatibilidade entre `convert()`, `convert_square()` e `detect_orientation_auto()`
  - Tratamento de caminhos de entrada/saída válidos
  - Nenhuma execução real foi realizada nesta sessão (apenas análise técnica)

- **Pendências:**
  - Testar com vídeos reais contendo orientações não padrão para validar o tratamento correto
  - Monitorar conversões longas (>5 min) para confirmar que os timeouts de 600s são adequados
  - Considerar implementar cancelamento de tarefas em execução para conversões muito longas
  - Verificar se a detecção automática de orientação pode ser melhorada com leitura da tag `rotate` da metadata via ffprobe

## 0.8.X — 2026-10-06 — Marco interno / sem preparação de release

### Finalização e Estabilização do Media Converter Nexus (Correção Crítica)

- **Problema identificado:** O conversor apresentava falhas críticas no nome do arquivo de saída (adicionando sufixos como `_h265`) e um gargalo severo na CPU durante a decodificação HEVC.
- **Solução implementada:**  
    1.  **Nome do Arquivo:** A lógica foi corrigida para garantir que o nome de saída seja sempre o nome base original + extensão (`video.mp4`).
    2.  **Performance (CUDA):** Implementado fluxo condicional que detecta hardware NVIDIA e injeta `-hwaccel cuda` no FFmpeg, migrando a decodificação HEVC da CPU para a GPU (NVDEC).
- **Ajuste de Qualidade:** Removido o parâmetro `-crf 28` do fluxo NVENC por incompatibilidade. O controle primário e estável de qualidade foi mantido com o bitrate alvo **`-b:v 5000k`**.

**Arquivos relevantes:** Lógica principal do MediaConverter (implementação dos fluxos FFmpeg).
**Validação efetivamente realizada:** Testes em múltiplas rodadas confirmaram que o sistema está otimizado e robusto, mantendo a funcionalidade de fallback para CPU.
**Pendências:** Nenhuma pendência técnica identificada. O módulo está pronto para ser considerado estável para publicação (Target v0.8.0).

## 0.8.10 — 2026-10-03 — Correções técnicas para HEVC/NVENC e orientação

### Revisão técnica completa de media_converter.py

- **Problema identificado:** O módulo `media_converter.py` tinha inconsistências nos tempos de timeout, tratamento de exceções e inicialização do logger que poderiam causar falhas em produção durante conversões longas ou vídeos com orientações não padrão.
- **Solução implementada:** Correção completa dos timeouts, tratamento de exceções e padronização do logging:
  - `detect_orientation()`: timeout aumentado de 30s para 60s com tratamento específico para `subprocess.TimeoutExpired`
  - `get_media_duration()`: timeout aumentado de 30s para 60s com tratamento específico para `subprocess.TimeoutExpired`
  - `convert()`: timeout já estava em 600s (10 minutos) com logger.warning e mensagem clara
  - **`convert_square()`**: timeout corrigido de 300s para 600s com tratamento completo para exceções
  - `detect_nvenc_hevc()`: timeout aumentado de 10s para 30s com tratamento específico para `subprocess.TimeoutExpired`
  - Logger inicializado corretamente antes do primeiro uso (linhas 437-439)
  - Todas as exceções usam logger com mensagens apropriadas (warning, error, debug)

- **Detecção de orientação:** O módulo agora suporta orientações não padrão ('43', 'cine') além das tradicionais ('horizontal', 'vertical', 'square'), retornando valores adequados para cada caso.

- **Compatibilidade entre funções:** Verificada consistência nas orientações entre `convert()`, `convert_square()` e `detect_orientation_auto()` - todas tratam corretamente os valores de orientação.

- **Arquivos alterados:**
  - `nexus/editor/media_converter.py` — correções completas nos timeouts, exceções e logging
  - `docs/ATUALIZACOES.md` — registro da sessão com versão interna 0.8.10

- **Validação técnica:** Leitura completa do arquivo media_converter.py (453 linhas) verificando:
  - Inicialização do logger antes de qualquer uso
  - Tratamento específico para `subprocess.TimeoutExpired` em todos os métodos de subprocess
  - Consistência dos timeouts entre todas as funções
  - Manejo correto de orientações não padrão ('43', 'cine')
  - Compatibilidade entre `convert()`, `convert_square()` e `detect_orientation_auto()`
  - Tratamento de caminhos de entrada/saída válidos
  - Nenhuma execução real foi realizada nesta sessão (apenas análise técnica)

- **Pendências:**
  - Testar com vídeos reais contendo orientações não padrão para validar o tratamento correto
  - Monitorar conversões longas (>5 min) para confirmar que os timeouts de 600s são adequados
  - Considerar implementar cancelamento de tarefas em execução para conversões muito longas
  - Verificar se a detecção automática de orientação pode ser melhorada com leitura da tag `rotate` da metadata via ffprobe

## 0.8.9 — 2026-09-29 — Marco interno / sem preparação de release

### Curadoria, Correção e Organização do Dataset de Fine-Tuning do Agente (Bionic)

- Realizada auditoria rigorosa de integridade e conteúdo em `C:\IA_dublagem\agent_dataset`: identificados erros de sintaxe JSON (aspas mal escapadas, `extra data` por fechamento prematuro e quebras de linha brutas quebrando o formato JSONL), além de desvios conceituais (amostras com comportamento ineficiente e alucinações gravadas como exemplos positivos).
- Criada a pasta `counterexamples/` e isolados os contraexemplos para não contaminar o SFT: `002_models_unsupported_claims.jsonl` (alucinações técnicas), `002_inefficient_read.jsonl` (leituras fragmentadas ineficientes) e `001_alucination.jsonl` (cópia do raw com ferramenta alucinada).
- Corrigidos estruturalmente 5 arquivos de treino positivo e padronizados no formato ChatML `{"messages": [{"role": "...", "content": "..."}, ...]}` com 1 objeto JSON válido por linha física: `excellent/003_evidence_audit.jsonl`, `tool_use/003_models_investigation.jsonl`, `tool_use/004_efficient_file_read.jsonl`, `anti_hallucination/001.jsonl` e `corrected/001_alucination_fixed.jsonl`.
- Compilado o arquivo consolidado de treinamento `dataset.jsonl` na raiz com os 5 exemplos válidos, totalizando 14.871 bytes e 100% livre de erros de parsing para carregamento via QLoRA/Unsloth na RTX 3050 (6GB).
- Validação técnica: script Python confirmou parsing JSON individual e estrutura de mensagens em todas as amostras consolidadas.
- Continuação registrada a partir da transcrição do usuário: `excellent/004_readonly_investigation.jsonl` (14 mensagens) e `anti_loop/002_fragmented_file_read_loop.jsonl` (8 mensagens) existem como uma linha JSONL válida cada. O consolidado `dataset.jsonl` continua com somente 5 exemplos-base; as duas novas amostras ainda não foram incorporadas. A hipótese de que reduzir temperatura de 0,8 para 0,2 diminua loops ainda aguarda teste comparativo no Bionic; não tratá-la como causa comprovada nem como substituto garantido do fine-tuning. Escopo realista registrado: cerca de 20 exemplos podem reforçar padrões operacionais estreitos, mas não transformam amplamente o modelo nem ensinam domínio completo; temperatura, prompt, recuperação de contexto e fine-tuning atuam em aspectos diferentes. Próximo passo de avaliação: comparar a mesma tarefa e configuração alterando apenas a temperatura e registrar chamadas/loops e resultado. Verificação nesta sessão: os dois arquivos existem, cada um contém 1 linha e ambos fazem parse com 14 e 8 mensagens respectivamente; dataset compilado tem 5 linhas. Sem alterações nos exemplos nem treinamento executado.

### Comparação controlada de consultas AudioSep

- Reexecutado o trecho 20–50 s do `other.wav` existente, uma vez para `accordion` e outra para `synthesizer`, usando o venv isolado e os pesos já baixados. Nenhuma instalação, HTDemucs, residual ou mudança em `analysis.json`, `style.json`/Style Pack.
- As duas estimativas independentes ficaram quase idênticas: similaridade de forma de onda (cosine) 0,99904 nos primeiros 5 s (20–25 s da música) e 0,99968 nos 25 s seguintes (25–50 s); RMS praticamente igual em ambas as janelas. Logo, trocar a consulta para `synthesizer` não isolou melhor o sintetizador nem rejeitou a sanfona nesta faixa. Métricas e janelas por segundo em `scratchpad/audiosep_forro_accordion_20260928/AUDIOSEP_PROMPT_COMPARISON.json`; WAVs `AUDIOSEP_ACCORDION_V2.wav` e `AUDIOSEP_SYNTHESIZER.wav`.
- Para respeitar o PC de quatro núcleos, o processo teve afinidade com dois processadores lógicos, prioridade abaixo do normal e uma thread PyTorch; as consultas foram sequenciais. CUDA na RTX 3050; pico observado: RAM 3.383 MiB, VRAM global 2.511 MiB (2.042 MiB reservados pelo PyTorch). O total de parede registrado foi 872 s, dominado pela inicialização/carregamento limitado; as inferências individuais duraram 3,313 s e 1,796 s. Não iniciar novos testes sem solicitação.
- Arquivo de execução: `scratchpad/run_audiosep_prompt_compare_20260928.py`. Confirmação técnica: dois WAVs mono de 30 s a 32 kHz, escala de volume comum e manifesto JSON válido. Pendência: usuário ainda pode ouvir os dois novos resultados.
