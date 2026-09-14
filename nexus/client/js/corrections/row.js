import {attachTiming, showGenerated} from './timing.js';
export function renderRow(ctx, item) {
const {root, el, api, apiRoot, select, message, persistDraft, flush, queue, guarded, controls, search, rememberTask, followTask} = ctx;
            const key = item.project_id;
            const row = document.createElement('section'); row.className = 'row'; row.dataset.segmentId = item.id; row.dataset.projectId = key;
            const name = document.createElement('div'); name.className = 'name';
            name.textContent = `${item.project_name} • ${item.id} • ${item.speaker}` + (item.approximate ? ' • Resultado aproximado' : '') + (item.start != null ? ` • ${item.start}s–${item.end}s` : '');
            const original = document.createElement('div'); original.className = 'original';
            original.textContent = 'Original em inglês: ' + (item.original || '(não disponível)');
            const text = document.createElement('textarea'); text.value = item.translated; text.maxLength = 3000;
            text.setAttribute('aria-label', 'Tradução de ' + item.id);
            const portuguese = document.createElement('div'); portuguese.className = 'count'; portuguese.textContent = 'Correção em português:';
            const meter = attachTiming(text,item.original_duration);
            const generated = document.createElement('div'); generated.className = 'generated-timing count';
            const label = document.createElement('div'); label.className = 'save';
            label.textContent = item.error || (item.draft_status === 'done' ? '✓ Correção gerada e salva' : item.draft_status === 'draft' ? '✓ Rascunho recuperado • clique em Salvar para enviar à fila' : item.draft_status ? '✓ Fala salva na fila' : 'Edite e clique em Salvar para adicionar à fila.');
            if (item.error) label.classList.add('error');
            let revision = item.revision;
            text.addEventListener('input', () => {
                revision = Math.max(Date.now() * 1000, revision + 1);
                item.revision = revision; item.translated = text.value;
                button.dataset.enqueued = 'false'; button.disabled = false;
                persistDraft({project_id: key, segment_id: item.id, text: text.value, revision}, label)
                    .then(queue).catch(() => {});
            });
            const bar = document.createElement('div'); bar.className = 'bar';
            const audio = document.createElement('audio'); audio.controls = true; audio.preload = 'none';
            audio.setAttribute('aria-label', 'Ouvir dublagem de ' + item.id);
            const query = {project_id: key};
            if (item.preview_token) query.token = item.preview_token; else query.segment_id = item.id;
            audio.src = apiRoot + '/audio?' + new URLSearchParams(query);
            bar.append(audio);
            const button = document.createElement('button'); button.type = 'button'; button.textContent = '💾 Salvar';
            button.dataset.enqueued = String(item.revision === item.queued_revision && item.draft_status !== 'error');
            button.addEventListener('click', guarded(async () => {
                if (!text.value.trim()) throw new Error('Digite o texto corrigido.');
                button.disabled = true;
                try {
                    await flush();
                    // Permite salvar a tradução existente sem exigir uma edição artificial.
                    if (!revision) {
                        revision = Date.now() * 1000;
                        await persistDraft({project_id: key, segment_id: item.id, text: text.value, revision}, label);
                    }
                    const result = await api('/enqueue', {project_id: key, segment_id: item.id});
                    button.dataset.enqueued = 'true';
                    label.textContent = item.kind === 'video' ? '✓ Na fila • aguardando Iniciar' : '✓ Na fila de dublagem';
                    await queue();
                    if (result.task_id) {
                        rememberTask(result.task_id, key, result.total);
                        followTask(result.task_id, key).catch(error => message(error.message, true));
                    } else message(result.message);
                } catch (error) { button.dataset.enqueued = 'false'; throw error; }
                finally { controls(); }
            }));
            bar.append(button);
            const openProject = document.createElement('button'); openProject.type = 'button'; openProject.className = 'quiet';
            openProject.textContent = item.kind === 'video' ? 'Abrir projeto / iniciar vídeo' : 'Abrir projeto / exportar';
            openProject.addEventListener('click', guarded(async () => {
                await flush(); select.value = key; ctx.offset = 0; await search();
            }));
            bar.append(openProject);
            row.append(name, original, portuguese, text, meter, generated, label, bar); el('.rows').append(row);
            row.dataset.originalDuration = item.original_duration || '';
            showGenerated(row,item.generated_duration,item.speed,item.original_duration);
            row.dataset.kind = item.kind;
            button.classList.add('save-one');
            ctx.batch.attach(row, item);

}
