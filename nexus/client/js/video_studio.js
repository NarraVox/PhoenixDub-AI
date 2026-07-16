let selectedVideoPath = null;
        let activeJobId = null;
        let statusInterval = null;
        let lastLoggedMsg = "";

        async function limparCacheAtual() {
            if (!activeJobId) { alert("NENHUM PROJETO ATIVO PARA LIMPAR!"); return; }
            if (!confirm(`Isso apagará backups e arquivos temporários APENAS do projeto [${activeJobId}]. Continuar?`)) return;
            
            try {
                const res = await fetch('http://127.0.0.1:5000/api/clear_cache', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ job_id: activeJobId })
                });
                const data = await res.json();
                alert(data.message);
                logToTerminal(`LIMPEZA CONCLUÍDA: ${activeJobId}`);
            } catch(e) { logToTerminal("ERRO AO CONECTAR COM O HUB (PORTA 5000)."); }
        }

        async function selectVideo() {
            try {
                const path = await window.pywebview.api.open_file_dialog("Vídeos (*.mp4;*.mkv;*.avi;*.mov)");
                if (path) {
                    selectedVideoPath = path;
                    document.getElementById('selected-file-name').textContent = "VÍDEO: " + path.split(/[\\\\/]/).pop();
                    document.getElementById('selected-file-name').style.color = "var(--accent)";
                }
            } catch (e) { console.error("Erro seletor:", e); }
        }

        let isHoveringTerminal = false;
        document.addEventListener("DOMContentLoaded", () => {
            const terminalEl = document.getElementById('vortex-terminal');
            if(terminalEl) {
                terminalEl.addEventListener('mouseenter', () => isHoveringTerminal = true);
                terminalEl.addEventListener('mouseleave', () => isHoveringTerminal = false);
            }
        });

        function logToTerminal(msg) {
            if (!msg || msg === lastLoggedMsg) return;
            const terminal = document.getElementById('vortex-terminal');
            const now = new Date();
            const time = now.getHours().toString().padStart(2, '0') + ":" + 
                         now.getMinutes().toString().padStart(2, '0') + ":" + 
                         now.getSeconds().toString().padStart(2, '0');
            
            const div = document.createElement('div');
            div.style.marginBottom = "5px";
            div.style.borderLeft = "2px solid var(--accent)";
            div.style.paddingLeft = "10px";
            div.innerHTML = `<span style="color: var(--accent); opacity: 0.5; font-size: 0.7rem;">[${time}]</span> <span style="color: #fff;">${msg}</span>`;
            terminal.appendChild(div);
            
            if (!isHoveringTerminal) {
                terminal.scrollTop = terminal.scrollHeight;
            }
            lastLoggedMsg = msg;
        }

        let lastEtapa = "";

        async function updateUI(data) {
            document.getElementById('video-progress-area').style.display = 'block';
            
            // Lógica de Tanque Neural (Reset por Etapa)
            const tank = document.getElementById('liquid-tank');
            if (data.etapa !== lastEtapa) {
                lastEtapa = data.etapa;
                tank.style.height = '0%';
                setTimeout(() => {
                    tank.style.height = data.progress + '%';
                }, 150);
            } else {
                tank.style.height = data.progress + '%';
            }

            document.getElementById('percent-text').textContent = Math.round(data.progress) + '%';
            
            const stepText = (data.status === 'Finalizado') ? 'OPERAÇÃO CONCLUÍDA' : (data.status || 'PROCESSANDO');
            document.getElementById('current-step-text').textContent = "ETAPA: " + stepText.toUpperCase();
            document.getElementById('status-msg-detail').textContent = data.message || "Executando tarefas da pipeline...";
            
            const dynamicBar = document.getElementById('dynamic-progress-bar');
            if (dynamicBar) {
                dynamicBar.style.width = data.progress + '%';
            }
            
            if (data.tool_name) {
                document.getElementById('active-tool-badge').textContent = data.tool_name.toUpperCase();
                document.getElementById('active-tool-badge').style.background = 'var(--accent)';
            }
            if (data.current_seg && data.total_seg) {
                document.getElementById('segment-counter').textContent = `${String(data.current_seg).padStart(3, '0')} / ${String(data.total_seg).padStart(3, '0')}`;
                document.getElementById('segment-counter').style.opacity = '1';
            }

            if (data.message) logToTerminal(data.message);
            
            // Mostra o botão de editar se a transcrição já estiver disponível (etapa_idx >= 1)
            const btnEdit = document.getElementById('btn-edit-script');
            if (btnEdit) {
                if (data.etapa_idx >= 1 && activeJobId) {
                    btnEdit.style.display = 'block';
                } else {
                    btnEdit.style.display = 'none';
                }
            }
            
            // [v2026.FIX] Só finaliza se for a ÚLTIMA ETAPA (Merge Final = 5) e progress for 100
            const isLastStep = (data.status === 'Merge Final' || data.etapa_idx === 5);
            
            if (isLastStep && data.progress >= 100) {
                document.getElementById('end-time-display').textContent = new Date().toLocaleTimeString();
                clearInterval(statusInterval);
                logToTerminal("🏁 OPERAÇÃO TITAN CONCLUÍDA COM SUCESSO!");
            }
        }

        async function loadProjectStatus(jobId) {
            try {
                const res = await fetch(`http://127.0.0.1:5004/api/status/${jobId}`);
                const data = await res.json();
                if (data && data.progress !== undefined) {
                    activeJobId = jobId;
                    updateUI(data);
                    logToTerminal(`RECUPERANDO PROJETO: ${jobId}`);
                    if (data.progress < 100 || (data.etapa_idx < 5)) startStatusPolling();
                }
            } catch(e) { logToTerminal("ERRO AO CONECTAR COM O MOTOR DE STATUS."); }
        }

        async function loadHistory(retries) {
            if (typeof retries !== 'number') retries = 120;
            // Garante que o motor de vídeo está online antes de mapear os status
            try {
                const checkRes = await fetch('http://127.0.0.1:5004/api/health');
                if (!checkRes.ok) throw new Error("Motor iniciando");
                logToTerminal("✅ MOTOR DE VÍDEO CONECTADO COM SUCESSO.");
                setInterval(pollQueueStatus, 3000);
            } catch (err) {
                if (retries > 0) {
                    const attempt = 120 - retries + 1;
                    if (attempt % 5 === 0 || attempt === 1) {
                        logToTerminal(`⏳ Inicializando motor de vídeo... (${attempt * 1}s/120s)`);
                    }
                    setTimeout(() => loadHistory(retries - 1), 1000);
                    return;
                } else {
                    logToTerminal("❌ FALHA AO CONECTAR COM O MOTOR DE VÍDEO. Por favor, reinicie os motores ou recarregue a página.");
                    return;
                }
            }

            try {
                const response = await fetch('/api/list_project_files'); 
                let files = await response.json();
                
                // Filtra apenas arquivos de vídeo individuais e pastas de projeto de vídeo (que começam com 'video_')
                files = files.filter(f => f.type === 'video' || (f.type === 'folder' && f.name.startsWith('video_')));
                
                const container = document.getElementById('job-history');
                
                if (files.length === 0) {
                    container.innerHTML = '<p style="color: rgba(0, 255, 0, 0.2); font-size: 0.8rem;">NENHUM ASSET DISPONÍVEL NO BANCO.</p>';
                    return;
                }

                container.innerHTML = (await Promise.all(files.map(async f => {
                    const jobId = f.name.includes('video_') ? f.name : null;
                    let progInfo = { progress: 0, status: 'Pronto' };
                    if (jobId) {
                        try {
                            const r = await fetch(`http://127.0.0.1:5004/api/status/${jobId}`);
                            progInfo = await r.json();
                        } catch(e) {}
                    }
                    const isDone = progInfo.progress >= 100;
                    const displayDate = f.date ? new Date(f.date).toLocaleString('pt-BR') : 'ASSET DE SISTEMA';
                    
                    return `
                    <div class="card" style="cursor: pointer; border-left: 5px solid ${isDone?'#fff':'var(--accent)'};" 
                          onclick="if('${jobId}') { loadProjectStatus('${jobId}'); } else { selectedVideoPath='${f.path.replace(/\\\\/g, '/')}'; document.getElementById('selected-file-name').textContent='VÍDEO: ${f.name}'; }">
                         <div style="display: flex; align-items: center; gap: 15px;">
                             <div style="font-size: 2rem;">${f.type==='video'?'🎬':'📁'}</div>
                             <div style="flex: 1;">
                                 <div style="font-size: 0.9rem; font-weight: 800; color: #fff; margin-bottom: 5px;">${f.name.substring(0, 30)}</div>
                                 <div style="font-size: 0.65rem; color: #555; display: flex; justify-content: space-between;">
                                     <span>📅 ${displayDate}</span>
                                     <span style="color: var(--accent); font-weight: bold;">${jobId?'PROJETO IA':'NATIVO'}</span>
                                 </div>
                                 ${jobId ? `<button class="btn-continue" style="background: var(--violet); margin-top: 5px; width: 100%; border: none; padding: 5px; color: #fff; cursor: pointer; font-weight: bold; font-size: 0.6rem; letter-spacing: 1px;" onclick="event.stopPropagation(); resumeJob('${jobId}', this);">REFAZER TRADUÇÃO (MANTER TRANSCRIÇÃO)</button>` : ''}
                             </div>
                         </div>
                    </div>
                `}))).join('');
            } catch (e) {
                document.getElementById('job-history').innerHTML = '<p style="color: red; font-size: 0.8rem;">ERRO DE TELEMETRIA.</p>';
            }
        }


        async function checkStatus() {
            if (!activeJobId) return;
            try {
                const res = await fetch(`http://127.0.0.1:5004/api/status/${activeJobId}`);
                const data = await res.json();
                if (data && data.progress !== undefined) updateUI(data);
            } catch (e) { console.warn("Polling error:", e); }
        }

        function startStatusPolling() {
            clearInterval(statusInterval);
            statusInterval = setInterval(checkStatus, 2000); // 2 segundos para sincronização fluida
        }

        async function iniciarProcesso() {
            if (!selectedVideoPath) { alert("POR FAVOR, SELECIONE UM VÍDEO PRIMEIRO!"); return; }

            document.getElementById('start-time-display').textContent = new Date().toLocaleTimeString();
            document.getElementById('end-time-display').textContent = "--:--:--";
            document.getElementById('vortex-terminal').innerHTML = ""; 

            let cleanPath = selectedVideoPath.replace('file://', '').replace(/\\/g, '/');

            try {
                const res = await fetch('http://127.0.0.1:5004/api/dublar_video', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        path: cleanPath,
                        profile: 'padrao',
                        source_lang: document.getElementById('src-lang').value,
                        target_lang: document.getElementById('tgt-lang').value,
                        narrative_mode: false
                    })
                });
                const data = await res.json();
                if (data.success) {
                    activeJobId = data.job_id;
                    logToTerminal(`MOTOR TITAN 5004 CONECTADO. PROJETO: ${activeJobId}`);
                    startStatusPolling();
                } else {
                    logToTerminal("ERRO NO MOTOR: " + data.message);
                    alert("ERRO NO MOTOR: " + data.message);
                }
            } catch(e) {
                logToTerminal("ERRO: MOTOR 5004 OFFLINE.");
                alert("ERRO AO CONECTAR COM O MOTOR DE VÍDEO (PORTA 5004).");
            }
        }

        async function resumeJob(jobId, btnElement = null) {
            if (btnElement) {
                btnElement.disabled = true;
                btnElement.textContent = "PROCESSANDO...";
                btnElement.style.opacity = "0.5";
            }
            document.getElementById('start-time-display').textContent = new Date().toLocaleTimeString();
            document.getElementById('end-time-display').textContent = "--:--:--";
            document.getElementById('vortex-terminal').innerHTML = ""; 
            
            try {
                const res = await fetch('http://127.0.0.1:5004/api/resume_video', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ job_id: jobId })
                });
                const data = await res.json();
                if (data.success) {
                    activeJobId = jobId;
                    logToTerminal(`MOTOR TITAN 5004: FORÇANDO TRADUÇÃO DO PROJETO: ${jobId}`);
                    startStatusPolling();
                } else {
                    alert("Erro ao retomar o projeto.");
                }
            } catch(e) {
                alert("ERRO AO CONECTAR COM O MOTOR (PORTA 5004).");
            }
        }

        async function checkConnection() {
            try {
                const res = await fetch('/api/engine_status').catch(() => null);
                const guard = document.getElementById('conn-guard');
                if (!res) {
                    guard.style.display = 'flex';
                } else if (guard.style.display === 'flex') {
                    location.reload();
                }
            } catch(e) {}
        }
        setInterval(checkConnection, 10000); // Sincronizado com telemetria Mega

        let localProjectSegments = [];
        let localProjectSpeakers = [];

        async function openScriptEditor() {
            if (!activeJobId) return;
            
            // Pausa temporariamente o polling de status enquanto o usuário edita
            clearInterval(statusInterval);
            
            logToTerminal("Carregando roteiro e mapeamento de oradores...");
            try {
                const res = await fetch(`http://127.0.0.1:5004/api/project/${activeJobId}/segments`);
                const data = await res.json();
                
                if (data.success) {
                    localProjectSegments = data.segments;
                    localProjectSpeakers = data.speakers;
                    
                    // Renderiza as linhas do editor
                    const tbody = document.getElementById('script-editor-rows');
                    tbody.innerHTML = '';
                    
                    localProjectSegments.forEach((seg, idx) => {
                        const tr = document.createElement('tr');
                        tr.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
                        tr.style.background = idx % 2 === 0 ? "rgba(0,0,0,0.2)" : "rgba(255,255,255,0.01)";
                        
                        // Formatação do tempo
                        const start = seg.start.toFixed(2);
                        const end = seg.end.toFixed(2);
                        
                        // Geração de opções do dropdown de voz
                        let optionsHtml = '';
                        localProjectSpeakers.forEach(spk => {
                            const isSelected = seg.speaker === spk ? 'selected' : '';
                            optionsHtml += `<option value="${spk}" ${isSelected}>${spk.replace('voz_', '').toUpperCase()}</option>`;
                        });
                        
                        tr.innerHTML = `
                            <td style="padding: 15px; font-family: monospace; color: var(--accent); font-weight: bold; font-size: 0.75rem;">${seg.id}</td>
                            <td style="padding: 15px; font-family: monospace; font-size: 0.75rem; color: #aaa;">${start}s - ${end}s</td>
                            <td style="padding: 15px;">
                                <input type="text" id="edit-text-${idx}" value="${seg.text.replace(/"/g, '&quot;')}" style="margin: 0; background: rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1); color: #fff; font-size: 0.8rem; padding: 8px; width: 100%; box-sizing: border-box;">
                            </td>
                            <td style="padding: 15px;">
                                <select id="edit-speaker-${idx}" style="margin: 0; background: rgba(0,0,0,0.7); border: 1px solid var(--border); color: var(--accent); font-weight: bold; font-size: 0.75rem; padding: 8px; width: 100%; box-sizing: border-box;">
                                    ${optionsHtml}
                                </select>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                    
                    document.getElementById('script-editor-modal').style.display = 'block';
                    logToTerminal("Roteiro carregado com sucesso no Alinhador!");
                } else {
                    alert("Erro ao carregar dados do roteiro: " + data.message);
                }
            } catch (e) {
                alert("Falha ao se conectar com o motor de roteiro.");
            }
        }

        function closeScriptEditor() {
            document.getElementById('script-editor-modal').style.display = 'none';
            // Retoma o polling de status
            startStatusPolling();
        }

        async function saveEditedScript() {
            if (!activeJobId) return;
            
            // Coleta os novos valores da tabela
            const updatedSegments = localProjectSegments.map((seg, idx) => {
                const textInput = document.getElementById(`edit-text-${idx}`);
                const speakerSelect = document.getElementById(`edit-speaker-${idx}`);
                
                return {
                    ...seg,
                    text: textInput.value,
                    speaker: speakerSelect.value
                };
            });
            
            logToTerminal("Enviando alterações de vozes e reconstruindo pastas de áudio...");
            
            try {
                const res = await fetch(`http://127.0.0.1:5004/api/project/${activeJobId}/segments`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ segments: updatedSegments })
                });
                
                const data = await res.json();
                if (data.success) {
                    logToTerminal("✅ ROTEIRO E FOLDERS DE VOZ RECONSTRUÍDOS COM SUCESSO!");
                    alert("Roteiro atualizado com sucesso! As amostras de áudio foram reorganizadas fisicamente sem contaminação.");
                    closeScriptEditor();
                } else {
                    alert("Erro ao salvar roteiro: " + data.message);
                }
            } catch (e) {
                alert("Falha de rede ao salvar as edições do roteiro.");
            }
        }

        let activeMode = 'single';
        let queueInterval = null;

        function switchMode(mode) {
            activeMode = mode;
            
            // Toggle active state on buttons
            document.getElementById('btn-mode-single').classList.toggle('active', mode === 'single');
            document.getElementById('btn-mode-batch').classList.toggle('active', mode === 'batch');
            
            // Toggle button styles dynamically
            if (mode === 'single') {
                document.getElementById('btn-mode-single').style.background = 'var(--accent)';
                document.getElementById('btn-mode-single').style.color = '#000';
                document.getElementById('btn-mode-batch').style.background = 'transparent';
                document.getElementById('btn-mode-batch').style.color = '#fff';
                
                document.getElementById('container-single').style.display = 'block';
                document.getElementById('container-batch').style.display = 'none';
                
                document.getElementById('job-history').style.display = 'block';
                document.getElementById('queue-history').style.display = 'none';
                document.getElementById('history-title').textContent = 'DOSSIÊS RECENTES';
            } else {
                document.getElementById('btn-mode-batch').style.background = 'var(--accent)';
                document.getElementById('btn-mode-batch').style.color = '#000';
                document.getElementById('btn-mode-single').style.background = 'transparent';
                document.getElementById('btn-mode-single').style.color = '#fff';
                
                document.getElementById('container-single').style.display = 'none';
                document.getElementById('container-batch').style.display = 'block';
                
                document.getElementById('job-history').style.display = 'none';
                document.getElementById('queue-history').style.display = 'block';
                document.getElementById('history-title').textContent = 'FILA EM LOTE';
                
                // Carrega status da fila imediatamente
                pollQueueStatus();
            }
        }

        async function addBatchFiles() {
            try {
                // Abre seletor com allow_multiple=True (segundo parâmetro como true)
                const paths = await window.pywebview.api.open_file_dialog("Vídeos (*.mp4;*.mkv;*.avi;*.mov)", true);
                if (paths && paths.length > 0) {
                    logToTerminal(`Adicionando ${paths.length} arquivos à fila...`);
                    
                    // Adiciona cada arquivo na fila do backend
                    for (let path of paths) {
                        let cleanPath = path.replace('file://', '').replace(/\\/g, '/');
                        const res = await fetch('http://127.0.0.1:5004/api/queue/add', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                path: cleanPath,
                                source_lang: document.getElementById('batch-src-lang').value,
                                target_lang: document.getElementById('batch-tgt-lang').value
                            })
                        });
                        const data = await res.json();
                        if (data.success) {
                            logToTerminal(`Fila: ${path.split(/[\\\\/]/).pop()} enfileirado.`);
                        }
                    }
                    pollQueueStatus();
                }
            } catch (e) {
                console.error("Erro ao abrir diálogo ou adicionar à fila:", e);
            }
        }

        async function openWatchdogFolder() {
            try {
                await fetch('http://127.0.0.1:5004/api/queue/open_watchdog', { method: 'POST' });
                logToTerminal("Abrindo pasta do Watchdog no Windows Explorer...");
            } catch(e) {
                logToTerminal("Erro ao solicitar abertura da pasta Watchdog.");
            }
        }

        async function controlQueue(action, itemId = null) {
            try {
                const payload = { action };
                if (itemId) payload.item_id = itemId;
                
                const res = await fetch('http://127.0.0.1:5004/api/queue/action', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    logToTerminal(`Comando enviado à fila: ${action.toUpperCase()}`);
                    pollQueueStatus();
                } else {
                    alert("Erro no comando da fila: " + data.message);
                }
            } catch(e) {
                logToTerminal("Erro ao conectar com o gerenciador de fila.");
            }
        }

        function getStageName(stageCode) {
            const names = {
                'Separation': 'Etapa 1/5 - Separando Voz/Fundo',
                'ASR': 'Etapa 2/5 - Transcrição & Diarização',
                'Translation': 'Etapa 3/5 - Tradução Agente',
                'TTS': 'Etapa 4/5 - Geração de Voz',
                'Merge': 'Etapa 5/5 - Masterização Final'
            };
            return names[stageCode] || 'Aguardando na fila';
        }

        function updateQueueUI(data) {
            const items = data.items || [];
            const status = data.status || 'idle';
            
            // Atualiza estatísticas do lote
            const pendingCount = items.filter(i => i.status === 'pending').length;
            const processingCount = items.filter(i => i.status === 'processing').length;
            const completedCount = items.filter(i => i.status === 'completed').length;
            const failedCount = items.filter(i => i.status === 'failed').length;
            
            const statsText = `CONCLUÍDOS: ${completedCount}/${items.length} | FALHAS: ${failedCount}`;
            document.getElementById('batch-stats-text').textContent = statsText;
            
            // Toggle botões de iniciar/pausar
            if (status === 'processing') {
                document.getElementById('btn-queue-start').style.display = 'none';
                document.getElementById('btn-queue-pause').style.display = 'block';
            } else {
                document.getElementById('btn-queue-start').style.display = 'block';
                document.getElementById('btn-queue-pause').style.display = 'none';
            }
            
            // Renderiza a lista de cards da fila
            const container = document.getElementById('queue-history');
            if (items.length === 0) {
                container.innerHTML = '<div style="color: rgba(0, 255, 0, 0.2); font-size: 0.8rem; text-align: center; margin-top: 50px;">FILA VAZIA.<br><span style="font-size:0.6rem; opacity:0.6;">Coloque arquivos na pasta input do Watchdog ou adicione vídeos acima.</span></div>';
                return;
            }
            
            container.innerHTML = items.map(item => {
                const isProcessing = item.status === 'processing';
                const isDone = item.status === 'completed';
                const isFailed = item.status === 'failed';
                
                let borderCol = 'rgba(255,255,255,0.1)';
                let statusBadgeCol = 'gray';
                if (isProcessing) { borderCol = 'var(--accent)'; statusBadgeCol = 'var(--accent)'; }
                if (isDone) { borderCol = '#00ff41'; statusBadgeCol = '#00ff41'; }
                if (isFailed) { borderCol = '#ff4f4f'; statusBadgeCol = '#ff4f4f'; }
                
                const stageLabel = getStageName(item.stage);
                
                return `
                <div class="card" style="border-left: 5px solid ${borderCol}; margin-bottom: 8px; padding: 10px; background: rgba(5,10,30,0.5); border: 1px solid rgba(0,243,255,0.05); position: relative;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 5px;">
                        <div style="font-size: 0.75rem; font-weight: bold; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; width: 200px;">
                            ${item.video_name}
                        </div>
                        <button style="background: transparent; border: none; color: #ff4f4f; font-size: 0.7rem; cursor: pointer; font-weight: bold;" onclick="controlQueue('remove_item', '${item.id}')">✕</button>
                    </div>
                    <div style="font-size: 0.6rem; color: #aaa; margin-bottom: 6px;">
                        ${stageLabel} ${isProcessing ? `(${item.progress}%)` : ''}
                    </div>
                    
                    ${isProcessing ? `
                    <div style="width: 100%; height: 3px; background: rgba(255,255,255,0.05); overflow: hidden; margin-bottom: 4px;">
                        <div style="width: ${item.progress}%; height: 100%; background: var(--accent); box-shadow: 0 0 10px var(--accent);"></div>
                    </div>
                    ` : ''}
                    
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                        <span style="font-size: 0.55rem; color: #555;">ID: ${item.id}</span>
                        <div style="font-size: 0.55rem; font-weight: 900; color: ${statusBadgeCol}; text-transform: uppercase; letter-spacing: 1px;">
                            ${item.status}
                        </div>
                    </div>
                </div>
                `;
            }).join('');
            
            // Se a fila estiver ativamente processando e houver um item ativo, atualiza o progresso no tanque neural principal
            // [v2026.QUEUE_FIX] Usa o current_item_id fornecido pela API em vez do primeiro 'processing' para não travar no item 1
            const activeItem = items.find(i => i.id === data.current_item_id);
            if (activeItem) {
                const activeIndex = items.findIndex(i => i.id === data.current_item_id) + 1;
                const totalItems = items.length;
                const queueCounter = activeIndex > 0 ? ` (VÍDEO ${activeIndex} DE ${totalItems})` : '';
                
                const tankData = {
                    progress: activeItem.progress,
                    status: getStageName(activeItem.stage) + queueCounter,
                    message: activeItem.message || 'Processando...',
                    etapa_idx: activeItem.stage === 'Separation' ? 0 : activeItem.stage === 'ASR' ? 1 : activeItem.stage === 'Translation' ? 2 : activeItem.stage === 'TTS' ? 4 : activeItem.stage === 'Merge' ? 5 : 0
                };
                document.getElementById('video-progress-area').style.display = 'block';
                document.getElementById('percent-text').textContent = Math.round(tankData.progress) + '%';
                document.getElementById('liquid-tank').style.height = tankData.progress + '%';
                
                // Exibe a etapa em letras garrafais no centro da tela abaixo da porcentagem
                document.getElementById('current-step-text').textContent = tankData.status.toUpperCase();
                document.getElementById('status-msg-detail').textContent = tankData.message;
                
                // Sincroniza o dynamic-progress-bar se ele existir
                const dynamicBar = document.getElementById('dynamic-progress-bar');
                if (dynamicBar) {
                    dynamicBar.style.width = tankData.progress + '%';
                }
            }
        }

        async function pollQueueStatus() {
            try {
                const res = await fetch('http://127.0.0.1:5004/api/queue/status');
                const data = await res.json();
                updateQueueUI(data);
            } catch(e) {
                console.warn("Queue polling error:", e);
            }
        }

        window.onload = loadHistory;