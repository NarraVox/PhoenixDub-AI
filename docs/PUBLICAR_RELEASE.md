# Procedimento de publicação

Quando o responsável pedir uma publicação, use este fluxo. O pedido autoriza publicar a versão escolhida; a preparação isolada evita enviar o conteúdo inteiro da pasta de trabalho.

1. Leia AGENTS.md e ATUALIZACOES.md; confirme a versão já escolhida no contexto e em `nexus/version.py`.
2. Execute `git fetch origin main --tags`. Preserve alterações remotas. Nunca faça force-push nem substitua a cópia de desenvolvimento por uma release.
3. Consolide NOTAS_PARA_GITHUB.md em RELEASE_NOTES.md e atualize as informações de versão no README.
4. Revise `release/policy.json`: somente código, interfaces, documentação, testes e ferramentas de publicação autorizados entram. Configurações locais, experimentos Qwen ASR, backups, uploads, modelos, env, resultados de testes e `.nexus-development` ficam fora. Dependências de fornecedor já rastreadas são preservadas, sem copiar modificações locais delas.
5. Rode `python release/prepare_release.py --destination C:\IA_releases\vVERSAO --base origin/main`, usando uma pasta nova. O comando verifica padrões comuns de credenciais e sintaxe Python, mescla alterações remotas sem sobrescrever conflitos e monta um worktree isolado. Ele não publica nem cria commits/tags. Uma checagem de padrões não substitui revisão humana do diff.
6. Revise o relatório local `_updates/release-preparation/report.json` e `git diff` no worktree. Execute os testes relevantes. A pasta original permanece com seu trabalho e marcador intactos.
7. Crie uma branch `codex/release-vVERSAO` no worktree, faça commit apenas ali e confira o diff do commit. Reconfira o remoto; envie a atualização de main apenas por fast-forward. Não use `git add .` na cópia de desenvolvimento.
8. Envie a tag `vVERSAO`. O workflow gera `Nexus_AI_Pro.exe`, `Setup_Nexus.exe` e `PhoenixDub_Update.zip`, testa as importações e publica a release com RELEASE_NOTES.md. Acompanhe até concluir e confira os três anexos.
9. Se o build falhar, corrija e valide antes de publicar; não apresente execução pendente/falha como release concluída. Não mova tags já publicadas silenciosamente.
10. Após confirmar a publicação, registre link, data, commit e artefatos em ATUALIZACOES.md e NOTAS_PARA_GITHUB.md. Não altere o marcador de desenvolvimento.

A autenticação é feita pelo Git Credential Manager. Nunca coloque tokens em arquivos do projeto, comandos de commit, URLs remotas ou notas públicas.

Se uma mesclagem automática apontar conflito, revise o arquivo contra HEAD e origin/main. Depois de reconciliar seu conteúdo explicitamente, pode usar `--resolved-remote NOME_DO_ARQUIVO`; essa exceção fica no relatório e não dispensa a revisão do diff.
