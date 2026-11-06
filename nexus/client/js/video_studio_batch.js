// NarraVox Studios - Video Studio Batch & Queue Engine
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
