import {showGenerated} from './timing.js';
export function tasks(ctx) {
const {root, el, select, api, apiRoot, message, flush, taskKey} = ctx;
const activeTasks = new Map();
const controls = () => ctx.controls();
const queue = () => ctx.queue();
    function rememberTask(token, key, total = null) {
        activeTasks.set(token, key);
        ctx.progress.register(token, key, total);
        const saved = JSON.parse(localStorage.getItem(taskKey) || '[]');
        if (!saved.some(t => t.id === token)) saved.push({id: token, project_id: key, total});
        localStorage.setItem(taskKey, JSON.stringify(saved));
    }
    async function followTask(token, key) {
        activeTasks.set(token, key); ctx.working = true; controls();
        ctx.progress.register(token, key);
        let terminal = false;
        try {
            for (;;) {
                const data = await api('/tasks/' + encodeURIComponent(token));
                ctx.progress.update(token, data);
                if (data.status === 'error') { terminal = true; throw new Error(data.error); }
                if (data.status === 'done') {
                    terminal = true;
                    ctx.outputFolder = data.result.folder || null;
                    el('.folder').hidden = !ctx.outputFolder;
                    const failures = data.result.failures || [];
                    message(data.result.message + (ctx.outputFolder ? '\nPasta: ' + ctx.outputFolder : '') +
                        (failures.length ? '\n' + failures.map(f => f.segment_id + ': ' + f.error).join('\n') : ''), failures.length > 0);
                    // Atualiza o áudio sem reconstruir campos que a pessoa pode estar editando.
                    for (const draft of data.result.queue?.items || []) {
                        const row = [...root.querySelectorAll('.row')].find(r => r.dataset.projectId === key && r.dataset.segmentId === draft.segment_id);
                        if (!row) continue;
                        if (draft.queued?.status === 'done' && draft.queued.preview_token) {
                            showGenerated(row,draft.queued.generated_duration,draft.queued.speed,Number(row.dataset.originalDuration));
                            row.querySelector('audio').src = apiRoot + '/audio?' + new URLSearchParams({project_id: key, token: draft.queued.preview_token});
                            if (row.querySelector('textarea').value === draft.queued.text) row.querySelector('.save').textContent = '✓ Áudio corrigido gerado e salvo';
                        }
                        if (draft.queued?.status === 'error') {
                            row.querySelector('.save').textContent = draft.queued.error;
                            row.querySelector('.save-one').dataset.enqueued = 'false';
                        }
                    }
                    break;
                }
                if (data.status === 'running') message(ctx.progress.statusMessage(data.message || 'Processando a fila de correção...'));
                await new Promise(resolve => setTimeout(resolve, 1500));
            }
        } catch (error) { ctx.progress.unavailable(token, error.message); message(error.message + '\nSuas alterações continuam salvas. Use Retomar fila (jogos) ou Iniciar (vídeos) para continuar.', true); }
        finally {
            activeTasks.delete(token);
            const saved = JSON.parse(localStorage.getItem(taskKey) || '[]').filter(t => !terminal || t.id !== token);
            localStorage.setItem(taskKey, JSON.stringify(saved));
            ctx.working = activeTasks.size > 0; controls(); await queue();
        }
    }
    async function execute(action) {
        if (ctx.working) return;
        ctx.working = true; controls();
        try {
            await flush();
            const data = await action();
            rememberTask(data.task_id, select.value, data.total);
            await followTask(data.task_id, select.value);
        } catch (error) { message(error.message, true); }
        finally { ctx.working = activeTasks.size > 0; controls(); }
    }

return {rememberTask, followTask, execute};
}
