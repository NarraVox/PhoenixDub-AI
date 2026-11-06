# Contexto do NarraVox para IA

Consulte também [Atualizações — Diário de evolução](../ATUALIZACOES.md) para o histórico recente. Ao concluir uma sessão com alterações, registre o trabalho nesse arquivo seguindo as regras de `AGENTS.md` na raiz.

Nexus Style Analyzer: a interface/API usam Open-Unmix em CUDA por padrão, com CPU como alternativa explícita; BPM/grade e várias extrações NumPy/librosa seguem em CPU, pois não têm adapter CUDA. HTDemucs permanece no código e em análises antigas, mas novas solicitações são rejeitadas. SheetSage2 é opcional e usa CUDA quando ativado; nenhum modelo é baixado automaticamente. O worker recebe prioridade abaixo do normal, usa até metade da afinidade de CPU e limites de threads. A pré-checagem reserva até 3,5 GiB de RAM e VRAM do worker mais 1 GiB de folga de RAM; só inicia se a projeção permanecer abaixo de 90% da RAM/VRAM. O supervisor observa o consumo e interrompe após três verificações acima de 90% do total ou acima de 3,5 GiB de RAM no worker. Entrada limitada a 5 minutos/128 MB e mínimo de 2 GB em disco. Se CUDA ou a leitura de VRAM via `nvidia-smi` estiver indisponível, a solicitação é bloqueada e o erro informado, inclusive em modo CPU, pois o teto global não poderia ser verificado. SheetSage2 usa apenas modelo já instalado. Se ausentes, `GET /api/styles` informa os caminhos esperados: `MODELS/SheetSage2-GGUF/sheetsage2-orig.gguf` e o CLI em `env/tools_yue2/.../audiocpp_cli.exe`. Os stems permanecem `drums`, `bass`, `vocals` e `other`.

Em projetos HTDemucs, a etapa experimental Instrument Discovery lê o `other.wav` existente e executa em processo DJ separado, na CPU, os modelos ONNX oficiais Discogs EffNet + MTG-Jamendo Instrument de `scratchpad/dj_instrument_models/`. O pacote Python nativo do Essentia não foi instalado no Windows/Python 3.12. `instrument_detection.json` e `analysis.json.instrument_detection` guardam as 40 pontuações por janela e regiões aproximadas; `style.json.instruments` guarda o resumo. Essas pontuações não são probabilidades calibradas nem confirmação auditiva de presença instrumental. Não usar essa saída ainda para escolher solos ou timbres do Arranger.

Na validação atual, `raw_predictions` preserva a saída do Detector A, `confirmed_instruments` fica vazio até confirmação humana e `ambiguous_instruments` contém apenas hipóteses de revisão. Detecções de `bass` e `drums` em `other.wav` não substituem os stems dedicados. Os cinco WAVs de escuta de Forró Perfeito estão em `scratchpad/forro_perfeito_instrument_review_20260928/`, com tempos em `REVIEW_MANIFEST.json`. Nenhum segundo detector foi instalado ainda.

O Detector B AST AudioSet foi testado no mesmo `other.wav`, usando ONNX INT8 local em CPU: Accordion alcançou score 0,89198 na janela 25–35 s, enquanto Synthesizer teve máximo 0,0463. O Detector A apontava o inverso, então ambos são evidência em conflito; `confirmed_instruments` segue vazio. O resultado integral B está em `instrument_detection_ast.json`. Opções pesquisadas para separar áudio por instrumento: HTDemucs 6s (guitarra/piano fixos, piano com bleed conhecido), Banquet (modelo musical query-conditioned; consulta de áudio, bom candidato para guitar/piano/reeds/organs) e AudioSep (texto livre, 32 kHz e chunking). AudioSep foi testado isoladamente em `scratchpad/audiosep_env` no trecho 20–50 s de `other.wav`, com consulta `accordion`, gerando `AUDIOSEP_ACCORDION.wav` e `AUDIOSEP_RESIDUAL.wav`. A escuta do responsável identificou sintetizador nos primeiros 5 s do alvo e sanfona nos 25 s restantes: boa captura temporal na maior parte, com vazamento inicial. Resultado e timeline estão em `AUDIOSEP_TEST.json`; não integrado ao pipeline nem aplicado ao Style Pack.

