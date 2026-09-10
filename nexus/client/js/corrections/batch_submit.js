export function bindBatchSubmit(ctx, selected, refresh) {
const {el, api, guarded, message, flush, persistDraft} = ctx;
    el('.batch-save').addEventListener('click', guarded(async () => {
        const text = el('.batch-text').value.trim();
        if (!text) throw new Error('Escreva a correção em português para as falas selecionadas.');
        const items = [...selected.values()];
        if (!items.length || ctx.batchSending) return;
        ctx.batchSending = true; refresh(); ctx.controls();
        try {
            await flush();
            const revisions = [];
            for (const [index, item] of items.entries()) {
                const revision = Math.max(Date.now() * 1000, item.revision + 1);
                const body = {project_id:item.project_id, segment_id:item.id, text, revision};
                message(`Salvando ${index + 1} de ${items.length} falas...`);
                await persistDraft(body, el('.batch-status'));
                item.revision = revision; item.translated = text; revisions.push({...body, text:undefined});
            }
            const result = await api('/enqueue-many', {items:revisions});
            for (const task of result.tasks) {
                ctx.rememberTask(task.task_id, task.project_id, task.total);
            }
            for (const task of result.tasks) {
                ctx.followTask(task.task_id, task.project_id).catch(error => message(error.message, true));
            }
            const details = result.errors.map(e => e.error);
            if (result.staged_video_projects.length) details.push('Vídeos: abra cada projeto e clique em Iniciar para montar o vídeo.');
            el('.batch-status').textContent = `${result.count} fala(s) salva(s). Cada áudio usa a própria referência de voz. ${details.join(' ')}`;
            if (result.errors.length) message('Textos salvos; algumas filas precisam ser retomadas pelo projeto. ' + details.join(' '), true);
            selected.clear();
            await ctx.search();
        } finally {ctx.batchSending = false; refresh(); ctx.controls();}
    }));
}
