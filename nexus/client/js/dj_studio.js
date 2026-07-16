// --- [v2026] MOTOR VISUAL PREMIUM DO VINIL & CANVAS ---
let canvas, ctx;
let animationId;
let currentEnergy = 0.1;
let isAudioPlaying = false;

function initVisualizer() {
    canvas = document.getElementById('visualizer-canvas');
    if(!canvas) return;
    ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    
    // Configura o vinil para iniciar pausado
    const vinyl = document.querySelector('.turntable-vinyl');
    if(vinyl) {
        vinyl.style.animationPlayState = 'paused';
    }
    
    animate();
}

function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = 180;
    const bars = 60;
    
    ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent');
    ctx.lineWidth = 3;
    
    // Se o áudio estiver tocando, vibra intensamente, se não, faz uma vibração bem sutil
    const multiplier = isAudioPlaying ? 1.0 : 0.05;
    
    for (let i = 0; i < bars; i++) {
        const angle = (i / bars) * Math.PI * 2;
        const amplitude = 5 + (Math.random() * 45 * multiplier);
        const x1 = centerX + Math.cos(angle) * radius;
        const y1 = centerY + Math.sin(angle) * radius;
        const x2 = centerX + Math.cos(angle) * (radius + amplitude);
        const y2 = centerY + Math.sin(angle) * (radius + amplitude);
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    }
    animationId = requestAnimationFrame(animate);
}

// Configuração dos controles de áudio
const audioPlayer = document.getElementById('audio-player');
const vinylElement = document.querySelector('.turntable-vinyl');

if(audioPlayer) {
    audioPlayer.addEventListener('play', () => {
        isAudioPlaying = true;
        if(vinylElement) {
            vinylElement.style.animationPlayState = 'running';
            vinylElement.style.animationDuration = '3s';
        }
        document.getElementById('system-status').innerText = "TOCANDO MÚSICA MASTERIZADA";
    });
    
    audioPlayer.addEventListener('pause', () => {
        isAudioPlaying = false;
        if(vinylElement) {
            vinylElement.style.animationPlayState = 'paused';
        }
        document.getElementById('system-status').innerText = "PLAYBACK PAUSADO";
    });
    
    audioPlayer.addEventListener('ended', () => {
        isAudioPlaying = false;
        if(vinylElement) {
            vinylElement.style.animationPlayState = 'paused';
        }
        document.getElementById('system-status').innerText = "SYSTEMS READY // IDLE";
    });
}

// --- CONSOLE LOG ---
let lastMessage = "";
function logBrain(msg) {
    if (msg === lastMessage) return; 
    lastMessage = msg;
    
    const now = new Date();
    const time = now.getHours().toString().padStart(2, '0') + ":" + 
                 now.getMinutes().toString().padStart(2, '0') + ":" + 
                 now.getSeconds().toString().padStart(2, '0');

    const log = document.getElementById('brain-log');
    if (!log) return;
    
    let color = "#00ff41"; 
    if (msg.includes("✅")) color = "#4ade80"; 
    if (msg.includes("⚠️") || msg.includes("❌")) color = "#f87171"; 
    if (msg.includes("[MASTER]")) color = "#ffaa00"; 
    if (msg.includes("[VRAM]")) color = "#00d4ff"; 
    if (msg.includes("[ACE-STEP]")) color = "#ff00ff"; 

    const cleanMsg = msg.replace(/\n/g, "<br>");
    log.innerHTML += `<div style="margin-bottom:6px; line-height:1.4; color:${color}; font-size:0.75rem;">
                        <span style="color:#666; font-family:monospace; font-size:0.9em">[${time}]</span> > ${cleanMsg}
                      </div>`;
    log.scrollTop = log.scrollHeight;
}

// --- CONTROLES DE INTERFACE & LOCKDOWN ---
let isLocked = false;
function setLockdown(locked) {
    isLocked = locked;
    
    const elements = [
        document.querySelector('.btn-ignition'),
        document.getElementById('song-title'),
        document.getElementById('song-style'),
        document.getElementById('song-lyrics'),
        document.querySelector('button[onclick="loadGeneratedSongs()"]')
    ];
    
    elements.forEach(el => {
        if (el) {
            el.disabled = locked;
            el.style.opacity = locked ? "0.3" : "1";
            el.style.pointerEvents = locked ? "none" : "auto";
        }
    });
}

