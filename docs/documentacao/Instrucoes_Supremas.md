# 📜 Instruções Supremas para Agentes de IA

Este documento define o comportamento padrão esperado de qualquer agente de IA (Aider, Antigravity, Gemma, etc.) ao trabalhar no projeto NarraVox Studios Premium.

---

## ⚡ Autonomia Operacional

O padrão de comportamento esperado é a **execução autônoma das tarefas**, minimizando interrupções desnecessárias.

O agente deve, **obrigatoriamente**, antes de qualquer modificação:

1. Ler `PROJECT_SCOPE.md` para entender os módulos ativos e experimentais.
2. Ler `ARCHITECTURE.md` antes de alterar qualquer pipeline ou adicionar modelos.
3. Ler `BUSINESS_RULES.md` antes de alterar lógica de processamento de áudio ou texto.
4. Ler `codebase_map.md` para localizar o arquivo correto antes de editar.
5. **Não assumir** a arquitetura do sistema sem verificar o código-fonte real.
6. **Não modificar** módulos experimentais (`nexus_godogen/`, `nexus/cine/`) sem autorização explícita.

---

## 🔄 Fluxo de Trabalho Padrão

### Para alterações de baixo ou médio risco (bug fix, ajuste de parâmetro, nova rota simples):
1. Analisar o problema.
2. Implementar a solução.
3. Documentar o que foi alterado (atualizar o doc relevante se necessário).
4. Apresentar um relatório final claro.

### Para alterações de alto impacto (novo módulo, mudança de pipeline, novo modelo de IA):
1. Analisar a arquitetura envolvida.
2. Elaborar um plano de execução detalhado.
3. Aguardar aprovação implícita ou explícita.
4. Implementar a solução.
5. Gerar um relatório detalhado ao final.

---

## 🤝 Interação com o Usuário

- Evite perguntas desnecessárias. O agente deve agir de forma autônoma sempre que houver informações suficientes para uma decisão razoável.
- **Solicite intervenção humana apenas quando:**
  - Houver ambiguidade real nos requisitos.
  - Existirem múltiplas arquiteturas possíveis com impactos significativos.
  - A alteração puder causar perda de dados (ex.: apagar backups de tradução).
  - A mudança afetar múltiplos pipelines críticos simultaneamente.

---

## 📊 Relatórios Técnicos

Ao apresentar análises, distinguir claramente:

### Estado Atual
Descreve o comportamento **atualmente implementado no código**. Apenas o que foi confirmado pela leitura do código-fonte.

### Hipóteses
Possíveis causas, interpretações ou suspeitas que **ainda precisam ser validadas**.

### Melhorias Propostas
Mudanças sugeridas para resolver problemas ou aprimorar o sistema, com justificativa técnica.

---

## 🛡️ Regras Críticas de Segurança de Código

1. **Preservar o `gema_lock`:** Toda chamada ao Gemma 4 deve ser feita dentro de `with gema_lock:`. Nunca remova ou ignore este lock.
2. **Preservar os Patches de Compatibilidade:** Os patches de `np.NAN`, `HF_HUB_DISABLE_SYMLINKS` e `GGML_CUDA_NO_PINNED` devem estar presentes no início de qualquer orquestrador pesado.
3. **Preservar o Handoff Sequencial de VRAM:** Nunca carregue dois modelos grandes ao mesmo tempo. Sempre chame `unload_*` + `gc.collect()` + `torch.cuda.empty_cache()` antes de carregar o próximo.
4. **Preservar o `safe_json_write`:** Nunca use `json.dump` diretamente em arquivos críticos (`job_status.json`, `project_data.json`). Use sempre `safe_json_write` para escrita atômica com lock.
5. **Preservar o Cache Granular:** Nunca apague a pasta `_backup_texto_final/` inteira. O agente pode apagar arquivos individuais para forçar re-tradução de segmentos específicos.
6. **Preservar a Edição Manual:** O campo `manual_edit_text` é **sagrado e inviolável**. Nunca sobrescreva ou apague sem instrução explícita do usuário.

---

## 🎯 Objetivo Principal

**Produtividade, autonomia e precisão técnica**, minimizando interrupções desnecessárias durante o desenvolvimento, enquanto preserva a integridade dos dados e a estabilidade do hardware.