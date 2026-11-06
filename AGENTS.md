# Registro permanente de atualizações

- Privacidade em publicações: use o e-mail `noreply` do GitHub e o nome público da conta em commits/tags. Antes de publicar, confira `git config user.email`; nunca use e-mail pessoal. Não inclua dados pessoais novos em documentação ou relatórios públicos. Remover dados do histórico exige escopo explícito e cópia de segurança isolada.

- Para preparar versões, use a entrada simples `python PREPARAR_RELEASE.py --version VERSAO` e siga `docs/PREPARAR_RELEASE_IA.md`. Leia `_updates/release-assistant/LEIA_PRIMEIRO.txt` e `ULTIMO_RESULTADO.json`; se FALHOU, pare e siga `next_action`. O comando não publica. Não contorne conflitos nem presuma sucesso por ausência de saída.

- Para pedidos de publicação no GitHub, siga `docs/PUBLICAR_RELEASE.md` e `release/policy.json`. Prepare a release com `release/prepare_release.py` em worktree separado; revise o relatório antes de commit/push. Nunca adicione toda a pasta de desenvolvimento ao Git indiscriminadamente.

- Esta instalação é uma cópia de desenvolvimento protegida por `.nexus-development`. Preserve esse marcador local, não o inclua nas releases e nunca use o atualizador para substituir este checkout. Versões públicas podem estar atrás do trabalho local.

- Antes de alterar o projeto, leia `docs/ATUALIZACOES.md` e `docs/documentacao/CONTEXTO_IA.md`.
- Ao concluir qualquer sessão que altere código, configuração ou documentação, atualize `docs/ATUALIZACOES.md` antes da resposta final. Assim, o histórico do dia fica registrado mesmo sem uma sessão adicional à noite.
- Siga o formato e a sequência descritos no arquivo: data de Brasília, marco interno, mudanças, arquivos relevantes, validação efetivamente realizada e pendências. Complemente a entrada do mesmo dia; abra o próximo marco no próximo dia com alterações.
- Não atribua alterações antigas ao dia atual, não invente datas ou testes e preserve o histórico. Consultas sem alterações não exigem uma entrada.
- Numeração (decisão do responsável em 2026-11-06): versões com duas partes. A v0.8.2 publicada equivale a 0.82; cada dia com alterações soma 0.01; com 9 dias de alterações após a v0.8.2, a entrada de 2026-11-06 é 0.91; a correção de segurança do mesmo dia saiu como 0.93 por decisão do responsável, e o próximo dia com alterações será 0.94, depois 0.95... (depois de 0.99 vem 1.0). O número da entrada mais recente em `docs/ATUALIZACOES.md` é o número da próxima release. Não publique tags ou releases apenas por atualizar o histórico; diferencie versão planejada de publicação concluída.

- A v0.91 foi publicada com sucesso no GitHub em 2026-11-06 (antes dela, v0.8.2). NÃO prepare nem publique uma nova versão sem pedido explícito do responsável. Por enquanto, continuar desenvolvimento normal em C:\IA_dublagem.
- Ao preparar uma release, consolide as entradas não publicadas em `docs/NOTAS_PARA_GITHUB.md` e `RELEASE_NOTES.md`; após publicar, registre versão, data, link e marcos incluídos no histórico.
