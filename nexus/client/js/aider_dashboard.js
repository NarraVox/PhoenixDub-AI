        // API Base URL
        const API_URL = ''; // Matches relative routes when served by Flask

        // State variables
        let serverRunning = false;
        let aiderRunning = false;
        let activeTab = 'server';
        let availableModels = [];
        let pollingInterval = null;
        let statsInterval = null;
        
        // Video Copilot state variables
        let activeMainTab = 'aider';
        let transcribeRunning = false;
        let renderRunning = false;
        let currentLoadedProjectFolder = "";
        let pendingChatAction = null;
        let pendingRenderAction = false;
        let currentVideoDuration = 0;

        // Prompt Queue state
        let promptQueue = [];

        // Initialize App
        window.addEventListener('DOMContentLoaded', async () => {
            await fetchModels();
            await fetchStatus();
            renderQueue(); // Initialize empty queue message
            updateConsolidatedPrompt(); // Initialize consolidated prompt text area
            
            // Add listeners to checkboxes to dynamically update consolidated prompt
            ['optRemoveSilence', 'optRemoveHesitations', 'optVerticalFormat', 'optGenerateChapters', 'optAddSoundtrack', 'optAddTransitions', 'optGenerateSrt', 'optNoiseReduction', 'optLoudnorm', 'optSmartZoom', 'optAudioPadding'].forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.addEventListener('change', () => {
                        if (id === 'optAddSoundtrack') {
                            toggleSoundtrackSection();
                        }
                        updateConsolidatedPrompt();
                        saveCopilotPaths();
                    });
                }
            });
            
            // Periodically check logs & stats based on active view
            pollingInterval = setInterval(() => {
                if (activeMainTab === 'aider') {
                    fetchLogs();
                } else {
                    fetchCopilotLogs();
                }
            }, 2000);
            
            statsInterval = setInterval(fetchStatus, 3000);
            
            // Add handler for click on settings panel (instantly shuts down LLM to free VRAM)
            document.getElementById('settingsCard').addEventListener('click', handleSettingsClick);
            initWelcomeMessage();
        });

        // Trigger VRAM release when user interacts with settings card
        async function handleSettingsClick() {
            if (serverRunning) {
                console.log("Settings panel clicked - shutting down server to free memory...");
                
                // Show minimal visual note
                const sub = document.getElementById('panelStateSubtitle');
                sub.innerHTML = "<span class='pulse-text' style='color:var(--warning)'>Descarregando modelo para liberar VRAM...</span>";
                
                try {
                    const res = await fetch(`${API_URL}/api/stop`, { method: 'POST' });
                    const data = await res.json();
                    if (data.success) {
                        serverRunning = false;
                        aiderRunning = false;
                        updateUIState();
                        fetchStatus(); // immediate refresh
                    }
                } catch (e) {
                    console.error("Failed to release VRAM: ", e);
                }
            }
        }

        // Fetch GGUF Models
        async function fetchModels() {
            try {
                const res = await fetch(`${API_URL}/api/models`);
                const data = await res.json();
                availableModels = data.models;
                
                const select = document.getElementById('modelSelect');
                select.innerHTML = '';
                
                if (availableModels.length === 0) {
                    select.innerHTML = '<option value="">Nenhum modelo GGUF encontrado em C:\\IA_dublagem\\_MODELS_</option>';
                    return;
                }
                
                availableModels.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model.path;
                    option.text = `${model.name} (${model.size_gb} GB)`;
                    option.dataset.size = model.size_gb;
                    select.appendChild(option);
                });
                
                // Select Qwen 3.5 by default if present
                const qwenOpt = Array.from(select.options).find(opt => opt.text.toLowerCase().includes('qwen3.5'));
                if (qwenOpt) {
                    select.value = qwenOpt.value;
                }
                
                onModelChange();
            } catch (e) {
                console.error("Erro ao carregar modelos: ", e);
            }
        }

        // Fetch server and PC status
        async function fetchStatus() {
            try {
                const res = await fetch(`${API_URL}/api/status`);
                const data = await res.json();
                
                serverRunning = data.server_running || data.port_responsive;
                aiderRunning = data.aider_running;
                
                // If it is first load, load configurations
                if (!document.getElementById('serverHost').dataset.loaded) {
                    loadConfigUI(data.config);
                    document.getElementById('serverHost').dataset.loaded = 'true';
                }
                
                updateUIState(data.loaded_model);
                updateSystemStatsUI(data.stats);
                
                if (activeMainTab === 'video') {
                    fetchCopilotStatus();
                }
            } catch (e) {
                console.error("Erro ao obter status: ", e);
                document.getElementById('statusDot').className = 'status-dot inactive';
                document.getElementById('statusText').innerText = 'Erro ao conectar no painel!';
            }
        }

        // Populate Config UI
        function loadConfigUI(config) {
            if (config.model_path) {
                document.getElementById('modelSelect').value = config.model_path;
            }
            if (config.n_gpu_layers !== undefined) {
                document.getElementById('gpuLayers').value = config.n_gpu_layers;
                document.getElementById('gpuLayersVal').innerText = config.n_gpu_layers;
            }
            
            if (config.n_ctx) {
                document.getElementById('contextSize').value = config.n_ctx;
                document.getElementById('contextVal').innerText = config.n_ctx;
            }
            

            if (config.flash_attn !== undefined) {
                document.getElementById('flashAttn').checked = config.flash_attn;
            }
            if (config.host) {
                document.getElementById('serverHost').value = config.host;
            }
            if (config.port) {
                document.getElementById('serverPort').value = config.port;
            }
            
            onModelChange();
        }

        // Helper to guess layers based on model name/size
        function getModelLayers(fileName, sizeGb) {
            const name = fileName.toLowerCase();
            if (name.includes("qwen3.5") || name.includes("4b")) {
                return 28;
            } else if (name.includes("gemma-4") || name.includes("9b")) {
                return 42;
            } else if (name.includes("0.6b") || name.includes("acestep")) {
                return 20;
            } else if (sizeGb <= 1.5) {
                return 20;
            } else if (sizeGb <= 3.5) {
                return 28;
            } else if (sizeGb <= 6.5) {
                return 32;
            } else {
                return 42;
            }
        }

        // Handle dropdown selection change
        function onModelChange() {
            const select = document.getElementById('modelSelect');
            if (select.selectedIndex === -1) return;
            
            const selectedOption = select.options[select.selectedIndex];
            const sizeGb = parseFloat(selectedOption.dataset.size || 0);
            document.getElementById('modelSizeDisplay').innerText = `${sizeGb} GB`;
            
            // Adjust GPU layers slider max dynamically based on model size/architecture
            const modelLayers = getModelLayers(selectedOption.text, sizeGb);
            const gpuLayersSlider = document.getElementById('gpuLayers');
            
            gpuLayersSlider.max = modelLayers;
            
            // If current value is higher than max layers, cap it
            if (parseInt(gpuLayersSlider.value) > modelLayers) {
                gpuLayersSlider.value = modelLayers;
            }
            document.getElementById('gpuLayersVal').innerText = gpuLayersSlider.value;
            
            // Update the label to show max layers dynamically
            const gpuLabel = document.querySelector('label[for="gpuLayers"]');
            if (gpuLabel) {
                gpuLabel.innerHTML = `Camadas na GPU (Máx do modelo: ${modelLayers}): <span id="gpuLayersVal">${gpuLayersSlider.value}</span>`;
            }
            
            updateEstimate();
        }

        // Update RAM/VRAM estimates in real-time
        function updateEstimate() {
            const select = document.getElementById('modelSelect');
            if (select.selectedIndex === -1) return;
            
            const selectedOption = select.options[select.selectedIndex];
            const modelSizeGb = parseFloat(selectedOption.dataset.size || 0);
            
            const gpuLayersSlider = document.getElementById('gpuLayers');
            const gpuLayers = parseInt(gpuLayersSlider.value);
            document.getElementById('gpuLayersVal').innerText = gpuLayers;
            
            const contextTokens = parseInt(document.getElementById('contextSize').value);
            document.getElementById('contextVal').innerText = contextTokens;
            
            // Formula heuristics using dynamic totalLayers of the selected model
            const totalLayers = parseInt(gpuLayersSlider.max) || 28;
            const offloadRatio = gpuLayers / totalLayers;
            
            // Model weight split
            const modelVram = modelSizeGb * offloadRatio;
            const modelRam = modelSizeGb * (1 - offloadRatio);
            
            // KV Cache memory: ~0.08 MB per token total
            const kvCacheGb = (contextTokens * 0.08) / 1024;
            const kvVram = kvCacheGb * offloadRatio;
            const kvRam = kvCacheGb * (1 - offloadRatio);
            
            // Overhead: CUDA runtime is approx 0.45 GB
            const overheadVram = gpuLayers > 0 ? 0.45 : 0;
            const overheadRam = 0.2; // minimal process allocation
            
            // Totals
            const estVram = modelVram + kvVram + overheadVram;
            const estRam = modelRam + kvRam + overheadRam;
            
            // Update VRAM UI
            document.getElementById('estVramVal').innerText = `${estVram.toFixed(1)} / 6.0 GB`;
            const vramPct = Math.min((estVram / 6.0) * 100, 100);
            const vramBar = document.getElementById('estVramBar');
            vramBar.style.width = `${vramPct}%`;
            
            const vramSafety = document.getElementById('vramSafetyText');
            if (estVram <= 4.5) {
                vramBar.className = 'gauge-bar-fill success';
                vramSafety.innerText = 'Status: Seguro';
                vramSafety.style.color = 'var(--success)';
            } else if (estVram <= 5.5) {
                vramBar.className = 'gauge-bar-fill warning';
                vramSafety.innerText = 'Status: Moderado';
                vramSafety.style.color = 'var(--warning)';
            } else {
                vramBar.className = 'gauge-bar-fill danger';
                vramSafety.innerText = 'Status: Risco de Estouro!';
                vramSafety.style.color = 'var(--danger)';
            }
            
            // Update RAM UI
            document.getElementById('estRamVal').innerText = `${estRam.toFixed(1)} / 16.0 GB`;
            const ramPct = Math.min((estRam / 16.0) * 100, 100);
            document.getElementById('estRamBar').style.width = `${ramPct}%`;
        }

        // Update UI states based on server state
        function updateUIState(modelName = "Carregando...") {
            const statusDot = document.getElementById('statusDot');
            const statusText = document.getElementById('statusText');
            const panelTitle = document.getElementById('panelStateTitle');
            const panelSubtitle = document.getElementById('panelStateSubtitle');
            const btnPower = document.getElementById('btnPower');
            
            if (serverRunning) {
                statusDot.className = 'status-dot active';
                statusText.innerText = 'Status: Servidor Online';
                panelTitle.innerText = 'Servidor de IA Ativo';
                panelSubtitle.innerHTML = `Modelo carregado: <span style="color:var(--secondary); font-weight:600;">${modelName}</span>${aiderRunning ? " | <span style='color:var(--success); font-weight:600;'>Aider Chat Pronto</span>" : ""}`;
                
                btnPower.className = 'btn-power on';
                btnPower.querySelector('span').innerText = 'Desligar';
            } else {
                statusDot.className = 'status-dot';
                statusText.innerText = 'Status: Desconectado';
                panelTitle.innerText = 'Servidor Inativo';
                panelSubtitle.innerText = 'Configure e ligue para iniciar o Aider Chat';
                
                btnPower.className = 'btn-power';
                btnPower.querySelector('span').innerText = 'Ligar';
            }
        }

        // Update real physical computer stats
        function updateSystemStatsUI(stats) {
            if (!stats) return;
            

            
            // Real VRAM
            const gpu = stats.gpu;
            const realVramVal = document.getElementById('realVramVal');
            const realVramBar = document.getElementById('realVramBar');
            const realVramDetail = document.getElementById('realVramDetail');
            
            if (gpu.error) {
                realVramVal.innerText = 'Sem Acesso';
                realVramBar.style.width = '0%';
                realVramDetail.innerText = gpu.msg || 'nvidia-smi indisponível';
            } else {
                const usedGb = (gpu.used_mb / 1024).toFixed(1);
                const totalGb = (gpu.total_mb / 1024).toFixed(1);
                realVramVal.innerText = `${usedGb} / ${totalGb} GB`;
                
                const vramPct = gpu.used_percent;
                realVramBar.style.width = `${vramPct}%`;
                
                if (vramPct < 75) realVramBar.className = 'gauge-bar-fill success';
                else if (vramPct < 90) realVramBar.className = 'gauge-bar-fill warning';
                else realVramBar.className = 'gauge-bar-fill danger';
                
                realVramDetail.innerText = `Livre: ${(gpu.free_mb / 1024).toFixed(1)} GB`;
            }
            
            // Real RAM
            const realRamVal = document.getElementById('realRamVal');
            const realRamBar = document.getElementById('realRamBar');
            const realRamDetail = document.getElementById('realRamDetail');
            const cpuUsageText = document.getElementById('cpuUsageText');
            
            realRamVal.innerText = `${stats.ram_used_gb} / ${stats.ram_total_gb} GB`;
            realRamBar.style.width = `${stats.ram_percent}%`;
            realRamDetail.innerText = `Uso: ${stats.ram_percent}%`;
            cpuUsageText.innerText = `CPU: ${stats.cpu_percent}%`;
        }

        // Fetch log console texts
        async function fetchLogs() {
            try {
                const res = await fetch(`${API_URL}/api/logs`);
                const data = await res.json();
                
                const terminal = document.getElementById('terminalBody');
                let rawText = '';
                
                if (activeTab === 'server') {
                    rawText = data.server_log || 'Nenhum log gerado pelo Llama Server até o momento.';
                } else {
                    rawText = data.aider_log || 'Nenhum log gerado pelo Aider até o momento.';
                }
                
                // Colorize logs slightly
                const lines = rawText.split('\n').map(line => {
                    if (line.includes('[INFO]') || line.includes('INFO:')) {
                        return `<span class="info">${escapeHtml(line)}</span>`;
                    } else if (line.includes('ERR') || line.includes('ERROR:') || line.includes('FAIL') || line.includes('❌')) {
                        return `<span class="error">${escapeHtml(line)}</span>`;
                    } else if (line.includes('WARN') || line.includes('WARNING') || line.includes('⚠️')) {
                        return `<span class="warn">${escapeHtml(line)}</span>`;
                    } else if (line.includes('OK') || line.includes('success') || line.includes('✅') || line.includes('online')) {
                        return `<span class="success">${escapeHtml(line)}</span>`;
                    }
                    return escapeHtml(line);
                });
                
                const isAtBottom = terminal.scrollHeight - terminal.clientHeight - terminal.scrollTop < 30;
                terminal.innerHTML = lines.join('\n');
                
                if (isAtBottom) {
                    terminal.scrollTop = terminal.scrollHeight;
                }
            } catch (e) {
                console.error("Erro ao ler logs: ", e);
            }
        }

        // Tab switcher for logs
        function switchTab(tab) {
            activeTab = tab;
            document.getElementById('tabServer').className = `terminal-tab ${tab === 'server' ? 'active' : ''}`;
            document.getElementById('tabAider').className = `terminal-tab ${tab === 'aider' ? 'active' : ''}`;
            fetchLogs();
        }

        // Helper to escape HTML tags in logs
        function escapeHtml(text) {
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");
        }

        // Save settings to backend
        async function saveSettings() {
            const config = getFormConfig();
            
            try {
                const res = await fetch(`${API_URL}/api/save_config`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                const data = await res.json();
                if (data.success) {
                    alert('Configurações salvas com sucesso!');
                } else {
                    alert('Erro ao salvar as configurações: ' + data.error);
                }
            } catch (e) {
                alert('Falha na comunicação com o servidor para salvar configurações.');
            }
        }

        // Helper to get configuration dictionary from UI
        function getFormConfig() {
            const modelSelect = document.getElementById('modelSelect');
            const contextTokens = parseInt(document.getElementById('contextSize').value);
            
            return {
                model_path: modelSelect.value,
                n_ctx: contextTokens,
                n_gpu_layers: parseInt(document.getElementById('gpuLayers').value),
                flash_attn: document.getElementById('flashAttn').checked,
                host: document.getElementById('serverHost').value,
                port: parseInt(document.getElementById('serverPort').value)
            };
        }

        // Restore default properties
        function restoreDefaults() {
            document.getElementById('gpuLayers').value = 33;
            document.getElementById('gpuLayersVal').innerText = 33;
            document.getElementById('contextSize').value = 4096;
            document.getElementById('contextVal').innerText = 4096;
            document.getElementById('flashAttn').checked = true;
            document.getElementById('serverHost').value = '127.0.0.1';
            document.getElementById('serverPort').value = 1234;
            
            updateEstimate();
        }

        // Start/Stop power trigger
        async function togglePower() {
            const overlay = document.getElementById('loaderOverlay');
            
            if (!serverRunning) {
                // STARTING
                overlay.style.display = 'flex';
                document.getElementById('loaderText').innerHTML = "Salvando configurações e iniciando Llama Server...<br><span style='font-size:13px; color:var(--text-muted); font-weight:normal;'>Isto alocará o modelo na GPU de forma otimizada. Por favor, aguarde.</span>";
                
                // Save current configuration first
                const config = getFormConfig();
                try {
                    await fetch(`${API_URL}/api/save_config`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(config)
                    });
                    
                    // Call start API
                    document.getElementById('loaderText').innerHTML = "Carregando modelo GGUF na VRAM da GPU...<br><span style='font-size:13px; color:var(--text-muted); font-weight:normal;'>Aguardando o servidor de IA ficar online na porta " + config.port + "...</span>";
                    
                    const startRes = await fetch(`${API_URL}/api/start`, { method: 'POST' });
                    const startData = await startRes.json();
                    
                    overlay.style.display = 'none';
                    if (startRes.ok && startData.success) {
                        serverRunning = true;
                        aiderRunning = true;
                        updateUIState(startData.model_loaded);
                        fetchStatus(); // immediate reload
                    } else {
                        alert('Erro ao carregar IA: ' + (startData.error || 'Erro desconhecido.'));
                    }
                } catch (e) {
                    overlay.style.display = 'none';
                    alert('Falha crítica de comunicação ao iniciar o servidor.');
                }
            } else {
                // STOPPING
                overlay.style.display = 'flex';
                document.getElementById('loaderText').innerHTML = "Descarregando Modelo e Liberando VRAM da GPU...<br><span style='font-size:13px; color:var(--text-muted); font-weight:normal;'>Limpando buffers do PyTorch e CUDA.</span>";
                
                try {
                    const stopRes = await fetch(`${API_URL}/api/stop`, { method: 'POST' });
                    const stopData = await stopRes.json();
                    
                    overlay.style.display = 'none';
                    if (stopData.success) {
                        serverRunning = false;
                        aiderRunning = false;
                        updateUIState();
                        fetchStatus();
                    }
                } catch (e) {
                    overlay.style.display = 'none';
                    alert('Erro ao parar o servidor de IA.');
                }
            }
        }

        // =====================================================================
        // JAVASCRIPT FUNCTIONS FOR AI VIDEO EDITOR COPILOT
        // =====================================================================

        // Switch between Aider Dashboard and Video Copilot Main Tab
        function switchMainTab(tab) {
            activeMainTab = tab;
            
            const navAider = document.getElementById('navAider');
            const navVideo = document.getElementById('navVideo');
            const contentAider = document.getElementById('contentAider');
            const contentVideo = document.getElementById('contentVideo');
            
            if (tab === 'aider') {
                navAider.classList.add('active');
                navVideo.classList.remove('active');
                contentAider.classList.remove('hidden');
                contentVideo.classList.add('hidden');
            } else {
                navAider.classList.remove('active');
                navVideo.classList.add('active');
                contentAider.classList.add('hidden');
                contentVideo.classList.remove('hidden');
                
                // Immediately query paths and status
                fetchCopilotStatus();
                fetchCopilotLogs();
                loadTranscriptionText();
            }
        }

        // Open file dialog to choose video
        async function chooseVideoFile() {
            try {
                let path = "";
                if (window.pywebview && window.pywebview.api && window.pywebview.api.open_file_dialog) {
                    path = await window.pywebview.api.open_file_dialog("Vídeos (*.mp4;*.mkv;*.avi;*.mov)");
                } else {
                    const typed = prompt("Digite o caminho absoluto do arquivo de vídeo no seu computador:\n(Ex: C:\\IA_dublagem\\uploads\\VID_20260624_171202119.mp4)", document.getElementById('vCopilotInput').value || "");
                    if (typed) {
                        path = typed.trim();
                    }
                }
                
                if (path) {
                    handleVideoSelection(path);
                }
            } catch (e) {
                console.error("Erro ao selecionar arquivo:", e);
                alert("Não foi possível abrir o seletor de arquivos.");
            }
        }

        // Handle path extraction and dynamic configuration of project folder
        function handleVideoSelection(videoPath) {
            if (!videoPath) return;
            
            const normalizedPath = videoPath.replace(/\//g, '\\');
            document.getElementById('vCopilotInput').value = normalizedPath;
            
            const filename = normalizedPath.split(/[\\\\/]/).pop();
            const baseName = filename.substring(0, filename.lastIndexOf('.')) || filename;
            
            const projectFolder = `C:\\IA_dublagem\\uploads\\video_${baseName}`;
            const outputPath = `${projectFolder}\\${baseName}_editado.mp4`;
            
            document.getElementById('vCopilotOutput').value = outputPath;
            
            document.getElementById('projectFolderPath').innerText = projectFolder;
            document.getElementById('projectFolderDisplay').style.display = 'block';
            
            saveCopilotPathsAuto(normalizedPath, outputPath, projectFolder);
        }

        // Auto-save paths during video selection without alert modal spam
        async function saveCopilotPathsAuto(video_path, output_path, project_folder) {
            const getCheck = id => { const el = document.getElementById(id); return el ? el.checked : false; };
            const options = {
                remove_silence: getCheck('optRemoveSilence'),
                remove_hesitations: getCheck('optRemoveHesitations'),
                vertical_format: getCheck('optVerticalFormat'),
                generate_chapters: getCheck('optGenerateChapters'),
                add_soundtrack: getCheck('optAddSoundtrack'),
                add_transitions: getCheck('optAddTransitions'),
                generate_srt: getCheck('optGenerateSrt'),
                noise_reduction: getCheck('optNoiseReduction'),
                loudnorm: getCheck('optLoudnorm'),
                smart_zoom: getCheck('optSmartZoom'),
                audio_padding: getCheck('optAudioPadding'),
                soundtrack_paths: (document.getElementById('soundtrackPathsInput')?.value || '').split(',').map(p => p.trim()).filter(p => p)
            };
            
            try {
                await fetch(`${API_URL}/api/video_copilot/save_paths`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ video_path, output_path, project_folder, options })
                });
                fetchCopilotStatus();
            } catch (e) {
                console.error("Erro ao salvar caminhos automaticamente:", e);
            }
        }

        // Save Paths
        async function saveCopilotPaths() {
            const video_path = document.getElementById('vCopilotInput').value;
            const output_path = document.getElementById('vCopilotOutput').value;
            
            let project_folder = "";
            if (video_path) {
                const filename = video_path.split(/[\\\\/]/).pop();
                const baseName = filename.substring(0, filename.lastIndexOf('.')) || filename;
                project_folder = `C:\\IA_dublagem\\uploads\\video_${baseName}`;
            }
            
            const getCheck = id => { const el = document.getElementById(id); return el ? el.checked : false; };
            const options = {
                remove_silence: getCheck('optRemoveSilence'),
                remove_hesitations: getCheck('optRemoveHesitations'),
                vertical_format: getCheck('optVerticalFormat'),
                generate_chapters: getCheck('optGenerateChapters'),
                add_soundtrack: getCheck('optAddSoundtrack'),
                add_transitions: getCheck('optAddTransitions'),
                generate_srt: getCheck('optGenerateSrt'),
                noise_reduction: getCheck('optNoiseReduction'),
                loudnorm: getCheck('optLoudnorm'),
                smart_zoom: getCheck('optSmartZoom'),
                audio_padding: getCheck('optAudioPadding'),
                soundtrack_paths: (document.getElementById('soundtrackPathsInput')?.value || '').split(',').map(p => p.trim()).filter(p => p)
            };
            
            try {
                const res = await fetch(`${API_URL}/api/video_copilot/save_paths`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ video_path, output_path, project_folder, options })
                });
                const data = await res.json();
                if (data.success) {
                    console.log('Caminhos e configurações salvas no servidor.');
                    fetchCopilotStatus();
                } else {
                    alert('Erro ao salvar caminhos: ' + data.error);
                }
            } catch (e) {
                alert('Erro ao comunicar com o servidor.');
            }
        }

        // Load Transcription Text
        async function loadTranscriptionText() {
            const container = document.getElementById('transcriptionContentContainer');
            if (!container) return;
            
            try {
                const res = await fetch(`${API_URL}/api/video_copilot/transcript`);
                const data = await res.json();
                
                if (data.success && data.content) {
                    container.innerText = data.content;
                } else {
                    container.innerText = data.error || "Nenhuma transcrição encontrada ou ainda não gerada.";
                }
            } catch (e) {
                console.error("Erro ao carregar transcrição:", e);
                container.innerText = "Erro ao carregar a transcrição do servidor.";
            }
        }

        // Start Whisper Transcription
        async function startTranscription() {
            try {
                const video_path = document.getElementById('vCopilotInput').value;
                const output_path = document.getElementById('vCopilotOutput').value;
                
                let project_folder = "";
                if (video_path) {
                    const filename = video_path.split(/[\\\\/]/).pop();
                    const baseName = filename.substring(0, filename.lastIndexOf('.')) || filename;
                    project_folder = `C:\\IA_dublagem\\uploads\\video_${baseName}`;
                }
                
                const getCheck = id => { const el = document.getElementById(id); return el ? el.checked : false; };
                const options = {
                    remove_silence: getCheck('optRemoveSilence'),
                    remove_hesitations: getCheck('optRemoveHesitations'),
                    vertical_format: getCheck('optVerticalFormat'),
                    generate_chapters: getCheck('optGenerateChapters'),
                    add_soundtrack: getCheck('optAddSoundtrack'),
                    add_transitions: getCheck('optAddTransitions'),
                    generate_srt: getCheck('optGenerateSrt'),
                    noise_reduction: getCheck('optNoiseReduction'),
                    loudnorm: getCheck('optLoudnorm'),
                    smart_zoom: getCheck('optSmartZoom'),
                    audio_padding: getCheck('optAudioPadding'),
                    soundtrack_paths: (document.getElementById('soundtrackPathsInput')?.value || '').split(',').map(p => p.trim()).filter(p => p)
                };
                
                await fetch(`${API_URL}/api/video_copilot/save_paths`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ video_path, output_path, project_folder, options })
                });

                const res = await fetch(`${API_URL}/api/video_copilot/transcribe`, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    fetchCopilotStatus();
                } else {
                    alert('Erro ao iniciar transcrição: ' + data.error);
                }
            } catch (e) {
                alert('Erro de comunicação.');
            }
        }

        // Collapsible Soundtrack custom section
        function toggleSoundtrackSection() {
            const optAddSoundtrack = document.getElementById('optAddSoundtrack');
            const soundtrackCustomSection = document.getElementById('soundtrackCustomSection');
            if (optAddSoundtrack && soundtrackCustomSection) {
                soundtrackCustomSection.style.display = optAddSoundtrack.checked ? 'block' : 'none';
            }
        }

        // Custom Soundtrack selector prompt
        function selectSoundtrackFiles() {
            let promptText = "Digite o caminho completo do arquivo de áudio (.mp3 ou .wav) no seu PC:";
            if (currentVideoDuration > 120) {
                promptText = `Seu vídeo possui mais de 2 minutos (${Math.round(currentVideoDuration)}s).\nVocê pode selecionar múltiplas músicas separadas por vírgula:\n(Ex: C:\\Musicas\\musica1.mp3, C:\\Musicas\\musica2.mp3)`;
            } else {
                promptText = `Digite o caminho completo da música no seu PC:\n(Ex: C:\\Musicas\\soundtrack.mp3)`;
            }
            
            const currentPaths = document.getElementById('soundtrackPathsInput').value;
            const typed = prompt(promptText, currentPaths);
            if (typed !== null) {
                const pathsArray = typed.split(',').map(p => p.trim()).filter(p => p);
                document.getElementById('soundtrackPathsInput').value = pathsArray.join(', ');
                updateConsolidatedPrompt();
                saveCopilotPaths();
            }
        }

        // Start Whisper Auto-Transcription
        async function triggerAutoTranscription() {
            if (transcribeRunning) return;
            
            addMessageToChat('system', 'Iniciando transcrição automática via Whisper (GPU CUDA) no background...', 'running');
            
            try {
                const transcribeRes = await fetch(`${API_URL}/api/video_copilot/transcribe`, { method: 'POST' });
                const transcribeData = await transcribeRes.json();

                if (!transcribeData.success) {
                    addMessageToChat('copilot', '❌ <b>Erro ao iniciar transcrição automática:</b> ' + transcribeData.error);
                    return;
                }
                
                transcribeRunning = true;
                startTranscriptionPolling();
            } catch (err) {
                addMessageToChat('copilot', '❌ <b>Erro ao conectar com servidor de transcrição:</b> ' + err.message);
            }
        }

        // Start Whisper Polling with Queue Management
        function startTranscriptionPolling() {
            if (copilotStatusPoll) clearInterval(copilotStatusPoll);
            
            copilotStatusPoll = setInterval(async () => {
                try {
                    const pollRes = await fetch(`${API_URL}/api/video_copilot/status`);
                    const pollData = await pollRes.json();
                    
                    transcribeRunning = pollData.transcribe_running;
                    
                    if (!pollData.transcribe_running) {
                        clearInterval(copilotStatusPoll);
                        copilotStatusPoll = null;
                        
                        if (pollData.transcript_exists) {
                            addMessageToChat('system', '✓ Transcrição automática via GPU concluída com sucesso!');
                            loadTranscriptionText();
                            
                            // Process queued actions
                            if (pendingChatAction) {
                                addMessageToChat('system', 'Whisper concluído. Processando mensagem enfileirada...');
                                pendingChatAction = null;
                                await startAiderChatFlow();
                            } else if (pendingRenderAction) {
                                addMessageToChat('system', 'Whisper concluído. Iniciando renderização enfileirada...');
                                pendingRenderAction = false;
                                triggerActualRender();
                            }
                        } else {
                            addMessageToChat('copilot', '❌ A transcrição automática falhou. Verifique os logs de inicialização.');
                            pendingChatAction = null;
                            pendingRenderAction = false;
                        }
                    }
                } catch (pollErr) {
                    console.error("Erro no polling da transcrição:", pollErr);
                }
            }, 2000);
        }

        // Trigger Actual FFmpeg Render Command
        async function triggerActualRender() {
            try {
                addMessageToChat('system', 'Iniciando renderização de vídeo no background...', 'running');
                const res = await fetch(`${API_URL}/api/video_copilot/render`, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    fetchCopilotStatus();
                } else {
                    addMessageToChat('copilot', '❌ <b>Erro ao iniciar renderização:</b> ' + data.error);
                }
            } catch (e) {
                addMessageToChat('copilot', '❌ <b>Erro de comunicação ao renderizar:</b> ' + e.message);
            }
        }

        // Start FFmpeg Rendering
        async function startRendering() {
            try {
                const video_path = document.getElementById('vCopilotInput').value;
                const output_path = document.getElementById('vCopilotOutput').value;
                
                let project_folder = "";
                if (video_path) {
                    const filename = video_path.split(/[\\\\/]/).pop();
                    const baseName = filename.substring(0, filename.lastIndexOf('.')) || filename;
                    project_folder = `C:\\IA_dublagem\\uploads\\video_${baseName}`;
                }
                
                const getCheck = id => { const el = document.getElementById(id); return el ? el.checked : false; };
                const options = {
                    remove_silence: getCheck('optRemoveSilence'),
                    remove_hesitations: getCheck('optRemoveHesitations'),
                    vertical_format: getCheck('optVerticalFormat'),
                    generate_chapters: getCheck('optGenerateChapters'),
                    add_soundtrack: getCheck('optAddSoundtrack'),
                    add_transitions: getCheck('optAddTransitions'),
                    generate_srt: getCheck('optGenerateSrt'),
                    noise_reduction: getCheck('optNoiseReduction'),
                    loudnorm: getCheck('optLoudnorm'),
                    smart_zoom: getCheck('optSmartZoom'),
                    audio_padding: getCheck('optAudioPadding'),
                    soundtrack_paths: (document.getElementById('soundtrackPathsInput')?.value || '').split(',').map(p => p.trim()).filter(p => p)
                };
                
                await fetch(`${API_URL}/api/video_copilot/save_paths`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ video_path, output_path, project_folder, options })
                });

                if (transcribeRunning) {
                    addMessageToChat('system', '⚠️ <b>[FILA]</b> Transcrição em andamento. O processo de renderização iniciará automaticamente assim que a transcrição terminar.', 'info');
                    pendingRenderAction = true;
                    return;
                }

                await triggerActualRender();
            } catch (e) {
                alert('Erro de comunicação.');
            }
        }

        // Stop Transcribe / Render Background Process
        async function stopCopilotProcess() {
            try {
                const res = await fetch(`${API_URL}/api/video_copilot/stop`, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    fetchCopilotStatus();
                }
            } catch (e) {
                console.error(e);
            }
        }

        // Prompt Queue operations
        function updateConsolidatedPrompt() {
            let promptText = "Quero fazer uma edição profissional neste vídeo seguindo as opções selecionadas:\n";
            
            if (document.getElementById('optRemoveSilence').checked) {
                promptText += "- O corte automático de silêncios está ATIVADO. Garanta que o pacing seja ágil e dinâmico, removendo pausas mortas.\n";
            } else {
                promptText += "- Manter os silêncios originais do palestrante.\n";
            }
            
            if (document.getElementById('optRemoveHesitations').checked) {
                promptText += "- A remoção de hesitações (como 'eee', 'humm') está ATIVADA.\n";
            }
            
            if (document.getElementById('optVerticalFormat').checked) {
                promptText += "- Formato VERTICAL (9:16) está ATIVADO. Centralize a câmera no palestrante e aplique zoom vertical para preencher a tela.\n";
            }
            
            if (document.getElementById('optGenerateChapters').checked) {
                promptText += "- Geração de capítulos para YouTube está ATIVADA.\n";
            }
            
            if (document.getElementById('optAddSoundtrack').checked) {
                promptText += "- A mixagem da trilha sonora de fundo está ATIVADA. Garanta que o volume da música seja abaixado (ducking/sidechain compression) de forma suave durante a fala.\n";
            }
            
            if (document.getElementById('optAddTransitions').checked) {
                promptText += "- Transições nos cortes (crossfades rápidos ou zoom-ins táticos de 1.2x alternando entre cortes) estão ATIVADAS para suavizar a edição.\n";
            }

            if (document.getElementById('optGenerateSrt').checked) {
                promptText += "- A geração de legenda externa SRT está ATIVADA. O script irá gerar um arquivo .srt na mesma pasta do vídeo com o mesmo nome.\n";
            }
            promptText += "- Não queime legendas completas na imagem do vídeo. O vídeo final deve conter apenas os destaques pontuais da lista 'key_captions' em 'editar_video_profissional.py'.\n";

            if (document.getElementById('optNoiseReduction').checked) {
                promptText += "- A redução de ruído FFT está ATIVADA para limpar o áudio da voz.\n";
            }
            
            if (document.getElementById('optLoudnorm').checked) {
                promptText += "- A normalização de áudio Loudnorm está ATIVADA para volume consistente.\n";
            }
            
            if (document.getElementById('optSmartZoom').checked) {
                promptText += "- O efeito de multi-câmera virtual (Cortes alternados com Zoom) está ATIVADO.\n";
            }
            
            if (document.getElementById('optAudioPadding').checked) {
                promptText += "- Adicionar margem de respiro (pequenos silêncios de transição) nos cortes está ATIVADO.\n";
            }

            promptText += "\nPor favor, leia a transcrição em 'transcricao_video.txt', identifique as melhores tomadas, e atualize a lista 'good_segments' em 'editar_video_profissional.py'. Também adicione palavras de impacto chave na lista 'key_captions' com estilos ASS animados, centralizados na parte inferior (Alignment=2, MarginV=60), garantindo que as legendas não entrem simultaneamente. Configure os caminhos de entrada e saída corretamente.";

            // Coletar instruções do histórico de chat do Copiloto (DOM)
            const chatInstructions = [];
            const chatHistoryEl = document.getElementById('chatHistory');
            if (chatHistoryEl) {
                const bubbles = chatHistoryEl.querySelectorAll('.chat-message.user');
                bubbles.forEach(bubble => {
                    const clone = bubble.cloneNode(true);
                    const metaEl = clone.querySelector('.chat-message-meta');
                    if (metaEl) {
                        clone.removeChild(metaEl);
                    }
                    const text = clone.innerText.trim();
                    if (text) {
                        chatInstructions.push(text);
                    }
                });
            }

            if (chatInstructions.length > 0 || promptQueue.length > 0) {
                promptText += "\n\n=== INSTRUÇÕES ADICIONAIS ENFILEIRADAS ===\n";
                let idx = 1;
                chatInstructions.forEach(prompt => {
                    promptText += `${idx}. [Chat] ${prompt}\n`;
                    idx++;
                });
                promptQueue.forEach(prompt => {
                    promptText += `${idx}. [Fila] ${prompt}\n`;
                    idx++;
                });
            }

            const consText = document.getElementById('consolidatedPromptText');
            if (consText) {
                consText.value = promptText;
            }
        }

        function addPromptToQueue() {
            const input = document.getElementById('queueInputText');
            const text = input.value.trim();
            if (!text) return;
            
            promptQueue.push(text);
            input.value = '';
            renderQueue();
            updateConsolidatedPrompt();
        }

        function removePromptFromQueue(index) {
            promptQueue.splice(index, 1);
            renderQueue();
            updateConsolidatedPrompt();
        }

        async function clearQueue() {
            promptQueue = [];
            renderQueue();
            
            // Limpa o histórico visual do chat
            const chatHistory = document.getElementById('chatHistory');
            if (chatHistory) {
                chatHistory.innerHTML = '';
            }
            
            // Deleta o histórico de chat salvo no servidor para este projeto
            try {
                await fetch(`${API_URL}/api/video_copilot/clear_chat`, { method: 'POST' });
            } catch (e) {
                console.error("Erro ao limpar histórico no servidor:", e);
            }
            
            initWelcomeMessage();
            updateConsolidatedPrompt();
        }

        async function copyConsolidatedPrompt() {
            updateConsolidatedPrompt();
            const promptText = document.getElementById('consolidatedPromptText').value;
            if (!promptText) return;
            
            try {
                await navigator.clipboard.writeText(promptText);
            } catch (err) {
                // Fallback copy
                const el = document.createElement('textarea');
                el.value = promptText;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
            }
            
            // Show feedback
            const feedback = document.getElementById('copyFeedback');
            if (feedback) {
                feedback.innerText = "✓ Copiado com sucesso!";
                feedback.style.opacity = '1';
                setTimeout(() => {
                    feedback.style.opacity = '0';
                }, 3000);
            }
        }

        function renderQueue() {
            const container = document.getElementById('queueListContainer');
            const countSpan = document.getElementById('queueCount');
            if (!container || !countSpan) return;
            
            countSpan.innerText = promptQueue.length;
            container.innerHTML = '';
            
            if (promptQueue.length === 0) {
                container.innerHTML = `<span style="color: var(--text-muted); font-size: 13px; font-style: italic; padding: 6px 4px;">Fila vazia. Digite uma instrução acima para enfileirar enquanto a IA carrega ou trabalha.</span>`;
                return;
            }
            
            promptQueue.forEach((prompt, index) => {
                const item = document.createElement('div');
                item.style.display = 'flex';
                item.style.alignItems = 'center';
                item.style.justifyContent = 'space-between';
                item.style.background = 'rgba(255, 255, 255, 0.03)';
                item.style.border = '1px solid rgba(255, 255, 255, 0.05)';
                item.style.borderRadius = '6px';
                item.style.padding = '8px 12px';
                item.style.gap = '10px';
                
                const badgeHtml = `<span style="font-size: 11px; color: var(--warning); background: rgba(255, 214, 0, 0.1); border: 1px solid rgba(255, 214, 0, 0.2); padding: 2px 6px; border-radius: 4px; display: inline-flex; align-items: center; gap: 4px; font-weight: 600; white-space: nowrap;"><span style="width: 6px; height: 6px; border-radius: 50%; background: var(--warning); display: inline-block;"></span>Aguardando IA</span>`;
                
                item.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 4px; flex-grow: 1; min-width: 0;">
                        <span style="font-size: 13px; color: var(--text-main); word-break: break-word;">${escapeHtml(prompt)}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        ${badgeHtml}
                        <button onclick="removePromptFromQueue(${index})" style="background: transparent; border: none; color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 4px; font-size: 16px; transition: all 0.2s;" onmouseover="this.style.color='var(--danger)'; this.style.background='rgba(255, 23, 68, 0.1)'" onmouseout="this.style.color='var(--text-muted)'; this.style.background='transparent'">✕</button>
                    </div>
                `;
                container.appendChild(item);
            });
        }

        // Copy Pre-prompt and Open Aider Chat
        async function copyPromptAndOpenAider() {
            let promptText = document.getElementById('prePromptText').value.trim();
            
            // Merge queued prompts if they exist
            if (promptQueue.length > 0) {
                promptText += "\n\n=== INSTRUÇÕES ADICIONAIS ENFILEIRADAS ===\n";
                promptQueue.forEach((prompt, index) => {
                    promptText += `${index + 1}. ${prompt}\n`;
                });
            }

            try {
                await navigator.clipboard.writeText(promptText);
                console.log('Fila de prompts copiada para a área de transferência.');
            } catch (err) {
                // Fallback copy
                const el = document.createElement('textarea');
                el.value = promptText;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
            }
            
            // Clear the queue and render
            promptQueue = [];
            renderQueue();
            
            // Show feedback
            const feedback = document.getElementById('copyFeedback');
            if (feedback) {
                feedback.style.opacity = '1';
                setTimeout(() => {
                    feedback.style.opacity = '0';
                }, 3000);
            }
            
            // Save paths
            const video_path = document.getElementById('vCopilotInput').value;
            const output_path = document.getElementById('vCopilotOutput').value;
            await fetch(`${API_URL}/api/video_copilot/save_paths`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ video_path, output_path })
            });

            // Start server if not running
            if (!serverRunning) {
                alert('Iniciando o servidor de IA local e o Aider. Aguarde a abertura da aba de chat...');
                await togglePower();
            } else {
                // If server is online, start aider if not started, or notify user
                alert('Fila de prompts copiada com sucesso! Cole o prompt (Ctrl+V) no chat do Aider.');
            }
        }

        // Fetch status of the Copilot processes
        async function fetchCopilotStatus() {
            try {
                const res = await fetch(`${API_URL}/api/video_copilot/status`);
                const data = await res.json();
                
                transcribeRunning = data.transcribe_running;
                renderRunning = data.render_running;
                
                // Update Whisper UI statuses (panel is hidden but elements still exist — use null guards)
                const tStatus = document.getElementById('transcribeStatusText');
                const btnTranscribe = document.getElementById('btnTranscribe');
                const btnStopTranscribe = document.getElementById('btnStopTranscribe');
                if (tStatus) {
                    if (transcribeRunning) {
                        tStatus.innerHTML = '<span class="pulse-text" style="color:var(--warning); font-weight:600;">Executando...</span>';
                    } else {
                        tStatus.innerText = data.transcript_exists ? 'Concluído' : 'Inativo';
                        tStatus.style.color = data.transcript_exists ? 'var(--success)' : 'var(--text-muted)';
                    }
                }
                if (btnTranscribe) btnTranscribe.disabled = transcribeRunning;
                if (btnStopTranscribe) btnStopTranscribe.disabled = !transcribeRunning;

                // Update Render UI statuses
                const rStatus = document.getElementById('renderStatusText');
                const btnRender = document.getElementById('btnRender');
                const btnStopRender = document.getElementById('btnStopRender');
                if (rStatus) {
                    if (renderRunning) {
                        let progressText = "";
                        if (data.job_status && data.job_status.total_segments) {
                            progressText = ` (${data.job_status.current_segment}/${data.job_status.total_segments} segs)`;
                        }
                        rStatus.innerHTML = `<span class="pulse-text" style="color:var(--warning); font-weight:600;">Executando${progressText}...</span>`;
                    } else {
                        if (data.job_status && data.job_status.status === "completed") {
                            rStatus.innerText = 'Concluído';
                            rStatus.style.color = 'var(--success)';
                        } else if (data.job_status && data.job_status.status === "failed") {
                            rStatus.innerText = 'Falhou';
                            rStatus.style.color = 'var(--danger)';
                        } else if (data.job_status && data.job_status.total_segments) {
                            rStatus.innerText = `Pausado (${data.job_status.completed_segments.length}/${data.job_status.total_segments} segs)`;
                            rStatus.style.color = 'var(--warning)';
                        } else {
                            rStatus.innerText = 'Inativo';
                            rStatus.style.color = 'var(--text-muted)';
                        }
                    }
                }
                if (btnRender) btnRender.disabled = renderRunning;
                if (btnStopRender) btnStopRender.disabled = !renderRunning;
                
                // Update chat input transcript status hint
                const chatInput = document.getElementById('chatInput');
                if (chatInput && !transcribeRunning) {
                    if (data.transcript_exists) {
                        chatInput.placeholder = 'Transcrição pronta! Digite instruções para refinar a edição...';
                    } else {
                        chatInput.placeholder = 'Digite suas instruções e clique Enviar — a transcrição será gerada automaticamente na GPU...';
                    }
                }
                
                // Populate paths if loaded and not modified by user
                const inp = document.getElementById('vCopilotInput');
                const out = document.getElementById('vCopilotOutput');
                if (inp && data.current_config.video_path && document.activeElement !== inp) {
                    inp.value = data.current_config.video_path;
                }
                if (out && data.current_config.output_path && document.activeElement !== out) {
                    out.value = data.current_config.output_path;
                }
                
                // Populate project folder display
                const folderPath = document.getElementById('projectFolderPath');
                const folderDisplay = document.getElementById('projectFolderDisplay');
                if (folderPath && folderDisplay) {
                    if (data.current_config.project_folder) {
                        folderPath.innerText = data.current_config.project_folder;
                        folderDisplay.style.display = 'block';
                    } else {
                        folderDisplay.style.display = 'none';
                    }
                }
                
                // Load chat history if project folder changed
                if (data.current_config.project_folder && data.current_config.project_folder !== currentLoadedProjectFolder) {
                    currentLoadedProjectFolder = data.current_config.project_folder;
                    loadChatHistory();
                    
                    // Auto start transcription if it doesn't exist and is not running, and video exists
                    if (data.current_config.video_path && !data.transcript_exists && !data.transcribe_running) {
                        triggerAutoTranscription();
                    }
                }
                
                transcribeRunning = data.transcribe_running;
                if (transcribeRunning && !copilotStatusPoll) {
                    startTranscriptionPolling();
                }

                currentVideoDuration = data.current_config.video_duration || 0;
                
                // Update soundtrack hint/limit text based on video duration
                const hintEl = document.getElementById('soundtrackHint');
                if (hintEl) {
                    if (currentVideoDuration > 120) {
                        hintEl.innerText = `Vídeo longo (${Math.round(currentVideoDuration)}s): você pode selecionar múltiplas músicas separadas por vírgula.`;
                    } else {
                        hintEl.innerText = `Vídeo curto (${Math.round(currentVideoDuration)}s): selecione um arquivo de áudio (.mp3, .wav).`;
                    }
                }
                
                // Populate options checkboxes
                if (data.current_config.options) {
                    const opts = data.current_config.options;
                    const setCheck = (id, val) => { const el = document.getElementById(id); if (el && val !== undefined) el.checked = val; };
                    setCheck('optRemoveSilence', opts.remove_silence);
                    setCheck('optRemoveHesitations', opts.remove_hesitations);
                    setCheck('optVerticalFormat', opts.vertical_format);
                    setCheck('optGenerateChapters', opts.generate_chapters);
                    setCheck('optAddSoundtrack', opts.add_soundtrack);
                    setCheck('optAddTransitions', opts.add_transitions);
                    setCheck('optGenerateSrt', opts.generate_srt);
                    setCheck('optNoiseReduction', opts.noise_reduction);
                    setCheck('optLoudnorm', opts.loudnorm);
                    setCheck('optSmartZoom', opts.smart_zoom);
                    setCheck('optAudioPadding', opts.audio_padding);

                    // Populate soundtrack paths
                    const pathsInput = document.getElementById('soundtrackPathsInput');
                    if (pathsInput && opts.soundtrack_paths) {
                        pathsInput.value = opts.soundtrack_paths.join(', ');
                    }
                    toggleSoundtrackSection();
                }
            } catch (e) {
                console.error("Erro ao carregar status do copiloto:", e);
            }
        }

        // Fetch logs of the Copilot processes
        async function fetchCopilotLogs() {
            if (activeMainTab !== 'video') return;
            
            try {
                const res = await fetch(`${API_URL}/api/video_copilot/logs`);
                const data = await res.json();
                
                const tTerminal = document.getElementById('transcribeTerminal');
                const rTerminal = document.getElementById('renderTerminal');
                
                if (transcribeRunning && data.transcribe_log) {
                    tTerminal.innerHTML = formatLogs(data.transcribe_log);
                    tTerminal.scrollTop = tTerminal.scrollHeight;
                } else if (!transcribeRunning && data.transcribe_log) {
                    tTerminal.innerHTML = formatLogs(data.transcribe_log);
                }
                
                if (renderRunning && data.render_log) {
                    rTerminal.innerHTML = formatLogs(data.render_log);
                    rTerminal.scrollTop = rTerminal.scrollHeight;
                } else if (!renderRunning && data.render_log) {
                    rTerminal.innerHTML = formatLogs(data.render_log);
                }
            } catch (e) {
                console.error("Erro ao obter logs do copiloto:", e);
            }
        }

        // Helper to format logs with color tags
        function formatLogs(rawText) {
            if (!rawText) return "Nenhum log disponível.";
            return rawText.split('\n').map(line => {
                if (line.includes('[INFO]') || line.includes('INFO:')) {
                    return `<span class="info">${escapeHtml(line)}</span>`;
                } else if (line.includes('ERR') || line.includes('ERROR:') || line.includes('FAIL') || line.includes('❌')) {
                    return `<span class="error">${escapeHtml(line)}</span>`;
                } else if (line.includes('WARN') || line.includes('WARNING') || line.includes('⚠️')) {
                    return `<span class="warn">${escapeHtml(line)}</span>`;
                } else if (line.includes('OK') || line.includes('success') || line.includes('SUCESSO') || line.includes('✅') || line.includes('online')) {
                    return `<span class="success">${escapeHtml(line)}</span>`;
                }
                return escapeHtml(line);
            }).join('\n');
        }

        // --- NEW CHAT CO-PILOT FUNCTIONS ---
        
        // Format timestamp for chat messages
        function getChatTimestamp() {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            return `${hours}:${minutes}`;
        }

        // Add message bubble to the UI only (DOM)
        function addMessageToChatUI(sender, text, type = '', timestamp = '') {
            const chatHistory = document.getElementById('chatHistory');
            if (!chatHistory) return;

            const msgWrapper = document.createElement('div');
            msgWrapper.className = 'chat-message-container';

            const bubble = document.createElement('div');
            bubble.className = `chat-message ${sender} ${type}`;
            bubble.innerHTML = text;

            const meta = document.createElement('div');
            meta.className = 'chat-message-meta';
            meta.innerText = timestamp || getChatTimestamp();
            bubble.appendChild(meta);

            msgWrapper.appendChild(bubble);
            chatHistory.appendChild(msgWrapper);

            // Auto scroll to bottom
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        // Add message to chat history UI and save it to the server
        async function addMessageToChat(sender, text, type = '') {
            const timestamp = getChatTimestamp();
            addMessageToChatUI(sender, text, type, timestamp);
            
            // Save to server project folder if selected
            const videoPath = document.getElementById('vCopilotInput').value.trim();
            if (videoPath) {
                try {
                    await fetch(`${API_URL}/api/video_copilot/chat_history`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            message: { sender, text, type, timestamp }
                        })
                    });
                } catch (e) {
                    console.error("Erro ao salvar mensagem no histórico do projeto:", e);
                }
            }
        }

        // Load project chat history from server
        async function loadChatHistory() {
            const chatHistory = document.getElementById('chatHistory');
            if (!chatHistory) return;

            try {
                const res = await fetch(`${API_URL}/api/video_copilot/chat_history`);
                const data = await res.json();
                
                chatHistory.innerHTML = '';
                
                if (data.success && data.history && data.history.length > 0) {
                    data.history.forEach(msg => {
                        addMessageToChatUI(msg.sender, msg.text, msg.type || '', msg.timestamp);
                    });
                } else {
                    initWelcomeMessage();
                }
            } catch (e) {
                console.error("Erro ao carregar histórico de chat:", e);
                initWelcomeMessage();
            } finally {
                updateConsolidatedPrompt();
            }
        }

        // Welcome introduction bubble
        function initWelcomeMessage() {
            const chatHistory = document.getElementById('chatHistory');
            if (chatHistory && chatHistory.children.length === 0) {
                addMessageToChat('copilot', 'Olá! Eu sou o <b>Copiloto de Vídeo IA da NarraVox</b>. 🎙️🎥<br><br>Selecione o vídeo original acima, marque as opções de edição desejadas e digite abaixo suas instruções adicionais para o refinamento da edição (ex: cortes finos, legendas, transições de áudio).<br><br>Quando estiver pronto, clique em <b>Enviar</b> para iniciar a transcrição e abrir a automação de edição do Aider.');
            }
        }

        // Global interval variables for polling
        let copilotStatusPoll = null;

        // Handle sending messages and orchestrating steps
        async function handleChatSend() {
            const chatInput = document.getElementById('chatInput');
            if (!chatInput) return;
            
            const text = chatInput.value.trim();
            if (!text) return;

            // 1. Get video path and validate
            const videoPath = document.getElementById('vCopilotInput').value.trim();
            if (!videoPath) {
                addMessageToChat('copilot', '⚠️ <b>Atenção:</b> Por favor, selecione um arquivo de vídeo acima antes de prosseguir com as instruções de edição.');
                return;
            }

            // Clear input
            chatInput.value = '';

            // 2. Add user bubble to chat
            addMessageToChat('user', text);
            updateConsolidatedPrompt();

            // 3. Save options and paths to server configuration
            await saveCopilotPaths();

            if (transcribeRunning) {
                addMessageToChat('system', '⚠️ <b>[FILA]</b> Transcrição em andamento. Sua mensagem foi salva e a automação do Aider iniciará automaticamente assim que a transcrição terminar.', 'info');
                pendingChatAction = text;
                return;
            }

            // 4. Check if transcription file already exists
            addMessageToChat('system', 'Verificando metadados e arquivos do projeto...', 'info');

            try {
                const res = await fetch(`${API_URL}/api/video_copilot/status`);
                const statusData = await res.json();

                if (!statusData.transcript_exists) {
                    pendingChatAction = text;
                    await triggerAutoTranscription();
                } else {
                    addMessageToChat('system', '✓ Arquivo de transcrição existente encontrado no projeto.');
                    // Proceed to Aider directly
                    await startAiderChatFlow();
                }

            } catch (err) {
                addMessageToChat('copilot', '❌ <b>Erro de comunicação com o servidor:</b> ' + err.message);
            }
        }

        // Consolidated Aider launch orchestration inside the Chat UI
        async function startAiderChatFlow() {
            addMessageToChat('system', 'Preparando prompt consolidado e carregando servidor de IA local...', 'running');

            // Get consolidated prompt and copy to clipboard
            updateConsolidatedPrompt();
            const promptText = document.getElementById('consolidatedPromptText').value;
            
            try {
                await navigator.clipboard.writeText(promptText);
                addMessageToChat('system', '✓ Prompt de edição profissional copiado para a Área de Transferência (Clipboard)!');
            } catch (err) {
                // Fallback copy
                const el = document.createElement('textarea');
                el.value = promptText;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                addMessageToChat('system', '✓ Prompt de edição profissional copiado para a Área de Transferência!');
            }

            // Clear visual queue locally since it has been compiled
            promptQueue = [];
            renderQueue();

            // Run start server API
            try {
                addMessageToChat('system', 'Alocando modelo de linguagem GGUF na VRAM e abrindo Aider...', 'running');
                
                const startRes = await fetch(`${API_URL}/api/start`, { method: 'POST' });
                const startData = await startRes.json();

                if (startRes.ok && startData.success) {
                    serverRunning = true;
                    aiderRunning = true;
                    updateUIState(startData.model_loaded);
                    
                    addMessageToChat('copilot', '🚀 <b>Aider Chat e Servidor local prontos!</b><br><br>1. O Aider abreu uma aba no seu navegador padrão.<br>2. <b>Basta colar (Ctrl+V)</b> o prompt pré-copiado na entrada de chat do Aider para que ele leia a transcrição, monte a lógica de cortes em <code>editar_video_profissional.py</code> e inicie o processamento.');
                } else {
                    addMessageToChat('copilot', '❌ <b>Erro ao iniciar IA/Aider:</b> ' + (startData.error || 'Erro desconhecido.'));
                }
            } catch (err) {
                addMessageToChat('copilot', '❌ <b>Falha crítica ao iniciar Aider:</b> ' + err.message);
            }
        }

        // Run Quick Actions (MP3, 10s Preview, Speedup, Denoise, Translation)
        async function runQuickAction(action) {
            const videoPath = document.getElementById('vCopilotInput').value.trim();
            if (!videoPath) {
                addMessageToChat('copilot', '⚠️ <b>Atenção:</b> Por favor, selecione um arquivo de vídeo acima antes de executar ações rápidas.');
                return;
            }
            
            // Save paths/options first to sync configs
            await saveCopilotPaths();
            
            addMessageToChat('system', `Iniciando ação rápida: ${action}...`, 'running');
            
            // Scroll to rendering terminal to show logs
            const renderTerminal = document.getElementById('renderTerminal');
            if (renderTerminal) {
                renderTerminal.scrollIntoView({ behavior: 'smooth' });
            }
            
            try {
                const res = await fetch(`${API_URL}/api/video_copilot/quick_action`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action })
                });
                const data = await res.json();
                
                if (data.success) {
                    addMessageToChat('system', `✓ Ação '${action}' iniciada. Acompanhe os logs abaixo!`);
                    fetchCopilotStatus();
                } else {
                    addMessageToChat('copilot', `❌ <b>Erro na ação rápida:</b> ${data.error}`);
                }
            } catch (err) {
                addMessageToChat('copilot', `❌ <b>Erro de comunicação:</b> ${err.message}`);
            }
        }

        // Analyze clips and hooks via local LLM
        async function analyzeClips() {
            const videoPath = document.getElementById('vCopilotInput').value.trim();
            if (!videoPath) {
                addMessageToChat('copilot', '⚠️ <b>Atenção:</b> Por favor, selecione um arquivo de vídeo acima antes de analisar clipes.');
                return;
            }
            
            const btn = document.getElementById('btnAnalyzeClips');
            const status = document.getElementById('clipsStatusText');
            const resultsDiv = document.getElementById('clipsAnalysisResults');
            
            if (btn) btn.disabled = true;
            if (status) {
                status.innerHTML = '<span class="pulse-text" style="color:var(--warning); font-weight:600;">Analisando...</span>';
            }
            
            addMessageToChat('system', 'Enviando transcrição para análise da IA local (Gemma/Qwen)...', 'running');
            
            try {
                const res = await fetch(`${API_URL}/api/video_copilot/analyze_clips`, {
                    method: 'POST'
                });
                const data = await res.json();
                
                if (data.success && data.analysis) {
                    const analysis = data.analysis;
                    
                    // Populate hooks
                    const hooksList = document.getElementById('scriptedHooksList');
                    if (hooksList) {
                        hooksList.innerHTML = '';
                        const hooks = analysis.scripted_hooks || [];
                        hooks.forEach(hook => {
                            const li = document.createElement('li');
                            li.innerHTML = hook;
                            hooksList.appendChild(li);
                        });
                    }
                    
                    // Populate existing hook
                    const existingHookEl = document.getElementById('existingHookText');
                    if (existingHookEl) {
                        existingHookEl.innerText = analysis.existing_hook || "Nenhum gancho detectado ou sugerido.";
                    }
                    
                    // Populate recommended clips
                    const clipsList = document.getElementById('recommendedClipsList');
                    if (clipsList) {
                        clipsList.innerHTML = '';
                        const clips = analysis.recommended_clips || [];
                        
                        if (clips.length === 0) {
                            clipsList.innerHTML = '<span style="font-size: 13px; color: var(--text-muted); font-style: italic;">Nenhum clipe sugerido.</span>';
                        }
                        
                        clips.forEach((clip, index) => {
                            const item = document.createElement('div');
                            item.style.background = 'rgba(255, 255, 255, 0.03)';
                            item.style.border = '1px solid rgba(255, 255, 255, 0.05)';
                            item.style.borderRadius = '8px';
                            item.style.padding = '12px';
                            item.style.display = 'flex';
                            item.style.flexDirection = 'column';
                            item.style.gap = '8px';
                            
                            item.innerHTML = `
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
                                    <span style="font-size: 14px; font-weight: 600; color: var(--primary);">${clip.title || 'Clipe ' + (index + 1)}</span>
                                    <span style="font-size: 12px; font-weight: 600; background: rgba(79,172,254,0.1); border: 1px solid rgba(79,172,254,0.2); color: var(--primary); padding: 2px 6px; border-radius: 4px; font-family: monospace;">
                                        ${clip.start}s - ${clip.end}s (Dur: ${(clip.end - clip.start).toFixed(1)}s)
                                    </span>
                                </div>
                                <p style="font-size: 13px; color: var(--text-main); margin: 2px 0;">${clip.reason || ''}</p>
                                <div style="display: flex; gap: 8px; margin-top: 4px;">
                                    <button class="btn-secondary" onclick="cutClip(${clip.start}, ${clip.end}, 'horizontal')" style="font-size: 11px; padding: 6px 12px; border-radius: 6px; display: inline-flex; align-items: center; gap: 4px;">
                                        🎬 Horizontal (16:9)
                                    </button>
                                    <button class="btn-secondary" onclick="cutClip(${clip.start}, ${clip.end}, 'vertical')" style="font-size: 11px; padding: 6px 12px; border-radius: 6px; display: inline-flex; align-items: center; gap: 4px; border-color: rgba(0,242,254,0.2); color: var(--secondary);">
                                        📱 Vertical (9:16)
                                    </button>
                                </div>
                            `;
                            clipsList.appendChild(item);
                        });
                    }
                    
                    if (status) {
                        status.innerText = 'Concluído';
                        status.style.color = 'var(--success)';
                    }
                    if (resultsDiv) resultsDiv.style.display = 'flex';
                    addMessageToChat('copilot', '🚀 <b>Análise de Clipes e Ganchos concluída!</b> Veja as recomendações sugeridas no painel do Estúdio de Clipes.');
                } else {
                    if (status) {
                        status.innerText = 'Falhou';
                        status.style.color = 'var(--danger)';
                    }
                    addMessageToChat('copilot', '❌ <b>Erro na análise de clipes:</b> ' + (data.error || 'A IA não retornou dados estruturados.'));
                }
            } catch (err) {
                if (status) {
                    status.innerText = 'Falhou';
                    status.style.color = 'var(--danger)';
                }
                addMessageToChat('copilot', '❌ <b>Erro ao conectar com o servidor:</b> ' + err.message);
            } finally {
                if (btn) btn.disabled = false;
            }
        }

        // Cut clip using FFmpeg
        async function cutClip(start, end, format) {
            addMessageToChat('system', `Iniciando recorte de clipe (${format}): ${start}s até ${end}s...`, 'running');
            
            // Scroll to rendering terminal to show logs
            const renderTerminal = document.getElementById('renderTerminal');
            if (renderTerminal) {
                renderTerminal.scrollIntoView({ behavior: 'smooth' });
            }
            
            try {
                const res = await fetch(`${API_URL}/api/video_copilot/cut_clip`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ start, end, format })
                });
                const data = await res.json();
                
                if (data.success) {
                    addMessageToChat('system', `✓ Recorte do clipe de ${start}s a ${end}s (${format}) iniciado. Acompanhe os logs abaixo!`);
                    fetchCopilotStatus();
                } else {
                    addMessageToChat('copilot', `❌ <b>Erro ao recortar clipe:</b> ${data.error}`);
                }
            } catch (err) {
                addMessageToChat('copilot', `❌ <b>Erro de rede:</b> ${err.message}`);
            }
        }

        // Copy Terminal Logs to Clipboard
        function copyTerminalLogs() {
            const terminal = document.getElementById('terminalBody');
            if (!terminal) return;
            const text = terminal.innerText;
            navigator.clipboard.writeText(text).then(() => {
                alert('Logs do Console de Inicialização copiados!');
            }).catch(err => {
                const el = document.createElement('textarea');
                el.value = text;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                alert('Logs do Console de Inicialização copiados!');
            });
        }
        
        // Copy Render Logs to Clipboard
        function copyRenderLogs() {
            const terminal = document.getElementById('renderTerminal');
            if (!terminal) return;
            const text = terminal.innerText;
            navigator.clipboard.writeText(text).then(() => {
                alert('Logs do Renderizador copiados!');
            }).catch(err => {
                const el = document.createElement('textarea');
                el.value = text;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                alert('Logs do Renderizador copiados!');
            });
        }
