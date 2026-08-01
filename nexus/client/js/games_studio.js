try {
    Object.defineProperty(window, 'native', {
        get: function() { return undefined; },
        set: function() {},
        configurable: true
    });
} catch(e) {}

let activeJobId = null;
let statusInterval = null;

        function logToTerminal(msg, type = 'info') {
            const manualLogs = document.getElementById('manual-logs');
            const time = new Date().toLocaleTimeString();
            const color = type === 'error' ? '#ff4f4f' : (type === 'success' ? '#00ff41' : '#00ff41');
            const entry = document.createElement('div');
            // [v2026.FIX] Timestamps mais claros (#aaa) para melhor visibilidade
            entry.innerHTML = `<span style="color: #aaa;">[${time}]</span> <span style="color: ${color};">${msg}</span>`;
            manualLogs.insertBefore(entry, manualLogs.firstChild);
        }

        async function selecionarArquivo(targetId, filter) {
            try {
                const result = await window.pywebview.api.open_file_dialog(filter);
                if (result) {
                    document.getElementById(targetId).value = result;
                    logToTerminal(`ALVO SELECIONADO: ${result.split(/[\\\\/]/).pop()}`, 'success');
                }
            } catch (e) { logToTerminal("ERRO NO PROTOCOLO DE SELEÇÃO.", 'error'); }
        }

        async function selecionarPasta(targetId) {
            try {
                const rawResult = await window.pywebview.api.open_folder_dialog(true);
                if (rawResult) {
                    let folderPaths = Array.isArray(rawResult) ? rawResult : [rawResult];
                    const formattedValue = folderPaths.join(';');
                    document.getElementById(targetId).value = formattedValue;
                    
                    const folderNames = folderPaths.map(p => p.split(/[\\/]/).pop());
                    logToTerminal(`PASTA(S) SELECIONADA(S): ${folderNames.join(', ')}`, 'success');
                    
                    try {
                        const previewRes = await fetch('http://127.0.0.1:5002/api/preview-folder', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ path: folderPaths[0], all_paths: folderPaths })
                        });
                        const previewData = await previewRes.json();
                        
                        if (previewData.success) {
                            window._lastPreviewCount = previewData.count;
                            const previewArea = document.getElementById('folder-preview-info');
                            previewArea.style.display = 'block';
                            previewArea.innerHTML = `
                                <div style="color: #00ff41; font-size: 0.65rem; font-weight: 900; margin-top: 10px; border-left: 3px solid #00ff41; padding-left: 10px; background: rgba(0, 255, 65, 0.05); padding-top: 6px; padding-bottom: 6px;">
                                    ✅ CONFIRMADO: ${previewData.folder_count || folderPaths.length} PASTA(S) NO LOTE<br>
                                    <span style="color: #00f3ff; font-size: 0.7rem; font-weight: bold;">📊 TOTAL ACUMULADO: ${previewData.count} ARQUIVOS DE ÁUDIO</span><br>
                                    <span style="opacity: 0.8; font-size: 0.55rem; color: #a0a0a0;">PASTAS: ${folderNames.join(', ')}</span>
                                </div>
                            `;
                            document.getElementById('project-progress-area').style.display = 'block';
                            document.getElementById('segment-counter').textContent = `000 / ${String(previewData.count).padStart(3, '0')}`;
                            document.getElementById('segment-counter').style.opacity = '1';
                            logToTerminal(`SCANNER: ${previewData.folder_count || folderPaths.length} pasta(s) e TOTAL de ${previewData.count} áudios validados no lote.`, 'success');
                        }
                    } catch(e_prev) { console.log("Erro no preview:", e_prev); }
                }
            } catch (e) { logToTerminal("ERRO AO ACESSAR DIRETÓRIO.", 'error'); }
        }

        async function loadProjectStatus(jobId) {
            try {
                const res = await fetch(`http://127.0.0.1:5002/api/job-status/${jobId}`);
                const data = await res.json();
                if (data.progress !== undefined) {
                    activeJobId = jobId;
                    document.getElementById('project-progress-area').style.display = 'block';
                    document.getElementById('dynamic-progress-bar').style.width = data.progress + '%';
                    document.getElementById('percent-text').textContent = Math.round(data.progress) + '%';
                    
                    const circle = document.querySelector('.progress-circle:not(.spinning-circle)');
                    if (circle) {
                        circle.style.background = `conic-gradient(var(--accent) ${data.progress}%, rgba(255,255,255,0.05) 0deg)`;
                    }

                    const stepText = (data.status === 'completed') ? 'OPERAÇÃO CONCLUÍDA' : (data.etapa ? data.etapa.toUpperCase() : 'PROCESSANDO');
                    document.getElementById('current-step-text').textContent = "STATUS: " + stepText;
                    document.getElementById('status-msg-detail').textContent = data.subetapa || data.message || "SINCRONIZANDO...";
                    
                    if (data.tool_name) {
                        document.getElementById('active-tool-badge').textContent = data.tool_name.toUpperCase();
                        document.getElementById('active-tool-badge').style.background = 'var(--accent)';
                    }

                    const curr = (data.current_seg !== undefined && data.current_seg !== null) ? data.current_seg : 0;
                    const tot = (data.total_seg !== undefined && data.total_seg !== null && data.total_seg > 0) ? data.total_seg : (window._lastPreviewCount || 0);
                    if (tot > 0) {
                        document.getElementById('segment-counter').textContent = `${String(curr).padStart(3, '0')} / ${String(tot).padStart(3, '0')}`;
                        document.getElementById('segment-counter').style.opacity = '1';
                    }

                    if (data.status === 'completed') {
                        document.getElementById('current-step-text').textContent = "STATUS: 🎉 OPERAÇÃO CONCLUÍDA COM SUCESSO!";
                        document.getElementById('current-step-text').style.color = "#00ff41";
                        document.getElementById('status-msg-detail').textContent = data.message || "100% dos áudios processados e masterizados.";
                        document.getElementById('dynamic-progress-bar').style.width = '100%';
                        document.getElementById('percent-text').textContent = '100%';
                        
                        if (!window._completedLogged) {
                            window._completedLogged = true;
                            logToTerminal("🎉 PROCESSO CONCLUÍDO COM SUCESSO! Todos os áudios foram gerados e masterizados.", "success");
                        }
                        
                        if (typeof statusInterval !== 'undefined') clearInterval(statusInterval);
                        const btn = document.getElementById('btn-iniciar');
                        if (btn) {
                            btn.disabled = false;
                            btn.style.opacity = '1';
                            btn.innerText = '🚀 INICIAR DUBLAGEM';
                        }
                    } else if (data.status === 'failed') {
                        document.getElementById('current-step-text').textContent = "STATUS: ❌ FALHA NA DUBLAGEM";
                        document.getElementById('current-step-text').style.color = "#ff0055";
                        document.getElementById('status-msg-detail').textContent = data.message || "Ocorreu um erro no pipeline.";
                        
                        if (!window._failedLogged) {
                            window._failedLogged = true;
                            logToTerminal("❌ ERRO NO MOTOR: " + (data.message || "Falha durante o processamento."), "error");
                        }
                        
                        if (typeof statusInterval !== 'undefined') clearInterval(statusInterval);
                        const btn = document.getElementById('btn-iniciar');
                        if (btn) {
                            btn.disabled = false;
                            btn.style.opacity = '1';
                            btn.innerText = '🚀 INICIAR DUBLAGEM';
                        }
                    }
                }
            } catch(e) { console.error("Erro status:", e); }
        }

        function formatDigitalTime(val) {
            if (!val) return "00:00";
            if (typeof val === 'string') {
                if (val.includes('h') || val.includes('m') || val.includes('s')) {
                    const h = (val.match(/(\d+)h/) || [])[1] || 0;
                    const m = (val.match(/(\d+)m/) || [])[1] || 0;
                    const s = (val.match(/(\d+)s/) || [])[1] || 0;
                    if (parseInt(h) > 0) return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
                    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
                }
                if (val.includes(':')) {
                    const parts = val.split(':');
                    return parts.map(p => p.padStart(2, '0')).join(':');
                }
            }
            const secs = parseInt(val, 10);
            if (isNaN(secs)) return "00:00";
            const hrs = Math.floor(secs / 3600);
            const mins = Math.floor((secs % 3600) / 60);
            const s = secs % 60;
            if (hrs > 0) return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
            return `${String(mins).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        }

        function startStatusPolling() {
            window._completedLogged = false;
            window._failedLogged = false;
            if (typeof statusInterval !== 'undefined') clearInterval(statusInterval);
            statusInterval = setInterval(() => {
                if (activeJobId) loadProjectStatus(activeJobId);
            }, 2000);
        }

        async function executar(action) {
            const projectId = document.getElementById('project-selector').value;
            const profile = document.getElementById('game-profile').value;
            const manualWav = document.getElementById('manual-wav-path').value;
            
            logToTerminal(`Iniciando comando: ${action.toUpperCase()}...`);
            
            let url = '';
            let body = {};

            if (action === 'analisar') {
                const path = document.getElementById('asset-path').value;
                url = 'http://127.0.0.1:5002/api/analisar';
                body = { path: path };
            } else if (action === 'extrair') {
                url = 'http://127.0.0.1:5002/api/descompactar';
                body = { project_id: projectId };
            } else if (action === 'fmod_extract') {
                url = 'http://127.0.0.1:5002/api/fmod_extract';
                body = { project_id: projectId };
            } else if (action === 'fmod_repack') {
                const fmodTool = document.getElementById('fmod-tool-path').value;
                const dubbedFolder = document.getElementById('dubbed-folder').value;
                url = 'http://127.0.0.1:5002/api/fmod_repack';
                body = { project_id: projectId, fmod_tool_path: fmodTool, dubbed_folder: dubbedFolder };
            } else if (action === 'dublar' || action === 'dublar_lote' || action === 'dublar_inteligente') {
                const btn = document.getElementById('btn-iniciar');
                if (btn && btn.disabled) {
                    logToTerminal("⚠️ UMA DUBLAGEM JÁ ESTÁ EM ANDAMENTO. AGUARDE...", 'warning');
                    return;
                }
                
                const selector = document.getElementById('project-selector');
                const selectedJobs = Array.from(selector.selectedOptions).map(opt => opt.value).filter(v => v && v !== "");
                
                if (btn) {
                    btn.disabled = true;
                    btn.style.opacity = '0.6';
                    btn.innerText = '⏳ DUBLAGEM EM ANDAMENTO...';
                }
                
                if ((manualWav && manualWav.length > 0) || (selectedJobs && selectedJobs.length > 0)) {
                    await startBatchDubbing(selectedJobs);
                } else {
                    const srcLang = document.getElementById('src-lang').value;
                    const targetLang = document.getElementById('target-lang').value;
                    url = 'http://127.0.0.1:5002/dublar_jogos';
                    const fd = new FormData();
                    fd.append('job_id', projectId);
                    fd.append('game_profile', profile);
                    fd.append('source_lang', srcLang);
                    fd.append('target_lang', targetLang);
                    fd.append('skip_lqa', 'true');
                    
                    try {
                        const res = await fetch(url, { method: 'POST', body: fd });
                        const data = await res.json();
                        if (data.success) {
                            activeJobId = data.job_id || projectId;
                            startStatusPolling();
                            logToTerminal(`PROTOCOLO LANÇADO: DUBLAGEM INICIADA!`, 'success');
                        } else {
                            logToTerminal(`FALHA NO MOTOR: ${data.message}`, 'error');
                            if (btn) { btn.disabled = false; btn.style.opacity = '1'; btn.innerText = '🚀 INICIAR DUBLAGEM'; }
                        }
                    } catch(e) { 
                        logToTerminal("Falha ao conectar com o motor de jogos.", 'error'); 
                        if (btn) { btn.disabled = false; btn.style.opacity = '1'; btn.innerText = '🚀 INICIAR DUBLAGEM'; }
                    }
                }
                return;
            }

            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });
                const data = await res.json();
                logToTerminal(data.message, data.success ? 'success' : 'error');
                if (data.success && action === 'analisar') setTimeout(loadProjects, 1000);
            } catch(e) { logToTerminal("Erro na comunicação com o servidor.", 'error'); }
        }

        async function startBatchDubbing(jobIdArray) {
            const manualWav = document.getElementById('manual-wav-path') ? document.getElementById('manual-wav-path').value : '';
            const payload = {};
            if (jobIdArray && jobIdArray.length > 0) payload.job_ids = jobIdArray;
            if (manualWav) payload.parent_folder = manualWav;

            if (!payload.job_ids && !payload.parent_folder) {
                logToTerminal("Nenhum projeto ou pasta selecionada para o lote.", 'error');
                return;
            }
            
            logToTerminal(`🚀 INICIANDO FILA POR ESTÁGIOS EM LOTE...`, 'info');
            try {
                const res = await fetch('http://127.0.0.1:5002/dublar_lote_jogos', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.status === 'enqueued') {
                    logToTerminal(`✅ FILA EM LOTE ATIVADA! ${data.message}`, 'success');
                    if (data.enqueued_jobs && data.enqueued_jobs.length > 0) {
                        activeJobId = data.enqueued_jobs[0];
                        startStatusPolling();
                    }
                } else {
                    logToTerminal(`⚠️ FALHA AO INICIAR LOTE: ${data.error || data.message}`, 'error');
                }
            } catch(e) {
                logToTerminal("Erro ao se comunicar com o motor de lote.", 'error');
            }
        }

        async function loadProjects(retries) {
            if (typeof retries !== 'number') retries = 120;
            try {
                const checkRes = await fetch('http://127.0.0.1:5002/api/health');
                if (!checkRes.ok) throw new Error("Motor iniciando");
                
                logToTerminal("✅ MOTOR DE JOGOS CONECTADO COM SUCESSO.", 'success');
                const overlay = document.getElementById('engine-loader-overlay');
                if (overlay) overlay.style.display = 'none';
                
                const res = await fetch('http://127.0.0.1:5002/api/get-projects');
                let projects = await res.json();
                // [FIX] Filtra apenas projetos reais do usuário, ignorando pastas de personagens
                projects = projects.filter(p => p.name && !p.name.includes('PERSONAGEM:'));
                const selector = document.getElementById('project-selector');
                selector.innerHTML = '<option value="">SELECIONE O PROJETO...</option>' + projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
                
                // [v2026.AUTO_SELECT] Se mudar, verifica se é retomada
                selector.onchange = async () => {
                    const jobId = selector.value;
                    if (!jobId) {
                        activeJobId = null;
                        return;
                    }
                    
                    activeJobId = jobId;
                    startStatusPolling(); // Ativa monitoramento contínuo em tempo real imediatamente
                    
                    logToTerminal(`ANALISANDO PROJETO: ${jobId}...`);
                    const statusRes = await fetch(`http://127.0.0.1:5002/api/job-status/${jobId}`);
                    const data = await statusRes.json();
                    
                    const btnIniciar = document.getElementById("btn-iniciar");
                    const btnContinuar = document.getElementById("btn-continuar");
                    if (data.progress > 0 && data.progress < 100) {
                        btnIniciar.style.display = "none";
                        btnContinuar.style.display = "block";
                        logToTerminal(`SESSÃO ANTERIOR DETECTADA: ${Math.round(data.progress)}% concluído.`, 'success');
                        loadProjectStatus(jobId);
                    } else {
                        btnIniciar.style.display = "block";
                        btnContinuar.style.display = "none";
                        loadProjectStatus(jobId); // Garante reset/atualização da UI para 0% ou valor atual
                    }
                };
            } catch(e) {
                if (retries > 0) {
                    const attempt = 120 - retries + 1;
                    if (attempt % 5 === 0 || attempt === 1) {
                        logToTerminal(`⏳ Inicializando motor de jogos... (${attempt * 1}s/120s)`, 'info');
                    }
                    setTimeout(() => loadProjects(retries - 1), 1000);
                } else {
                    logToTerminal("❌ FALHA AO CONECTAR COM O MOTOR DE JOGOS. Por favor, reinicie os motores ou recarregue a página.", 'error');
                }
            }
        }

        // PERSISTÊNCIA DE CAMINHOS
        function setupPersistence() {
            const paths = ['fmod-tool-path', 'manual-wav-path', 'dubbed-folder', 'asset-path'];
            paths.forEach(id => {
                const input = document.getElementById(id);
                // Carregar
                const saved = localStorage.getItem('titan-' + id);
                if (saved) input.value = saved;
                // Salvar ao mudar
                input.addEventListener('input', () => localStorage.setItem('titan-' + id, input.value));
            });
        }

        // Sobrescrever função de seleção para salvar após escolher
        const originalExecutar = executar;
        
        // [v2026.CMD_MIRROR] Sincronização de Logs em Tempo Real (Espelhamento do CMD)
        async function updateLogs() {
            try {
                const res = await fetch('http://127.0.0.1:5002/api/get-logs');
                const data = await res.json();
                if (data.logs) {
                    const consoleLog = document.getElementById('console-log');
                    consoleLog.innerHTML = data.logs;
                    
                    // Auto-scroll para o final do container principal
                    const container = document.getElementById('console-container');
                    container.scrollTop = container.scrollHeight;
                }
            } catch(e) { console.log("Erro ao buscar logs:", e); }
        }

        window.onload = () => {
            loadProjects();
            setupPersistence();
            setInterval(updateLogs, 2000); // [v2026.REALTIME_SYNC] Sincronização em tempo real (2s)
        };

        // MutationObserver para salvar quando o valor mudar via script (pelo file dialog)
        const observer = new MutationObserver((mutations) => {
            mutations.forEach(m => {
                if (m.target.id) localStorage.setItem('titan-' + m.target.id, m.target.value);
            });
        });
        ['fmod-tool-path', 'manual-wav-path', 'dubbed-folder', 'asset-path'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                // Infelizmente o evento 'input' não dispara quando o valor muda via script
                // Então vamos criar um pequeno intervalo para checar mudanças se necessário
                setInterval(() => {
                    const current = el.value;
                    const saved = localStorage.getItem('titan-' + id);
                    if (current !== saved) localStorage.setItem('titan-' + id, current);
                }, 2000);
            }
        });