// --- GERAR MÚSICA ---
let monitorInterval = null;
async function generateMusic() {
    if (isLocked) return;
    
    const title = document.getElementById('song-title').value.trim();
    const mode = document.getElementById('generation-mode').value;
    const style = (mode === 'text2music') ? document.getElementById('song-style').value.trim() : "";
    const lyrics = document.getElementById('song-lyrics').value.trim();
    const sourceAudio = document.getElementById('source-audio-select').value;
    const coverStrength = parseFloat(document.getElementById('cover-strength').value);
    const extendDuration = parseInt(document.getElementById('extend-duration').value);
    const enableMastering = document.getElementById('enable-mastering') ? document.getElementById('enable-mastering').checked : true;
    const upscaleSteps = parseInt(document.getElementById('upscale-steps')?.value || 25);
    const steps = parseInt(document.getElementById('gen-steps')?.value || 50);
    const cfgScale = parseFloat(document.getElementById('gen-cfg')?.value || 4.0);
    const duration = parseInt(document.getElementById('gen-duration')?.value || 180);
    const batchCount = parseInt(document.getElementById('batch-count')?.value || 1);
    if (!title) {
        logBrain("⚠️ INSIRA O NOME DA MÚSICA!");
        alert("Por favor, preencha o Nome da Música!");
        return;
    }
    if (mode === 'text2music' && !style) {
        logBrain("⚠️ INSIRA O ESTILO DA MÚSICA!");
        alert("Por favor, preencha o Estilo Musical!");
        return;
    }
    
    if (mode !== 'text2music' && !sourceAudio) {
        logBrain("⚠️ SELECIONE UMA MÚSICA DE ORIGEM!");
        alert("Por favor, selecione uma música base de origem!");
        return;
    }
    
    try {
        setLockdown(true);
        resetFxLights();
        
        logBrain(`🚀 INICIANDO GERAÇÃO (${mode.toUpperCase()}): "${title}" | Qtd: ${batchCount} | Steps: ${steps} | Duração: ${duration}s | Upscale Steps: ${upscaleSteps}`);
        document.querySelector('.btn-ignition').innerText = "PREPARANDO...";
        
        // Dispara a requisição de geração
        const response = await fetch('http://127.0.0.1:5005/api/generate_music', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                title: title,
                style: style,
                lyrics: lyrics,
                mode: mode,
                source_audio: sourceAudio,
                cover_strength: coverStrength,
                extend_duration: extendDuration,
                enable_mastering: enableMastering,
                upscale_steps: upscaleSteps,
                steps: steps,
                cfg_scale: cfgScale,
                duration: duration,
                batch_count: batchCount
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            logBrain(`❌ ERRO: ${data.error || "Falha na inicialização da geração"}`);
            setLockdown(false);
            document.querySelector('.btn-ignition').innerText = "⚡ GERAR MÚSICA POR IA";
            return;
        }
        
        logBrain("⚡ PROCESSO INICIADO COM SUCESSO. INICIANDO MONITORAMENTO...");
        startMonitoringProgress();
        
    } catch(e) {
        logBrain("❌ ERRO CONEXÃO: Não foi possível contatar o servidor.");
        setLockdown(false);
        document.querySelector('.btn-ignition').innerText = "⚡ GERAR MÚSICA POR IA";
    }
}

// --- MONITORAMENTO DE PROGRESSO ---
function startMonitoringProgress() {
    if (monitorInterval) clearInterval(monitorInterval);
    let logsPrintedCount = 0;
    
    // Ativa luzes de forma progressiva com base no status do backend
    monitorInterval = setInterval(async () => {
        try {
            const res = await fetch('http://127.0.0.1:5005/api/get_job_status');
            const status = await res.json();
            
            // Sincronia de Logs (Evita duplicados filtrando apenas novas mensagens)
            if (status.logs && status.logs.length > logsPrintedCount) {
                const newLogs = status.logs.slice(logsPrintedCount);
                newLogs.forEach(msg => logBrain(msg));
                logsPrintedCount = status.logs.length;
            }
            
            const currentTask = status.current_task || "";
            const isBusy = status.worker_busy === true;
            
            if (currentTask) {
                document.getElementById('system-status').innerText = `STATUS: ${currentTask}`;
                document.getElementById('now-playing').innerText = currentTask.toUpperCase();
                
                // Mapeamento de luzes de efeitos
                updateFxLights(currentTask);
                
                // Atualização da barra de progresso
                const pctMatch = currentTask.match(/(\d+)%/);
                if (pctMatch) {
                    document.getElementById('progress-fill').style.width = pctMatch[1] + '%';
                }
            }
            
            if (!isBusy) {
                // Terminou
                clearInterval(monitorInterval);
                monitorInterval = null;
                setLockdown(false);
                
                document.querySelector('.btn-ignition').innerText = "⚡ GERAR MÚSICA POR IA";
                document.getElementById('system-status').innerText = "GERAÇÃO CONCLUÍDA COM SUCESSO!";
                document.getElementById('now-playing').innerText = "STANDBY";
                document.getElementById('progress-fill').style.width = '100%';
                
                // Ativa a luz de concluído
                resetFxLights();
                document.getElementById('fx-completed').classList.add('active');
                
                logBrain("✅ PROCESSO DE GERAÇÃO E MASTERIZAÇÃO FINALIZADO!");
                
                // Recarrega a lista de músicas
                loadGeneratedSongs();
                
                // Carrega a música gerada no player
                if (status.last_generated_song) {
                    playSong(status.last_generated_song);
                }
            }
        } catch(e) {
            console.error("Erro no polling de status:", e);
        }
    }, 800); // [v2026.REALTIME] Reduzido de 1500ms → 800ms (logs vêm da RAM agora)
}

