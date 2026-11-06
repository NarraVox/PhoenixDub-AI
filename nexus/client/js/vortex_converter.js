// -*- coding: utf-8 -*-
// VORTEX CONVERTER UI - Módulo Frontend para Conversão Inteligente de Músicas & Vídeos H.265/H.264
// Copyright (c) 2026 Paulo Henrik Carvalho de Araújo

let converterQueue = [];
let conversionPollTimer = null;
let currentConversionMode = 'music'; // 'music' | 'video_h265'
let itemStatuses = {}; // path -> { status, progress, skip_reason, explanation }

function safeLog(msg) {
    if (typeof logToTerminal === 'function') {
        logToTerminal(msg);
    } else {
        console.log('[CONVERTER]', msg);
    }
}

function formatMb(mb) {
    if (!Number.isFinite(mb) || mb <= 0) return '0 MB';
    if (mb >= 1024) return `${(mb / 1024).toFixed(2)} GB`;
    return `${mb.toFixed(0)} MB`;
}

function setConversionMode(mode) {
    currentConversionMode = mode;
    const btnMusic = document.getElementById('tab-mode-music');
    const btnVideo = document.getElementById('tab-mode-video');
    const panelMusic = document.getElementById('panel-music-opts');
    const panelVideo = document.getElementById('panel-video-opts');

    if (mode === 'music') {
        btnMusic.classList.add('active-tab');
        btnVideo.classList.remove('active-tab');
        if (panelMusic) panelMusic.style.display = 'grid';
        if (panelVideo) panelVideo.style.display = 'none';
    } else {
        btnVideo.classList.add('active-tab');
        btnMusic.classList.remove('active-tab');
        if (panelMusic) panelMusic.style.display = 'none';
        if (panelVideo) panelVideo.style.display = 'grid';
    }
}

async function addFilesToConverter() {
    try {
        let filter = "Músicas e Áudios (*.mp3;*.wav;*.flac;*.aac;*.ogg;*.m4a)|Vídeos (*.mp4;*.mkv;*.avi;*.mov)|Todos (*.*)";
        if (currentConversionMode === 'video_h265') {
            filter = "Vídeos (*.mp4;*.m4v;*.mkv;*.avi;*.mov;*.wmv;*.webm;*.flv;*.ts;*.h264;*.h265;*.hevc)|Todos (*.*)";
        }

        let paths = null;
        if (window.pywebview && window.pywebview.api && window.pywebview.api.open_file_dialog) {
            const res = await window.pywebview.api.open_file_dialog(filter, true);
            if (!res) return;
            paths = Array.isArray(res) ? res : [res];
        } else {
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.multiple = true;
            fileInput.onchange = (e) => {
                const fl = Array.from(e.target.files).map(f => f.path || f.name);
                enqueueConverterFiles(fl);
            };
            fileInput.click();
            return;
        }

        if (paths && paths.length > 0) {
            enqueueConverterFiles(paths);
        }
    } catch (e) {
        console.error('[CONVERTER] Erro ao selecionar arquivos:', e);
        safeLog(`❌ [CONVERTER] Erro de seleção: ${e.message}`);
    }
}

async function enqueueConverterFiles(paths) {
    const newPaths = [];
    paths.forEach(p => {
        const name = p.split(/[\\\/]/).pop();
        if (!converterQueue.some(item => item.path === p)) {
            const item = {
                path: p,
                name: name,
                mode: currentConversionMode,
                info: null,
                plan: null
            };
            converterQueue.push(item);
            newPaths.push(p);
            safeLog(`[FILA] Adicionado: ${name} (${currentConversionMode === 'music' ? 'Música' : 'Vídeo'})`);
        }
    });

    renderConverterQueue();

    if (newPaths.length > 0) {
        await probeBatchPaths(newPaths);
    }
}

