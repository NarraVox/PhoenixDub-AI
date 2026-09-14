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
                // [v2026.BATCH_SYNC] Verifica se há um lote global ativo no motor
                let data = null;
                let isBatchActive = false;
                try {
                    const batchRes = await fetch('http://127.0.0.1:5002/api/active-batch-status');
                    if (batchRes.ok) {
                        const batchData = await batchRes.json();
                        if (batchData.is_running && batchData.active_job_id) {
                            jobId = batchData.active_job_id;
                            activeJobId = jobId;
                            data = batchData;
                            isBatchActive = true;
                        }
                    }
                } catch(e_b) {}

                if (!data && jobId) {
                    const res = await fetch(`http://127.0.0.1:5002/api/job-status/${jobId}`);
                    if (res.ok) data = await res.json();
                }

                if (data && data.progress !== undefined) {
                    activeJobId = jobId;
                    document.getElementById('project-progress-area').style.display = 'block';
                    document.getElementById('dynamic-progress-bar').style.width = data.progress + '%';
                    document.getElementById('percent-text').textContent = Math.round(data.progress) + '%';
                    
                    const circle = document.querySelector('.progress-circle:not(.spinning-circle)');
                    if (circle) {
                        circle.style.background = `conic-gradient(var(--accent) ${data.progress}%, rgba(255,255,255,0.05) 0deg)`;
                    }

                    // Exibição clara de estágio e lote
                    let isCompletedOverall = (data.status === 'completed' && !isBatchActive);
                    let stepText = isCompletedOverall ? 'OPERAÇÃO CONCLUÍDA' : (data.etapa ? data.etapa.toUpperCase() : 'PROCESSANDO');
                    if (data.current_index && data.total_jobs) {
                        stepText = `${stepText} [LOTE: PASTA ${data.current_index}/${data.total_jobs}]`;
                    }
                    document.getElementById('current-step-text').textContent = "STATUS: " + stepText;
                    document.getElementById('status-msg-detail').textContent = data.subetapa || data.message || "SINCRONIZANDO...";
                    
                    if (data.tempo_decorrido) {
                        const timerEl = document.getElementById('titan-timer');
                        if (timerEl) timerEl.textContent = formatDigitalTime(data.tempo_decorrido);
                    }

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

                    if (isCompletedOverall) {
                        document.getElementById('current-step-text').textContent = "STATUS: 🎉 OPERAÇÃO CONCLUÍDA COM SUCESSO!";
                        document.getElementById('current-step-text').style.color = "#00ff41";
                        document.getElementById('status-msg-detail').textContent = data.message || "100% dos áudios processados e masterizados.";
                        document.getElementById('dynamic-progress-bar').style.width = '100%';
                        document.getElementById('percent-text').textContent = '100%';
                        
                        if (!window._completedLogged) {
                            window._completedLogged = true;
                            logToTerminal("🎉 PROCESSO CONCLUÍDO COM SUCESSO! Todos os áudios foram gerados e masterizados.", "success");
                        }
                        
                        const btn = document.getElementById('btn-iniciar');
                        if (btn) {
                            btn.disabled = false;
                            btn.style.opacity = '1';
                            btn.innerText = '🚀 INICIAR DUBLAGEM';
                        }
                        setTimeout(refreshProjectsList, 500);
                    } else if (data.status === 'failed' && !isBatchActive) {
                        document.getElementById('current-step-text').textContent = "STATUS: ❌ FALHA NA DUBLAGEM";
                        document.getElementById('current-step-text').style.color = "#ff0055";
                        document.getElementById('status-msg-detail').textContent = data.message || "Ocorreu um erro no pipeline.";
                        
                        if (!window._failedLogged) {
                            window._failedLogged = true;
                            logToTerminal("❌ ERRO NO MOTOR: " + (data.message || "Falha durante o processamento."), "error");
                        }
                        
                        const btn = document.getElementById('btn-iniciar');
                        if (btn) {
                            btn.disabled = false;
                            btn.style.opacity = '1';
                            btn.innerText = '🚀 INICIAR DUBLAGEM';
                        }
                        setTimeout(refreshProjectsList, 500);
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
            if (typeof statusInterval !== 'undefined' && statusInterval) clearInterval(statusInterval);
            statusInterval = setInterval(() => {
                loadProjectStatus(activeJobId);
            }, 1500);
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
            const gameProfile = document.getElementById('game-profile');
            if (jobIdArray && jobIdArray.length > 0) payload.job_ids = jobIdArray;
            if (manualWav) payload.parent_folder = manualWav;
            if (gameProfile) payload.game_profile = gameProfile.value;

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
                window._cachedProjects = projects;
                const selector = document.getElementById('project-selector');
                selector.innerHTML = '<option value="">SELECIONE O PROJETO...</option>' + projects.map(p => `<option value="${p.id}">${p.name || p.id}</option>`).join('');
                
                renderProjectCards(projects);

                // [v2026.AUTO_SELECT] Seleção e preparação de projetos individuais ou em lote
                selector.onchange = async () => {
                    const selected = Array.from(selector.selectedOptions).map(opt => opt.value).filter(v => v && v !== "");
                    updateSelectedBadge(selected.length);
                    
                    const btnIniciar = document.getElementById("btn-iniciar");
                    const btnContinuar = document.getElementById("btn-continuar");

                    if (selected.length === 1) {
                        const jobId = selected[0];
                        activeJobId = jobId;

                        logToTerminal(`ANALISANDO PROJETO: ${jobId}...`);
                        try {
                            const statusRes = await fetch(`http://127.0.0.1:5002/api/job-status/${jobId}`);
                            const data = await statusRes.json();

                            if (data.progress > 0 && data.progress < 100) {
                                if (btnIniciar) btnIniciar.style.display = "none";
                                if (btnContinuar) {
                                    btnContinuar.style.display = "block";
                                    btnContinuar.disabled = false;
                                    btnContinuar.style.opacity = '1';
                                }
                                logToTerminal(`SESSÃO ANTERIOR DETECTADA: ${Math.round(data.progress)}% concluído.`, 'success');
                                loadProjectStatus(jobId);
                            } else {
                                if (btnIniciar) {
                                    btnIniciar.style.display = "block";
                                    btnIniciar.disabled = false;
                                    btnIniciar.style.opacity = '1';
                                    btnIniciar.innerText = data.progress >= 100 ? '🚀 REINICIAR DUBLAGEM' : '🚀 INICIAR DUBLAGEM';
                                }
                                if (btnContinuar) btnContinuar.style.display = "none";
                                loadProjectStatus(jobId);
                            }
                        } catch(e_st) {
                            if (btnIniciar) {
                                btnIniciar.style.display = "block";
                                btnIniciar.disabled = false;
                                btnIniciar.style.opacity = '1';
                                btnIniciar.innerText = '🚀 INICIAR DUBLAGEM';
                            }
                        }
                    } else if (selected.length > 1) {
                        logToTerminal(`📦 LOTE SELECIONADO: ${selected.length} pastas marcadas para processamento simultâneo.`, 'info');
                        if (btnIniciar) {
                            btnIniciar.style.display = "block";
                            btnIniciar.disabled = false;
                            btnIniciar.style.opacity = '1';
                            btnIniciar.innerText = `🚀 INICIAR DUBLAGEM EM LOTE (${selected.length} PROJETOS)`;
                        }
                        if (btnContinuar) btnContinuar.style.display = "none";
                    } else {
                        if (btnIniciar) {
                            btnIniciar.style.display = "block";
                            btnIniciar.disabled = false;
                            btnIniciar.style.opacity = '1';
                            btnIniciar.innerText = '🚀 INICIAR DUBLAGEM';
                        }
                        if (btnContinuar) btnContinuar.style.display = "none";
                    }
                };

                // [v2026.LAST_BATCH_CHECK] Verifica se há manifesto de lote anterior para exibição do botão
                await checkLastBatchButton();

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

        // [v2026.AUTO_SYNC] Atualização silenciosa em tempo real dos cards e status do disco sem resetar seleções
        async function refreshProjectsList() {
            try {
                const res = await fetch('http://127.0.0.1:5002/api/get-projects');
                if (!res.ok) return;
                const projects = await res.json();
                window._cachedProjects = projects;

                const selector = document.getElementById('project-selector');
                if (selector) {
                    const prevSelected = Array.from(selector.selectedOptions).map(o => o.value).filter(v => v);
                    selector.innerHTML = '<option value="">SELECIONE O PROJETO...</option>' + projects.map(p => `<option value="${p.id}">${p.name || p.id}</option>`).join('');
                    prevSelected.forEach(val => {
                        const opt = Array.from(selector.options).find(o => o.value === val);
                        if (opt) opt.selected = true;
                    });
                }
                renderProjectCards(projects);
                syncCardUIFromSelector();
            } catch(e) {}
        }

        async function checkLastBatchButton() {
            try {
                const res = await fetch('http://127.0.0.1:5002/api/get-last-batch');
                const data = await res.json();
                const btnRetomar = document.getElementById('btn-retomar-fila');
                if (btnRetomar && data.has_batch && data.manifest) {
                    const count = data.manifest.folder_count || (data.manifest.jobs ? data.manifest.jobs.length : 0);
                    if (count > 0) {
                        btnRetomar.textContent = `⚡ RETOMAR ÚLTIMA FILA (${count} PASTAS DETECTADAS)`;
                        btnRetomar.style.display = "block";
                    }
                }
            } catch(e) {}
        }

        function renderProjectCards(projects) {
            const container = document.getElementById('project-cards-container');
            if (!container) return;

            if (!projects || projects.length === 0) {
                container.innerHTML = '<div style="color: #888; font-size: 0.7rem; text-align: center; padding: 15px;">Nenhum projeto encontrado. Selecione uma pasta WAV abaixo para iniciar.</div>';
                return;
            }

            container.innerHTML = projects.map(p => {
                const prog = Math.round(p.progress || 0);
                const isComplete = prog >= 100;
                const statusColor = isComplete ? '#00ff41' : (prog > 0 ? '#ffaa00' : '#00f3ff');
                const statusBg = isComplete ? 'rgba(0,255,65,0.12)' : (prog > 0 ? 'rgba(255,170,0,0.12)' : 'rgba(0,243,255,0.12)');
                const statusBorder = isComplete ? 'rgba(0,255,65,0.35)' : (prog > 0 ? 'rgba(255,170,0,0.35)' : 'rgba(0,243,255,0.35)');
                const displayName = p.folder_name || p.id || p.name;
                const etapaStr = p.etapa ? p.etapa : (isComplete ? 'CONCLUÍDO' : 'PRONTO');
                const segInfo = (p.total_seg && p.total_seg > 0) ? `${p.total_seg} falas` : '';

                let badgeText = `${prog}% • CONCLUÍDO`;
                if (prog === 0) badgeText = `PRONTO`;
                else if (prog < 100) badgeText = `${prog}% • EM ANDAMENTO`;

                return `
                    <div class="project-dossier-card" id="card-${p.id}" onclick="toggleProjectCardSelection('${p.id}')" style="background: rgba(20, 5, 10, 0.9); border: 1px solid rgba(255, 18, 79, 0.3); border-radius: 6px; padding: 12px 14px; cursor: pointer; transition: all 0.2s ease; position: relative; margin-bottom: 8px;">
                        <!-- Linha 1: Checkbox + Nome Completo do Projeto (Sem cortes) -->
                        <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 8px;">
                            <input type="checkbox" id="chk-${p.id}" style="accent-color: #00f3ff; cursor: pointer; pointer-events: none; width: 16px; height: 16px; margin-top: 2px; flex-shrink: 0;" />
                            <span style="font-size: 0.88rem; font-weight: 900; color: #fff; letter-spacing: 0.5px; word-break: break-word; line-height: 1.3; flex: 1;">
                                ${displayName}
                            </span>
                        </div>

                        <!-- Linha 2: Barra de Progresso com Glow -->
                        <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden; margin-bottom: 8px;">
                            <div style="width: ${prog}%; height: 100%; background: linear-gradient(90deg, #ff124f, ${statusColor}); box-shadow: 0 0 10px ${statusColor}; transition: 0.3s ease;"></div>
                        </div>

                        <!-- Linha 3: Etapa Detalhada Completa com Texto Ampliado -->
                        ${etapaStr ? `
                        <div style="font-size: 0.85rem; color: #00f3ff; font-weight: 800; background: rgba(0, 243, 255, 0.08); border: 1px solid rgba(0, 243, 255, 0.2); border-left: 4px solid #00f3ff; padding: 7px 10px; margin-bottom: 10px; border-radius: 4px; line-height: 1.4; word-break: break-word;">
                            <span style="color: #00f3ff; margin-right: 4px;">⚡</span><span style="color: #ffffff; font-weight: 700;">${etapaStr}</span>
                        </div>` : ''}

                        <!-- Linha 4: Metadados Completos (Data + Falas + Status) -->
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; font-size: 0.75rem;">
                            <span style="font-weight: 700; color: #fff; display: flex; align-items: center; gap: 5px;">
                                📅 <span>${p.date || 'Recente'}</span>
                            </span>
                            <div style="display: flex; gap: 6px; align-items: center;">
                                ${segInfo ? `<span style="color: #00f3ff; font-weight: 900; background: rgba(0,243,255,0.1); border: 1px solid rgba(0,243,255,0.3); padding: 2px 8px; border-radius: 3px; font-size: 0.7rem;">🗣️ ${segInfo}</span>` : ''}
                                <span style="font-size: 0.68rem; font-weight: 900; color: ${statusColor}; background: ${statusBg}; border: 1px solid ${statusBorder}; padding: 2px 8px; border-radius: 3px; letter-spacing: 0.5px;">
                                    ${badgeText}
                                </span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function toggleProjectCardSelection(jobId) {
            const selector = document.getElementById('project-selector');
            if (!selector) return;

            const opt = Array.from(selector.options).find(o => o.value === jobId);
            if (opt) {
                opt.selected = !opt.selected;
            }

            syncCardUIFromSelector();
            selector.dispatchEvent(new Event('change'));
        }

        function toggleSelectAllProjects(selectBool) {
            const selector = document.getElementById('project-selector');
            if (!selector) return;

            Array.from(selector.options).forEach(opt => {
                if (opt.value) opt.selected = selectBool;
            });

            syncCardUIFromSelector();
            selector.dispatchEvent(new Event('change'));
        }

        function syncCardUIFromSelector() {
            const selector = document.getElementById('project-selector');
            if (!selector) return;

            const selectedValues = Array.from(selector.selectedOptions).map(o => o.value);
            updateSelectedBadge(selectedValues.filter(v => v !== "").length);

            if (window._cachedProjects) {
                window._cachedProjects.forEach(p => {
                    const card = document.getElementById(`card-${p.id}`);
                    const chk = document.getElementById(`chk-${p.id}`);
                    const isSelected = selectedValues.includes(p.id);

                    if (card) {
                        if (isSelected) {
                            card.style.borderColor = '#00f3ff';
                            card.style.background = 'rgba(0, 243, 255, 0.08)';
                            card.style.boxShadow = '0 0 12px rgba(0, 243, 255, 0.3)';
                        } else {
                            card.style.borderColor = 'rgba(255, 18, 79, 0.25)';
                            card.style.background = 'rgba(20, 5, 10, 0.8)';
                            card.style.boxShadow = 'none';
                        }
                    }
                    if (chk) chk.checked = isSelected;
                });
            }
        }

        function updateSelectedBadge(count) {
            const badge = document.getElementById('selected-projects-badge');
            if (badge) {
                badge.textContent = `${count} SELECIONADO(S)`;
                if (count > 0) {
                    badge.style.color = '#00f3ff';
                    badge.style.background = 'rgba(0,243,255,0.15)';
                    badge.style.borderColor = '#00f3ff';
                } else {
                    badge.style.color = '#00ff41';
                    badge.style.background = 'rgba(0,255,65,0.1)';
                    badge.style.borderColor = 'rgba(0,255,65,0.3)';
                }
            }
        }

        async function retomarUltimaFila() {
            const btnRetomar = document.getElementById('btn-retomar-fila');
            if (btnRetomar) {
                btnRetomar.disabled = true;
                btnRetomar.style.opacity = '0.6';
                btnRetomar.textContent = '⏳ RETOMANDO FILA EM LOTE...';
            }
            logToTerminal("⚡ RETOMANDO ÚLTIMA FILA EM LOTE (SMART RESUME)...", 'info');
            try {
                const res = await fetch('http://127.0.0.1:5002/api/resume-last-batch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await res.json();
                if (data.success) {
                    logToTerminal(`✅ ${data.message}`, 'success');
                    if (data.enqueued_jobs && data.enqueued_jobs.length > 0) {
                        activeJobId = data.enqueued_jobs[0];
                    }
                    startStatusPolling();
                } else {
                    logToTerminal(`⚠️ ${data.message}`, 'error');
                    if (btnRetomar) {
                        btnRetomar.disabled = false;
                        btnRetomar.style.opacity = '1';
                    }
                }
            } catch(e) {
                logToTerminal("Falha ao comunicar com o servidor para retomar fila.", 'error');
                if (btnRetomar) {
                    btnRetomar.disabled = false;
                    btnRetomar.style.opacity = '1';
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
            startStatusPolling(); // [v2026.LIVE_HUD] Polling contínuo do Monitor HUD (1.5s)
            setInterval(updateLogs, 2000); // [v2026.REALTIME_SYNC] Sincronização em tempo real de logs (2s)
            setInterval(refreshProjectsList, 3000); // [v2026.REALTIME_CARDS] Sincronização contínua de status dos cards (3s)
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