Na comparação controlada de 29/09/2026, consultas independentes `accordion` e `synthesizer` no mesmo trecho produziram saídas quase idênticas: cosine 0,99904 na janela original 20–25 s e 0,99968 em 25–50 s, com RMS praticamente igual. A consulta textual não separou seletivamente sintetizador e sanfona nesse material. Os WAVs e dados por segundo estão em `scratchpad/audiosep_forro_accordion_20260928/`; CPU limitada a um thread PyTorch/dois processadores lógicos, prioridade abaixo do normal. Não integrar ainda.

O projeto Style Analyzer `uploads/dj_styles/797e6ec8e105f08869ad5759` usa os stems HTDemucs de Forró Perfeito e hints de grade 95,043 BPM/2/4/offset 0,221 s; produziu 58 compassos e perfis rítmicos de bateria, baixo e acompanhamento. O controle `offset` é encaminhado com esse nome ao detector. O manifesto registra separador e dispositivo também nas retomadas. Esse Style Pack ainda não contém score harmônico novo, motivo de baixo relativo confirmado nem loops A/C auditados nos novos stems; não misturar automaticamente a auditoria feita sobre Open-Unmix com esta separação.

O Style Analyzer 0.6.1 calcula fills no stem drums HTDemucs: assinaturas low/mid/high e ataques em 16 passos são comparados a um MAIN recorrente; desvios com ataques adicionais e retorno próximo ao MAIN são candidatos automáticos. `analysis.json.fill_detection` guarda evidências por compasso, thresholds, limites parciais, rejeições e clusters; `style.json.fills` e `style_pack.fill_patterns` guardam os grupos. Uma revisão humana explícita em `fill_review.json` pode confirmar regiões que falharam no critério de retorno ao MAIN, sem relaxá-lo para outras faixas. Em Forró Perfeito, o detector encontrou oito dos dez trechos exportados; a escuta confirmou todos os dez como viradas. O compasso 10 foi agrupado como cauda curta de FILL_A; 17–18 entrou em FILL_A e o compasso 58 permaneceu um FILL_C isolado. A seção MAIN do classificador de frases permanece uma camada separada e pode sobrepor um fill localizado; não usar uma frase inteira como loop estável somente por ela ter rótulo MAIN.

Em 2026-09-28, o responsável também aprovou pelo ouvido os tipos FILL_A/B/C reunidos nos WAVs de comparação; `analysis.json` e `style.json` registram essa aprovação, sem novo cálculo do detector. O MAIN A deste projeto recebeu um motivo de baixo relativo 1–3–5 / 1–♭3–5 a partir do bass.wav HTDemucs: 38 compassos limpos com acorde único previamente alinhado exibiram os três graus, com ataques quantizados nos passos 0/8/12 e terça/quinta abaixo da raiz. O alinhamento anterior do SheetSage2 é fraco e o motivo ainda não passou por escuta humana específica; os detalhes e exclusões estão em `scratchpad/forro_perfeito_htdemucs_bass_validation_20260928.json`. MAIN B segue sem padrão de baixo distinto confirmado. Uma futura reanálise integral do projeto ainda poderá sobrescrever essas anotações manuais se não houver mecanismo de reaplicação; não executar o worker apenas para revisar o baixo.

> Leia antes de alterar o projeto. Este é um mapa curto; o código em `nexus/` é a fonte de verdade. Atualize-o somente quando uma mudança estrutural for concluída.

Preparação de versões: execute `python PREPARAR_RELEASE.py --version VERSAO` na raiz, seguindo [PREPARAR_RELEASE_IA.md](../PREPARAR_RELEASE_IA.md). Leia o resultado em `_updates/release-assistant/LEIA_PRIMEIRO.txt`; falhas exigem revisão, nunca descarte automático ou publicação.

## Propósito e início

NarraVox Studios é uma suíte local para dublagem PT-BR de jogos e vídeos, edição de vídeo e mixagem de DJ com IA. Roda no Windows, é voltada a RTX 3050 com 6 GB de VRAM e exige FFmpeg no `PATH`.

Entrada: `python nexus/nexus_app.py`, a partir da raiz. Ele abre a janela PyWebView e o Hub em `127.0.0.1:5000`.

## Motores