async function probeBatchPaths(paths) {
    try {
        const maxRes = document.getElementById('sel-video-max-res')?.value || '1080p';
        const targetCodec = document.getElementById('sel-video-codec')?.value || 'h265';
        const videoAudioBitrate = document.getElementById('sel-video-audio-bitrate')?.value || '160k';
        const skipLess10 = document.getElementById('chk-skip-less-10')?.checked !== false;

        const resp = await fetch('http://127.0.0.1:5003/api/probe_media_batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                paths: paths,
                target_codec: targetCodec,
                max_res: maxRes,
                audio_bitrate: videoAudioBitrate,
                skip_if_less_10_pct: skipLess10
            })
        });
        const data = await resp.json();
        if (data && data.results) {
            data.results.forEach(res => {
                const item = converterQueue.find(it => it.path === res.path);
                if (item) {
                    item.info = res.info;
                    item.plan = res.plan;
                }
            });
            renderConverterQueue();
        }
    } catch (e) {
        console.warn('[PROBE] Falha ao analisar mídias:', e);
    }
}

async function recalculateQueuePlans() {
    const paths = converterQueue.map(it => it.path);
    if (paths.length > 0) {
        await probeBatchPaths(paths);
    }
}

function renderConverterQueue() {
    const listEl = document.getElementById('converter-queue-list');
    const summaryEl = document.getElementById('converter-queue-summary');
    const badgeCount = document.getElementById('converter-queue-count');
    const btnStart = document.getElementById('btn-start-conversion');

    if (badgeCount) badgeCount.textContent = `${converterQueue.length} arquivo(s)`;

    if (converterQueue.length === 0) {
        listEl.innerHTML = '<div style="text-align:center; padding: 25px; color: rgba(255,255,255,0.2); font-size: 0.8rem; letter-spacing: 1px;">Nenhum arquivo na fila de conversão. Adicione músicas ou vídeos acima.</div>';
        if (summaryEl) summaryEl.style.display = 'none';
        if (btnStart) btnStart.disabled = true;
        return;
    }

    if (btnStart) btnStart.disabled = false;

    // 1. Calcula Resumo Geral da Fila (Antes vs Depois)
    let totalOrigMb = 0;
    let totalEstMb = 0;
    let hasVideoEstimates = false;

    converterQueue.forEach(item => {
        if (item.info && item.info.is_video && item.plan) {
            hasVideoEstimates = true;
            const om = item.info.size_mb || 0;
            const em = (item.plan.action === 'skip' || item.plan.action === 'remux') ? om : (item.plan.estimated_size_mb || om);
            totalOrigMb += om;
            totalEstMb += em;
        }
    });

    if (summaryEl) {
        if (hasVideoEstimates && totalOrigMb > 0) {
            const totalSavedMb = Math.max(0, totalOrigMb - totalEstMb);
            const totalPct = Math.round((totalSavedMb / totalOrigMb) * 100);
            summaryEl.style.display = 'block';
            summaryEl.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between; background: linear-gradient(90deg, rgba(0, 255, 170, 0.1) 0%, rgba(0, 200, 255, 0.06) 100%); border: 1px solid rgba(0, 255, 170, 0.35); border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; font-size: 0.68rem;">
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="font-size: 0.9rem;">📊</span>
                        <span style="color: #8899a6; font-weight: 700;">TOTAL ESTIMADO:</span>
                        <span style="color: #ffffff; font-weight: 800;">${formatMb(totalOrigMb)}</span>
                        <span style="color: #00c8ff; font-weight: 900;">➔</span>
                        <span style="color: #00ffaa; font-weight: 800;">${formatMb(totalEstMb)}</span>
                    </div>
                    <span style="background: ${totalPct > 0 ? '#00ffaa' : 'rgba(255,255,255,0.1)'}; color: ${totalPct > 0 ? '#000' : '#fff'}; font-weight: 900; padding: 3px 10px; border-radius: 4px; font-size: 0.65rem; box-shadow: ${totalPct > 0 ? '0 0 10px rgba(0,255,170,0.5)' : 'none'};">
                        ${totalPct > 0 ? `ECONOMIA: -${totalPct}% (-${formatMb(totalSavedMb)})` : 'SEM ALTERAÇÃO DE TAMANHO'}
                    </span>
                </div>
            `;
        } else {
            summaryEl.style.display = 'none';
        }
    }

    // 2. Renderiza Itens Individuais com Bloco Antes/Depois
    listEl.innerHTML = converterQueue.map((item, idx) => {
        const isMusic = item.mode === 'music';
        const st = itemStatuses[item.path] || { status: 'pending', progress: 0 };
        const info = item.info;
        const plan = item.plan;

        let statusBadge = `<span style="background: rgba(255, 255, 255, 0.06); color: #8899a6; font-weight: 700; padding: 3px 8px; border-radius: 4px; font-size: 0.65rem;">⏳ NA FILA</span>`;
        let cardBorder = 'border: 1px solid rgba(255,204,0,0.15); background: rgba(255,255,255,0.03);';
        let miniBar = '';

        if (st.status === 'converting') {
            cardBorder = 'border: 1px solid #ffaa00; background: rgba(255, 170, 0, 0.09); box-shadow: 0 0 15px rgba(255, 170, 0, 0.25);';
            statusBadge = `<span style="background: #ffaa00; color: #000; font-weight: 900; padding: 3px 10px; border-radius: 4px; font-size: 0.72rem; box-shadow: 0 0 12px rgba(255,170,0,0.6);">⚡ ${st.progress}%</span>`;
            miniBar = `
                <div style="width: 100%; height: 5px; background: rgba(0,0,0,0.5); border-radius: 3px; overflow: hidden; margin-top: 8px;">
                    <div style="width: ${st.progress}%; height: 100%; background: linear-gradient(90deg, #ff5500, #ffaa00); box-shadow: 0 0 8px #ffaa00; transition: width 0.3s ease;"></div>
                </div>
            `;
        } else if (st.status === 'done') {
            cardBorder = 'border: 1px solid rgba(0, 255, 100, 0.4); background: rgba(0, 255, 100, 0.04);';
            statusBadge = `<span style="background: rgba(0, 255, 100, 0.15); border: 1px solid #00ff64; color: #00ff64; font-weight: 900; padding: 3px 8px; border-radius: 4px; font-size: 0.65rem;">✅ CONCLUÍDO</span>`;
        } else if (st.status === 'skipped') {
            cardBorder = 'border: 1px solid rgba(255, 170, 0, 0.4); background: rgba(255, 170, 0, 0.05);';
            statusBadge = `<span style="background: rgba(255, 170, 0, 0.15); border: 1px solid #ffaa00; color: #ffaa00; font-weight: 900; padding: 3px 8px; border-radius: 4px; font-size: 0.65rem;" title="${st.skip_reason || 'Economia inferior a 10%'}">⏭️ PULADO (&lt;10%)</span>`;
        } else if (st.status === 'error') {
            cardBorder = 'border: 1px solid rgba(255, 60, 60, 0.4); background: rgba(255, 60, 60, 0.04);';
            statusBadge = `<span style="background: rgba(255, 60, 60, 0.2); border: 1px solid #ff4444; color: #ff6666; font-weight: 900; padding: 3px 8px; border-radius: 4px; font-size: 0.65rem;">❌ ERRO</span>`;
        }

        // Bloco detalhado Antes / Depois
        let estimateBarHtml = '';
        if (info && info.is_video && plan) {
            const origMb = info.size_mb || 0;
            const estMb = (plan.action === 'skip' || plan.action === 'remux') ? origMb : (plan.estimated_size_mb || origMb);
            const savings = (plan.action === 'skip' || plan.action === 'remux') ? 0 : (plan.savings_pct || 0);
            const diffMb = Math.max(0, origMb - estMb);

            let pillHtml = '';
            if (plan.action === 'remux') {
                pillHtml = `<span style="background: rgba(0, 200, 255, 0.15); border: 1px solid #00c8ff; color: #00c8ff; font-weight: 800; padding: 2px 7px; border-radius: 4px; font-size: 0.62rem;">⚡ REMUX EM ~5s (0% GPU)</span>`;
            } else if (plan.action === 'skip') {
                pillHtml = `<span style="background: rgba(255, 170, 0, 0.15); border: 1px solid #ffaa00; color: #ffaa00; font-weight: 800; padding: 2px 7px; border-radius: 4px; font-size: 0.62rem;">⏭️ JÁ OTIMIZADO (&lt;10%)</span>`;
            } else if (savings >= 10) {
                pillHtml = `<span style="background: rgba(0, 255, 170, 0.18); border: 1px solid #00ffaa; color: #00ffaa; font-weight: 900; padding: 2px 7px; border-radius: 4px; font-size: 0.64rem;">📉 -${savings.toFixed(0)}% (-${formatMb(diffMb)})</span>`;
            } else {
                pillHtml = `<span style="background: rgba(255, 255, 255, 0.08); color: #ccc; font-weight: 700; padding: 2px 6px; border-radius: 4px; font-size: 0.62rem;">Mesmo tamanho est.</span>`;
            }

            estimateBarHtml = `
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 6px; padding: 5px 8px; background: rgba(0,0,0,0.35); border-radius: 5px; border: 1px solid rgba(255,255,255,0.06); font-size: 0.64rem;">
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <span style="color: #8899a6; font-size: 0.58rem; font-weight: 800;">ANTES:</span>
                        <span style="color: #ffffff; font-weight: 800;">${formatMb(origMb)}</span>
                        <span style="color: #667788; font-size: 0.6rem;">(${info.resolution_label})</span>
                    </div>
                    <span style="color: #00c8ff; font-weight: 900;">➔</span>
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <span style="color: #8899a6; font-size: 0.58rem; font-weight: 800;">DEPOIS (EST.):</span>
                        <span style="color: #00ffaa; font-weight: 800;">${formatMb(estMb)}</span>
                        <span style="color: #667788; font-size: 0.6rem;">(${plan.target_res_label})</span>
                    </div>
                    <div>${pillHtml}</div>
                </div>
            `;
        }

        const canRemove = st.status !== 'converting';

        return `
            <div class="queue-item-card" style="display:flex; flex-direction:column; ${cardBorder} border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; transition: all 0.25s ease;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="display:flex; align-items:center; gap: 10px; overflow:hidden; flex: 1;">
                        <span style="font-size: 1.3rem;">${isMusic ? '🎵' : '🎬'}</span>
                        <div style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width: 380px;">
                            <div style="font-size: 0.78rem; font-weight: 800; color: #fff; overflow:hidden; text-overflow:ellipsis;">${item.name}</div>
                            <div style="font-size: 0.62rem; color: ${isMusic ? '#00ffaa' : '#00c8ff'}; font-weight: 600;">
                                ${isMusic ? 'Música / Áudio' : (info ? `${info.codec.toUpperCase()} • ${info.resolution_label}` : 'Vídeo H.265 / H.264')}
                            </div>
                        </div>
                    </div>
                    <div style="display:flex; align-items:center; gap: 10px;">
                        ${statusBadge}
                        ${canRemove ? `<button onclick="removeQueueItem(${idx})" style="background:rgba(255,60,60,0.15); border:1px solid #ff4444; color:#ff6666; border-radius:4px; padding:4px 8px; font-size:0.65rem; cursor:pointer;" title="Remover da fila">✕</button>` : ''}
                    </div>
                </div>
                ${estimateBarHtml}
                ${miniBar}
            </div>
        `;
    }).join('');
}

function removeQueueItem(idx) {
    if (idx >= 0 && idx < converterQueue.length) {
        converterQueue.splice(idx, 1);
        renderConverterQueue();
    }
}

function clearConverterQueue() {
    converterQueue = [];
    itemStatuses = {};
    renderConverterQueue();
    fetch('http://127.0.0.1:5003/api/conversion_clear', { method: 'POST' }).catch(() => {});
}

async function startBatchConversion() {
    if (converterQueue.length === 0) {
        alert('Adicione arquivos à fila antes de iniciar.');
        return;
    }

    const audioBitrate = document.getElementById('sel-audio-bitrate')?.value || '160k';
    const audioFormat = document.getElementById('sel-audio-format')?.value || 'mp3';
    const videoAudioBitrate = document.getElementById('sel-video-audio-bitrate')?.value || '160k';
    const maxRes = document.getElementById('sel-video-max-res')?.value || '1080p';
    const targetCodec = document.getElementById('sel-video-codec')?.value || 'h265';
    const skipLess10 = document.getElementById('chk-skip-less-10')?.checked !== false;

    itemStatuses = {};
    converterQueue.forEach(it => {
        itemStatuses[it.path] = { status: 'pending', progress: 0 };
    });
    renderConverterQueue();

    const items = converterQueue.map(item => ({
        input_path: item.path,
        mode: item.mode,
        format: item.mode === 'music' ? audioFormat : 'mp4',
        audio_bitrate: item.mode === 'music' ? audioBitrate : videoAudioBitrate,
        video_bitrate: null,
        target_codec: targetCodec,
        max_res: maxRes,
        skip_if_less_10_pct: skipLess10,
        orientation: 'auto' // a conversão sempre mantém o formato original
    }));

    const statusEl = document.getElementById('conversion-status-box');
    if (statusEl) statusEl.style.display = 'block';

    try {
        safeLog(`🚀 [CONVERTER] Enviando ${items.length} item(ns) para fila de conversão...`);
        const resp = await fetch('http://127.0.0.1:5003/api/convert_batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ items: items })
        });
        const res = await resp.json();

        if (res.success) {
            safeLog(`✅ [CONVERTER] Fila iniciada: ${res.message}`);
            startConversionPolling();
        } else {
            alert(`Erro ao iniciar conversão: ${res.message}`);
            safeLog(`❌ [CONVERTER] Erro: ${res.message}`);
        }
    } catch (e) {
        alert('Erro ao conectar com o motor Vortex (porta 5003).');
        safeLog(`❌ [CONVERTER] Falha de conexão: ${e.message}`);
    }
}

function startConversionPolling() {
    if (conversionPollTimer) clearInterval(conversionPollTimer);

    const queueProgBar = document.getElementById('conv-progress-bar');
    const queueProgVal = document.getElementById('conv-percent-label');
    const statusMsg = document.getElementById('conv-status-text');

    const itemFilename = document.getElementById('conv-item-filename');
    const itemDetails = document.getElementById('conv-item-details');
    const itemTelemetry = document.getElementById('conv-item-telemetry');
    const itemPercent = document.getElementById('conv-item-percent');
    const itemProgressBar = document.getElementById('conv-item-progress-bar');

    conversionPollTimer = setInterval(async () => {
        try {
            const resp = await fetch('http://127.0.0.1:5003/api/conversion_status');
            const data = await resp.json();

            // 1. Atualiza bloco da Fila Geral
            if (queueProgBar) queueProgBar.style.width = `${data.overall_progress}%`;
            if (queueProgVal) queueProgVal.textContent = `${data.overall_progress}%`;
            const totalCount = data.queue_count + data.history_count;
            if (statusMsg) {
                statusMsg.textContent = `📊 FILA TOTAL: (${data.history_count}/${totalCount || 1} PROCESSADOS)`;
            }

            // 2. Atualiza bloco do Arquivo Individual
            if (data.current_item) {
                const cur = data.current_item;
                const isMusic = cur.mode === 'audio';
                if (itemFilename) itemFilename.textContent = cur.filename || 'Processando...';
                if (itemPercent) itemPercent.textContent = `${data.item_progress}%`;
                if (itemProgressBar) itemProgressBar.style.width = `${data.item_progress}%`;

                if (itemDetails) {
                    if (isMusic) {
                        itemDetails.textContent = `Áudio ${cur.format.toUpperCase()} • Taxa: ${cur.audio_bitrate} • Codificando...`;
                    } else {
                        const srcLabel = cur.info?.resolution_label || 'Vídeo';
                        const codecLabel = cur.info?.codec ? cur.info.codec.toUpperCase() : 'H.265';
                        const targetLabel = cur.plan?.target_res_label || '1080p Full HD';
                        const fpsStr = Number.isFinite(cur.fps) ? `${cur.fps.toFixed(1)} quadros/s` : 'medindo fps';
                        const spdStr = Number.isFinite(cur.speed) ? `${cur.speed.toFixed(2)}× real` : 'medindo veloc.';
                        itemDetails.textContent = `${srcLabel} ${codecLabel} ➔ ${targetLabel} • ${fpsStr} • ${spdStr} • Áudio: ${cur.audio_bitrate}`;
                    }
                }

                if (itemTelemetry) {
                    const expl = cur.explanation || cur.plan?.explanation;
                    if (expl) {
                        itemTelemetry.style.display = 'block';
                        itemTelemetry.innerHTML = `<strong>ℹ️ Detalhe da Operação:</strong> ${expl}`;
                    } else {
                        itemTelemetry.style.display = 'none';
                    }
                }
            } else if (!data.is_running) {
                if (itemFilename) itemFilename.textContent = 'Fila de conversão finalizada!';
                if (itemPercent) itemPercent.textContent = '100%';
                if (itemProgressBar) itemProgressBar.style.width = '100%';
                if (itemDetails) itemDetails.textContent = 'Todos os arquivos foram processados.';
                if (itemTelemetry) itemTelemetry.style.display = 'none';
            }

            // 3. Atualiza mapa de status dos itens para refletir na lista
            if (data.history) {
                data.history.forEach(h => {
                    itemStatuses[h.input_path] = {
                        status: h.status,
                        progress: 100,
                        skip_reason: h.skip_reason,
                        explanation: h.explanation
                    };
                });
            }
            if (data.current_item) {
                itemStatuses[data.current_item.input_path] = {
                    status: 'converting',
                    progress: data.item_progress,
                    explanation: data.current_item.explanation
                };
            }
            renderConverterQueue();

            if (!data.is_running && data.queue_count === 0) {
                clearInterval(conversionPollTimer);
                conversionPollTimer = null;
                safeLog(`🎉 [CONVERTER] Lote concluído com sucesso!`);
            }
        } catch (e) {
            console.error('[POLL] Erro de status:', e);
        }
    }, 450);
}

async function cancelConversion() {
    try {
        await fetch('http://127.0.0.1:5003/api/conversion_cancel', { method: 'POST' });
        safeLog(`🛑 [CONVERTER] Cancelamento solicitado.`);
    } catch (e) {}
}

async function openConvertedFolder() {
    const status = document.getElementById('converter-folder-status');
    const showStatus = message => {
        if (status) status.textContent = message;
        try { safeLog(message); } catch (error) { console.warn(error); }
    };
    showStatus('Abrindo a pasta de conversões...');
    const errors = [];
    const nativeOpen = window.pywebview?.api?.open_conversions_folder;
    if (typeof nativeOpen === 'function') {
        try {
            const result = await nativeOpen();
            if (result?.success === true) {
                showStatus(`Abertura solicitada ao Explorador: ${result.folder}`);
                return;
            }
            errors.push(result?.error || 'Abertura nativa indisponível');
        } catch (error) { errors.push(error.message); }
    }
    for (const url of [
        'http://127.0.0.1:5000/api/open_conversions_folder',
        'http://127.0.0.1:5003/api/open_output_folder'
    ]) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);
        try {
            const response = await fetch(url, { method: 'POST', signal: controller.signal });
            clearTimeout(timeout);
            if (!response.ok) {
                errors.push(`HTTP ${response.status} de ${url}`);
                continue;
            }
            const data = await response.json();
            if (data?.success === true && data.folder) {
                showStatus(`Abertura solicitada ao Explorador: ${data.folder}`);
                return;
            }
            errors.push(data?.error || `Resposta inválida de ${url}`);
        } catch (error) {
            clearTimeout(timeout);
            errors.push(error.name === 'AbortError' ? `Timeout em ${url}` : error.message);
        }
    }
    showStatus('Não foi possível abrir a pasta de conversões automaticamente.');
    safeLog(`❌ [CONVERTER] Falha ao abrir pasta: ${errors.join(' | ')}`);
}

function toggleConverterPanel() {
    const modal = document.getElementById('converter-modal');
    if (!modal) return;
    const isVisible = modal.style.display === 'flex';
    modal.style.display = isVisible ? 'none' : 'flex';
    if (!isVisible) {
        renderConverterQueue();
    }
}

// Expõe globalmente
window.setConversionMode = setConversionMode;
window.addFilesToConverter = addFilesToConverter;
window.enqueueConverterFiles = enqueueConverterFiles;
window.removeQueueItem = removeQueueItem;
window.clearConverterQueue = clearConverterQueue;
window.startBatchConversion = startBatchConversion;
window.cancelConversion = cancelConversion;
window.openConvertedFolder = openConvertedFolder;
window.toggleConverterPanel = toggleConverterPanel;
window.recalculateQueuePlans = recalculateQueuePlans;
