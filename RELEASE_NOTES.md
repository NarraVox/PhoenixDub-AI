# PhoenixDub AI v0.8.2 — Correções do instalador

- Instalador e instalação por pip compartilham requirements.txt, com versões compatíveis de Qwen3-TTS, Transformers, WhisperX e pyannote.audio.
- TESTAR_SETUP.bat usa sua própria pasta, confere erros e deixa a configuração do token para a interface.
- FFmpeg e ffprobe são verificados; quando ausentes, são baixados com conferência SHA-256 para o ambiente local.
- Ambiente inválido não é apagado nem substituído por instalação global. pip check bloqueia conclusão com dependências incompatíveis.
- Corrigida falha no download dos modelos causada por import local de subprocess.
- Preparação de release exige endereço noreply do GitHub para evitar exposição de e-mail pessoal em novos commits.

Validação em andamento: testes do instalador e resolução de dependências. Build e publicação ainda não concluídos. Dublagem em GPU e instalação completa com modelos não validadas nesta correção.