// Gerenciador de luzes LED de progresso
function updateFxLights(task) {
    resetFxLights();
    
    if (task.includes("Geração") || task.includes("ACE-Step") || task.includes("Diffusion")) {
        document.getElementById('fx-generation').classList.add('active');
    }
    else if (task.includes("Unload") || task.includes("Descarregando") || task.includes("VRAM")) {
        document.getElementById('fx-vram-purge').classList.add('active');
    }
    else if (task.includes("Masterização") || task.includes("FFmpeg") || task.includes("Polimento")) {
        document.getElementById('fx-mastering').classList.add('active');
    }
}

function resetFxLights() {
    const lights = ['fx-generation', 'fx-vram-purge', 'fx-mastering', 'fx-completed'];
    lights.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.remove('active');
    });
}

// --- HISTÓRICO DE MÚSICAS GERADAS ---
let globalSongsList = [];

function toggleGenerationMode() {
    const mode = document.getElementById('generation-mode').value;
    const container = document.getElementById('source-audio-container');
    const coverContainer = document.getElementById('cover-strength-container');
    const extendContainer = document.getElementById('extend-time-container');
    const styleInput = document.getElementById('song-style');
    
    if (mode === 'text2music') {
        container.style.display = 'none';
        coverContainer.style.display = 'none';
        extendContainer.style.display = 'none';
        if (styleInput) {
            styleInput.disabled = false;
            styleInput.style.opacity = '1';
            styleInput.placeholder = "Ex: Arabic Deep House, Dark Arabic Bass House";
        }
    } else {
        container.style.display = 'block';
        if (styleInput) {
            styleInput.disabled = true;
            styleInput.style.opacity = '0.4';
            styleInput.placeholder = "Ignorado (estilo herdado automaticamente do áudio original)";
        }
        
        const select = document.getElementById('source-audio-select');
        select.innerHTML = '';
        if (globalSongsList.length === 0) {
            select.innerHTML = '<option value="">(Nenhuma música no histórico)</option>';
        } else {
            globalSongsList.forEach(song => {
                select.innerHTML += `<option value="${song.filename}">${song.title}</option>`;
            });
        }
        
        if (mode === 'cover') {
            coverContainer.style.display = 'block';
            extendContainer.style.display = 'none';
        } else if (mode === 'extend') {
            coverContainer.style.display = 'none';
            extendContainer.style.display = 'block';
        }
    }
}

async function loadGeneratedSongs() {
    try {
        const res = await fetch('http://127.0.0.1:5005/api/list_uploads'); // Reutiliza endpoint para listar arquivos
        const data = await res.json();
        
        const list = document.getElementById('track-list');
        list.innerHTML = '';
        
        const resSongs = await fetch('http://127.0.0.1:5005/api/list_generated_songs');
        const songsData = await resSongs.json();
        
        globalSongsList = songsData.songs || [];
        
        if (globalSongsList.length === 0) {
            list.innerHTML = '<div class="track-item" style="font-size:0.6rem; opacity:0.5;">Nenhuma música criada localmente.</div>';
            return;
        }
        
        globalSongsList.forEach(song => {
            const item = document.createElement('div');
            item.className = 'track-item';
            
            // Verifica se a música é masterizada
            const isMastered = song.mastered !== false;
            
            let masterButtonHtml = '';
            let badgeHtml = '<span class="badge mastered">Hi-Fi</span>';
            
            if (!isMastered) {
                badgeHtml = '<span class="badge raw">Normal</span>';
                masterButtonHtml = `
                    <button class="btn-track-master" onclick="event.stopPropagation(); masterSong('${song.filename}')" title="Masterizar áudio com AudioSR (Hi-Fi)">
                        ✨ MASTERIZAR
                    </button>
                `;
            }
            
            item.innerHTML = `
                <div style="flex:1; min-width:0;" onclick="playSong('${song.filename}')">
                    <div class="track-name" style="text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">
                        🎵 ${song.title} ${badgeHtml}
                    </div>
                    <div class="track-meta"><span>${song.style}</span> <span>${song.date ? song.date.split(' ')[0] : ''}</span></div>
                </div>
                ${masterButtonHtml}
            `;
            
            list.appendChild(item);
        });
        
        if (document.getElementById('generation-mode').value !== 'text2music') {
            toggleGenerationMode();
        }
        
        logBrain(`HISTÓRICO: ${globalSongsList.length} MÚSICAS CARREGADAS.`);
    } catch(e) {
        console.error("Erro ao listar músicas:", e);
    }
}

