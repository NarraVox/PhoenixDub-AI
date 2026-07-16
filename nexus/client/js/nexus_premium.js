const glow = document.getElementById('mouse-glow');
        document.addEventListener('mousemove', (e) => {
            glow.style.left = e.clientX + 'px';
            glow.style.top = e.clientY + 'px';
        });

        async function runSecurityAudit() {
            const led = document.getElementById('sentinel-led');
            const text = document.getElementById('sentinel-text');
            
            text.innerText = "ESCANER ATIVO...";
            led.style.background = "#ffff00";
            led.style.boxShadow = "0 0 10px #ffff00";

            try {
                const res = await fetch('/api/security_audit');
                const data = await res.json();
                
                if (data.status === "safe") {
                    led.style.background = "var(--neon-cyan)";
                    led.style.boxShadow = "0 0 10px var(--neon-cyan)";
                    text.innerText = "SISTEMA ÍNTEGRO";
                    alert(data.message);
                } else if (data.status === "danger") {
                    led.style.background = "var(--neon-red)";
                    led.style.boxShadow = "0 0 20px var(--neon-red)";
                    text.innerText = "PERIGO DETECTADO!";
                    
                    let errorMsg = "⚠️ ALERTA DE SEGURANÇA ⚠️\n\n" + data.message + "\n\n";
                    data.details.forEach(v => {
                        errorMsg += `- ${v.package}: ${v.advisory}\n`;
                    });
                    errorMsg += "\nPOR FAVOR, COMUNIQUE O DESENVOLVEDOR IMEDIATAMENTE!";
                    
                    if(confirm(errorMsg + "\n\nDeseja tentar o AUTO-REPARO SEGURO agora?")) {
                        runSecurityRepair();
                    }
                } else {
                    alert("Erro na auditoria: " + data.message);
                    text.innerText = "ERRO NO ESCANER";
                }
            } catch(e) {
                alert("Falha ao conectar com o motor de segurança.");
                text.innerText = "OFFLINE";
            }
        }

        async function runSecurityRepair() {
            const text = document.getElementById('sentinel-text');
            text.innerText = "REPARANDO AMBIENTE...";
            
            try {
                const res = await fetch('/api/security_repair', { method: 'POST' });
                const data = await res.json();
                alert(data.message);
                location.reload(); // Recarrega para garantir que tudo suba limpo
            } catch(e) {
                alert("Erro crítico durante o reparo.");
            }
        }

        async function restartServer() {
            if (confirm("Deseja realmente reiniciar o servidor mestre? Isso interromperá todos os processos ativos (Whisper, Gemma, etc).")) {
                try {
                    // [v2026.KILL_SWITCH] Tenta parar os motores pesados antes de reiniciar
                    console.log("🛑 [MASTER] Enviando comando de parada para os motores...");
                    await fetch('http://127.0.0.1:5005/api/stop_job', { method: 'POST' }).catch(() => null);
                    
                    const res = await fetch('/api/restart_server', { method: 'POST' });
                    alert("Comando de reinicialização total enviado. O sistema voltará em breve.");
                } catch(e) {
                    alert("Erro ao enviar comando de reinicialização.");
                }
            }
        }

        let isHoveringTelemetry = false;
        document.querySelectorAll('.telemetry-box').forEach(box => {
            box.addEventListener('mouseenter', () => isHoveringTelemetry = true);
            box.addEventListener('mouseleave', () => isHoveringTelemetry = false);
        });

        async function updateTelemetry() {
            if (isHoveringTelemetry) return;
            
            try {
                // 1. Heartbeat do Servidor Principal (Porta 5000)
                const checkMain = await fetch('/').catch(() => null);
                if (!checkMain) {
                    document.getElementById('conn-guard').style.display = 'flex';
                } else if (document.getElementById('conn-guard').style.display === 'flex') {
                    location.reload(); 
                }

                // 2. Mapeamento de Motores e IDs de Status
                const engines = [
                    { port: 5002, id: 'games-status', name: 'TITAN GAMES' },
                    { port: 5003, id: 'vortex-status', name: 'VORTEX EDITOR' },
                    { port: 5004, id: 'video-status', name: 'TITAN VIDEO' },
                    { port: 5005, id: 'dj-status', name: 'VORTEX DJ' }
                ];

                // Consulta centralizada de status no Hub
                const statusRes = await fetch('/api/engine_status').catch(() => null);
                if (statusRes && statusRes.ok) {
                    const statusData = await statusRes.json();
                    for (const engine of engines) {
                        const statusEl = document.getElementById(engine.id);
                        if (!statusEl) continue;
                        
                        const state = statusData[engine.port.toString()] || "standby";
                        if (state === "running") {
                            statusEl.textContent = `SISTEMA OPERACIONAL // PORTA ${engine.port}`;
                            statusEl.style.color = "#00f3ff";
                            statusEl.parentElement.style.borderColor = "rgba(0, 243, 255, 0.3)";
                            statusEl.parentElement.style.background = "rgba(0, 243, 255, 0.05)";
                        } else if (state === "busy") {
                            statusEl.textContent = `PROCESSANDO TAREFA // PORTA ${engine.port}`;
                            statusEl.style.color = "#00ff41";
                            statusEl.parentElement.style.borderColor = "rgba(0, 255, 65, 0.3)";
                            statusEl.parentElement.style.background = "rgba(0, 255, 65, 0.05)";
                        } else {
                            // standby
                            statusEl.textContent = `STANDBY // POUPANDO MEMÓRIA`;
                            statusEl.style.color = "#888";
                            statusEl.parentElement.style.borderColor = "rgba(255, 255, 255, 0.1)";
                            statusEl.parentElement.style.background = "rgba(255, 255, 255, 0.02)";
                        }
                    }
                } else {
                    // Fallback para quando o hub está indisponível
                    for (const engine of engines) {
                        const statusEl = document.getElementById(engine.id);
                        if (statusEl) {
                            statusEl.textContent = "AGUARDANDO HUB...";
                            statusEl.style.color = "#ffa500";
                        }
                    }
                }
            } catch(e) {
                console.log("Erro na telemetria:", e);
            }
        }
        setInterval(updateTelemetry, 10000); // 10 segundos para sincronização remota Mega
        updateTelemetry();