| Motor | Porta | Código principal | Função |
|---|---:|---|---|
| Hub | 5000 | `nexus/nexus_app.py`, `nexus/nexus_routes.py` | Janela, UI e controle de motores. |
| Titan Games | 5002 | `nexus/dub/dubbing.py`, `nexus/core/orchestrator_jobs_games.py` | Dublagem em lote e ferramentas VPK/PCK/FMOD. |
| Vortex Editor | 5003 | `nexus/editor/narravox_editor.py` | Edição, cortes, legendas e efeitos. |
| Titan Video | 5004 | `nexus/dub/dubbing.py` | Dublagem de vídeo e fila de vídeos. |
| Vortex DJ | 5005 | `nexus/dj/vortex_dj.py`, `vortex_*` | Análise e mixagem de faixas. |

Vortex DJ: a opção Cover usa `cover-nofsq` (Cover fiel experimental), com o áudio enviado como origem e referência de timbre. Ignora o campo de estilo e usa instrução neutra de preservação, evitando gêneros incorretos inferidos pelo LM. AudioSR/masterização é opcional e desativado por padrão. A fidelidade musical ainda depende de avaliação auditiva.

SheetSage2 produz ABC/eventos que contribuem com tonalidade, acordes por compasso, estrutura e perfil de notas. A consolidação combina essas hipóteses de BPM/métrica com Nexus Rhythm e a duração/acentuação dos stems; a harmonia é mapeada por compasso usando suporte de tons nos stems bass/other. Resultados ficam em `analysis.json`/`style.json`, com confiança heurística e alinhamento fraco sinalizado. A experiência histórica chegou a consumir quase toda a VRAM de uma RTX 3050 de 6 GB; o fluxo atual limita a ocupação observada a 90%. O modelo usa somente os arquivos locais informados pelo endpoint de disponibilidade, sem download automático. A licença é CC BY-NC 4.0; distribuição/uso comercial requer revisão.

Nexus Arranger: o Style Analyzer inclui `style_pack` v2.1 em `analysis.json`/`style.json`, com ataques de bateria por passos, probabilidade de repetição e evidência grosseira de faixas de frequência. Perfis de baixo têm `relative_pattern`; quando há somente evidência de energia, ele fica `unconfirmed`. No pack atual de Forró Perfeito, MAIN A guarda o motivo experimental 1–3–5 alinhado à harmonia (terça menor nos acordes menores), duração/ritmo estimados e confiança média; MAIN B permanece explicitamente não confirmado. O planner transpõe esses graus ao acorde novo. Acompanhamento segue guardando somente posição/força dos ataques, sem alturas ou eventos vocais. São extraídos perfis apenas de padrões repetidos e seções classificadas como detectadas. O planner leva os eventos ao `arrangement.json`, repete a bateria aprendida e cria notas novas de baixo/voicings de acompanhamento nos mesmos passos usando os novos acordes. Se não houver forma detectada, exige `song.sections` do usuário em vez de inventar INTRO/FILL/ENDING. A entrada opcional é `song: {title, lyrics, key, sections:[{type,bars,chords}], melody_by_bar}`; acordes/melodia submetidos são da música nova. Sem melodia, cria motivo determinístico de tons de acorde, sem consultar notas da referência. `arrangement.json` preserva padrões detalhados de bateria, baixo e acompanhamento do Style Pack. A ponte ABC para YuE2 segue o dialeto documentado: somente `Vocal` e `Ins` monofônicos, símbolos de acordes sobre Vocal, e cabeçalhos `M`, `Q` (BPM inteiro), `L` e `K`; a linha Ins pode carregar baixo novo revozeado aos acordes. Em `L:1/32`, cada compasso soma `32 × numerador / denominador` unidades (por exemplo, 16 em 2/4). Os blocos seguem Vocal antes de Ins, em grupos de até quatro compassos e com comentários estruturais documentados. Não enviar Drums/Bass/Comp como vozes ABC ou acordes empilhados. O controle `style` resume gênero/groove/timbres e BPM/métrica; ataques exatos de bateria, passos de acompanhamento, voicings polifônicos e dinâmica não têm controles dedicados no backend YuE2. O limite semântico padrão no fluxo Arranger é 6× a estimativa (+512 mínimo), pois o runtime pode ultrapassar a duração estimada; valide `semantic.truncated` e a duração real nos logs. `POST /api/styles/<id>/generate` prepara `generation_preview.json` com `cot=full` e `abc_file=<caminho>`; `dry_run=false` chama o worker/gera áudio. Qwen é opt-in. YuE2 pode reinterpretar score/prompt e a duração é aproximada; não há garantia auditiva de aderência nem renderer separado para stems.

