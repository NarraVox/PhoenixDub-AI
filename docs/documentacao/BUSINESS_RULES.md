# 📜 Regras de Negócio — NarraVox Studios Premium

Este documento centraliza as **regras operacionais, critérios de aceitação e comportamentos esperados** que governam todos os pipelines do sistema (Jogos, Vídeo, DJ, Editor). Estas regras devem ser consultadas por qualquer agente ou módulo antes de tomar decisões sobre como processar ou descartar dados.

---

## 🎯 Prioridade Operacional Máxima

**A prioridade absoluta do sistema é preservar o conteúdo vocal autêntico.**

É fundamental que a perda de informação falada seja evitada, mesmo que exija processamento mais intensivo. O sistema deve **preferir processar um segmento extra a descartá-lo por engano**.

---

## 🔊 Regras de Conteúdo Vocal

As seguintes condições são consideradas **conteúdo vocal válido** e não devem ser descartadas:

1. **Comunicações de Rádio:** Qualquer áudio identificável como comunicação de rádio (transmissões, boletins) é diálogo legítimo e deve passar por todo o pipeline.
2. **Vozes Curtas/Fragmentos:** Trechos muito curtos são válidos. O sistema deve priorizar a captura em detrimento da limpeza excessiva.
3. **Diálogo de Uma Palavra:** Uma única palavra isolada ("Sim", "Não", "Fogo") é um diálogo legítimo que deve ser transcrito e processado.
4. **Segmentos de Texto Vazio com Longa Duração:** Se um segmento tem texto vazio mas duração > 0.5 segundos, o Whisper falhou. O segmento deve ser **re-transcrito**, não descartado.

---

## 🎶 Regras de Áudio Não-Verbal

**Objetivo primário: nunca perder conteúdo vocal, mesmo não-verbal.**

1. **Gemidos e Sons Curtos (<0.5s):** Sons como "Ah", "Uh", "Hmm" com duração inferior a 0.5 segundos são classificados como `Copiado Diretamente (Som Não-Verbal)` e copiados sem dublagem de IA. Isso preserva a autenticidade e economiza VRAM.
2. **Lista de Sons a Ignorar (`SONS_A_IGNORAR`):** Existe uma lista de sons que, se forem o único conteúdo de um segmento, levam ao tratamento como Não-Verbal. Inclui: "mm", "ah", "oh", "hm", "uh", "hmm", "wow", "haha", "yeah", "ooh", etc.
3. **CANTORIA (Alucinação de Texto Repetido):** Se o Whisper repetir a mesma frase 4 ou mais vezes consecutivas (indicando que ele alucinou música de fundo), o segmento é marcado com `emotion: CANTORIA` e a dublagem é ignorada.
4. **Bleedout / Interferência:** Sons de fundo capturados durante o diálogo são informativos. Não devem ser removidos sem análise.

---

## 👤 Regras de Diarização e Falante

1. **Prioridade da Diarização:** Os limites temporais definidos pelo **Pyannote 3.1** são o *ground truth* do segmento. A transcrição (Whisper) deve se subordinar a eles.
2. **Sem VAD Filter no Whisper:** O Whisper é invocado **sem `vad_filter=True`** para transcrever o conteúdo integral de cada segmento Pyannote, maximizando a captura.
3. **Speaker ID como Chave de Clonagem:** O campo `speaker` (ex: `SPEAKER_00`, `voz1`) é a chave que determina qual áudio de referência será usado para a clonagem de voz no TTS. Ele deve ser sempre mantido consistente.

---

## 🌐 Regras de Tradução

1. **Prioridade de Edição Manual:** Se o campo `manual_edit_text` estiver preenchido, ele **anula qualquer tradução de IA, cache ou glossário**. É o texto sagrado e inviolável.
2. **Filtro de Idioma:** Segmentos já em Português (`detected_language: pt`) não são enviados ao Gemma. Seu texto original é preservado diretamente como `sanitized_text`.
3. **Deduplicação de Frases Idênticas (Micro-Cache):** Se a mesma frase em inglês aparece múltiplas vezes, ela é traduzida apenas uma vez e o resultado é clonado, economizando tempo e recursos.
4. **Janela de Contexto:** A tradução de cada segmento considera as 3 frases anteriores e as 3 seguintes como contexto, para manter a coerência narrativa.
5. **Anti-Alucinação (Correction Master):** Se o Gemma devolver o texto original intacto (não traduziu), uma segunda tentativa é disparada automaticamente (`gema_etapa_correcao_master`).
6. **Glossário Personalizado:** O usuário pode definir termos fixos (`Nome=Nome, Termo=Tradução`) que o Gemma é obrigado a respeitar. Ex: Nomes de personagens do jogo.
7. **Perfis de Jogo:** O sistema suporta perfis de tradução específicos por jogo (ex: `bioshock`, `cod`) que ajustam o tom, vocabulário e volume do TTS.

---

