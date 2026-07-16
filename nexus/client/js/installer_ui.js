var pollInterval = null;

        function copyLogs() {
            var btn = document.querySelector('.btn-copy');
            var oldText = btn.innerText;
            var logBox = document.getElementById('log-console');
            var text = logBox.innerText || logBox.textContent;
            var textArea = document.createElement("textarea");
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            
            btn.innerText = "✅ COPIADO COM SUCESSO!";
            btn.style.borderColor = "var(--success)";
            setTimeout(function() {
                btn.innerText = oldText;
                btn.style.borderColor = "rgba(0, 242, 255, 0.5)";
            }, 2000);
        }

        function addLog(msg, type) {
            type = type || "info";
            var logBox = document.getElementById('log-console');
            var entry = document.createElement('div');
            entry.style.marginBottom = '2px';
            var now = new Date();
            var time = now.getHours() + ":" + now.getMinutes() + ":" + now.getSeconds();
            
            if (type === "success") entry.style.color = "#00ff88";
            if (type === "warn") entry.style.color = "#ffcc00";
            if (type === "error") entry.style.color = "#ff4444";
            if (type === "cmd") entry.style.color = "#00f2ff";
            
            entry.innerHTML = '<span style="opacity:0.4">[' + time + ']</span> ' + msg;
            logBox.appendChild(entry);
            logBox.scrollTop = logBox.scrollHeight;
        }

        function showSelectionScreen() {
            document.getElementById('main-content').style.display = 'none';
            document.getElementById('selection-content').style.display = 'block';
            calcTotalSize();
        }

        function hideSelectionScreen() {
            document.getElementById('selection-content').style.display = 'none';
            document.getElementById('main-content').style.display = 'block';
        }

        function calcTotalSize() {
            var size = 2.1; // Base & Aceleração GPU module: ~2.10 GB
            if (document.getElementById('mod-voice').checked) size += 9.00;
            if (document.getElementById('mod-video').checked) size += 13.50;
            
            document.getElementById('total-size-label').innerText = "~" + size.toFixed(2) + " GB";
        }

        function confirmAndInstall() {
            var modules = {
                base: true,
                llama: true, // Sempre obrigatório para aceleração GPU
                voice: document.getElementById('mod-voice').checked,
                video: document.getElementById('mod-video').checked
            };
            
            document.getElementById('selection-content').style.display = 'none';
            document.getElementById('progress-container').style.display = 'block';
            
            fetch('/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({mode: 'modular', modules: modules})
            }).then(function() {
                if (pollInterval) clearInterval(pollInterval);
                pollInterval = setInterval(fetchLogs, 1000);
            });
        }

        function startSetup(mode) {
            document.getElementById('main-content').style.display = 'none';
            document.getElementById('progress-container').style.display = 'block';
            
            fetch('/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({mode: mode})
            }).then(function() {
                if (pollInterval) clearInterval(pollInterval);
                pollInterval = setInterval(fetchLogs, 1000);
            });
        }

        function fetchLogs() {
            fetch('/logs')
                .then(function(res) { return res.json(); })
                .then(function(data) {
                    data.forEach(function(item) {
                        if (item.type === "system" && item.msg.indexOf("[PROGRESS]") !== -1) {
                            var parts = item.msg.replace("[PROGRESS]", "").split("|");
                            updateProgress(parts[0], parts[1]);
                        } else {
                            addLog(item.msg, item.type);
                            if (item.msg.indexOf("CONCLUIDA") !== -1 || item.msg.indexOf("FINALIZADO") !== -1) {
                                clearInterval(pollInterval);
                                updateProgress(100, "Instalação Finalizada!");
                            }
                        }
                    });
                });
        }

        function updateProgress(percent, label) {
            if (label.indexOf("[NEED_TOKEN]") !== -1) {
                var parts = label.replace("[NEED_TOKEN]", "").split("|");
                var repoId = parts[0];
                var termsUrl = parts[1];
                
                document.getElementById('gated-repo-name').innerText = repoId;
                document.getElementById('gated-repo-link').href = termsUrl;
                document.getElementById('token-modal').style.display = 'flex';
                
                updateProgress(percent, "Aguardando Token do Hugging Face...");
                return;
            }
            document.getElementById('progress-fill').style.width = percent + '%';
            document.getElementById('progress-percent').innerText = percent + '%';
            document.getElementById('status-label').innerText = label;
        }

        function submitToken() {
            var token = document.getElementById('hf-token-input').value.trim();
            var checkbox = document.getElementById('hf-terms-checkbox').checked;
            
            if (!checkbox) {
                alert("Por favor, marque a caixa confirmando que aceitou os termos no site.");
                return;
            }
            if (!token) {
                alert("Por favor, insira o token do Hugging Face.");
                return;
            }
            
            document.getElementById('submit-token-btn').disabled = true;
            document.getElementById('submit-token-btn').innerText = "Enviando...";
            
            fetch('/submit_token', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({token: token})
            }).then(function(res) {
                if (res.ok) {
                    document.getElementById('token-modal').style.display = 'none';
                    document.getElementById('hf-token-input').value = '';
                    document.getElementById('hf-terms-checkbox').checked = false;
                } else {
                    alert("Falha ao enviar o token para o instalador.");
                }
            }).catch(function(err) {
                alert("Erro de conexão: " + err);
            }).finally(function() {
                document.getElementById('submit-token-btn').disabled = false;
                document.getElementById('submit-token-btn').innerText = "Confirmar e Continuar";
            });
        }

        function showCredits() { document.getElementById('credits-modal').style.display = 'flex'; }
        function hideCredits() { document.getElementById('credits-modal').style.display = 'none'; }