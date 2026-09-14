# Guia de manutenção para IA

> Use junto com `CONTEXTO_IA.md`. O objetivo é localizar o código certo, fazer a menor mudança segura e verificar o resultado.

## Antes de editar

1. Leia `CONTEXTO_IA.md` e localize o motor afetado.
2. Leia a rota/entrada e a função chamada por ela. Código e logs valem mais que documentação antiga.
3. Antes de mudar dados, confira `job_status.json` e `project_data.json` do fluxo afetado.
4. Preserve `uploads/`, `MODELS/` e `env/`.
5. Não faça reformatação ou refatoração ampla junto com uma correção pequena.

## Mapa de diagnóstico

| Pedido ou sintoma | Comece por | Depois confira |
|---|---|---|
| Janela, portas ou motores | `nexus/nexus_app.py`, `nexus/nexus_routes.py` | `nexus/client/nexus_premium.*` |
| Tela Games/Video | `nexus/client/games_studio.*` ou `video_studio.*` | `nexus/dub/dubbing.py` |
| Job Games | `nexus/core/orchestrator_jobs_games.py` | `diarization.py`, `whisper.py`, `translation*.py`, `tts.py` |
| Vídeo, fila ou remux | `nexus/dub/dubbing.py` | FFmpeg e JSON do job |
| Tradução, sincronia, LQA | `translation_processors.py`, `translation_sync.py`, `translation_corrector.py` | `translation_utils.py`, `translation_api.py` |
| Voz e diarização | `diarization.py`, `whisper.py`, `tts.py` | loaders `*_loader.py` |
| VRAM/CUDA/modelos | `model_loader.py`, `qwen_loader.py`, `tts_loader.py`, `whisper_loader.py` | `requirements.txt` e logs |
| Editor | `nexus/editor/narravox_editor.py` | `nexus/client/vortex_editor.*` |
| DJ | `nexus/dj/vortex_dj.py` | módulos `vortex_*` |
| Caminhos/stream | `nexus/core/security.py`, `nexus/nexus_routes.py` | não liberar caminhos arbitrários |

## Diagnosticar e validar

- Leia logs e JSON do job antes de repetí-lo. Para jobs retomáveis, use rotas e caches existentes em vez de recriar pastas.
- Diferencie fato confirmado, hipótese e mudança proposta no relatório final.
- Em falha de modelo, confirme VRAM liberada, arquivos de modelo e FFmpeg antes de alterar o pipeline.
- Se a mudança puder apagar áudio, cache, texto manual ou saída final, peça autorização.
- Depois de editar, faça a checagem de sintaxe/importação apropriada, confirme a combinação rota/API/UI e revise o diff para garantir que `uploads/`, `MODELS/` e `env/` não foram tocados.

## Regra desta pasta

Mantenha somente dois arquivos aqui: este guia e `CONTEXTO_IA.md`. Não crie resumos de correções, mapas paralelos ou changelogs. Correções pontuais ficam no Git e no relatório; mudanças permanentes entram, em uma frase curta, no arquivo adequado.
