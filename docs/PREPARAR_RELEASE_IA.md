# Preparar release — guia curto para IA local

Entrada fácil de achar: `PREPARAR_RELEASE.py`, na raiz do projeto.
Serve para qualquer versão futura; use o número escolhido pelo responsável.
Não carrega modelos nem usa CUDA. Não instala dependências e não publica.

## Comando

No PowerShell, dentro de `C:\IA_dublagem`:

```powershell
python PREPARAR_RELEASE.py --version 0.8.1
```

Troque `0.8.1` pela versão solicitada. Python 3.10+, Git e Node devem estar no PATH;
o Python escolhido deve ter as dependências dos testes (incluindo Flask e requests).
Pode usar o Python do ambiente existente; não recrie o ambiente nem baixe modelos.

Antes, confira `nexus/version.py`, README.md, RELEASE_NOTES.md e
docs/NOTAS_PARA_GITHUB.md: devem corresponder à versão escolhida, com as notas
consolidadas. O script não inventa notas nem muda o número da aplicação sozinho.
Uma simples menção ao número não substitui a revisão documental.

Para somente verificar pré-requisitos, sem rede, worktree ou testes:

```powershell
python PREPARAR_RELEASE.py --version 0.8.1 --check-only
```

Sem internet, acrescente `--offline` ao comando normal. Isso usa a referência
origin/main já disponível; a conferência remota fica pendente. Não é necessário
ter uma IA na nuvem: com internet, Git acessa o GitHub diretamente.

## Leia o resultado, não tente adivinhar

Abra `_updates/release-assistant/LEIA_PRIMEIRO.txt`.
O resultado estruturado fica em `_updates/release-assistant/ULTIMO_RESULTADO.json`.
Cada execução mantém seus próprios logs e result.json em uma subpasta; anteriores
não são apagados. Código de saída 0 indica sucesso da modalidade solicitada;
1 indica falha, e 2 indica argumentos inválidos (veja `--help`).

| Resultado | Próximo passo |
|---|---|
| PASSOU_PRE_REQUISITOS | Ainda não preparou nada. Execute sem --check-only. |
| PASSOU_PREPARACAO_LOCAL | Revise destination, preparation.json e diff, inclusive arquivos novos. |
| FALHOU | Leia next_action e o log da etapa; pare antes de publicar. |

O comando normal faz fetch (exceto offline), fixa o SHA remoto, chama
release/prepare_release.py em pasta nova fora do desenvolvimento, confere hashes,
executa git diff --check, testes de preparação/atualização/distribuição e três
arquivos JavaScript. Essa seleção não executa síntese nem modelos de IA; não é a
suíte funcional completa. Cada comando tem limite de cinco minutos.

Não transforma falhas em sucesso, não resolve conflitos por conta própria e não
reutiliza permissões antigas de `--resolved-remote`. Se houver conflito, siga
[PUBLICAR_RELEASE.md](PUBLICAR_RELEASE.md), compare as versões e preserve o trabalho.
Não use reset --hard, pull, rebase ou descarte de arquivos como tentativa de reparo.
Se falhar depois de criar uma cópia, ela fica preservada para inspeção.

Nenhum commit, push, tag, instalador, atualização do checkout ou publicação é
executado por este comando. Mesmo com PASSOU, faltam revisão humana, build dos
executáveis, instalação real e teste de dublagem. Consulte PUBLICAR_RELEASE.md
somente na etapa posterior, com autorização do responsável.

A versão deve corresponder à cópia de código usada. Se a cópia de desenvolvimento ainda declarar uma versão anterior, a verificação deve parar até reconciliação explícita; não altere a numeração sem decisão do responsável.