## 🎙️ Regras de Síntese de Voz (TTS)

1. **Clonagem por Falante:** Cada `speaker_id` possui seu próprio **Super Ref** (referência de até 15s a 22050Hz mono, normalizada), que é usado para clonar a identidade vocal.
2. **Emoção Injetada:** O Gemma analisa o texto e atribui uma emoção (`NORMAL`, `HAPPY`, `SAD`, `ANGRY`, etc.) que é passada ao Qwen3-TTS para ajustar a prosódia.
3. **Zero-Shot Híbrido:** Para segmentos com mais de 4 segundos, a referência utilizada é o **próprio áudio original da cena** (e não o Super Ref genérico), para capturar a emoção pura do ator.
4. **Safety Gate (Pipeline Cinema):** O pipeline de vídeo possui um **bloqueio de qualidade de 90%**: se menos de 90% dos segmentos foram dublados com sucesso, a masterização final é abortada para evitar um vídeo com partes mudas.
5. **Reação/Ruído → Manter Original:** Sons filtrados por `is_reaction_or_noise()` não recebem dublagem. O áudio original é usado no lugar.

---

## 💾 Regras de Cache e Persistência

1. **Cache Granular por Segmento:** Cada segmento traduzido gera um arquivo `.json` individual na pasta `_backup_texto_final/`. Se o arquivo existir e tiver texto válido, a IA não é invocada novamente. Para apagar a tradução de um segmento, basta deletar o `.json` correspondente.
2. **Phoenix Recovery (Reconstrução de Dados):** Antes de qualquer processamento, o sistema tenta reconstruir o `project_data.json` a partir dos backups individuais, tornando o pipeline resiliente a falhas de energia ou travamentos.
3. **Auto-Purge Inteligente:** Se o relatório LQA indica que um áudio dublado está defeituoso, o sistema o apaga automaticamente na **próxima execução** para forçar a re-geração. Porém, se o arquivo é **mais novo** que o relatório, ele é preservado (indica que o usuário o corrigiu manualmente).
4. **Edição Manual Sagrada (Golden Rule):** Se um segmento tem `manual_edit_text`, mesmo que seu backup seja deletado, o sistema **recria o backup a partir da memória**, nunca apaga o texto manual.
5. **Fusão Inteligente de Backup:** Ao sincronizar um backup, o campo `manual_edit_text` de um backup vazio nunca sobrescreve uma edição manual que já existe na memória.

---

## 🎧 Regras do Vortex DJ

1. **Personalidade do Set:** A personalidade da mixagem é determinada pela energia média das faixas:
   - Energia > 0.08 → `festival` (Extended Mix de 40s + Silêncio Épico + Echo)
   - Energia > 0.05 → `agressivo` (Corte Drop de 6s + Scratches)
   - Energia ≤ 0.05 → `suave` (Crossfade de 12s)
2. **Super Mix:** Se a diferença de BPM entre duas faixas for menor que 4 e a energia for alta, uma **Super Mix Épica** é ativada, com separação de stems e mashup estendido.
3. **Resolução de Conflito Vocal:** Se ambas as faixas têm vocais nas regiões de transição, os stems instrumentais de uma delas são extraídos via OpenUnmix para evitar conflito de vozes.
4. **Checkpointing:** Cada mixagem concluída é salva no `job_status.json`. Se o processo for interrompido, retoma da última mixagem completa.

---

## 🎬 Regras do Cine-Gen

1. **IP-Lock de Atores:** O nome do ator é o trigger word primário para o modelo Wan 2.2. O prompt sempre deve formatar o ator como `([NomeDoAtor]:1.5)` com peso de 150% para evitar deformação de rosto.
2. **Duração de Cena:** Cada cena deve ter entre 2 e 5 segundos. Falas longas devem ser distribuídas em múltiplas cenas (técnica Extended).
3. **Fala Máxima:** O diálogo de uma cena tem no máximo 75 caracteres.
4. **Áudio Separado:** O vídeo é gerado mudo pelo Wan 2.2. SFX (TangoFlux) e Música (TangoFlux) são gerados separadamente com prompts distintos.
5. **VRAM Swap:** O Gemma 4 é descarregado antes da ativação do Wan 2.2 para não exceder os 6GB da RTX 3050.

---

## 🛠️ Critérios Gerais de Operação

| Regra | Detalhe |
|---|---|
| **Máxima Retenção** | Preferir processar um segmento extra a descartar conteúdo vocal legítimo. |
| **VRAM Hard Limit** | O sistema bloqueia automaticamente se a VRAM ultrapassar 5.0 GB. |
| **Retomada Automática** | Todo pipeline pode ser interrompido e retomado do ponto onde parou. |
| **Isolamento de Ambiente** | `sys.path` é limpo no início de cada motor para evitar conflito com pacotes do AppData. |
| **Prioridade de Processo** | O processo do TTS opera com prioridade abaixo do normal para não travar o sistema. |