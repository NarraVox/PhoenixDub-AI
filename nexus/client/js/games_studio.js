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
                const result = await window.pywebview.api.open_folder_dialog();
                if (result) {
                    document.getElementById(targetId).value = result;
                    logToTerminal(`REPOSITÓRIO SELECIONADO: ${result.split(/[\\\\/]/).pop()}`, 'success');
                    
                    // [v2026.PREVIEW] Busca confirmação visual dos arquivos na pasta
                    try {
                        const previewRes = await fetch('http://127.0.0.1:5002/api/preview-folder', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ path: result })
                        });
                        const previewData = await previewRes.json();
                        
                        if (previewData.success) {
                            const previewArea = document.getElementById('folder-preview-info');
                            previewArea.style.display = 'block';
                            previewArea.innerHTML = `
                                <div style="color: #00ff41; font-size: 0.6rem; font-weight: 900; margin-top: 10px; border-left: 2px solid #00ff41; padding-left: 10px;">
                                    ✅ CONFIRMADO: ${previewData.count} ARQUIVOS DETECTADOS<br>
                                    <span style="opacity: 0.6; font-size: 0.5rem;">AMOSTRA: ${previewData.sample.join(', ')}...</span>
                                </div>
                            `;
                            logToTerminal(`SCANNER: ${previewData.count} arquivos de áudio validados na pasta.`, 'success');
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
                    
                    const stepText = (data.status === 'completed') ? 'OPERAÇÃO CONCLUÍDA' : (data.etapa ? data.etapa.toUpperCase() : 'PROCESSANDO');
                    document.getElementById('current-step-text').textContent = "STATUS: " + stepText;
                    document.getElementById('status-msg-detail').textContent = data.subetapa || data.message || "SINCRONIZANDO...";
                    
                    // NOVA TELEMETRIA MONUMENTAL
                    if (data.tool_name) {
                        document.getElementById('active-tool-badge').textContent = data.tool_name.toUpperCase();
                        document.getElementById('active-tool-badge').style.background = 'var(--accent)';
                    }
                    if (data.current_seg && data.total_seg) {
                        document.getElementById('segment-counter').textContent = `${String(data.current_seg).padStart(3, '0')} / ${String(data.total_seg).padStart(3, '0')}`;
                        document.getElementById('segment-counter').style.opacity = '1';
                    }
                    if (data.tempo_decorrido) {
                        document.getElementById('titan-timer').textContent = data.tempo_decorrido;
                        document.getElementById('titan-timer').style.color = "#00ff41"; // Verde quando ativo
                    }
                }
            } catch(e) { console.error("Erro status:", e); }
        }

        function startStatusPolling() {
            clearInterval(statusInterval);
            statusInterval = setInterval(() => {
                if (activeJobId) loadProjectStatus(activeJobId);
            }, 2000); // [v2026.REALTIME_SYNC] Sincronizado 2s para resposta imediata UI
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
            } else if (action === 'dublar') {
                const srcLang = document.getElementById('src-lang').value;
                const targetLang = document.getElementById('target-lang').value;
                const skipLqa = true;
                url = 'http://127.0.0.1:5002/dublar_jogos';
                const fd = new FormData();
                fd.append('job_id', projectId);
                fd.append('game_profile', profile);
                fd.append('source_lang', srcLang);
                fd.append('target_lang', targetLang);
                fd.append('skip_lqa', 'true');
                if (manualWav) fd.append('manual_wav_path', manualWav);
                
                try {
                    const res = await fetch(url, { method: 'POST', body: fd });
                    const data = await res.json();
                    if (data.success) {
                        activeJobId = data.job_id || projectId;
                        startStatusPolling();
                        logToTerminal(`PROTOCOLO LANÇADO: DUBLAGEM INICIADA!`, 'success');
                    } else {
                        logToTerminal(`FALHA NO MOTOR: ${data.message}`, 'error');
                    }
                    return;
                } catch(e) { logToTerminal("Falha ao conectar com o motor de jogos.", 'error'); return; }
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

        async function loadProjects(retries) {
            if (typeof retries !== 'number') retries = 120;
            try {
                const checkRes = await fetch('http://127.0.0.1:5002/api/health');
                if (!checkRes.ok) throw new Error("Motor iniciando");
                
                logToTerminal("✅ MOTOR DE JOGOS CONECTADO COM SUCESSO.", 'success');
                const overlay = document.getElementById('engine-loader-overlay');
                if (overlay) overlay.style.display = 'none';
                
                const res = await fetch('http://127.0.0.1:5002/api/get-projects');
                const projects = await res.json();
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