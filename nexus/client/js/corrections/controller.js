import template from './template.js';
import {persistence} from './persistence.js';
import {setupControls} from './controls.js';
import {tasks} from './tasks.js';
import {renderRow} from './row.js';
import {setupBatch} from './batch.js';
import {setupProgress} from './progress.js';
export function mount(host) {
 const root = host.attachShadow({mode:'open'}); root.innerHTML = template;
 const el = selector => root.querySelector(selector);
 const dialog = el('dialog'), select = el('select'), status = el('.status');
 const ctx = {root, el, select, projects:[], offset:0, total:0, working:false, outputFolder:null,
  apiRoot:'/api/corrections', draftPrefix:'nexus-correction-draft:', taskKey:'nexus-correction-task'};
 const {draftPrefix, taskKey} = ctx;
 const message = (text, error=false) => {status.textContent=text; status.classList.toggle('error',error);};
 ctx.message=message; ctx.guarded=guarded;
 Object.assign(ctx, persistence(ctx));
 const {api, persistDraft, recoverDrafts, flush} = ctx;
 Object.assign(ctx, setupControls(ctx));
 const {controls, queue} = ctx;
 ctx.progress = setupProgress(ctx);
 Object.assign(ctx, tasks(ctx));
 const {rememberTask, followTask, execute} = ctx;
 ctx.search=search;
 ctx.batch = setupBatch(ctx);
 let searchSerial=0;
    async function search() {
        const serial = ++searchSerial;
        const filterKey = select.value;
        const query = el('.query').value;
        ctx.batch.resetScope(JSON.stringify([filterKey, query]));
        el('.summary').textContent = 'Buscando falas...';
        const data = await api('/segments?' + new URLSearchParams({project_id: filterKey, q: query, offset: ctx.offset}));
        if (serial !== searchSerial || filterKey !== select.value) return;
        ctx.searchQuery = query;
        ctx.searchProject = filterKey;
        ctx.total = data.total;
        el('.rows').replaceChildren();
        el('.summary').textContent = `${ctx.total} fala(s) encontrada(s) em ${data.projects_searched} projeto(s) • página ${Math.floor(ctx.offset / 40) + 1}`;
        if (!ctx.total) el('.summary').textContent += ' • Tente um trecho menor ou uma palavra da fala.';
        ctx.pageItems = data.items;
        for (const item of data.items) renderRow(ctx, item);
        ctx.batch.refresh();
        el('.previous').disabled = ctx.offset === 0;
        el('.next').disabled = ctx.offset + 40 >= ctx.total;
        controls();
        await queue();
    }
    async function loadProjects() {
        const selected = select.value;
        ctx.projects = await api('/projects');
        ctx.projects.sort((a, b) => Number(b.kind === host.dataset.kind) - Number(a.kind === host.dataset.kind));
        select.replaceChildren();
        const all = document.createElement('option'); all.value = ''; all.textContent = 'Todos os projetos de uploads'; select.append(all);
        for (const project of ctx.projects) {
            const option = document.createElement('option'); option.value = project.id;
            option.textContent = `${project.kind === 'video' ? 'Vídeo' : 'Jogo'} — ${project.name} (${project.count} falas)`;
            select.append(option);
        }
        if (ctx.projects.some(p => p.id === selected)) select.value = selected;
        await recoverDrafts(); controls();
        ctx.progress.render();
        if (!ctx.projects.length) { message('Nenhum projeto com roteiro encontrado. Preserve a pasta do projeto em uploads para corrigir suas falas.'); return; }
        ctx.offset = 0; await search();
        message('Alterações recuperadas. Edite as falas que deseja corrigir.');
    }
    function guarded(action) { return () => Promise.resolve().then(action).catch(error => message(error.message, true)); }
    el('.launch').addEventListener('click', guarded(async () => {
        dialog.showModal();
        if (ctx.working) return;
        await loadProjects();
        el('.query').focus();
        const tasks = JSON.parse(localStorage.getItem(taskKey) || '[]');
        if (tasks.length && ctx.projects.some(p => p.id === tasks[0].project_id)) {
            await search();
            for (const task of tasks) ctx.progress.register(task.id, task.project_id, task.total);
            for (const task of tasks) followTask(task.id, task.project_id).catch(error => message(error.message, true));
        }
    }));
    el('.close').addEventListener('click', () => dialog.close());
    el('.refresh').addEventListener('click', guarded(loadProjects));
    select.addEventListener('change', guarded(async () => { await flush(); ctx.offset = 0; ctx.outputFolder = null; el('.folder').hidden = true; message('Edite as falas e clique em Salvar para enviá-las à fila.'); await search(); }));
    el('.search').addEventListener('click', guarded(async () => { await flush(); ctx.offset = 0; await search(); }));
    el('.query').addEventListener('keydown', event => { if (event.key === 'Enter') el('.search').click(); });
    el('.previous').addEventListener('click', guarded(async () => { await flush(); ctx.offset = Math.max(0, ctx.offset - 40); await search(); }));
    el('.next').addEventListener('click', guarded(async () => { await flush(); ctx.offset += 40; await search(); }));
    el('.start').addEventListener('click', () => execute(() => api('/start', {project_id: select.value})));
    el('.export').addEventListener('click', () => execute(() => api('/export', {project_id: select.value})));
    el('.folder').addEventListener('click', guarded(async () => {
        if (window.pywebview?.api?.open_folder_explorer) await window.pywebview.api.open_folder_explorer(ctx.outputFolder);
        else message('Pasta de saída: ' + ctx.outputFolder);
    }));
    window.addEventListener('pagehide', () => {
        for (const key of Object.keys(localStorage).filter(key => key.startsWith(draftPrefix))) {
            const body = JSON.parse(localStorage.getItem(key));
            api('/draft', body, true).catch(() => {});
        }
    });

}
