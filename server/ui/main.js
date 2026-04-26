document.addEventListener("DOMContentLoaded", () => {
    const state = {
        task: new URLSearchParams(window.location.search).get("task") || "all",
        mapStyle: "terrain",
        showSubmitted: true,
        autoFit: true,
        liveMode: true,
        priorityFilter: "all",
        search: "",
        incidents: [],
        score: 0,
        resources: 100,
        socket: null,
        _pingInterval: null,
        _lastHeartbeatLog: 0,
    };

    // ── GEMINI KEY ──────────────────────────────────────────────────────────
    const GEMINI_KEY = "PASTE_YOUR_GEMINI_KEY_HERE";
    const TEAM_ICONS = { rescue: "🚁", medical: "🏥", utilities: "⚡", shelter: "🏠", logistics: "🚛", general: "📋" };

    // ── AUDIO ───────────────────────────────────────────────────────────────
    let audioCtx = null;
    function getAudioCtx() {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (audioCtx.state === "suspended") audioCtx.resume();
        return audioCtx;
    }
    function playAlertSound(priority) {
        try {
            const ctx = getAudioCtx(), osc = ctx.createOscillator(), gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            if (priority === "urgent") {
                osc.type = "sawtooth";
                osc.frequency.setValueAtTime(800, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(300, ctx.currentTime + 0.3);
                gain.gain.setValueAtTime(0.1, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
                osc.start(); osc.stop(ctx.currentTime + 0.3);
            } else if (priority === "high") {
                osc.type = "sine"; osc.frequency.setValueAtTime(600, ctx.currentTime);
                gain.gain.setValueAtTime(0.05, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
                osc.start(); osc.stop(ctx.currentTime + 0.2);
            } else {
                osc.type = "sine"; osc.frequency.setValueAtTime(400, ctx.currentTime);
                gain.gain.setValueAtTime(0.02, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.1);
                osc.start(); osc.stop(ctx.currentTime + 0.1);
            }
        } catch (e) { }
    }
    document.addEventListener("click", () => { try { getAudioCtx(); } catch (e) { } }, { once: true });

    // ── DOM REFS ─────────────────────────────────────────────────────────────
    const elements = {
        taskSelect: document.getElementById("task-select"),
        mapStyle: document.getElementById("map-style"),
        searchInput: document.getElementById("search-input"),
        showSubmitted: document.getElementById("show-submitted"),
        autoFit: document.getElementById("auto-fit"),
        liveMode: document.getElementById("live-mode"),
        reloadBtn: document.getElementById("reload-btn"),
        clearFeedBtn: document.getElementById("clear-feed-btn"),
        incidentList: document.getElementById("incident-list"),
        eventFeed: document.getElementById("event-feed"),
        totalCount: document.getElementById("total-count"),
        urgentCount: document.getElementById("urgent-count"),
        highCount: document.getElementById("high-count"),
        submittedCount: document.getElementById("submitted-count"),
        score: document.getElementById("score"),
        resources: document.getElementById("resources"),
        liveStatus: document.getElementById("live-status"),
        lastUpdate: document.getElementById("last-update"),
        priorityFilters: document.getElementById("priority-filters"),
    };

    // ── MAP ──────────────────────────────────────────────────────────────────
    const map = L.map("map", { zoomControl: false }).setView([20, 0], 2);
    L.control.zoom({ position: "topleft" }).addTo(map);
    const markerLayer = L.layerGroup().addTo(map);
    const mapLayers = {
        terrain: L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }),
        light: L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
            attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
        }),
        dark: L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
            attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
        }),
    };
    let activeLayer = null;
    function setMapLayer(name) {
        if (activeLayer) map.removeLayer(activeLayer);
        activeLayer = mapLayers[name] || mapLayers.terrain;
        activeLayer.addTo(map);
        state.mapStyle = name;
    }

    // ── UTILS ─────────────────────────────────────────────────────────────────
    function formatNow() { return new Date().toLocaleTimeString(); }
    function escapeHtml(v) {
        return String(v).replaceAll("&", "&amp;").replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
    }

    // ── OPERATIONS FEED ───────────────────────────────────────────────────────
    const FEED_PREFIXES = { urgent: "🚨", submit: "✅", ai: "⚡", warn: "⚠️", error: "❌", ok: "📡", info: "ℹ️" };
    function addFeedEntry(text, type = "info") {
        const li = document.createElement("li");
        li.className = `feed-item feed-${type}`;
        li.innerHTML = `<span class="feed-time">${formatNow()}</span><span class="feed-text typewriter-text">${FEED_PREFIXES[type] || "•"} ${escapeHtml(text)}</span>`;
        elements.eventFeed.prepend(li);
        try { playAlertSound(type === "urgent" || type === "error" ? "urgent" : "low"); } catch (e) { }
        while (elements.eventFeed.children.length > 50) elements.eventFeed.removeChild(elements.eventFeed.lastChild);
    }

    // ── BADGE + THREAT BAR ────────────────────────────────────────────────────
    function updateBadgeAndThreat(incidents) {
        const badge = document.getElementById("incident-badge");
        const fill = document.getElementById("threat-fill");
        const lvlText = document.getElementById("threat-level-text");
        const active = incidents.filter(i => !i.submitted);
        if (badge) badge.textContent = active.length;
        const urgN = active.filter(i => i.priority === "urgent").length;
        const hiN = active.filter(i => i.priority === "high").length;
        let label = "LOW", color = "#62dd8d", width = "15%";
        if (urgN >= 3 || (urgN >= 1 && hiN >= 2)) { label = "CRITICAL"; color = "#ff4545"; width = "100%"; }
        else if (urgN >= 1 || hiN >= 3) { label = "HIGH"; color = "#ff8a4d"; width = "72%"; }
        else if (hiN >= 1) { label = "MEDIUM"; color = "#ffc458"; width = "45%"; }
        if (fill) { fill.style.width = width; fill.style.background = color; }
        if (lvlText) { lvlText.textContent = label; lvlText.style.color = color; }
    }

    // ── DATA ──────────────────────────────────────────────────────────────────
    function normalizeIncident(item) {
        return {
            id: item?.id || item?.ticket_id || "Unknown",
            message: item?.message || "No message available.",
            priority: String(item?.priority || "medium").toLowerCase(),
            lat: item?.lat,
            lon: item?.lon,
            submitted: Boolean(item?.submitted),
            team: item?.team || null,
            score: typeof item?.score === "number" ? item.score : 0.0,
        };
    }
    function getFilteredIncidents() {
        const q = state.search.trim().toLowerCase();
        return state.incidents.filter(i => {
            if (!state.showSubmitted && i.submitted) return false;
            if (state.priorityFilter !== "all" && i.priority !== state.priorityFilter) return false;
            if (q && !`${i.id} ${i.message}`.toLowerCase().includes(q)) return false;
            return true;
        });
    }

    // ── METRIC CARDS ──────────────────────────────────────────────────────────
    function updateMetricCards() {
        const incs = state.incidents;
        elements.totalCount.textContent = incs.length;
        elements.urgentCount.textContent = incs.filter(i => i.priority === "urgent").length;
        elements.highCount.textContent = incs.filter(i => i.priority === "high").length;
        elements.submittedCount.textContent = incs.filter(i => i.submitted).length;
        elements.score.textContent = Number(state.score).toFixed(3);
        elements.resources.textContent = `${Math.round(Number(state.resources) || 0)}%`;
        elements.liveStatus.textContent = state.liveMode ? "Live" : "Paused";
        elements.lastUpdate.textContent = formatNow();
    }

    // ── INCIDENT LIST ──────────────────────────────────────────────────────────
    const PRIORITY_LABELS = { urgent: "🔴 URGENT", high: "🟠 HIGH", medium: "🟡 MEDIUM", low: "🟢 LOW" };
    function renderIncidentList(incidents) {
        elements.incidentList.innerHTML = "";
        if (!incidents.length) {
            const e = document.createElement("li"); e.className = "empty-state";
            e.textContent = "No incidents match the current filters.";
            elements.incidentList.appendChild(e); return;
        }
        for (const inc of incidents) {
            const li = document.createElement("li");
            li.className = `incident-item priority-${inc.priority}${inc.submitted ? " submitted" : ""}`;
            const teamIcon = inc.team ? (TEAM_ICONS[inc.team] || "📋") : "";
            const teamLabel = inc.team ? `${teamIcon} ${inc.team.toUpperCase()}` : "UNASSIGNED";
            const priLabel = PRIORITY_LABELS[inc.priority] || inc.priority.toUpperCase();
            const scoreHtml = inc.submitted
                ? `<div class="score-bar-wrap">
                    <span class="score-bar-label">SCORE</span>
                    <div class="score-bar"><div class="score-bar-fill" style="width:${Math.round(inc.score * 100)}%"></div></div>
                    <span class="score-bar-val">${Number(inc.score).toFixed(2)}</span>
                   </div>` : "";
            li.innerHTML = `
                <div class="incident-top">
                    <span class="incident-id">${escapeHtml(inc.id)}</span>
                    <span class="incident-priority-tag priority-tag-${escapeHtml(inc.priority)}">${priLabel}</span>
                </div>
                <p class="incident-message">${escapeHtml(inc.message)}</p>
                <div class="incident-meta">
                    <span class="incident-team-badge">${escapeHtml(teamLabel)}</span>
                    <span class="incident-state-badge ${inc.submitted ? "state-submitted" : "state-active"}">${inc.submitted ? "✅ CLOSED" : "🔴 ACTIVE"}</span>
                </div>
                <div class="incident-actions">
                    <button type="button" class="btn-locate" data-lat="${escapeHtml(inc.lat)}" data-lon="${escapeHtml(inc.lon)}">📍 Locate</button>
                    <button type="button" class="btn-analyse" data-id="${escapeHtml(inc.id)}" data-msg="${escapeHtml(inc.message)}" data-priority="${escapeHtml(inc.priority)}" data-team="${escapeHtml(inc.team || "")}">⚡ AI Analyse</button>
                </div>
                ${scoreHtml}`;
            elements.incidentList.appendChild(li);
        }
    }

    // ── MAP RENDER ────────────────────────────────────────────────────────────
    function renderMap(incidents) {
        markerLayer.clearLayers();
        const latLngs = [];
        for (const inc of incidents) {
            const lat = Number(inc.lat), lon = Number(inc.lon);
            if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
            latLngs.push([lat, lon]);
            const iconHtml = inc.submitted
                ? `<div class="marker-pin marker-submitted"><span style="font-size:10px;line-height:16px;">✓</span></div>`
                : `<div class="marker-pin marker-${escapeHtml(inc.priority)}"><div class="marker-ring"></div></div>`;
            const marker = L.marker([lat, lon], {
                icon: L.divIcon({ html: iconHtml, className: "", iconSize: [16, 16], iconAnchor: [8, 8] })
            }).addTo(markerLayer);
            const tIcon = inc.team ? (TEAM_ICONS[inc.team] || "") : "";
            marker.bindPopup(`<strong>${escapeHtml(inc.id)}</strong><br>${escapeHtml(inc.message)}<br><em>Priority: ${escapeHtml(inc.priority)}</em><br>Team: ${tIcon} ${escapeHtml(inc.team || "Unassigned")}`);
        }
        if (state.autoFit && latLngs.length > 0)
            map.fitBounds(L.latLngBounds(latLngs), { padding: [28, 28], maxZoom: 11 });
    }

    function rerender() {
        const visible = getFilteredIncidents();
        updateMetricCards();
        renderIncidentList(visible);
        renderMap(visible);
    }

    // ── PAYLOAD HANDLER ───────────────────────────────────────────────────────
    function applyPayload(payload, source) {
        const prev = state.incidents.slice();
        if (typeof payload.score === "number") state.score = payload.score;
        if (typeof payload.resources === "number") state.resources = payload.resources;
        state.incidents = Array.isArray(payload.incidents) ? payload.incidents.map(normalizeIncident) : [];
        updateBadgeAndThreat(state.incidents);

        if (source === "Live") {
            let changed = false;
            state.incidents.forEach(inc => {
                const p = prev.find(x => x.id === inc.id);
                if (inc.submitted && p && !p.submitted) {
                    addFeedEntry(`Ticket ${inc.id} CLOSED → ${(TEAM_ICONS[inc.team] || "")} ${(inc.team || "?").toUpperCase()} | Score: ${Number(inc.score).toFixed(2)}`, "submit");
                    changed = true;
                }
                if (!inc.submitted && inc.priority === "urgent" && (!p || p.priority !== "urgent")) {
                    addFeedEntry(`URGENT INCIDENT — ${inc.id}: ${inc.message.slice(0, 70)}${inc.message.length > 70 ? "…" : ""}`, "urgent");
                    playAlertSound("urgent");
                    changed = true;
                }
                if (p && inc.team && !p.team) {
                    addFeedEntry(`${inc.id} routed → ${(TEAM_ICONS[inc.team] || "")} ${inc.team.toUpperCase()}`, "ok");
                    changed = true;
                }
            });
            if (!changed) {
                const now = Date.now();
                if (now - state._lastHeartbeatLog > 10000) {
                    const active = state.incidents.filter(i => !i.submitted).length;
                    const done = state.incidents.filter(i => i.submitted).length;
                    addFeedEntry(`Stream sync — ${active} active, ${done} closed, score ${Number(state.score).toFixed(3)}`, "info");
                    state._lastHeartbeatLog = now;
                }
            }
        } else {
            const active = state.incidents.filter(i => !i.submitted).length;
            addFeedEntry(`Environment loaded — ${state.incidents.length} incidents, ${active} active`, "ok");
        }
        rerender();
    }

    // ── BOOTSTRAP ─────────────────────────────────────────────────────────────
    async function loadBootstrap() {
        try {
            const res = await fetch(`/ui/bootstrap?task=${encodeURIComponent(state.task)}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            applyPayload(await res.json(), "Bootstrap");
        } catch (err) { addFeedEntry(`Bootstrap error: ${err.message}`, "error"); }
    }

    // ── WEBSOCKET ──────────────────────────────────────────────────────────────
    function disconnectSocket() {
        if (state._pingInterval) { clearInterval(state._pingInterval); state._pingInterval = null; }
        if (state.socket) { const s = state.socket; state.socket = null; s.close(); }
    }
    function connectSocket() {
        if (!state.liveMode) return;
        const proto = window.location.protocol === "https:" ? "wss" : "ws";
        const socket = new WebSocket(`${proto}://${window.location.host}/dashboard-ws`);
        state.socket = socket;
        socket.onopen = () => {
            addFeedEntry("WebSocket connected — live stream active", "ok");
            elements.liveStatus.textContent = "Live";
            if (state._pingInterval) clearInterval(state._pingInterval);
            state._pingInterval = setInterval(() => {
                if (state.socket?.readyState === WebSocket.OPEN) state.socket.send("ping");
            }, 20000);
        };
        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === "update" && data.payload) applyPayload(data.payload, "Live");
            } catch { addFeedEntry("Malformed payload skipped", "warn"); }
        };
        socket.onerror = () => addFeedEntry("Stream connection error", "error");
        socket.onclose = () => {
            if (state.liveMode) { addFeedEntry("Stream disconnected — reconnecting…", "warn"); setTimeout(connectSocket, 1800); }
        };
    }

    // ── GEMINI AI ANALYST ──────────────────────────────────────────────────────
    function typewriter(el, text, speed = 16) {
        if (!el) return;
        el.textContent = "";
        let i = 0;
        const tick = () => { if (i < text.length) { el.textContent += text[i++]; setTimeout(tick, speed); } };
        tick();
    }

    async function analyzeWithGemini(incident) {
        const modal = document.getElementById("ai-modal");
        const body = document.getElementById("ai-modal-body");
        const incEl = document.getElementById("ai-modal-incident-text");
        const statusEl = document.getElementById("ai-modal-status");

        incEl.textContent = `${incident.id} — ${incident.message}`;
        statusEl.textContent = "INITIALIZING…";
        body.innerHTML = `
            <div class="ai-boot-sequence">
                <div class="ai-boot-line" style="animation-delay:0s">▸ LOADING INCIDENT DATA…</div>
                <div class="ai-boot-line" style="animation-delay:0.35s">▸ CONNECTING TO GEMINI FLASH…</div>
                <div class="ai-boot-line" style="animation-delay:0.7s">▸ RUNNING THREAT ASSESSMENT…</div>
                <div class="ai-boot-line" style="animation-delay:1.05s">▸ GENERATING RESPONSE PROTOCOL…</div>
            </div>`;
        modal.classList.remove("hidden");
        addFeedEntry(`AI analysis requested — ${incident.id}`, "ai");

        const prompt = `You are ARIA, an AI Emergency Operations Commander. Analyze this disaster incident.

INCIDENT ID: ${incident.id}
REPORT: "${incident.message}"
CURRENT PRIORITY: ${incident.priority}
CURRENT TEAM: ${incident.team || "UNASSIGNED"}

Respond ONLY in valid JSON (no markdown, no extra text):
{"recommended_team":"<rescue|medical|utilities|shelter|logistics|general>","recommended_priority":"<low|medium|high|urgent>","confidence":"<high|medium|low>","threat_assessment":"<one sentence military-style threat summary>","reasoning":"<2 sentences on why this team and priority>","immediate_actions":["<action1>","<action2>","<action3>"],"resource_estimate":"<e.g. 2 rescue units, 1 helicopter>"}`;

        try {
            statusEl.textContent = "QUERYING GEMINI…";
            const res = await fetch(
                `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_KEY}`,
                {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { temperature: 0.15, maxOutputTokens: 512 } })
                }
            );
            const data = await res.json();
            const raw = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
            const p = JSON.parse(raw.replace(/```json|```/g, "").trim());

            statusEl.textContent = "ANALYSIS COMPLETE ✓";
            const tIcon = TEAM_ICONS[p.recommended_team] || "📋";
            const actsHtml = (p.immediate_actions || []).map((a, i) =>
                `<div class="ai-action-row"><span class="ai-action-num">0${i + 1}</span><span class="ai-action-text" id="ai-act-${i}"></span></div>`
            ).join("");

            body.innerHTML = `<div class="ai-result">
                <div class="ai-verdict-row">
                    <div class="ai-verdict-block">
                        <div class="ai-verdict-label">RECOMMENDED TEAM</div>
                        <div class="ai-verdict-val">${tIcon} ${escapeHtml((p.recommended_team || "").toUpperCase())}</div>
                    </div>
                    <div class="ai-verdict-block">
                        <div class="ai-verdict-label">PRIORITY LEVEL</div>
                        <div class="ai-verdict-val ai-priority-${escapeHtml(p.recommended_priority)}">${escapeHtml((p.recommended_priority || "").toUpperCase())}</div>
                    </div>
                    <div class="ai-verdict-block">
                        <div class="ai-verdict-label">CONFIDENCE</div>
                        <div class="ai-verdict-val">${escapeHtml((p.confidence || "").toUpperCase())}</div>
                    </div>
                </div>
                <div class="ai-section-title">▸ THREAT ASSESSMENT</div>
                <div class="ai-reasoning" id="ai-threat-txt"></div>
                <div class="ai-section-title">▸ TACTICAL REASONING</div>
                <div class="ai-reasoning" id="ai-reason-txt"></div>
                <div class="ai-section-title">▸ IMMEDIATE ACTIONS</div>
                <div class="ai-actions-list">${actsHtml}</div>
                ${p.resource_estimate ? `<div class="ai-section-title">▸ RESOURCE ESTIMATE</div><div class="ai-reasoning" id="ai-res-txt"></div>` : ""}
            </div>`;

            setTimeout(() => typewriter(document.getElementById("ai-threat-txt"), p.threat_assessment || "", 13), 100);
            setTimeout(() => typewriter(document.getElementById("ai-reason-txt"), p.reasoning || "", 13), 700);
            (p.immediate_actions || []).forEach((a, i) =>
                setTimeout(() => typewriter(document.getElementById(`ai-act-${i}`), a, 16), 1300 + i * 400)
            );
            if (p.resource_estimate)
                setTimeout(() => typewriter(document.getElementById("ai-res-txt"), p.resource_estimate, 18), 2500);

            addFeedEntry(`AI verdict — ${incident.id} → ${(p.recommended_team || "").toUpperCase()} | ${(p.recommended_priority || "").toUpperCase()} | Confidence: ${p.confidence}`, "ai");

        } catch (err) {
            statusEl.textContent = "ANALYSIS FAILED";
            body.innerHTML = `<div class="ai-error-block">
                <div class="ai-error-title">⚠ GEMINI CONNECTION FAILURE</div>
                <div class="ai-error-msg">${escapeHtml(err.message)}</div>
                <div class="ai-error-hint">Set <code>GEMINI_KEY</code> in main.js — free key at <a href="https://aistudio.google.com/app/apikey" target="_blank">aistudio.google.com</a></div>
            </div>`;
            addFeedEntry(`AI analysis failed — ${err.message}`, "error");
        }
    }

    document.getElementById("ai-modal-close")?.addEventListener("click", () =>
        document.getElementById("ai-modal").classList.add("hidden"));
    document.getElementById("ai-modal")?.addEventListener("click", e => {
        if (e.target.id === "ai-modal") e.target.classList.add("hidden");
    });

    // ── CONTROLS ──────────────────────────────────────────────────────────────
    function wireControls() {
        elements.taskSelect.value = state.task;
        elements.mapStyle.value = state.mapStyle;
        elements.showSubmitted.checked = state.showSubmitted;
        elements.autoFit.checked = state.autoFit;
        elements.liveMode.checked = state.liveMode;

        elements.taskSelect.addEventListener("change", async e => {
            state.task = e.target.value;
            window.history.replaceState({}, "", `${window.location.pathname}?task=${encodeURIComponent(state.task)}`);
            await loadBootstrap();
        });
        elements.mapStyle.addEventListener("change", e => { setMapLayer(e.target.value); rerender(); });
        elements.searchInput.addEventListener("input", e => { state.search = e.target.value; rerender(); });
        elements.showSubmitted.addEventListener("change", e => { state.showSubmitted = e.target.checked; rerender(); });
        elements.autoFit.addEventListener("change", e => { state.autoFit = e.target.checked; rerender(); });
        elements.liveMode.addEventListener("change", e => {
            state.liveMode = e.target.checked;
            if (state.liveMode) connectSocket();
            else { disconnectSocket(); elements.liveStatus.textContent = "Paused"; addFeedEntry("Live stream paused by operator", "warn"); }
        });
        elements.reloadBtn.addEventListener("click", () => loadBootstrap());
        elements.clearFeedBtn.addEventListener("click", () => {
            elements.eventFeed.innerHTML = "";
            addFeedEntry("Feed cleared by operator", "info");
        });
        elements.priorityFilters.addEventListener("click", e => {
            const btn = e.target.closest("button[data-priority]");
            if (!btn) return;
            state.priorityFilter = btn.dataset.priority;
            elements.priorityFilters.querySelectorAll("button[data-priority]")
                .forEach(b => b.classList.toggle("active", b === btn));
            rerender();
        });
        elements.incidentList.addEventListener("click", e => {
            const loc = e.target.closest(".btn-locate");
            if (loc) { const lat = Number(loc.dataset.lat), lon = Number(loc.dataset.lon); if (Number.isFinite(lat) && Number.isFinite(lon)) map.flyTo([lat, lon], 10, { duration: 0.7 }); return; }
            const ai = e.target.closest(".btn-analyse");
            if (ai) analyzeWithGemini({ id: ai.dataset.id, message: ai.dataset.msg, priority: ai.dataset.priority, team: ai.dataset.team });
        });
    }

    // ── INIT ──────────────────────────────────────────────────────────────────
    setMapLayer(state.mapStyle);
    wireControls();
    loadBootstrap();
    connectSocket();
    addFeedEntry("Tactical Command Dashboard initialized — all systems nominal", "ok");
});