document.addEventListener("DOMContentLoaded", () => {
    // --- Elementi principali ---
    const chatArea = document.getElementById("chat-area");
    const input = document.getElementById("user-input");
    const sendBtn = document.getElementById("send-btn");
    const modelInfo = document.getElementById("model-info");
    const sidebarList = document.getElementById("sidebar-list");
    const clearHistoryBtn = document.getElementById("clear-history-btn");
    const deepStepToggle = document.getElementById("deep-step-toggle");
    const deepStepsPanel = document.getElementById("deep-steps-panel");
    const sidebar = document.getElementById("chat-history-sidebar");
    const toggleSidebarBtn = document.getElementById("toggle-sidebar-btn");
    const terminalContent = document.getElementById("terminal-content");
    const clearOutputBtn = document.getElementById("clear-output-btn");
    const clearTerminalBtn = document.getElementById("clear-terminal-btn");
    const toggleAutoscrollBtn = document.getElementById("toggle-autoscroll-btn");
    const securityBypassToggle = document.getElementById("security-bypass-toggle");
    const panelTitle = document.getElementById("panel-title");
    const sidePanelTitle = document.getElementById("side-panel-title");

    let modelName = "...";
    let busy = false;
    let autoScroll = true;
    let securityBypass = false;
    let currentChatId = null; // Track conversazione corrente
    let currentTaskId = null; // 🎯 Track task corrente per contesto persistente
    let currentExecutionState = null; // 🎯 Stato esecuzione corrente (per resume)
    
    // === SECURITY BYPASS TOGGLE ===
    if (securityBypassToggle) {
        securityBypassToggle.addEventListener("change", () => {
            securityBypass = securityBypassToggle.checked;
            if (securityBypass) {
                addTerminalLine("warning", "[SECURITY]", "⚠️ Security bypass ATTIVO - Solo per test in ambiente sicuro!");
            } else {
                addTerminalSystem("Security bypass disattivato");
            }
        });
    }
    
    // === DEEP STEP MODE TOGGLE ===
    function updateModeUI() {
        const isDeepStep = deepStepToggle.checked;
        
        if (isDeepStep) {
            // Modalità Deep Step
            panelTitle.textContent = "⚙️ Deep Step Executor";
            sidePanelTitle.textContent = "💻 Terminal Output";
            deepStepsPanel.style.display = "block";
            chatArea.style.display = "none";
            sendBtn.querySelector(".btn-text").textContent = "Esegui";
            sendBtn.querySelector(".btn-icon").textContent = "🚀";
            addTerminalSystem("Deep Step mode activated");
        } else {
            // Modalità Chat normale
            panelTitle.textContent = "💬 GhostBrain Assistant";
            sidePanelTitle.textContent = "📊 Info";
            deepStepsPanel.style.display = "none";
            chatArea.style.display = "block";
            sendBtn.querySelector(".btn-text").textContent = "Invia";
            sendBtn.querySelector(".btn-icon").textContent = "💬";
            addTerminalSystem("Chat mode activated");
        }
        input.focus();
    }
    
    // Funzione legacy per retrocompatibilità
    function switchToMode(mode) {
        if (mode === "step") {
            deepStepToggle.checked = true;
        } else if (mode === "chat") {
            deepStepToggle.checked = false;
        }
        updateModeUI();
    }
    
    // Listener per cambio modalità
    if (deepStepToggle) {
        deepStepToggle.addEventListener("change", updateModeUI);
    }
    
    // === SIDEBAR TOGGLE ===
    if (toggleSidebarBtn) {
        toggleSidebarBtn.addEventListener("click", () => {
            sidebar.classList.toggle("collapsed");
        });
    }
    
    // === TERMINAL FUNCTIONS ===
    function addTerminalLine(type, prompt, text) {
        const line = document.createElement("div");
        line.className = `terminal-line ${type}`;
        
        const promptSpan = document.createElement("span");
        promptSpan.className = "terminal-prompt";
        promptSpan.textContent = prompt;
        
        const textSpan = document.createElement("span");
        textSpan.className = "terminal-text";
        textSpan.textContent = text;
        
        line.appendChild(promptSpan);
        line.appendChild(textSpan);
        terminalContent.appendChild(line);
        
        if (autoScroll) {
            terminalContent.scrollTop = terminalContent.scrollHeight;
        }
        
        // Limita a 500 linee
        const lines = terminalContent.querySelectorAll(".terminal-line");
        if (lines.length > 500) {
            lines[0].remove();
        }
    }
    
    function addTerminalCommand(command) {
        addTerminalLine("command", "$ ", command);
    }
    
    function addTerminalOutput(output) {
        // Split per linee e aggiungi ognuna
        const lines = output.split('\n');
        lines.forEach(line => {
            if (line.trim()) {
                addTerminalLine("output", "", line);
            }
        });
    }
    
    function addTerminalSystem(message) {
        const timestamp = new Date().toLocaleTimeString();
        addTerminalLine("system", `[${timestamp}]`, message);
    }
    
    function addTerminalError(message) {
        addTerminalLine("error", "[ERROR]", message);
    }
    
    function addTerminalSuccess(message) {
        addTerminalLine("success", "[OK]", message);
    }
    
    function addTerminalWarning(message) {
        addTerminalLine("warning", "[WARN]", message);
    }
    
    function addTerminalStepStart(stepNum, stepDesc) {
        const line = document.createElement("div");
        line.className = "terminal-line step-start";
        line.innerHTML = `<span class="terminal-prompt">━━━ STEP ${stepNum} ━━━</span> <span class="terminal-text">${escapeHtml(stepDesc)}</span>`;
        terminalContent.appendChild(line);
        if (autoScroll) {
            terminalContent.scrollTop = terminalContent.scrollHeight;
        }
    }
    
    if (clearOutputBtn) {
        clearOutputBtn.addEventListener("click", () => {
            // Pulisci sia chat che terminal che steps
            chatArea.innerHTML = "";
            terminalContent.innerHTML = '';
            deepStepsPanel.innerHTML = '<div class="welcome-message"><div class="welcome-icon">🧩</div><h3>Modalità Deep Step Attivata</h3><p>Il tuo obiettivo verrà suddiviso in step eseguibili automaticamente</p><ul class="feature-list"><li>✓ Generazione automatica degli step</li><li>✓ Esecuzione sequenziale intelligente</li><li>✓ Retry con cambio strategia</li><li>✓ Visualizzazione in tempo reale</li></ul></div>';
            addTerminalSystem("Output cleared");
        });
    }
    
    // Pulsante per pulire SOLO il terminale
    if (clearTerminalBtn) {
        clearTerminalBtn.addEventListener("click", () => {
            terminalContent.innerHTML = '';
            addTerminalSystem("Terminal cleared");
        });
    }
    
    if (toggleAutoscrollBtn) {
        toggleAutoscrollBtn.addEventListener("click", () => {
            autoScroll = !autoScroll;
            toggleAutoscrollBtn.classList.toggle("active", autoScroll);
            addTerminalSystem(autoScroll ? "Auto-scroll enabled" : "Auto-scroll disabled");
        });
    }

    const newChatBtn = document.getElementById("new-chat-btn");
    if (newChatBtn) {
        newChatBtn.onclick = () => {
            // Reset stato
            currentChatId = null;
            input.value = "";
            chatArea.innerHTML = "";
            
            // Rimuovi active da sidebar
            document.querySelectorAll('.chat-history-item').forEach(el => {
                el.classList.remove('active');
            });
            
            // Reset welcome screen
            deepStepsPanel.innerHTML = `
                <div class="welcome-message">
                    <div class="welcome-icon">🧩</div>
                    <h3>Benvenuto nel Step Executor</h3>
                    <p>Inserisci un obiettivo e clicca "Esegui Step" per vedere la magia operare</p>
                    <ul class="feature-list">
                        <li>✓ Generazione automatica degli step</li>
                        <li>✓ Esecuzione sequenziale con verifica</li>
                        <li>✓ Retry automatico in caso di errore</li>
                        <li>✓ Visualizzazione in tempo reale</li>
                    </ul>
                </div>
            `;
            
            // NON pulire il terminal - conserva lo storico
            // terminalContent.innerHTML = "";  // Commentato per conservare log
            addTerminalSystem("═".repeat(50));
            addTerminalSystem("New session started");
            addTerminalSystem("═".repeat(50));
            
            switchToMode("step");
        };
    }

    function showDeepSteps(steps = [], mode = "generation") {
        deepStepsPanel.innerHTML = "";
        if (!steps || steps.length === 0) {
            deepStepsPanel.innerHTML = "<div class='deep-steps-empty'>Nessuno step generato.</div>";
            return;
        }
        
        const ul = document.createElement("ul");
        ul.className = "deep-steps-list";
        
        if (mode === "execution") {
            // Mostra step con risultati di esecuzione
            steps.forEach((step) => {
                const li = document.createElement("li");
                li.className = step.status === "completato" ? "step-completed" : "step-failed";
                li.innerHTML = `
                    <div class="step-header">
                        <span class="deep-step-num">${step.step_number}.</span>
                        <span class="deep-step-text">${escapeHtml(step.step_description)}</span>
                        <span class="step-status ${step.status}">${step.status === "completato" ? "✓" : "✗"}</span>
                    </div>
                    <div class="step-result">${escapeHtml(step.result)}</div>
                `;
                ul.appendChild(li);
            });
        } else {
            // Mostra solo step (senza esecuzione)
            steps.forEach((step, i) => {
                const li = document.createElement("li");
                li.innerHTML = `<span class="deep-step-num">${i + 1}.</span> <span class="deep-step-text">${escapeHtml(step)}</span>`;
                ul.appendChild(li);
            });
        }
        
        deepStepsPanel.appendChild(ul);
    }

    async function runDeepStep() {
        if (busy) {
            addTerminalLine("warning", "[BUSY]", "Sistema occupato, attendere...");
            return;
        }
        const text = input.value.trim();
        if (!text) {
            addTerminalLine("warning", "[WARN]", "Inserisci un obiettivo");
            return;
        }
        
        addTerminalSystem("═".repeat(50));
        addTerminalSystem(`Starting execution: ${text.slice(0, 60)}`);
        deepStepsPanel.innerHTML = `
            <div class='deep-steps-loading'>
                <div class="loading-spinner"></div>
                <p>🧠 Elaborazione in corso...</p>
                <p class="loading-hint">Il modello sta analizzando la richiesta (può richiedere 10-30 secondi)</p>
            </div>
        `;
        
        busy = true;
        input.value = "";  // Pulisci input
        
        // Struttura per tenere traccia degli step
        let stepsData = {
            total: 0,
            steps: [],
            currentStep: null
        };
        
        // Salva stepsData globalmente per accesso da resume
        window.currentStepsData = stepsData;

        try {
            // Usa EventSource per ricevere aggiornamenti in tempo reale
            const response = await fetch("/deepstep", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    message: text,
                    security_bypass: securityBypass
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            while (true) {
                const {done, value} = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, {stream: true});
                const lines = buffer.split('\n\n');
                buffer = lines.pop(); // Mantieni l'ultima linea incompleta
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            handleStepEvent(data, stepsData);
                        } catch (e) {
                            console.error('Error parsing SSE event:', e, 'Line:', line);
                            addTerminalError(`Parse error: ${e.message}`);
                        }
                    }
                }
            }
            
            // Mostra riepilogo finale
            const completed = stepsData.steps.filter(s => s.status === "completato").length;
            if (completed === stepsData.total) {
                addTerminalSuccess(`Execution completed: ${completed}/${stepsData.total} steps successful`);
            } else {
                addTerminalError(`Execution incomplete: ${completed}/${stepsData.total} steps completed`);
            }
            
            // UNIFICAZIONE: Passa automaticamente in Chat Mode
            addTerminalSystem("═".repeat(50));
            addTerminalSystem("🔄 Switching to CHAT MODE for follow-up questions...");
            addTerminalSystem("═".repeat(50));
            
            // Switch a chat mode
            switchToMode("chat");
            
            // Mostra messaggio informativo nella chat
            addMessage(`
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 15px; border-radius: 8px; color: white;">
                    <strong>✅ Esecuzione step completata: ${completed}/${stepsData.total}</strong><br><br>
                    💬 <strong>Chat Mode Attiva</strong> - Ora puoi fare domande sui risultati:<br>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>Perché lo step X è fallito?</li>
                        <li>Come completo manualmente lo step Y?</li>
                        <li>Analizza i risultati e suggerisci prossimi passi</li>
                        <li>Dammi comandi alternativi per Z</li>
                    </ul>
                </div>
            `, "bot");
            
            // Salva contesto per prossime chat
            window.lastStepContext = {
                objective: text,
                results: stepsData.steps,
                completed: completed,
                total: stepsData.total
            };
            
            // Focus sull'input per domande
            input.focus();
            
            // Aggiorna cronologia e evidenzia la nuova esecuzione
            await loadChatHistory();
            
            // Trova e evidenzia l'ultima esecuzione (quella appena completata)
            setTimeout(() => {
                const items = document.querySelectorAll('.chat-history-item');
                if (items.length > 0) {
                    // La prima è la più recente (ordinata reverse)
                    items[0].classList.add('active');
                    currentChatId = items[0].dataset?.chatId;
                }
            }, 500);
            
        } catch (e) {
            deepStepsPanel.innerHTML = `<div class='deep-steps-error'>❌ Errore: ${escapeHtml(e.message)}</div>`;
            addTerminalError(`Fatal error: ${e.message}`);
        } finally {
            busy = false;
        }
    }
    
    function handleStepEvent(event, stepsData) {
        // Gestisce i diversi tipi di eventi in tempo reale
        switch(event.type) {
            case "init":
                deepStepsPanel.innerHTML = "<div class='deep-steps-loading'>⚙️ " + escapeHtml(event.message) + "</div>";
                addTerminalSystem(event.message);
                break;
                
            case "memory_recalled":
                addTerminalSuccess(`Recalled ${event.memories} relevant memories from previous executions`);
                addTerminalSystem("─".repeat(50));
                break;
                
            case "generating":
                deepStepsPanel.innerHTML = "<div class='deep-steps-loading'>🧠 Generazione step...</div>";
                addTerminalSystem("Analyzing objective and generating execution steps...");
                break;
                
            case "steps_generated":
                stepsData.total = event.total_steps;
                stepsData.steps = event.steps.map((desc, idx) => ({
                    number: idx + 1,
                    description: desc,
                    status: "pending",
                    attempts: 0,
                    result: null
                }));
                renderSteps(stepsData);
                addTerminalSuccess(`Generated ${event.total_steps} steps for execution`);
                addTerminalSystem("─".repeat(50));
                break;
                
            case "step_start":
                const step = stepsData.steps[event.step_number - 1];
                if (step) {
                    step.status = "running";
                    stepsData.currentStep = event.step_number;
                    addTerminalStepStart(event.step_number, step.description);
                    addTerminalSystem(`Executing step ${event.step_number}/${event.total_steps}...`);
                }
                renderSteps(stepsData);
                break;
                
            case "step_attempt":
                const attemptStep = stepsData.steps[event.step_number - 1];
                if (attemptStep) {
                    attemptStep.attempts = event.attempt;
                    attemptStep.status = "running";
                    if (event.attempt > 1) {
                        addTerminalSystem(`Retry attempt ${event.attempt}/${event.max_attempts}`);
                    }
                }
                renderSteps(stepsData);
                break;
                
            case "step_retry":
                const retryStep = stepsData.steps[event.step_number - 1];
                if (retryStep) {
                    retryStep.status = "retrying";
                    retryStep.lastError = event.reason;
                    addTerminalError(`Step needs retry: ${event.reason}`);
                }
                renderSteps(stepsData);
                break;
                
            case "step_success":
                const successStep = stepsData.steps[event.step_number - 1];
                if (successStep) {
                    successStep.status = "completato";
                    successStep.result = event.result;
                    successStep.attempts = event.attempt;
                    
                    // Mostra output nel terminal
                    addTerminalSuccess(`Step ${event.step_number} completed successfully`);
                    if (event.result) {
                        // Cerca comandi nel risultato (righe che iniziano con $ o contengono "nmap", "echo", etc)
                        const lines = event.result.split('\n');
                        lines.forEach(line => {
                            line = line.trim();
                            if (line.startsWith('$') || line.startsWith('#')) {
                                addTerminalCommand(line.replace(/^[$#]\s*/, ''));
                            } else if (/^(nmap|echo|cat|ls|grep|wget|curl|sudo|python|bash)\s/.test(line)) {
                                addTerminalCommand(line);
                            } else if (line) {
                                addTerminalOutput(line);
                            }
                        });
                    }
                    addTerminalSystem("─".repeat(50));
                }
                renderSteps(stepsData);
                break;
                
            case "step_failed":
                const failedStep = stepsData.steps[event.step_number - 1];
                if (failedStep) {
                    failedStep.status = "fallito";
                    failedStep.result = event.error;
                    addTerminalError(`Step ${event.step_number} failed: ${event.error}`);
                }
                renderSteps(stepsData);
                break;
                
            case "step_error":
                const errorStep = stepsData.steps[event.step_number - 1];
                if (errorStep) {
                    errorStep.status = "error";
                    errorStep.lastError = event.error;
                    addTerminalError(`Error in step ${event.step_number}: ${event.error}`);
                }
                renderSteps(stepsData);
                break;
                
            case "complete":
                addTerminalSuccess("All steps completed!");
                addTerminalSystem("═".repeat(50));
                break;
            
            case "chat_ready":
                // NUOVO: Evento per passaggio automatico a chat mode
                addTerminalSystem("═".repeat(50));
                addTerminalSuccess(event.message || "Chat mode ready for follow-up");
                addTerminalSystem("═".repeat(50));
                
                // Switch automatico a chat mode
                setTimeout(() => {
                    switchToMode("chat");
                    
                    // Mostra summary e invito
                    if (event.summary) {
                        addMessage(`
                            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 15px; border-radius: 8px; color: white; margin: 10px 0;">
                                <strong>📊 ${event.summary}</strong><br><br>
                                💬 <strong>Hai domande sui risultati?</strong><br>
                                <small style="opacity: 0.9;">
                                Esempi: "Perché step X fallito?", "Come procedo?", "Comandi alternativi?"
                                </small>
                            </div>
                        `, "bot");
                    }
                    
                    input.focus();
                    input.placeholder = "Fai una domanda sui risultati...";
                }, 500);
                break;
                
            case "target_selection_required":
                // 🎯 NUOVO: Interfaccia collaborativa per selezione target
                addTerminalWarning(`⚠️ Confidenza identificazione target troppo bassa: ${event.confidence}/10`);
                addTerminalSystem("🔍 Richiesta selezione manuale target all'utente");
                
                // Mostra interfaccia di selezione nel panel principale
                showTargetSelectionUI(event, stepsData);
                break;
                
            case "target_confirmed":
                // Target confermato automaticamente o manualmente
                addTerminalSuccess(`🎯 Target IP confermato: ${event.target_ip} (confidenza: ${event.confidence || 'N/A'}/10)`);
                break;
                
            case "steps_completed":
                addTerminalSystem(event.message);
                // 🎯 SALVA TASK_ID per contesto persistente
                if (event.task_id) {
                    currentTaskId = event.task_id;
                    addTerminalSystem(`[TASK] Contesto salvato: ${event.task_id}`);
                }
                // Switch automatico a chat mode per follow-up
                switchToMode("chat");
                break;
                
            case "heartbeat":
                // Mantiene la connessione viva
                break;
        }
    }
    
    // 🎯 NUOVO: Mostra interfaccia di selezione target
    function showTargetSelectionUI(event, stepsData) {
        const candidates = event.candidates || [];
        const confidence = event.confidence || 0;
        const stepNumber = event.step_number || 1;
        
        // Crea container per selezione
        const selectionContainer = document.createElement("div");
        selectionContainer.className = "target-selection-container";
        selectionContainer.innerHTML = `
            <div class="target-selection-header">
                <h3>🎯 Selezione Target Richiesta</h3>
                <p class="selection-subtitle">Confidenza identificazione: ${confidence}/10 (minimo richiesto: 7/10)</p>
                <p class="selection-hint">Seleziona il target corretto dalla lista dei candidati trovati:</p>
            </div>
            <div class="candidates-list">
                ${candidates.map((cand, idx) => `
                    <div class="candidate-item" data-ip="${cand.ip}">
                        <div class="candidate-header">
                            <span class="candidate-ip">${escapeHtml(cand.ip)}</span>
                            <span class="candidate-score">Score: ${cand.score}</span>
                        </div>
                        <div class="candidate-details">
                            <div class="candidate-info">
                                <span class="info-label">Hostname:</span>
                                <span class="info-value">${escapeHtml(cand.hostname || 'N/A')}</span>
                            </div>
                            <div class="candidate-info">
                                <span class="info-label">Vendor:</span>
                                <span class="info-value">${escapeHtml(cand.vendor || 'N/A')}</span>
                            </div>
                            ${cand.reasons && cand.reasons.length > 0 ? `
                                <div class="candidate-reasons">
                                    <span class="info-label">Motivi:</span>
                                    <ul>
                                        ${cand.reasons.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                        </div>
                        <button class="select-target-btn" data-ip="${cand.ip}">
                            ✓ Seleziona questo target
                        </button>
                    </div>
                `).join('')}
            </div>
            <div class="target-selection-footer">
                <button class="skip-selection-btn" id="skip-target-selection">
                    ⏭️ Continua senza selezione (usa IP con score più alto)
                </button>
            </div>
        `;
        
        // Sostituisci il contenuto del panel
        deepStepsPanel.innerHTML = "";
        deepStepsPanel.appendChild(selectionContainer);
        
        // Aggiungi event listeners per i pulsanti
        selectionContainer.querySelectorAll('.select-target-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const selectedIP = btn.dataset.ip;
                resumeExecutionWithTarget(selectedIP, event.task_id, stepNumber);
            });
        });
        
        // Pulsante skip
        const skipBtn = selectionContainer.querySelector('#skip-target-selection');
        if (skipBtn) {
            skipBtn.addEventListener('click', () => {
                // Usa il candidato con score più alto
                const bestCandidate = candidates[0];
                if (bestCandidate) {
                    resumeExecutionWithTarget(bestCandidate.ip, event.task_id, stepNumber);
                } else {
                    addTerminalError("Nessun candidato disponibile per continuare");
                }
            });
        }
        
        // Salva stato per resume
        currentExecutionState = {
            task_id: event.task_id,
            step_number: stepNumber,
            candidates: candidates
        };
    }
    
    // 🎯 NUOVO: Riprende esecuzione con target selezionato
    async function resumeExecutionWithTarget(selectedIP, taskId, stepNumber) {
        if (busy) {
            addTerminalWarning("Sistema occupato, attendere...");
            return;
        }
        
        addTerminalSuccess(`🎯 Target selezionato: ${selectedIP}`);
        addTerminalSystem(`Ripresa esecuzione dallo step ${stepNumber + 1}...`);
        
        busy = true;
        
        try {
            const response = await fetch("/resume_execution", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    task_id: taskId,
                    selected_ip: selectedIP,
                    resume_from_step: stepNumber + 1
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            // Usa lo stesso stepsData esistente
            let stepsData = window.currentStepsData || {
                total: 0,
                steps: [],
                currentStep: null
            };
            
            while (true) {
                const {done, value} = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, {stream: true});
                const lines = buffer.split('\n\n');
                buffer = lines.pop();
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            handleStepEvent(data, stepsData);
                        } catch (e) {
                            console.error('Error parsing SSE event:', e);
                            addTerminalError(`Parse error: ${e.message}`);
                        }
                    }
                }
            }
            
            // Mostra riepilogo finale
            const completed = stepsData.steps.filter(s => s.status === "completato").length;
            if (completed === stepsData.total) {
                addTerminalSuccess(`Execution completed: ${completed}/${stepsData.total} steps successful`);
            } else {
                addTerminalError(`Execution incomplete: ${completed}/${stepsData.total} steps completed`);
            }
            
        } catch (e) {
            addTerminalError(`Errore ripresa esecuzione: ${e.message}`);
        } finally {
            busy = false;
        }
    }
    
    function renderSteps(stepsData) {
        // Renderizza l'interfaccia completa degli step in tempo reale
        if (!stepsData.steps || stepsData.steps.length === 0) return;
        
        const container = document.createElement("div");
        container.className = "steps-container";
        
        // Header con progresso
        const completed = stepsData.steps.filter(s => s.status === "completato").length;
        const header = document.createElement("div");
        header.className = "steps-header";
        header.innerHTML = `
            <span class="steps-progress">Progresso: ${completed}/${stepsData.total}</span>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${(completed / stepsData.total) * 100}%"></div>
            </div>
        `;
        container.appendChild(header);
        
        // Lista step
        const ul = document.createElement("ul");
        ul.className = "deep-steps-list";
        
        stepsData.steps.forEach((step) => {
            const li = document.createElement("li");
            li.className = `step-item step-${step.status}`;
            
            // Icona stato
            let statusIcon = "⏳";
            if (step.status === "completato") statusIcon = "✅";
            else if (step.status === "fallito") statusIcon = "❌";
            else if (step.status === "running") statusIcon = "⚙️";
            else if (step.status === "retrying") statusIcon = "🔄";
            
            li.innerHTML = `
                <div class="step-header">
                    <span class="step-icon">${statusIcon}</span>
                    <span class="deep-step-num">${step.number}.</span>
                    <span class="deep-step-text">${escapeHtml(step.description)}</span>
                    ${step.attempts > 0 ? `<span class="step-attempts">Tentativo ${step.attempts}</span>` : ''}
                </div>
                ${step.result ? `<div class="step-result">${escapeHtml(step.result)}</div>` : ''}
                ${step.lastError && step.status === "retrying" ? `<div class="step-error-detail">⚠️ ${escapeHtml(step.lastError)}</div>` : ''}
            `;
            
            ul.appendChild(li);
        });
        
        container.appendChild(ul);
        deepStepsPanel.innerHTML = "";
        deepStepsPanel.appendChild(container);
    }


    // --- Carica e mostra la cronologia chat nella sidebar ---
    async function loadChatHistory() {
        sidebarList.innerHTML = `<div class="loading">Caricamento cronologia...</div>`;
        try {
            const resp = await fetch('/chat_history');
            const data = await resp.json();
            sidebarList.innerHTML = ""; // pulisci lista

            if (!data.history || data.history.length === 0) {
                sidebarList.innerHTML = `<div class="empty-history">Nessuna chat salvata.</div>`;
                return;
            }
            
            data.history.forEach(chat => {
                const item = document.createElement('div');
                item.className = 'chat-history-item';
                
                // Determina icona basata sul tipo
                const typeIcon = chat.type === "step_execution" ? "🧩" : "💬";
                const typeBadge = chat.type === "step_execution" ? "STEP" : "CHAT";
                
                // Preview più informativa
                const preview = chat.user_input.slice(0, 50);
                const timestamp = chat.timestamp.slice(0,16).replace('T', ' ');
                
                item.dataset.chatId = chat.id;  // Store ID per tracking
                
                item.innerHTML = `
                    <div class="history-icon">${typeIcon}</div>
                    <div class="history-content">
                        <div class="history-preview">${escapeHtml(preview)}</div>
                        <div class="history-meta">
                            <span class="history-badge ${chat.type || 'chat'}">${typeBadge}</span>
                            <span class="history-time">${timestamp}</span>
                        </div>
                    </div>
                `;
                
                // Al click: mostra conversazione completa
                item.onclick = () => {
                    // Rimuovi active da tutti gli altri
                    document.querySelectorAll('.chat-history-item').forEach(el => {
                        el.classList.remove('active');
                    });
                    // Aggiungi active a questo
                    item.classList.add('active');
                    currentChatId = chat.id;
                    loadConversation(chat);
                };
                
                // Se è la chat corrente, evidenziala
                if (currentChatId === chat.id) {
                    item.classList.add('active');
                }

                sidebarList.appendChild(item);
            });
        } catch (e) {
            sidebarList.innerHTML = `<div class="empty-history">Errore caricamento cronologia.</div>`;
        }
    }
    
    // --- Carica conversazione completa ---
    function loadConversation(chat) {
        if (chat.type === "step_execution") {
            // Mostra step execution
            switchToMode("step");
            
            // Pulisci e mostra gli step
            deepStepsPanel.innerHTML = "";
            
            if (chat.steps && chat.steps.length > 0) {
                const stepsData = {
                    total: chat.steps.length,
                    steps: chat.steps.map(s => ({
                        number: s.step_number,
                        description: s.step_description,
                        status: s.status,
                        attempts: s.attempts || 1,
                        result: s.result
                    }))
                };
                renderSteps(stepsData);
            }
            
            // Mostra nel terminal
            addTerminalSystem("═".repeat(50));
            addTerminalSystem(`Loaded session: ${chat.user_input}`);
            addTerminalSystem(`Timestamp: ${chat.timestamp}`);
            addTerminalSystem("─".repeat(50));
            
            if (chat.steps) {
                chat.steps.forEach(s => {
                    addTerminalStepStart(s.step_number, s.step_description);
                    if (s.result) {
                        addTerminalOutput(s.result);
                    }
                    if (s.status === "completato") {
                        addTerminalSuccess(`Step ${s.step_number} completed`);
                    } else {
                        addTerminalError(`Step ${s.step_number} ${s.status}`);
                    }
                    addTerminalSystem("─".repeat(50));
                });
            }
            
        } else {
            // Mostra chat normale
            switchToMode("chat");
            chatArea.innerHTML = "";
            
            addMessage("> " + escapeHtml(chat.user_input), "user");
            addMessage(chat.reply, "bot");
            
            if (chat.memoria_usata && chat.memoria_usata.length > 0) {
                addMemory(chat.memoria_usata);
            }
        }
        
        // Metti il prompt nell'input per riferimento
        input.value = chat.user_input;
        input.focus();
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 150) + "px";
        
        addTerminalSystem(`Session loaded from history`);
    }

    // --- Cancella tutta la cronologia ---
    if (clearHistoryBtn) {
        clearHistoryBtn.onclick = async () => {
            if (!confirm("Sei sicuro di voler cancellare tutta la cronologia?")) return;
            await fetch("/chat_history", { method: "DELETE" });
            loadChatHistory();
        };
    }

    function addMessage(content, sender = "bot") {
        const msg = document.createElement("div");
        msg.classList.add("message", sender);
        msg.innerHTML = content;
        chatArea.appendChild(msg);
        chatArea.scrollTop = chatArea.scrollHeight;
    }


    // --- Helpers per sicurezza HTML ---
    function escapeHtml(unsafe) {
        return unsafe.replace(/[&<>"']/g, function(m) {
            return ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            })[m];
        });
    }

    // --- Sicuro: nasconde pulsante download se esiste (per future funzioni deepsearch) ---
    function hideDownloadBtn() {
        const downloadBtn = document.getElementById("download-btn");
        if (downloadBtn) {
            downloadBtn.style.display = "none";
            downloadBtn.href = "#";
            downloadBtn.removeAttribute("download");
        }
    }
    function showDownloadBtn(filename) {
        const downloadBtn = document.getElementById("download-btn");
        if (downloadBtn) {
            downloadBtn.style.display = "inline-block";
            downloadBtn.href = `/download/${filename}`;
            downloadBtn.setAttribute("download", filename);
        }
    }

    // --- Recupera modello attivo all'avvio ---
    fetch("/api/model")
    .then(res => res.json())
    .then(data => {
        modelName = data.model || "...";
        modelInfo.textContent = modelName;
        addTerminalSystem(`AI Model loaded: ${modelName}`);
        addTerminalSystem("═".repeat(50));
    });

    // --- Auto-resize dinamico per textarea input ---
    input.addEventListener("input", function () {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 150) + "px";
    });

    // --- Aggiungi messaggio in chat (user o bot) ---
    function addMemory(memoriaUsata = []) {
        if (!memoriaUsata || memoriaUsata.length === 0) return;
        const memDiv = document.createElement("div");
        memDiv.className = "memory-context";
        memDiv.innerHTML = `
        <strong>🧠 Ricordi usati:</strong>
        <ul>
        ${memoriaUsata.map(mem => `<li><pre>${escapeHtml(mem.doc)}</pre></li>`).join('')}
        </ul>
        `;
        chatArea.appendChild(memDiv);
        chatArea.scrollTop = chatArea.scrollHeight;
    }


    function addSpinner() {
        const spinner = document.createElement("div");
        spinner.classList.add("message", "bot");
        spinner.innerHTML = `<span class="spinner"></span> In attesa di risposta...`;
        spinner.id = "pending-spinner";
        chatArea.appendChild(spinner);
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    function removeSpinner() {
        const spinner = document.getElementById("pending-spinner");
        if (spinner) spinner.remove();
    }

    // --- Invio classico (chatbot, NO deepsearch) ---
    function runChat() {
        if (busy) {
            addTerminalLine("warning", "[BUSY]", "Sistema occupato, attendere...");
            return;
        }
        const text = input.value.trim();
        if (!text) {
            addTerminalLine("warning", "[WARN]", "Inserisci un messaggio");
            return;
        }
        
        addMessage("> " + escapeHtml(text), "user");
        addTerminalSystem(`[Chat Request] ${text.slice(0, 60)}...`);
        input.value = "";
        input.style.height = "60px";
        busy = true;
        addSpinner();
        
        // Controlla se abbiamo contesto da step precedenti
        const useStepContext = window.lastStepContext ? true : false;
        
        if (useStepContext) {
            addTerminalSystem("Using context from previous step execution");
        }

        fetch("/ask", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                message: text,
                use_step_context: useStepContext,
                task_id: currentTaskId  // 🎯 Invia task_id per contesto persistente
            })
        })
        .then(async res => {
            removeSpinner();
            let data;
            try { 
                data = await res.json();
                addTerminalSuccess("[Chat Response] Received");
            }
            catch (e) { 
                addMessage(`<span style="color:#ff4444">[Errore API]</span>`, "bot"); 
                addTerminalError(`[Chat Error] ${e.message}`);
                return; 
            }
            addMessage(data.reply, "bot");
            addTerminalSuccess("[Chat Response] Received");
            addTerminalSystem(`[Chat] ${data.reply.slice(0, 100)}...`);
            if (data.memoria_usata && data.memoria_usata.length > 0) {
                addMemory(data.memoria_usata);
            }
            if (data.model) modelInfo.textContent = data.model;
            
            // Reset contesto step dopo prima risposta (evita riuso eccessivo)
            if (window.lastStepContext) {
                delete window.lastStepContext;
                addTerminalSystem("Step context used and cleared");
            }
            
            loadChatHistory();
        })
        .catch(err => {
            removeSpinner();
            addMessage(`<span style="color:#ff4444">[Errore invio: ${err}]</span>`, "bot");
            addTerminalError(`[Chat Fatal Error] ${err}`);
        })
        .finally(() => { 
            busy = false;
            addTerminalSystem("[Chat] Request completed");
        });
    }

    // --- Invio Ricerca Profonda (deepsearch) ---
    function runDeepSearch() {
        if (busy) return;
        hideDownloadBtn();
        const text = input.value.trim();
        if (!text) return;
        
        addLog(`DeepSearch: ${text}`, "info");
        if (chatPanel.classList.contains("collapsed")) {
            chatPanel.classList.remove("collapsed");
        }
        addMessage("> Ricerca profonda: " + escapeHtml(text), "user");
        input.value = "";
        input.style.height = "60px";
        busy = true;
        addSpinner();

        fetch("/deepsearch", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({query: text})
        })
        .then(async res => {
            removeSpinner();
            let data;
            try { data = await res.json(); }
            catch (e) { addMessage(`<span style="color:#ff4444">[Errore API]</span>`, "bot"); return; }
            if (data.error) {
                addMessage(`<span style="color:#ff4444">[DeepSearch Errore]: ${data.error}</span>`, "bot");
                addLog(`DeepSearch fallito: ${data.error}`, "error");
                hideDownloadBtn();
            } else if (data.filename) {
                addMessage(`✅ File Markdown pronto: <a href="/download/${data.filename}" target="_blank">${escapeHtml(data.filename)}</a>`, "bot");
                addLog(`File generato: ${data.filename}`, "success");
                if (data.model) modelInfo.textContent = data.model;
                showDownloadBtn(data.filename);
            } else {
                addMessage("Nessun risultato trovato.", "bot");
                addLog("Nessun risultato", "warning");
                hideDownloadBtn();
            }
            loadChatHistory();
        })
        .catch(err => {
            removeSpinner();
            addMessage(`<span style="color:#ff4444">[DeepSearch errore: ${err}]</span>`, "bot");
            addLog(`Errore DeepSearch: ${err}`, "error");
            hideDownloadBtn();
        })
        .finally(() => { busy = false; });
    }

    // --- Invio: ENTER (senza Shift) - Usa modalità corrente ---
    input.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            const text = input.value.trim();
            if (!text) return;
            
            if (deepStepToggle.checked) {
                runDeepStep();
            } else {
                runChat();
            }
        }
    });

    // --- Pulsante unificato Invia ---
    sendBtn.addEventListener("click", () => {
        const text = input.value.trim();
        if (!text) {
            input.focus();
            addTerminalError(deepStepToggle.checked ? "Inserisci un obiettivo da eseguire" : "Inserisci un messaggio");
            return;
        }
        
        // Esegui in base allo stato del toggle
        if (deepStepToggle.checked) {
            runDeepStep();
        } else {
            runChat();
        }
    });

    // --- Extra: ESC pulisce campo input ---
    input.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            input.value = "";
            input.style.height = "42px";
        }
    });

    // --- Focus all'avvio e download nascosto ---
    input.focus();
    hideDownloadBtn();

    // --- Carica la cronologia chat all'avvio ---
    loadChatHistory();
    
    // --- Inizializza UI in base al toggle ---
    updateModeUI();
});
