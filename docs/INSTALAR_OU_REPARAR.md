# Instalar ou reparar o PhoenixDub AI

## Pelo código no Windows

1. Instale Python de 64 bits, versão 3.10 a 3.12, com a opção de adicionar ao PATH.
2. Abra `TESTAR_SETUP.bat` na pasta do projeto.
3. Escolha os módulos na janela e aguarde. Configure o token Hugging Face na interface, se necessário.
4. Se houver erro, pare e leia a mensagem. Não apague `env`, modelos ou projetos para tentar corrigir.

O BAT verifica erros e preserva ambientes existentes. Ele instala apenas a biblioteca da
janela antes de abrir `Setup_Nexus.py`; a instalação dos módulos acontece pela interface.
O executável `Setup_Nexus.exe` usa o mesmo instalador. O pacote publicado é voltado
ao Windows x64 com NVIDIA; o driver NVIDIA continua sendo um pré-requisito externo.

## O que mudou na v0.8.2

- `requirements.txt` é a fonte única das dependências. A seleção modular usa essa
  mesma matriz como restrição, inclusive para dependências transitivas.
- Qwen3-TTS 0.1.1 exige Transformers 4.57.3. Faster-Qwen3-TTS fica em 0.2.6;
  WhisperX 3.3.4 e pyannote.audio 3.3.2 evitam a atualização implícita para outra
  geração de PyTorch/pyannote. Alterações nessa matriz exigem nova resolução pelo pip.
- Dependências legadas de Cine Gen/restauração facial não integram a instalação ativa.
- FFmpeg e ffprobe existentes são testados. Se estiverem ausentes, o instalador
  baixa a distribuição Essentials de Gyan, verifica SHA-256 e executa os binários
  antes de copiá-los para `env/ffmpeg/bin`. O aplicativo adiciona essa pasta ao PATH
  de seus próprios processos; não altera o PATH global do Windows.
- CTranslate2 4.4 usa cuDNN 8 para CUDA 12; essa biblioteca e fornecida separadamente, sem substituir a biblioteca interna do PyTorch. Referencia: https://github.com/SYSTRAN/faster-whisper#gpu
- Os termos de diarização correspondem a `pyannote/speaker-diarization-3.1`.
- `pip check` precisa passar antes do download dos modelos e da conclusão.

Fontes: [distribuições Windows indicadas pelo FFmpeg](https://ffmpeg.org/download.html),
[Gyan](https://www.gyan.dev/ffmpeg/builds/),
[Qwen3-TTS 0.1.1](https://pypi.org/project/qwen-tts/0.1.1/).

O diagnóstico de importações, os testes automatizados e a resolução de dependências
não comprovam qualidade de dublagem. Um fluxo completo com modelos/GPU e uma
instalação completa em máquina limpa continuam sendo validações separadas.

## Para a IA local

Não execute o setup para conferir o código. Rode primeiro:

```powershell
python -B -m unittest discover -s tests -p test_setup_support.py
```

Para preparar publicação, siga [PREPARAR_RELEASE_IA.md](PREPARAR_RELEASE_IA.md).
Use sempre e-mail `noreply` do GitHub nos commits. Nunca publique senhas, tokens
ou logs do computador. Se qualquer verificação falhar, informe o erro e pare antes da tag.