Nexus Renderer MVP: `nexus.dj.arranger.renderer.render_arrangement()` transforma eventos `performance_by_bar` em WAV sem YuE2. Usa ataques rítmicos extraídos para bateria (descarta probabilidade abaixo de 0,6667), passos do baixo com notas revozeadas à harmonia nova e ataques do acompanhamento com voicings novos. Por padrão, bateria usa síntese procedural; opcionalmente, `reference_drum_stem` toca one-shots curtos do stem isolado nos passos correspondentes do padrão aprendido, usando `reference_grid_start_seconds` para alinhar a primeira barra da referência. Com stem fornecido, não há fallback para sons sintéticos: se nenhum trecho-fonte servir, o ataque fica em silêncio. Para cada passo, a amostra mais forte entre as ocorrências observadas é usada de forma consistente. Essa opção pode conservar timbres mais naturais, mas herda vazamento/artefatos do stem e não garante sons de bateria limpos. Sem amostras, bandas low/mid/high são evidência espectral, não instrumentos: low vira um impacto grave, mid um toque tonal curto e high um toque metálico. O render é mono e determinístico; não identifica timbres reais. Toca somente seções presentes no arrangement e não inventa FILL/INTRO/ENDING sem evidência; para representar um MAIN A com padrão de 8 compassos, renderize a frase completa em vez de cortar no meio.

O Renderer também aceita `reference_drum_loop` e `drum_loop_bars` para repetir um loop contínuo do stem, em estéreo, com duração ajustada à grade e suavização curta nas junções. Em Forró Perfeito, o MAIN A de quatro compassos aprovado foi repetido quatro vezes em uma prévia de 20,20 s com baixo relativo revozeado. O template de ataques do baixo foi corrigido com os compassos 49–50 do stem para aproximar seus ataques dos da fonte; esse ajuste ainda requer avaliação auditiva.

A revisão auditiva posterior marcou os compassos 43–46 (A) e 51–54 (C) como loops estáveis MAIN A. Os compassos 47–50 (B) contêm uma virada de localização ainda não determinada; B permanece como candidato, sem classificação da faixa inteira como FILL. `style_pack_review.json` conserva a revisão e o motivo relativo de baixo quando o pipeline é reexecutado, produzindo o pack auditado v2.2. O Arranger grava A–C como plano de loops, e `reference_drum_loop_stem` no Renderer toca somente os trechos auditados diretamente do stem, alternando-os em blocos de quatro compassos.

Na prévia posterior de bateria e baixo, o excerto B47–48 serve apenas como entrada única e não como loop MAIN A ou FILL inteiramente identificado. O groove normal segue A–C–A–C. Os ataques do baixo 1–3–5 usam os passos 0/8/12 aferidos nas ocorrências estáveis A/C. O Renderer coloca excertos do stem e notas do baixo na mesma timeline de BPM/métrica, 16 passos por compasso e limites de amostras; conserva o microtiming interno do áudio de bateria. A confirmação auditiva do encaixe final ainda está pendente.

OpenUnmix foi retirado do fluxo ativo de geração/mixagem por decisão do responsável. O Style Analyzer isolado reutiliza o adapter Open-Unmix somente para sua análise explícita, em CPU ou CUDA segundo a opção selecionada, preservando os quatro stems. As separações antigas em `uploads/dj_projects/separated_*` permanecem no disco, sem painel/rotas de reutilização. Não apagar esses dados. Extended utiliza o áudio original como contexto e exporta somente a continuação após o fim da referência, antes da masterização.

As telas ficam em `nexus/client/`. `nexus/dub/dubbing.py` atende Games e Video; não separe seus dois modos sem uma necessidade comprovada.

## Core compartilhado

