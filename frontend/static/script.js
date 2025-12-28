document.addEventListener('DOMContentLoaded', () => {
    // === CONFIG ===
    const API_BASE = "/api";

    // === STATE ===
    let currentTaskId = null;
    let isBusy = false;
    let arenaEventSource = null;

    // === DOM ELEMENTS ===
    const els = {
        navLinks: document.querySelectorAll('.nav-menu li, .nav-links li'), // Support both old and new HTML
        views: document.querySelectorAll('.view-panel'),
        chatArea: document.getElementById('chat-area'),
        userInput: document.getElementById('user-input'),
        sendBtn: document.getElementById('send-btn'),
        deepStepToggle: document.getElementById('deep-step-toggle'),
        bypassToggle: document.getElementById('security-bypass-toggle'),
        historyList: document.getElementById('sidebar-list'),
        clearHistoryBtn: document.getElementById('clear-history-btn'),
        arenaStartBtn: document.getElementById('arena-start-btn'),
        arenaStopBtn: document.getElementById('arena-stop-btn'),
        arenaStatus: document.getElementById('arena-status'),
        redLog: document.getElementById('arena-log-red'),
        blueLog: document.getElementById('arena-log-blue'),
        psycheSync: document.querySelector('.fill.sync'),
        psycheStress: document.querySelector('.fill.stress'),
        modelInfo: document.getElementById('model-info')
    };

    // === NAVIGATION ===
    els.navLinks.forEach(link => {
        link.addEventListener('click', () => {
            // Active State
            els.navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // View Switching
            const targetId = `view-${link.dataset.view}`;
            els.views.forEach(view => {
                if (view.id === targetId) view.classList.add('active');
                else view.classList.remove('active');
            });
        });
    });

    // === CHAT LOGIC ===
    async function sendMessage() {
        const text = els.userInput.value.trim();
        if (!text || isBusy) return;

        isBusy = true;
        appendMessage("user", text);
        els.userInput.value = "";

        // Mode Selection
        const isSwarmOps = els.deepStepToggle.checked;
        const isUnsafe = els.bypassToggle.checked;
        const endpoint = isSwarmOps ? "/deepstep" : "/ask";

        appendMessage("system", "Transmitting to Section 9...");

        try {
            if (isSwarmOps) {
                // Handling SSE for DeepStep
                await handleDeepStep(text, isUnsafe);
            } else {
                // Standard Chat
                const resp = await fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: text, task_id: currentTaskId })
                });
                const data = await resp.json();
                appendMessage("bot", data.reply || "No response.");
                if (data.model) els.modelInfo.innerText = data.model;
                refreshHistory();
            }
        } catch (e) {
            appendMessage("error", `Transmission Failed: ${e}`);
        } finally {
            isBusy = false;
        }
    }

    async function handleDeepStep(prompt, unsafe) {
        // Use Fetch with ReadableStream for SSE handling if needed, 
        // or just standard POST if the backend streams text. 
        // The backend /deepstep returns an EventSource-compatible stream if handled by GET, 
        // OR a POST that returns a stream. Standard EventSource doesn't support POST bodies easily.
        // We used fetch-event-source in the previous version or just fetch reading chunks.
        // Let's use basic fetch reading for now.

        const response = await fetch("/deepstep", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: prompt, security_bypass: unsafe })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split("\n");

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    try {
                        const json = JSON.parse(line.substring(6));
                        handleDeepStepEvent(json);
                    } catch (e) { console.error("JSON Error", e); }
                }
            }
        }
        refreshHistory();
    }

    function handleDeepStepEvent(event) {
        // Skip heartbeat and noisy events
        if (event.type === "heartbeat" || event.type === "init") return;

        switch (event.type) {
            case "step_start":
                // Show agent thinking indicator (compact)
                const agentMatch = event.step_description?.match(/\[(\w+)\]/);
                const agent = agentMatch ? agentMatch[1] : "Agent";
                appendMessage("system", `🔄 ${agent} analyzing...`);
                break;

            case "step_success":
                // Main content - show agent message
                if (event.result && event.result.length > 10) {
                    // Extract agent name and clean content
                    const parts = event.result.split(": ");
                    const sender = parts[0] || "Agent";
                    const content = parts.slice(1).join(": ").replace(/\.\.\.$/, '');

                    // Skip empty or trivial messages
                    if (content.length < 5) return;

                    appendMessage("bot", `**[${sender}]** ${content}`);
                }
                break;

            case "step_failed":
                appendMessage("error", `❌ Step ${event.step_number} failed: ${event.error || "Unknown error"}`);
                break;

            case "therapy_session":
                // Show therapy report summary
                appendMessage("success", `🧠 **THERAPY SESSION COMPLETE**\n${event.report || ""}`);
                // Show ledger metrics if available
                if (event.ledger_metrics) {
                    const m = event.ledger_metrics;
                    appendMessage("system", `📊 **Metrics:** Success: ${(m.success_rate * 100).toFixed(0)}% | Tools: ${m.total_tool_calls} | Risk: ${(m.risk_score * 100).toFixed(0)}%`);
                }
                break;

            case "steps_completed":
                appendMessage("success", `✅ ${event.message || "Mission complete"}`);
                if (event.task_id) currentTaskId = event.task_id;
                break;

            case "error":
                appendMessage("error", `❌ ${event.error || "Unknown error"}`);
                break;

            case "target_confirmed":
                appendMessage("success", `🎯 Target confirmed: **${event.target_ip}**`);
                break;

            case "replanning":
            case "strategic_analysis":
                appendMessage("system", `📋 ${event.message || "Strategic analysis..."}`);
                break;

            // Legacy support
            case "step":
                appendMessage("bot", `[STEP ${event.step}] ${event.description}`);
                break;

            case "log":
                // Skip verbose logs
                break;

            default:
                // Log unknown events for debugging (don't show to user)
                console.log("Unknown event:", event);
        }
    }

    function appendMessage(role, text) {
        const div = document.createElement('div');
        div.className = `message ${role}`;

        // Simple Markdown parsing
        let html = text
            .replace(/\n/g, "<br>")
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/`([^`]+)`/g, "<code>$1</code>");

        div.innerHTML = html;
        els.chatArea.appendChild(div);
        els.chatArea.scrollTop = els.chatArea.scrollHeight;
    }

    els.sendBtn.addEventListener('click', sendMessage);
    els.userInput.addEventListener('keydown', (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // === ARENA LOGIC ===
    if (els.arenaStartBtn) {
        els.arenaStartBtn.addEventListener('click', async () => {
            try {
                const res = await fetch("/api/arena/start", { method: "POST" });
                const data = await res.json();
                if (data.status === "started") {
                    setArenaStatus("active");
                    startArenaStream();
                } else {
                    alert(data.message);
                }
            } catch (e) { alert("Error starting Arena"); }
        });
    }

    if (els.arenaStopBtn) {
        els.arenaStopBtn.addEventListener('click', async () => {
            await fetch("/api/arena/stop", { method: "POST" });
            setArenaStatus("stopped");
            if (arenaEventSource) arenaEventSource.close();
        });
    }

    function startArenaStream() {
        if (arenaEventSource) arenaEventSource.close();
        arenaEventSource = new EventSource("/api/arena/stream");

        arenaEventSource.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === "heartbeat") return;

            const msg = data.message || "";
            const timestamp = new Date().toLocaleTimeString();
            const logLine = document.createElement('div');
            logLine.className = "line";
            logLine.innerText = `[${timestamp}] ${msg}`;

            if (msg.includes("[RED TEAM")) {
                els.redLog.appendChild(logLine);
                els.redLog.scrollTop = els.redLog.scrollHeight;
            } else if (msg.includes("[BLUE TEAM")) {
                els.blueLog.appendChild(logLine);
                els.blueLog.scrollTop = els.blueLog.scrollHeight;
            } else {
                // Broadcast to both if general system
                const clone = logLine.cloneNode(true);
                els.redLog.appendChild(logLine);
                els.blueLog.appendChild(clone);
            }
        };
    }

    function setArenaStatus(status) {
        els.arenaStatus.className = `status-badge ${status}`;
        els.arenaStatus.innerText = status.toUpperCase();
    }

    // === HISTORY ===
    async function refreshHistory() {
        try {
            const res = await fetch("/chat_history");
            const data = await res.json();
            els.historyList.innerHTML = "";

            data.history.forEach(item => {
                const div = document.createElement('div');
                div.className = "history-item";
                div.innerHTML = `
                    <div class="title">${item.user_input}</div>
                    <div class="meta">${new Date(item.timestamp).toLocaleString()}</div>
                `;
                div.onclick = () => loadHistoryItem(item);
                els.historyList.appendChild(div);
            });
        } catch (e) { console.error("History Error", e); }
    }

    function loadHistoryItem(item) {
        els.chatArea.innerHTML = "";
        appendMessage("user", item.user_input);
        appendMessage("bot", item.reply || "No content.");
        currentTaskId = null; // Reset context on history load
    }

    els.clearHistoryBtn.addEventListener('click', async () => {
        if (!confirm("Wipe Section 9 Archive?")) return;
        await fetch("/chat_history", { method: "DELETE" });
        refreshHistory();
    });

    // === PSYCHE STATUS (Real Data) ===
    async function refreshPsycheStatus() {
        try {
            const res = await fetch("/api/psyche/state");
            const data = await res.json();

            // Convert dopamine (0-1) to sync ratio percentage
            const syncRatio = data.dopamine * 100;
            // Convert cortisol (0-1) to stress percentage
            const stressLevel = data.cortisol * 100;

            if (els.psycheSync) els.psycheSync.style.width = `${syncRatio}%`;
            if (els.psycheStress) els.psycheStress.style.width = `${stressLevel}%`;

            // Update color based on state
            if (data.state === "PARANOID" || data.state === "MANIC") {
                if (els.psycheStress) els.psycheStress.style.background = "#ff0000";
            } else if (data.state === "FLOW") {
                if (els.psycheSync) els.psycheSync.style.background = "#00ff88";
            }
        } catch (e) {
            console.error("Psyche fetch error:", e);
        }
    }

    // Refresh psyche every 5 seconds
    setInterval(refreshPsycheStatus, 5000);
    refreshPsycheStatus(); // Initial fetch

    // === INIT ===
    refreshHistory();
    // Check initial model
    fetch("/api/model").then(r => r.json()).then(d => {
        if (els.modelInfo) els.modelInfo.innerText = d.model;
    }).catch(() => { });
});
