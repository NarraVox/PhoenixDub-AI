# Contexto do NarraVox para IA

Consulte também [Atualizações — Diário de evolução](../ATUALIZACOES.md) para o histórico recente. Ao concluir uma sessão com alterações, registre o trabalho nesse arquivo seguindo as regras de `AGENTS.md` na raiz.

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

OpenUnmix foi retirado do fluxo ativo por decisão do responsável. As separações antigas em `uploads/dj_projects/separated_*` permanecem no disco, sem painel/rotas de reutilização. Não apagar esses dados. Extended utiliza o áudio original como contexto e exporta somente a continuação após o fim da referência, antes da masterização.

As telas ficam em `nexus/client/`. `nexus/dub/dubbing.py` atende Games e Video; não separe seus dois modos sem uma necessidade comprovada.

## Core compartilhado

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

`uploads/` contém projetos e resultados do usuário. `MODELS/` contém modelos locais. `env/` é o ambiente Python. Não mova, renomeie ou apague esses itens em manutenção comum.

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
