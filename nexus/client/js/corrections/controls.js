export function setupControls(ctx) {
const {root, el, select, api} = ctx;
    const currentProject = () => ctx.projects.find(p => p.id === select.value);
    function controls() {
        const project = currentProject();
        el('.start').hidden = !project;
        el('.start').textContent = project?.kind === 'video' ? '▶ INICIAR FILA E GERAR VÍDEO' : '▶ RETOMAR FILA PENDENTE';
        el('.start').disabled = ctx.working || !project;
        el('.export').disabled = ctx.working || !project;
        select.disabled = ctx.working || ctx.batchSending;
        el('.refresh').disabled = ctx.working || ctx.batchSending;
        el('.previous').disabled = ctx.batchSending || ctx.offset === 0;
        el('.next').disabled = ctx.batchSending || ctx.offset + 40 >= ctx.total;
        root.querySelectorAll('.row textarea, .row button').forEach(node => {
            node.disabled = ctx.batchSending || node.dataset.enqueued === 'true' || (ctx.working && node.closest('.row').dataset.kind === 'video');
        });
        root.querySelectorAll('.pick-page, .pick-all, .pick-clear, .batch-text, .search, .query').forEach(node => { node.disabled = !!ctx.batchSending; });
        el('.intro').textContent = project?.kind === 'video'
            ? 'Edite e clique em Salvar em cada segmento para montar a fila. Quando terminar, clique em Iniciar: todas as falas serão geradas e o vídeo será montado uma única vez no final. O JSON protege o texto enquanto você digita, sem iniciar a dublagem. Preserve a pasta original do projeto.'
            : 'Edite a fala e clique em Salvar: só então ela entra na fila e começa a dublagem. Continue editando as próximas enquanto a fila roda. O JSON protege o texto ao digitar. Os áudios corrigidos ficam em uma pasta separada para substituição ou repack do jogo.';
        if (!project) el('.intro').textContent = 'Busque em português ou inglês, mesmo com pequenos erros. Confira o original e corrija uma fala ou selecione várias. Cada personagem mantém sua própria voz.';
    }
    async function queue() {
        if (!select.value) { el('.queue').textContent = 'Busca em todos os uploads. Cada fala será salva no projeto indicado no resultado.'; return; }
        const key = select.value;
        const data = await api('/queue?project_id=' + encodeURIComponent(key));
        if (key !== select.value) return;
        el('.queue').textContent = `${data.pending} fala(s) na fila • ${data.completed} gerada(s) • ${data.drafts} rascunho(s) ainda não enviados. A fila é recuperada ao reabrir o programa.`;
    }

return {controls, queue};
}
