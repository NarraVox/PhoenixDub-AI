// NEXUS CINE-GEN :: CONTROLADOR DE INTERFACE (v2026.DIRECTOR)

function addActor(name = '', gender = 'Feminino') {
    const list = document.getElementById('character-list');
    const id = Date.now();
    const div = document.createElement('div');
    div.className = 'scene-item';
    div.id = `actor-card-${id}`;
    div.style = 'padding: 10px; flex-direction: column; align-items: stretch; position: relative;';
    div.innerHTML = `
        <button onclick="document.getElementById('actor-card-${id}').remove()" style="position: absolute; top: 5px; right: 5px; background: none; border: none; color: var(--danger); cursor: pointer; font-weight: 800; font-size: 0.8rem;">×</button>
        <input type="text" class="actor-name vram-badge" placeholder="Nome do Personagem" value="${name}" style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: #fff; width: 100%; margin-bottom: 8px; font-family: 'Outfit';">
        <select class="actor-gender vram-badge" style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: var(--text-dim); width: 100%; margin-bottom: 8px; font-family: 'Outfit'; cursor: pointer;">
            <option value="Feminino" ${gender === 'Feminino' ? 'selected' : ''}>Feminino</option>
            <option value="Masculino" ${gender === 'Masculino' ? 'selected' : ''}>Masculino</option>
        </select>
        <input type="file" class="actor-img" style="font-size: 0.7rem; color: var(--text-dim);">
    `;
    list.appendChild(div);
}

// Carrega projetos salvos na inicialização
window.onload = () => {
    addActor('Paulo', 'Masculino');
    addActor('Carol', 'Feminino');
    loadSavedProjects();
};

async function loadSavedProjects() {
    try {
        const res = await fetch('/api/cine/projects');
        const data = await res.json();
        const select = document.getElementById('saved-projects-select');
        if (data.success && data.projects && data.projects.length > 0) {
            select.innerHTML = '<option value="">Selecione um projeto para continuar...</option>';
            data.projects.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.job_id;
                opt.textContent = `[${p.progress || 0}%] ${p.title || p.job_id} (${p.current_stage || 'status'})`;
                select.appendChild(opt);
            });
        }
    } catch(e) {
        console.error("Erro ao carregar projetos:", e);
    }
}

async function resumeSelectedProject() {
    const select = document.getElementById('saved-projects-select');
    const jobId = select.value;
    if (!jobId) {
        alert("Por favor, selecione um projeto na lista.");
        return;
    }

    const btn = document.getElementById('resume-btn');
    btn.disabled = true;
    btn.textContent = "⏳ Retomando...";

    try {
        const res = await fetch('/api/cine/resume-project', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ job_id: jobId })
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('global-status').textContent = `🔄 Retomando projeto ${jobId}...`;
        }
    } catch(e) {
        console.error("Erro ao retomar:", e);
    } finally {
        btn.disabled = false;
        btn.textContent = "🔄 RETOMAR";
    }
}

async function startGeneration() {
    const script = document.getElementById('script-input').value;
    if(!script) return;

    const btn = document.getElementById('start-btn');
    const status = document.getElementById('global-status');

    btn.disabled = true;
    btn.style.opacity = '0.4';
    btn.style.cursor = 'not-allowed';
    status.innerHTML = '<div style="width: 8px; height: 8px; border-radius: 50%; background: var(--accent); animation: pulse 1s infinite;"></div> Orquestrando Qwen 3.5 + Wan 2.2...';

    const actorCards = document.querySelectorAll('#character-list .scene-item');
    const actors = [];

    for (let card of actorCards) {
        const name = card.querySelector('.actor-name').value || "Desconhecido";
        const gender = card.querySelector('.actor-gender').value;
        const fileInput = card.querySelector('.actor-img');
        let base64Img = null;

        if (fileInput.files && fileInput.files[0]) {
            base64Img = await new Promise((resolve) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.readAsDataURL(fileInput.files[0]);
            });
        }

        actors.push({ name, gender, image: base64Img });
    }

    try {
        const res = await fetch('/api/start-cine', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                script: script,
                actors: actors
            })
        });
        const data = await res.json();
        setTimeout(loadSavedProjects, 3000);
    } catch(e) {
        console.error("Erro na produção:", e);
    }
}

// Polling de atualização contínua
setInterval(async () => {
    try {
        const res = await fetch('/api/get-scenes');
        const data = await res.json();
        updateSceneList(data.scenes);
        updateProgress(data.progress);

        if(data.status) {
            document.getElementById('global-status').textContent = data.status;
        }
    } catch(e) {}
}, 2000);

function updateSceneList(scenes) {
    const container = document.getElementById('scene-list');
    if(!scenes || scenes.length === 0) return;

    container.innerHTML = '';
    scenes.forEach(scene => {
        const div = document.createElement('div');
        div.className = 'scene-item';
        div.innerHTML = `
            <div class="scene-thumb" style="background: rgba(0, 240, 255, 0.1); color: var(--accent); font-weight: 800;">SCENE</div>
            <div class="scene-info">
                <h4>${scene.name || scene.titulo}</h4>
                <p style="color: var(--text-dim); font-size: 0.75rem;">${scene.status || 'Pendente'}</p>
            </div>
            ${scene.active ? '<span class="tag-active" style="background: var(--accent); color: #000; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 800;">Renderizando</span>' : ''}
        `;
        container.appendChild(div);
    });
}

function updateProgress(p) {
    p = p || 0;
    document.getElementById('progress-bar').style.width = p + '%';
    document.getElementById('progress-text').textContent = p + '%';
}