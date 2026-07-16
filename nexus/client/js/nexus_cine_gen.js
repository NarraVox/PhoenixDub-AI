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
                
                // Adiciona os dois primeiros por padrão
                window.onload = () => {
                    addActor('Carol', 'Feminino');
                    addActor('Paulo', 'Masculino');
                };

async function startGeneration() {
            const script = document.getElementById('script-input').value;
            if(!script) return;

            const btn = document.getElementById('start-btn');
            const status = document.getElementById('global-status');
            
            btn.disabled = true;
            btn.style.opacity = '0.4';
            btn.style.cursor = 'not-allowed';
            status.innerHTML = '<div style="width: 8px; height: 8px; border-radius: 50%; background: var(--accent); animation: pulse 1s infinite;"></div> Orquestrando Gemma 4...';

            // Captura dinamicamente todos os atores e converte imagens para Base64
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
            } catch(e) {
                console.error("Erro na produção:", e);
            }
        }

        // Polling de atualização
        setInterval(async () => {
            try {
                const res = await fetch('/api/get-scenes');
                const data = await res.json();
                updateSceneList(data.scenes);
                updateProgress(data.progress);
                
                // Atualiza o status global na tela
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
                    <div class="scene-thumb">SCENE</div>
                    <div class="scene-info">
                        <h4>${scene.name}</h4>
                        <p>${scene.status}</p>
                    </div>
                    ${scene.active ? '<span class="tag-active">Renderizando</span>' : ''}
                `;
                container.appendChild(div);
            });
        }

        function updateProgress(p) {
            document.getElementById('progress-bar').style.width = p + '%';
            document.getElementById('progress-text').textContent = p + '%';
        }