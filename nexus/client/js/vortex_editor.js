let shortsPhotos = [];
        let shortsMusic = null;
        let activeVideoPath = null;
        const player = document.getElementById('main-player');
        const BASE_UPLOAD_PATH = "C:/IA_dublagem/uploads"; // [v2026.PATH]

        function openShortsModal() { document.getElementById('shorts-modal').style.display = 'flex'; }
        function closeShortsModal() { document.getElementById('shorts-modal').style.display = 'none'; }

        async function selectShortsPhotos() {
            try {
                const res = await window.pywebview.api.open_file_dialog("Imagens (*.jpg;*.png;*.jpeg)", true);
                if (res) {
                    shortsPhotos = Array.isArray(res) ? res : [res];
                    document.getElementById('shorts-photos-list').innerHTML = shortsPhotos.map(p => `<div>🖼️ ${p.split(/[\\\\/]/).pop()}</div>`).join('');
                }
            } catch(e) { console.error(e); }
        }

        async function selectShortsMusic() {
            try {
                const res = await window.pywebview.api.open_file_dialog("Áudio (*.mp3;*.wav)");
                if (res) {
                    shortsMusic = res;
                    document.getElementById('shorts-music-name').textContent = `🎵 ${shortsMusic.split(/[\\\\/]/).pop()}`;
                }
            } catch(e) { console.error(e); }
        }

        async function generateShort() {
            if (shortsPhotos.length < 3 || !shortsMusic) { alert("Selecione 3 fotos e 1 música!"); return; }
            closeShortsModal();
            startVortexPolling();
            try {
                const res = await fetch('http://127.0.0.1:5003/api/create_shorts', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ photos: shortsPhotos, music: shortsMusic })
                });
            } catch(e) { alert("Erro de conexão com o Motor Vortex (5003)."); }
        }

        function createClipCard(type, filename, fullPath) {
            const container = document.getElementById('clips-sequence');
            document.getElementById('empty-msg').style.display = 'none';
            
            const cardId = 'clip_' + Math.random().toString(36).substr(2, 9);
            const card = document.createElement('div');
            card.className = 'clip-card';
            card.id = cardId;
            card.onclick = (e) => {
                if (e.target.classList.contains('remove-clip')) return;
                loadToPlayer(type, fullPath, card);
            };
            
            card.innerHTML = `
                <div class="remove-clip" onclick="removeClip('${cardId}')" style="position: absolute; top: 5px; right: 5px; width: 20px; height: 20px; background: rgba(255,0,0,0.5); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; border-radius: 2px; z-index: 20;">X</div>
                <div style="font-size: 2rem; color: ${type === 'video' ? 'var(--accent)' : '#fff'}; margin-bottom:10px;">${type === 'video' ? '🎞️' : '🎵'}</div>
                <h5 style="margin:0; font-size:0.65rem; color:#fff; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${filename}</h5>
            `;
            container.appendChild(card);
            recalculateSpiral();
            if (type === 'video') loadToPlayer(type, fullPath, card);
            logToTerminal(`ADICIONADO: ${filename}`);
        }

        function removeClip(id) {
            const card = document.getElementById(id);
            if (card) {
                card.remove();
                recalculateSpiral();
                const cards = document.querySelectorAll('.clip-card');
                if (cards.length === 0) {
                    document.getElementById('empty-msg').style.display = 'block';
                    player.src = "";
                    player.style.display = 'none';
                    document.getElementById('empty-monitor').style.display = 'flex';
                }
                logToTerminal(`REMOVIDO: Clip ${id}`);
            }
        }

        function clearTimeline() {
            document.getElementById('clips-sequence').innerHTML = '<p id="empty-msg" style="color: rgba(255,255,255,0.05); font-size: 0.7rem; letter-spacing: 4px; font-weight: 900;">INJETAR ATIVOS</p>';
            player.src = "";
            player.style.display = 'none';
            logToTerminal("TIMELINE LIMPA.");
        }

        // --- BLOQUEIO DE COMPORTAMENTO PADRÃO DO WINDOWS (EVITA ABRIR O PLAYER) ---
        window.addEventListener("dragover", function(e) {
            e.preventDefault();
        }, false);

        window.addEventListener("drop", function(e) {
            e.preventDefault();
        }, false);

        function handleBrowserDrop(e) {
            e.preventDefault();
            const files = e.dataTransfer.files;
            if (files && files.length > 0) {
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    // No PyWebView/Windows, o path real às vezes está em propriedades específicas
                    const path = file.path || file.name; 
                    const ext = path.split('.').pop().toLowerCase();
                    const type = ['mp4', 'mkv', 'avi', 'mov'].includes(ext) ? 'video' : 'audio';
                    
                    createClipCard(type, path.split(/[\\\\/]/).pop(), path);
                }
            }
        }

        // Fallback para o evento nativo do PyWebView
        window.handleNativeDrop = function(files) {
            if (Array.isArray(files)) {
                files.forEach(f => {
                    const ext = f.split('.').pop().toLowerCase();
                    const type = ['mp4', 'mkv', 'avi', 'mov'].includes(ext) ? 'video' : 'audio';
                    createClipCard(type, f.split(/[\\\\/]/).pop(), f);
                });
            }
        };

        function recalculateSpiral() {
            const cards = document.querySelectorAll('.clip-card');
            cards.forEach((card, i) => {
                card.style.setProperty('--index', i);
                card.style.zIndex = 100 - i;
                card.style.transform = `rotateY(calc(${i} * 20deg)) translateZ(calc(${i} * -40px))`;
            });
        }

        function loadToPlayer(type, fullPath, card) {
            if (type !== 'video') return;
            activeVideoPath = fullPath;
            const filename = fullPath.split(/[\\\\/]/).pop();
            
            document.querySelectorAll('.clip-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            
            document.getElementById('empty-monitor').style.display = 'none';
            document.getElementById('visual-trimmer').style.display = 'block';
            player.style.display = 'block';
            
            // Mostra Loader
            document.getElementById('player-loader').style.display = 'flex';
            
            // Atualiza Inspetor
            document.getElementById('active-file-indicator').style.display = 'block';
            document.getElementById('current-video-name').textContent = filename;
            
            // [v2026.RTX_FIX] Garante que o path use barras normais e a porta correta
            let cleanPath = fullPath.replace(/\\\\/g, '/');
            player.src = `http://127.0.0.1:5003/stream_media?path=${encodeURIComponent(cleanPath)}`;
            player.load(); // Força o carregamento da nova fonte
            logToTerminal(`CONECTANDO STREAM RTX: ${filename}`);
        }

        player.oncanplay = () => {
            document.getElementById('player-loader').style.display = 'none';
            logToTerminal(`✅ SINAL DE VÍDEO ESTABILIZADO: ${player.videoWidth}x${player.videoHeight}`);
        };

        player.onerror = () => {
            document.getElementById('player-loader').style.display = 'none';
            const error = player.error;
            let msg = "ERRO DESCONHECIDO";
            if (error) {
                switch(error.code) {
                    case 1: msg = "ABORTADO PELO USUÁRIO"; break;
                    case 2: msg = "ERRO DE REDE (CONEXÃO 5003?)"; break;
                    case 3: msg = "ERRO DE DECODIFICAÇÃO (CODEC INVÁLIDO)"; break;
                    case 4: msg = "MÍDIA NÃO SUPORTADA (USE .MP4)"; break;
                }
            }
            logToTerminal(`❌ FALHA CRÍTICA NA MÍDIA: ${msg}`);
            console.error("Video Error Details:", error);
        };

        function togglePlay() {
            if (!player.src) return;
            if (player.paused) {
                player.play();
                document.getElementById('play-btn').textContent = '⏸ PAUSE';
            } else {
                player.pause();
                document.getElementById('play-btn').textContent = '▶ PLAY';
            }
        }

        async function addClip(type) {
            try {
                const filter = type === 'video' ? "Vídeo (*.mp4;*.mkv)" : "Áudio (*.mp3;*.wav)";
                const result = await window.pywebview.api.open_file_dialog(filter);
                if (result) createClipCard(type, result.split(/[\\\\/]/).pop(), result);
            } catch (e) { console.error(e); }
        }

        async function refreshProjectFiles() {
            try {
                const res = await fetch('/api/list_project_files');
                const files = await res.json();
                const list = document.getElementById('project-files-list');
                list.innerHTML = files.map(f => `
                    <div onclick="createClipCard('${f.type}', '${f.name}', '${f.path.replace(/\\\\/g, '/')}')" 
                         style="padding: 8px; border-bottom: 1px solid #222; cursor: pointer; font-size: 0.65rem; transition: 0.3s;"
                         onmouseover="this.style.background='rgba(255,204,0,0.1)'"
                         onmouseout="this.style.background='transparent'">
                        ${f.type === 'video' ? '🎞️' : '🎵'} ${f.name}
                    </div>
                `).join('');
            } catch (e) { console.error(e); }
        }

        let vortexPollInterval = null;
        let renderStartTime = null;
        let timerTicker = null;

        async function startVortexPolling() {
            document.getElementById('vortex-progress-area').style.display = 'block';
            if (vortexPollInterval) clearInterval(vortexPollInterval);
            
            renderStartTime = Date.now();
            if (timerTicker) clearInterval(timerTicker);
            timerTicker = setInterval(() => {
                const elapsed = Date.now() - renderStartTime;
                const m = Math.floor(elapsed / 60000).toString().padStart(2, '0');
                const s = Math.floor((elapsed % 60000) / 1000).toString().padStart(2, '0');
                document.getElementById('vortex-timer').textContent = `⏱️ ${m}:${s}`;
            }, 1000);
            
            vortexPollInterval = setInterval(async () => {
                try {
                    const res = await fetch('http://127.0.0.1:5003/api/vortex_status');
                    const data = await res.json();
                    document.getElementById('vortex-progress-bar').style.width = data.progress + '%';
                    document.getElementById('vortex-percent').textContent = data.progress + '%';
                    document.getElementById('vortex-status-msg').textContent = data.message || data.status;
                    
                    if (data.status === 'done' || data.status === 'error') {
                        clearInterval(vortexPollInterval);
                        clearInterval(timerTicker);
                        if (data.status === 'done') {
                            const finalTime = document.getElementById('vortex-timer').textContent;
                            logToTerminal(`✅ PROCESSO CONCLUÍDO EM ${finalTime.replace('⏱️ ', '')}`);
                        }
                    }
                } catch (e) {}
            }, 800);
        }

        let lastLoggedMsg = "";
        function logToTerminal(msg) {
            if (!msg || msg === lastLoggedMsg) return;
            const terminal = document.getElementById('vortex-terminal');
            if (!terminal) return;
            const now = new Date();
            const time = now.getHours().toString().padStart(2, '0') + ":" + 
                         now.getMinutes().toString().padStart(2, '0') + ":" + 
                         now.getSeconds().toString().padStart(2, '0');
            
            const div = document.createElement('div');
            div.style.marginBottom = "5px";
            div.style.borderLeft = "2px solid var(--accent)";
            div.style.paddingLeft = "10px";
            div.style.animation = "fadeIn 0.3s ease";
            div.innerHTML = `<span style="color: var(--accent); opacity: 0.5; font-size: 0.65rem;">[${time}]</span> <span style="color: #fff;">${msg}</span>`;
            terminal.appendChild(div);
            terminal.scrollTop = terminal.scrollHeight;
            lastLoggedMsg = msg;
        }

        function renderizar() {
            if (!activeVideoPath) { alert("Selecione um vídeo!"); return; }
            executarFerramenta('trim');
        }

        function markTrim(type) {
            const currentTime = player.currentTime;
            const duration = player.duration;
            if (isNaN(duration)) return;

            const timeStr = formatTimeForFFmpeg(currentTime);
            const percent = (currentTime / duration) * 100;

            if (type === 'start') {
                document.getElementById('trim-start').value = timeStr;
                document.getElementById('trim-selection').style.left = percent + '%';
                logToTerminal(`PONTO DE INÍCIO DEFINIDO: ${timeStr}`);
            } else {
                document.getElementById('trim-end').value = timeStr;
                const startPercent = parseFloat(document.getElementById('trim-selection').style.left) || 0;
                document.getElementById('trim-selection').style.width = (percent - startPercent) + '%';
                logToTerminal(`PONTO DE FIM DEFINIDO: ${timeStr}`);
            }
        }

        function formatTimeForFFmpeg(seconds) {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = (seconds % 60).toFixed(2);
            return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(5, '0')}`;
        }

        player.ontimeupdate = () => {
            if (player.duration) {
                const percent = (player.currentTime / player.duration) * 100;
                document.getElementById('seeker-needle').style.left = percent + '%';
            }
        };

        async function selecionarParaJuntar() {
            try {
                // Abre o seletor múltiplo (o true ativa a seleção múltipla no pywebview)
                const res = await window.pywebview.api.open_file_dialog("Vídeos (*.mp4;*.mkv;*.avi;*.mov)", true);
                if (res) {
                    const files = Array.isArray(res) ? res : [res];
                    logToTerminal(`FILA DE JUNÇÃO: ${files.length} vídeos selecionados.`);
                    
                    startVortexPolling();
                    await fetch(`http://127.0.0.1:5003/api/vortex_tool`, { 
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            tool: 'merge',
                            files: files
                        })
                    });
                }
            } catch(e) { alert("Erro de conexão com o Motor Vortex (5003)."); }
        }

        async function executarFerramenta(tool) {
            startVortexPolling();
            try {
                await fetch(`http://127.0.0.1:5003/api/vortex_tool`, { 
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        tool: tool,
                        input_file: activeVideoPath,
                        start: document.getElementById('trim-start').value,
                        end: document.getElementById('trim-end').value
                    })
                });
            } catch (e) { alert("Erro de conexão com o Motor Vortex (5003)."); }
        }

        let cutsQueue = [];

        function addCurrentToQueue() {
            const start = document.getElementById('trim-start').value;
            const end = document.getElementById('trim-end').value;
            
            if (start === end) { alert("Início e Fim não podem ser iguais!"); return; }
            
            cutsQueue.push({ start, end });
            updateCutsUI();
            logToTerminal(`ADICIONADO À FILA: Corte ${cutsQueue.length} (${start} -> ${end})`);
        }

        function updateCutsUI() {
            const list = document.getElementById('cuts-list');
            const btn = document.getElementById('btn-render-batch');
            
            if (cutsQueue.length === 0) {
                list.innerHTML = '<p style="opacity: 0.3; text-align: center;">Nenhum trecho adicionado...</p>';
                btn.style.display = 'none';
                return;
            }

            btn.style.display = 'block';
            list.innerHTML = cutsQueue.map((cut, i) => `
                <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.05); padding: 5px 10px; margin-bottom: 5px; border-left: 3px solid var(--accent);">
                    <span>#${i+1}: <b>${cut.start}</b> ➔ <b>${cut.end}</b></span>
                    <button onclick="removeCut(${i})" style="background: none; border: none; color: #ff4444; cursor: pointer; font-weight: bold;">[X]</button>
                </div>
            `).join('');
        }

        function removeCut(index) {
            cutsQueue.splice(index, 1);
            updateCutsUI();
        }

        async function renderBatch() {
            if (cutsQueue.length === 0) return;
            if (!activeVideoPath) { alert("Selecione um vídeo primeiro!"); return; }

            startVortexPolling();
            try {
                await fetch(`http://127.0.0.1:5003/api/vortex_tool`, { 
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        tool: 'multi_trim',
                        input_file: activeVideoPath,
                        cuts: cutsQueue
                    })
                });
                // Limpa a fila após disparar
                // cutsQueue = [];
                // updateCutsUI();
            } catch (e) { alert("Erro de conexão com o Motor Vortex (5003)."); }
        }

        window.onload = refreshProjectFiles;

        // Efeito de Hover no Drag & Drop
        const dropZone = document.getElementById('clips-sequence');
        dropZone.ondragenter = () => dropZone.style.background = 'rgba(255,204,0,0.1)';
        dropZone.ondragleave = () => dropZone.style.background = 'rgba(0,0,0,0.4)';
        dropZone.ondrop = (e) => {
            dropZone.style.background = 'rgba(0,0,0,0.4)';
            handleBrowserDrop(e);
        };