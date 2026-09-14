# Registro permanente de atualizações

- Para preparar versões, use a entrada simples `python PREPARAR_RELEASE.py --version VERSAO` e siga `docs/PREPARAR_RELEASE_IA.md`. Leia `_updates/release-assistant/LEIA_PRIMEIRO.txt` e `ULTIMO_RESULTADO.json`; se FALHOU, pare e siga `next_action`. O comando não publica. Não contorne conflitos nem presuma sucesso por ausência de saída.

- Para pedidos de publicação no GitHub, siga `docs/PUBLICAR_RELEASE.md` e `release/policy.json`. Prepare a release com `release/prepare_release.py` em worktree separado; revise o relatório antes de commit/push. Nunca adicione toda a pasta de desenvolvimento ao Git indiscriminadamente.

- Esta instalação é uma cópia de desenvolvimento protegida por `.nexus-development`. Preserve esse marcador local, não o inclua nas releases e nunca use o atualizador para substituir este checkout. Versões públicas podem estar atrás do trabalho local.

- Antes de alterar o projeto, leia `docs/ATUALIZACOES.md` e `docs/documentacao/CONTEXTO_IA.md`.
- Ao concluir qualquer sessão que altere código, configuração ou documentação, atualize `docs/ATUALIZACOES.md` antes da resposta final. Assim, o histórico do dia fica registrado mesmo sem uma sessão adicional à noite.
- Siga o formato e a sequência descritos no arquivo: data de Brasília, marco interno, mudanças, arquivos relevantes, validação efetivamente realizada e pendências. Complemente a entrada do mesmo dia; abra o próximo marco no próximo dia com alterações.
- Não atribua alterações antigas ao dia atual, não invente datas ou testes e preserve o histórico. Consultas sem alterações não exigem uma entrada.
- A versão alvo escolhida pelo responsável é 0.8.0. Os próximos marcos internos seguem 0.8.1, 0.8.2 etc., salvo nova decisão explícita. Não publique tags ou releases apenas por atualizar o histórico; diferencie versão planejada de publicação concluída.
- Ao preparar uma release, consolide as entradas não publicadas em `docs/NOTAS_PARA_GITHUB.md` e `RELEASE_NOTES.md`; após publicar, registre versão, data, link e marcos incluídos no histórico.