// [v2026.GLOBAL_CORRECTION_ENGINE] MODO CORREÇÃO GLOBAL AVANÇADO
async function buscarDialogosGlobais() {
    const input = document.getElementById('global-search-input');
    const q = input ? input.value.trim() : '';
    const container = document.getElementById('correction-results-list');
    if (!q || q.length < 2) {
        if (container) container.innerHTML = '<div style="color:#ffaa00; font-size:0.6rem; text-align:center;">Digite pelo menos 2 caracteres para buscar.</div>';
        return;
    }

    if (container) container.innerHTML = '<div style="color:#00f3ff; font-size:0.6rem; text-align:center;">🔍 Varendo todos os projetos...</div>';

    try {
        const res = await fetch(`/api/global_search_dialogues?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        
        if (!data || data.length === 0) {
            container.innerHTML = `<div style="color:#ff4444; font-size:0.6rem; text-align:center;">Nenhum diálogo encontrado para "${q}".</div>`;
            return;
        }

        let html = '';
        data.forEach((item, idx) => {
            const inputId = `edit-input-${idx}`;
            const btnId = `btn-redub-${idx}`;
            const statusId = `status-${idx}`;
            const audioUrl = `/stream_media?path=${encodeURIComponent(item.full_audio_path)}`;

            html += `
                <div style="background: rgba(0,0,0,0.5); border: 1px solid rgba(0,243,255,0.2); padding: 10px; border-radius: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.6rem; margin-bottom: 5px;">
                        <span style="color: #00f3ff; font-weight: 900;">📁 [${item.folder.toUpperCase()}] ${item.filename}</span>
                        <audio controls src="${audioUrl}" style="height: 24px; width: 150px;"></audio>
                    </div>
                    <div style="font-size: 0.55rem; color: #888; margin-bottom: 5px;">Original (EN): <i style="color:#ccc;">"${item.original}"</i></div>
                    
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <input type="text" id="${inputId}" value="${item.translated}" style="margin-bottom: 0; font-size: 0.7rem; flex: 1; border: 1px solid #00f3ff; background: rgba(0,0,0,0.8); color: #fff; padding: 4px 8px;">
                        <button id="${btnId}" onclick="redublarSegmentoUnico('${item.folder}', '${item.filename}', '${inputId}', '${btnId}', '${statusId}')" style="background: #00f3ff; color: #000; font-weight: 900; font-size: 0.6rem; border: none; padding: 6px 12px; cursor: pointer; border-radius: 2px;">⚡ REDUBLAR</button>
                    </div>
                    <div id="${statusId}" style="font-size: 0.55rem; margin-top: 4px; display: none;"></div>
                </div>
            `;
        });

        container.innerHTML = html;
    } catch(e) {
        if (container) container.innerHTML = `<div style="color:#ff4444; font-size:0.6rem; text-align:center;">Erro ao conectar com o motor de busca: ${e}</div>`;
    }
}

// --- FILA DE REDUBLAGEM ASSÍNCRONA EM SEGUNDO PLANO (ETAPA 5) ---
const redubQueue = [];
let isProcessingRedubQueue = false;

function redublarSegmentoUnico(folder, filename, inputId, btnId, statusId) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(btnId);
    const status = document.getElementById(statusId);
    
    const newText = input ? input.value.trim() : '';
    if (!newText) return;

    // Enfileira a tarefa sem travar a interface
    const task = { folder, filename, inputId, btnId, statusId, newText };
    redubQueue.push(task);

    const position = redubQueue.length;
    if (btn) { 
        btn.disabled = true; 
        btn.style.background = '#ffaa00';
        btn.innerText = `⏳ #${position} NA FILA`; 
    }
    if (status) { 
        status.style.display = "block"; 
        status.style.color = "#ffaa00"; 
        status.innerText = `Adicionado à fila de correção (Posição #${position})...`; 
    }

    if (!isProcessingRedubQueue) {
        processRedubQueue();
    }
}

async function processRedubQueue() {
    if (redubQueue.length === 0) {
        isProcessingRedubQueue = false;
        return;
    }

    isProcessingRedubQueue = true;
    const task = redubQueue.shift();
    const { folder, filename, inputId, btnId, statusId, newText } = task;

    const btn = document.getElementById(btnId);
    const status = document.getElementById(statusId);

    if (btn) {
        btn.style.background = '#00f3ff';
        btn.innerText = "⚡ GRAVANDO...";
    }
    if (status) {
        status.style.color = "#00f3ff";
        status.innerText = "Sintetizando áudio GPU Qwen3 em segundo plano...";
    }

    // Atualiza as posições visuais dos itens restantes na fila
    redubQueue.forEach((t, idx) => {
        const b = document.getElementById(t.btnId);
        const s = document.getElementById(t.statusId);
        if (b) b.innerText = `⏳ #${idx + 1} NA FILA`;
        if (s) s.innerText = `Aguardando fila de correção (Posição #${idx + 1})...`;
    });

    try {
        const res = await fetch('/api/redub_single_segment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ folder: folder, filename: filename, new_text: newText })
        });
        const data = await res.json();

        if (data.status === 'success') {
            if (btn) { btn.disabled = false; btn.style.background = "#00ff41"; btn.innerText = "✅ CONCLUÍDO"; }
            if (status) { status.style.color = "#00ff41"; status.innerText = "✨ Áudio re-dublado e atualizado no jogo com sucesso!"; }
            if (typeof logToTerminal === 'function') logToTerminal(`✅ [REDUBLAGEM OK] ${folder}/${filename}: "${newText}"`, 'success');
        } else {
            if (btn) { btn.disabled = false; btn.style.background = "#ff4444"; btn.innerText = "❌ ERRO"; }
            if (status) { status.style.color = "#ff4444"; status.innerText = `Erro: ${data.message}`; }
        }
    } catch(e) {
        if (btn) { btn.disabled = false; btn.style.background = "#ff4444"; btn.innerText = "⚡ REDUBLAR"; }
        if (status) { status.style.color = "#ff4444"; status.innerText = `Erro de conexão: ${e}`; }
    }

    // Processa a próxima correção da fila automaticamente
    setTimeout(processRedubQueue, 200);
}