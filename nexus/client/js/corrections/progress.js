export function summarize(records) {
    let total = 0, completed = 0, failed = 0, running = 0, unknown = false;
    for (const task of records) {
        const p = task.progress || {};
        if (p.total == null) unknown = true;
        const n = p.total || 0, done = p.completed || 0;
        total += n; completed += done;
        failed += task.status === 'error' ? Math.max(p.failed || 0, n - done) : p.failed || 0;
        if (task.status === 'running' && p.current) running++;
    }
    return {total, completed, failed, running, unknown,
        waiting: Math.max(0, total - completed - failed - running),
        percent: total ? Math.floor(completed * 100 / total) : 0};
}

export function setupProgress(ctx) {
    const {el} = ctx, storageKey = 'nexus-correction-progress';
    let records;
    try { records = new Map(JSON.parse(localStorage.getItem(storageKey) || '[]')); }
    catch (_) { records = new Map(); }
    const terminal = task => ['done', 'error'].includes(task.status);
    function render() {
        const list = [...records.values()], counts = summarize(list);
        el('.task-progress').hidden = !list.length;
        if (!list.length) return;
        const allFinished = list.every(terminal);
        el('.progress-summary').textContent = counts.unknown ? 'Carregando contagem das falas…' :
            `${counts.completed} de ${counts.total} falas concluídas (${counts.percent}%) • ${counts.running} em geração • ${counts.waiting} aguardando • ${counts.failed} com falha`;
        const bar = el('.progress-bar');
        if (counts.unknown || !counts.total) bar.removeAttribute('value'); else bar.value = counts.percent;
        if (!counts.unknown && !counts.total) {
            el('.progress-summary').textContent = allFinished ? 'Processamento de arquivos encerrado.' : 'Processando os arquivos…';
            if (allFinished) bar.value = 100;
        }
        el('.progress-stage').textContent = allFinished ?
            (list.some(t => t.status === 'error') || counts.failed ? 'Encerrado com erros. Confira o registro abaixo.' : 'Concluído: áudios e exportações finalizados.') :
            list.some(t => t.status === 'unavailable') ? 'Não foi possível atualizar uma tarefa. Reabra o painel para consultar novamente.' :
            counts.completed === counts.total && counts.total ? 'Falas geradas; finalizando a exportação dos arquivos…' : 'A geração acontece uma fala por vez.';
        const entries = [];
        for (const task of list) {
            const name = ctx.projects.find(p => p.id === task.project_id)?.name || task.project_id;
            for (const line of task.logs || []) entries.push({...line, name});
        }
        entries.sort((a, b) => a.time - b.time || a.sequence - b.sequence);
        const log = el('.progress-log');
        const atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
        log.textContent = entries.slice(-300).map(line =>
            `[${new Date(line.time * 1000).toLocaleTimeString('pt-BR')}] ${line.name}: ${line.message}`).join('\n');
        if (atBottom) log.scrollTop = log.scrollHeight;
        try {localStorage.setItem(storageKey, JSON.stringify([...records]));} catch (_) {}
    }
    function register(id, project_id, total = null) {
        if (!records.has(id) && [...records.values()].every(terminal)) records.clear();
        if (!records.has(id)) records.set(id, {project_id, status:'queued', progress:{total, completed:0, failed:0},
            logs:[{sequence:0, time:Date.now()/1000, message:'Aguardando na fila.'}]});
        render();
    }
    function update(id, data) {
        const previous = records.get(id) || {};
        records.set(id, {...previous, project_id:data.project_id || previous.project_id,
            status:data.status, progress:data.progress || previous.progress, logs:data.logs || previous.logs});
        render();
    }
    function unavailable(id, message) {
        const task = records.get(id);
        if (task && !terminal(task)) {
            task.status = 'unavailable';
            task.logs.push({sequence:999999, time:Date.now()/1000, message});
            render();
        }
    }
    function statusMessage(message) {
        const counts = summarize([...records.values()]);
        if (counts.unknown || !counts.total) return message;
        return `${counts.percent}% da fila • ${counts.completed} de ${counts.total} falas concluídas • ${Math.max(0, counts.total - counts.completed - counts.failed)} restantes\n${message}`;
    }
    return {register, update, render, unavailable, statusMessage};
}
