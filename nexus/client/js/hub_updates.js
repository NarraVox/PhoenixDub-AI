(() => {
    const dialog = document.getElementById('updates-dialog');
    const check = document.getElementById('check-updates');
    const install = document.getElementById('install-update');
    const message = document.getElementById('updates-message');
    const versions = document.getElementById('updates-versions');
    const notes = document.getElementById('updates-notes');
    const link = document.getElementById('updates-release');
    const progress = document.getElementById('updates-progress');
    let working = false;
    async function api(url, method = 'GET') {
        const response = await fetch(url, {method, headers: {'X-Nexus-Update': '1'}, cache: 'no-store'});
        const data = await response.json();
        if (!response.ok || data?.success === false) throw new Error(data?.message || 'Não foi possível consultar as atualizações.');
        return data;
    }
    document.getElementById('close-updates').addEventListener('click', () => dialog.close());
    check.addEventListener('click', async () => {
        if (!dialog.open) dialog.showModal();
        if (working) return;
        check.disabled = true;
        install.hidden = true;
        progress.hidden = true;
        notes.textContent = '';
        versions.textContent = '';
        link.hidden = true;
        message.textContent = 'Verificando atualizações no GitHub...';
        try {
            const data = await api('/api/check-update');
            versions.textContent = `Instalada: ${data.current_version} · Publicada: ${data.latest_version}`;
            message.textContent = data.status === 'available' ? 'Atualização detectada!' :
                data.status === 'ahead' ? 'Você está usando uma versão de desenvolvimento mais recente que a publicada.' : 'Você já está na versão mais recente.';
            if (data.development_copy) {
                message.textContent += ' Cópia de desenvolvimento protegida: instalação automática desativada. Seus arquivos locais não serão substituídos pelo atualizador.';
            }
            notes.textContent = data.notes;
            link.href = data.release_url;
            link.hidden = false;
            if (data.has_update) {
                install.hidden = !data.automatic_supported;
                if (!data.automatic_supported && !data.development_copy) message.textContent += ' Consulte a release para atualizar esta instalação.';
            }
        } catch (error) { message.textContent = error.message; }
        finally { check.disabled = false; }
    });
    install.addEventListener('click', async () => {
        if (working) return;
        working = true; install.disabled = true; progress.hidden = false;
        try {
            await api('/api/updates/download', 'POST');
            for (;;) {
                const state = await api('/api/updates/status');
                message.textContent = state.message;
                progress.value = state.progress || 0;
                if (state.status === 'error') throw new Error(state.message);
                if (state.status === 'ready') break;
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
            const result = await api('/api/updates/install', 'POST');
            message.textContent = result.message;
        } catch (error) {
            message.textContent = error.message;
            install.disabled = false; working = false;
        }
    });
    api('/api/app-version').then(data => {
        document.getElementById('hub-version').textContent = `v${data.current_version}${data.development_copy ? ' · Desenvolvimento protegido' : ''}`;
    }).catch(() => {});
    api('/api/updates/result').then(result => {
        if (result && !result.success) {
            message.textContent = result.message;
            dialog.showModal();
        }
    }).catch(() => {});
})();