// Masterizar uma música específica sob demanda
async function masterSong(filename) {
    if (isLocked) return;
    
    if (!confirm("Deseja aplicar a masterização neural Hi-Fi (AudioSR) nesta música agora? Isso leva cerca de 20-30 segundos.")) {
        return;
    }
    
    try {
        setLockdown(true);
        resetFxLights();
        
        logBrain(`✨ INICIANDO MASTERIZAÇÃO SOB DEMANDA: "${filename}"`);
        document.querySelector('.btn-ignition').innerText = "MASTERIZANDO...";
        
        const response = await fetch('http://127.0.0.1:5005/api/master_song', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ filename: filename })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            logBrain(`❌ ERRO: ${data.error || "Falha ao iniciar masterização"}`);
            setLockdown(false);
            document.querySelector('.btn-ignition').innerText = "⚡ GERAR MÚSICA POR IA";
            return;
        }
        
        logBrain("⚡ PROCESSANDO MASTERIZAÇÃO. MONITORANDO EM TEMPO REAL...");
        startMonitoringProgress();
        
    } catch(e) {
        logBrain("❌ ERRO CONEXÃO: Não foi possível contatar o servidor.");
        setLockdown(false);
        document.querySelector('.btn-ignition').innerText = "⚡ GERAR MÚSICA POR IA";
    }
}

// Tocar uma música do histórico
function playSong(filename) {
    const playerContainer = document.getElementById('player-container');
    const audioPlayer = document.getElementById('audio-player');
    const nowPlaying = document.getElementById('now-playing');
    
    if(!audioPlayer) return;
    
    // O backend serve os arquivos em http://127.0.0.1:5005/generated/filename
    const url = `http://127.0.0.1:5005/generated/${filename}`;
    
    audioPlayer.src = url;
    if(playerContainer) playerContainer.style.display = 'block';
    
    // Limpa título de exibição (tirando underscore e extensão)
    const cleanTitle = filename.replace(/_/g, ' ').replace('.mp3', '').toUpperCase();
    nowPlaying.innerText = `REPRODUZINDO: ${cleanTitle}`;
    
    audioPlayer.play().catch(e => {
        logBrain("⚠️ Falha ao iniciar reprodução automática.");
    });
}

// Enviar áudio local para a pasta de uploads do backend
async function uploadLocalAudio() {
    const fileInput = document.getElementById('local-audio-file');
    if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        logBrain("⚠️ SELECIONE UM ARQUIVO DE ÁUDIO NO SEU COMPUTADOR!");
        alert("Por favor, selecione um arquivo de áudio local antes de carregar.");
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('audio', file);
    
    logBrain(`⏳ CARREGANDO ÁUDIO DO PC: "${file.name}"...`);
    
    try {
        const response = await fetch('http://127.0.0.1:5005/api/upload_audio_file', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.filename) {
            logBrain(`✅ ÁUDIO CARREGADO COM SUCESSO: "${data.filename}"`);
            
            // Adiciona a música carregada no select de áudio base e a seleciona
            const select = document.getElementById('source-audio-select');
            if (select) {
                let exists = false;
                for (let i = 0; i < select.options.length; i++) {
                    if (select.options[i].value === data.filename) {
                        select.selectedIndex = i;
                        exists = true;
                        break;
                    }
                }
                
                if (!exists) {
                    const option = document.createElement('option');
                    option.value = data.filename;
                    option.text = `📁 LOCAL: ${file.name}`;
                    select.appendChild(option);
                    select.value = data.filename;
                }
            }
            alert(`Áudio "${file.name}" carregado com sucesso! Agora você pode gerar o seu remix.`);
        } else {
            logBrain(`❌ ERRO NO UPLOAD: ${data.error || 'Falha ao processar o arquivo.'}`);
            alert(`Erro no upload: ${data.error || 'Falha ao processar o arquivo.'}`);
        }
    } catch(e) {
        logBrain("❌ ERRO CONEXÃO: Não foi possível realizar o upload do arquivo.");
        alert("Não foi possível conectar com o servidor para realizar o upload.");
    }
}

// --- COMANDOS DO SISTEMA ---
async function stopAndRefresh() {
    logBrain("🛑 INTERROMPENDO MOTORES DE GERAÇÃO...");
    try {
        await fetch('http://127.0.0.1:5005/api/stop_job', {method: 'POST'});
    } catch(e) {}
    if (monitorInterval) clearInterval(monitorInterval);
    window.location.reload();
}

// --- ONLOAD ---
window.onload = () => {
    initVisualizer();
    loadGeneratedSongs();
};