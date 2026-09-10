# Atualização pelo Hub

O Hub mostra a versão definida em `nexus/version.py`. O botão **Verificar atualizações** consulta a release pública estável mais recente de NarraVox/PhoenixDub-AI e compara números de versão. Uma versão local superior à publicada é apresentada como desenvolvimento; erro de conexão nunca é apresentado como aplicativo atualizado.

Quando existe pacote compatível, **Atualizar e reiniciar** baixa `PhoenixDub_Update.zip`, confere o SHA-256 fornecido pelo GitHub e os hashes do manifesto interno. Um processo externo espera o Hub encerrar, guarda os arquivos antigos em `_updates/<id>/backup`, substitui os arquivos do programa e inicia o aplicativo novamente. Se a cópia falhar, tenta restaurar os arquivos substituídos. O resultado fica em `_updates/result.json`.

## Preservação e limites

- O pacote admite apenas arquivos de código/interface sob `nexus/`, o executável, a entrada Python e requirements.txt. Não inclui uploads, MODELS, env nem server_config.json.
- A instalação é bloqueada enquanto houver motores abertos ou tarefas de correção ativas. Retorne ao Hub após concluir os trabalhos.
- Cópias com `.git` ou `.nexus-development`, inclusive em uma pasta ancestral, não permitem download/instalação automática. O Hub mostra **Desenvolvimento protegido** e permite somente consultar as releases. A pasta de trabalho de Paulo tem esse marcador local, ignorado pelo Git e fora dos pacotes de distribuição.
- A atualização exige uma versão estritamente superior. Versões iguais ou anteriores são bloqueadas na preparação, no lançamento do aplicador e novamente antes da cópia. A última verificação lê `nexus/version.py` do disco sem executá-lo, protegendo também uma versão local avançada depois do download.
- A atualização automática exige que requirements.txt permaneça compatível por igualdade das linhas. Quando houver mudança, o usuário é direcionado ao instalador da release; não há migração automática das dependências nesta implementação.
- É necessário um Python local disponível no ambiente da instalação para executar o aplicador fora do executável. Ausência desse ambiente orienta usar o instalador.
- O mecanismo adiciona/substitui arquivos; não remove automaticamente módulos antigos. Falhas de energia e falhas de inicialização posteriores à cópia não têm reversão automática nesta implementação. O backup permanece disponível.
- A versão 0.6.0 já instalada não ganhará esse botão sozinha: é necessário instalar a versão que introduz o atualizador. As próximas releases devem incluir o pacote.

## Preparação de releases

1. Atualize `APP_VERSION` em `nexus/version.py` e as notas de lançamento.
2. A tag deve ser `v` seguida exatamente dessa versão. O empacotador rejeita divergências.
3. O workflow gera `dist/PhoenixDub_Update.zip` após os executáveis e o anexa à release.
4. O manifesto contém versão e SHA-256 de cada arquivo. O download exige também o digest SHA-256 do asset na API do GitHub; enquanto ele não estiver disponível, a instalação é recusada.
5. Antes de distribuir o recurso como validado, teste o ciclo entre duas builds empacotadas em uma instalação de teste, incluindo o reinício da janela. Não use a instalação de desenvolvimento como destino de teste.

Referência da integração: [API de releases do GitHub](https://docs.github.com/en/rest/releases/releases#get-the-latest-release).

## Validação em 2026-09-10

Testes automatizados com releases e pacotes simulados cobrem comparação de versões, falha de rede, origem das requisições, integridade, caminhos, preservação de dados, rollback de cópia e preparação do processo externo. A interface foi conferida em navegador local com uma release fictícia 0.9.0; nenhuma atualização real foi instalada. A consulta real retornou versão local 0.8.0 superior à pública 0.6.0. O ciclo com executável empacotado ainda precisa de validação.

A suíte geral passou 44 testes antes do reforço de proteção de desenvolvimento. Após esse reforço, os 20 testes específicos de atualização passaram, incluindo bloqueio de versão igual/anterior, marcador sem Git, pasta ancestral, tentativa direta no aplicador e versão de disco avançada após o download. A consulta real confirmou `development_copy=true` e `automatic_supported=false` na instalação local.
