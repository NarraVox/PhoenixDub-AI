# PhoenixDub AI v0.93 — Correção de segurança

### O que mudou

Esta versão corrige uma falha de segurança que já existia em versões anteriores (inclusive v0.8.2 e v0.91). **Recomenda-se atualizar.**

- **Editor de vídeo (Vortex):** as ferramentas de cortar, cortar vários trechos e juntar vídeos montavam o comando do FFmpeg como texto e o entregavam ao terminal do Windows. Um nome de arquivo ou um tempo de início/fim preparado de propósito poderia executar outro comando no computador. Agora o FFmpeg é chamado diretamente com a lista de argumentos, e os tempos aceitam só números (ex.: `12`, `1:05`, `00:01:05.50`). Nomes de arquivo com apóstrofo também passaram a funcionar na junção.
- **Serviços locais (Hub, dublagem de jogos e vídeos, DJ e editor):** antes aceitavam pedidos vindos de qualquer site aberto no navegador. Agora só aceitam pedidos do próprio programa (`127.0.0.1` / `localhost`), impedindo que uma página externa use essas APIs enquanto o programa está aberto.
- No corte sem GPU NVIDIA, foram removidas opções exclusivas do NVENC que não se aplicam ao libx265.

### Por que 0.93?

A v0.91 foi publicada hoje mais cedo. A pedido do responsável, esta correção sai como **0.93**. As novidades da v0.91 continuam valendo e estão descritas abaixo.

---

## Novidades da v0.91 — Conversor inteligente, diarização corrigida e tradução com contexto

### Por que a versão saltou de 0.8.2 para 0.91?

A numeração mudou para ficar mais simples: agora as versões têm duas partes (0.91, 0.92, 0.93...). A v0.8.2 equivale a **0.82**, e cada dia de desenvolvimento com novidades soma 0.01. Desde a v0.8.2 foram **9 dias de atualizações**, de 29/09 a 06/11/2026; por isso esta versão é a **0.91**, e não 0.8.3. O salto reflete a quantidade de mudanças acumuladas. As próximas versões seguem 0.92, 0.93..., e depois de 0.99 vem 1.0.

### Principais mudanças

#### Conversor de vídeos e músicas

- **Fila inteligente:** antes de converter, o programa analisa cada arquivo e mostra a resolução, o tamanho estimado e a ação planejada.
  - Troca de formato rápida (cópia direta, sem perda de qualidade) quando só o contêiner precisa mudar, como .mkv/.mov → .mp4.
  - Vídeos acima de 1080p, como 4K, são reduzidos para 1080p.
  - Conversões que economizariam menos de 10% são puladas.
- **Não deixa mais o vídeo mais pesado:** se a conversão deixaria o arquivo maior e o vídeo já toca em TV (MP4 com H.264/HEVC), ele é pulado. Se o codec é compatível mas o formato não (.mov, .mkv, .ts), só o formato é trocado para MP4. Formatos que dificilmente tocam em TV, como ProRes, DivX/MPEG-4, WMV e VP9, continuam sendo convertidos. Depois de cada conversão, o tamanho real também é conferido.
- **Formato original preservado:** vídeo vertical continua vertical e horizontal continua horizontal. Acabou o problema antigo de vídeos verticais convertidos para horizontal, que ficavam pequenos no meio da tela. A tela agora mostra "AUTO • mantém o formato original".
- **GPU NVIDIA de verdade:** o NVENC é testado com uma codificação real antes de ser usado. O perfil agora é p4 / alta qualidade com bitrate médio de 3 Mbps (máx. 5 Mbps), e a decodificação é feita pela GPU quando disponível. Se a GPU falhar, a conversão segue pela CPU.
- Remoção do painel antigo de conversão e do botão "Consertar vídeo quadrado", que não funcionavam e geravam erro ao abrir o editor.

#### Dublagem de vídeos

- **Separação de vozes corrigida:** o Pyannote voltou a distinguir os locutores, por exemplo homem e mulher. Antes, uma incompatibilidade com o Python 3.12 juntava todas as vozes em uma só.
- **Tradução com contexto:** cada fala é traduzida conhecendo a fala anterior e a próxima.
- **Prompts do Qwen reorganizados** em formato estruturado, com proteção contra tradução ao pé da letra de gírias e expressões comuns.
- Correção de um erro no cache de contexto que impedia a leitura de falas anteriores.
- Botão **📂 Abrir pasta do vídeo dublado** ao concluir a dublagem e em cada projeto do histórico.

#### Memória e estabilidade

- Antes de carregar modelos, a dublagem de jogos e vídeos confere se há RAM e VRAM suficientes e avisa na tela quando falta margem.
- O uso de VRAM fica limitado a 90%. Quando a GPU não tem espaço, Whisper e Pyannote podem rodar na CPU, e o Qwen3-TTS usa o modelo 0.6B se o 1.7B não couber.
- O Qwen local usa até metade dos núcleos do processador, deixando o Windows e a interface responsivos.
- **Style Analyzer (DJ):** limites de tamanho (128 MB), duração (5 min) e memória, com um supervisor que encerra a análise se o limite for ultrapassado.

#### Nexus DJ (experimental)

- Esta versão publica pela primeira vez o código do Style Analyzer, do Arranger e da integração com o YuE2 para criação de músicas. Esses módulos são **experimentais** e não foram validados de ponta a ponta nesta versão.

#### Documentação

- O histórico antigo de atualizações (até a v0.8.2) foi preservado em `docs/historico/`.

#### Licença

- O projeto agora traz o texto oficial da **Apache License 2.0** (`LICENSE`), o arquivo `NOTICE` com as atribuições e o `COPYRIGHT.md`.

### Limites conhecidos

- Várias mudanças foram verificadas com compilação, testes automatizados e testes pontuais, mas **não houve um teste completo de dublagem em GPU** com esta versão. A qualidade da tradução continua dependendo do modelo e da revisão humana.
- O instalador e os executáveis são gerados automaticamente na publicação. A instalação limpa e a atualização pelo Hub ainda precisam ser conferidas na prática.
