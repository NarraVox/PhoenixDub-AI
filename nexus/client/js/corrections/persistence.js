export function persistence(ctx) {
const {message, apiRoot, draftPrefix} = ctx;
const saving = new Set();
    async function api(path, body, keepalive = false) {
        const response = await fetch(apiRoot + path, body === undefined ? {} : {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body), keepalive
        });
        let result;
        try { result = await response.json(); }
        catch (_) { throw new Error('Reabra o Nexus para carregar o servidor atualizado da correção.'); }
        if (!response.ok) throw new Error(result.error || result.message || `Erro HTTP ${response.status}`);
        return result;
    }
    function persistDraft(body, label) {
        const localKey = draftPrefix + body.project_id + ':' + body.segment_id;
        try { localStorage.setItem(localKey, JSON.stringify(body)); }
        catch (_) { message('O armazenamento de recuperação do navegador está cheio. Aguarde a confirmação de salvamento no servidor.', true); }
        label.textContent = 'Salvando alteração...';
        const promise = api('/draft', body, true).then(saved => {
            const local = JSON.parse(localStorage.getItem(localKey) || 'null');
            if (local && local.revision === body.revision && saved.revision >= body.revision) {
                localStorage.removeItem(localKey);
                label.textContent = '✓ Rascunho salvo em JSON • clique em Salvar para enviar à fila';
                label.classList.remove('error');
            }
        }).catch(error => {
            label.textContent = 'Ainda não salvo no servidor: ' + error.message;
            label.classList.add('error');
            throw error;
        }).finally(() => saving.delete(promise));
        saving.add(promise);
        promise.catch(() => {});
        return promise;
    }
    async function recoverDrafts() {
        const entries = Object.keys(localStorage).filter(key => key.startsWith(draftPrefix));
        for (const key of entries) {
            const body = JSON.parse(localStorage.getItem(key));
            if (!body || !ctx.projects.some(p => p.id === body.project_id)) continue;
            const saved = await api('/draft', body);
            const latest = JSON.parse(localStorage.getItem(key) || 'null');
            if (latest?.revision === body.revision && saved.revision >= body.revision) localStorage.removeItem(key);
        }
    }
    async function flush() {
        await Promise.all([...saving]);
        await recoverDrafts();
    }

return {api, persistDraft, recoverDrafts, flush};
}