Na dublagem, o fluxo existente mantém etapas de IA sequenciais e descarrega Whisper/TTS/Qwen nas transições; jogos geram as falas uma por vez. A proteção foi encaixada nesses mesmos pontos, sem trocar os motores: preserva ao menos 4 GiB de RAM livre e reserva mais para modelos grandes; bloqueia novas cargas quando uso global de RAM atinge 90%, reserva VRAM prevista antes dos modelos e mantém 10% da VRAM total para driver/desktop. Whisper e Pyannote podem usar CPU se a GPU não tiver margem; Qwen3-TTS tenta 0.6B caso 1.7B não caiba no teto; o Qwen GGUF local interrompe a etapa com mensagem quando não houver margem CUDA e usa no máximo metade dos núcleos lógicos. O evento de tela preta permanece sem causa confirmada; estas barreiras reduzem risco, mas não provam que a causa anterior foi memória ou driver.

Atualizações do Hub: versão central em `nexus/version.py`, consulta em `nexus/updates.py`, download em `update_manager.py` e aplicação externa em `update_worker.py`. Consulte [ATUALIZACAO_AUTOMATICA.md](../ATUALIZACAO_AUTOMATICA.md) antes de alterar empacotamento ou atualização. Nunca inclua dados/modelos/configurações locais no pacote.

A cópia de desenvolvimento de Paulo é protegida por `.nexus-development` (local, fora do Git). Preserve o marcador. O atualizador deve permitir apenas consulta nessa cópia e jamais substituir o trabalho local pela release pública, mesmo que a numeração pública seja superior.

Motor de transcrição adotado: **Whisper**. Qwen ASR foi um experimento considerado mais lento pelo responsável; não deve ser ativado como padrão nem anunciado como recurso da v0.8.0. Isso não altera o uso de Qwen para tradução e síntese de voz.

`nexus/core/` contém a lógica comum:

- `model_loader.py`, `qwen_loader.py`, `whisper_loader.py`, `tts_loader.py`: modelos e VRAM.
- `diarization.py`, `whisper.py`, `translation*.py`, `tts.py`: voz, texto, tradução, sincronia e LQA.
- `vocals.py`, `utils_audio.py`, `utils.py`: stems, áudio, progresso e JSON seguro.
- `orchestrator_jobs_games.py`, `orchestrator_jobs_core.py`, `batch_orchestrator.py`: jobs, etapas e retomada.
- `security.py`, `system_guard.py`: Flask local, caminhos permitidos e proteção da máquina.

`nexus/core/__init__.py` reexporta símbolos e resolve dependências circulares; não altere imports do Core isoladamente.

## Dados e fluxos

`uploads/` contém projetos e resultados do usuário. `MODELS/` contém modelos locais, principalmente GGUFs. `env/` guarda o ambiente Python e ferramentas locais instaladas, como `tools_yue2`, `tools_acestep` e `tools_vgmstream`. Não mova, renomeie ou apague esses itens em manutenção comum.

Em `uploads/<job_id>/`: `job_status.json` guarda o estado; `project_data.json`, os segmentos; `_backup_transcricao/` e `_backup_texto_final/`, os caches; `_dubbed_audio/`, a síntese; `_saida_final/`, a saída. Em Games, `_1_MOVER_OS_FICHEIROS_DAQUI/` é a entrada e `_2_PARA_AS_PASTAS_DE_VOZ/` guarda referências de falantes.

Games: entrada → diarização/referências → transcrição → tradução/sincronia → TTS → LQA/mixagem → saída.

Video: cópia do vídeo → FFmpeg → vocais/instrumental → diarização/transcrição → tradução/sincronia → TTS → mixagem/remux.

## Regras críticas

1. **VRAM sequencial:** descarregue o modelo pesado anterior; preserve `unload_*`, `gc.collect()` e `torch.cuda.empty_cache()`.
2. **JSON seguro:** use `safe_json_read` e `safe_json_write` para dados críticos; não use `json.dump` diretamente.
3. **Edição manual:** `manual_edit_text` tem prioridade e nunca deve ser sobrescrito sem ordem explícita.
4. **Cache granular:** não delete `_backup_texto_final/` inteiro; trate somente o segmento autorizado.
5. **Voz:** preserve diálogos curtos; texto vazio em áudio audível pede nova transcrição, não descarte.
6. **Segurança:** mantenha `security.py` como primeiro import de `nexus_app.py` e não libere caminhos arbitrários.
7. **Estado atual:** esta cópia não contém Cine-Gen/Godogen ativos dentro de `nexus/`; não trate módulos ausentes como produção.

Após mudar portas, arquitetura, fluxo, dados ou regras permanentes, atualize apenas a seção pertinente deste arquivo.
