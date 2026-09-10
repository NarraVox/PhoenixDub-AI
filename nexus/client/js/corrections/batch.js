import {bindBatchSubmit} from './batch_submit.js';
import {setupBatchTiming} from './batch_timing.js';
export function setupBatch(ctx) {
    const {el, root, api, guarded, message, flush, persistDraft} = ctx;
    const selected = new Map();
    const updateTiming = setupBatchTiming(el,selected);
    let scope = ''; 
    const identity = item => item.project_id + ':' + item.id;
    function refresh() {
        updateTiming();
        const items = [...selected.values()];
        el('.batch-count').textContent = `${items.length} fala(s) selecionada(s) em ${new Set(items.map(i => i.project_id)).size} projeto(s)`;
        el('.batch-save').disabled = ctx.batchSending || !items.length;
        root.querySelectorAll('.pick').forEach(box => { box.checked = selected.has(box.dataset.identity); box.disabled = ctx.batchSending; });
        const review = el('.batch-review'); review.replaceChildren();
        for (const item of items) {
            const line = document.createElement('div'); line.className = 'original';
            line.textContent = `${item.project_name} • Voz: ${item.speaker} • ${item.id}\nInglês: ${item.original || '(não disponível)'}\nPortuguês atual: ${item.translated}`;
            review.append(line);
        }
    }
    function resetScope(value) {
        if (scope !== value) { selected.clear(); scope = value; }
        refresh();
    }
    function attach(row, item) {
        const label = document.createElement('label'); label.className = 'pick-label';
        const box = document.createElement('input'); box.type = 'checkbox'; box.className = 'pick';
        box.dataset.identity = identity(item);
        box.setAttribute('aria-label', `Selecionar ${item.id} de ${item.project_name}`);
        box.checked = selected.has(identity(item));
        if (box.checked) selected.set(identity(item), item);
        box.addEventListener('change', () => {
            if (box.checked) selected.set(identity(item), item); else selected.delete(identity(item));
            refresh();
        });
        label.append(box, ' Incluir na correção em grupo'); row.prepend(label);
        const same = document.createElement('button'); same.type = 'button'; same.className = 'quiet';
        same.textContent = 'Selecionar mesmo inglês em todos os projetos';
        same.disabled = !item.original;
        same.addEventListener('click', guarded(async () => {
            const requestedScope = scope;
            const data = await api('/selection?' + new URLSearchParams({original: item.original}));
            if (scope !== requestedScope) return;
            selected.clear(); data.items.forEach(i => selected.set(identity(i), i)); refresh();
            el('.batch-details').open = true;
            message(`${data.total} fala(s) com o mesmo original selecionada(s). Confira o grupo e escreva a correção.`);
        }));
        row.querySelector('.bar').append(same);
    }
    el('.pick-page').addEventListener('click', () => {ctx.pageItems.forEach(i => selected.set(identity(i), i)); refresh();});
    el('.pick-all').addEventListener('click', guarded(async () => {
        const requestedScope = scope;
        const data = await api('/selection?' + new URLSearchParams({q: ctx.searchQuery || '', project_id: ctx.searchProject || ''}));
        if (scope !== requestedScope) return;
        selected.clear(); data.items.forEach(i => selected.set(identity(i), i)); refresh();
        el('.batch-details').open = true;
    }));
    el('.pick-clear').addEventListener('click', () => {selected.clear(); refresh();});
    bindBatchSubmit(ctx, selected, refresh);
    return {attach, refresh, resetScope};
}
