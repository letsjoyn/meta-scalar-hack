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
    };

    
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    
    function playAlertSound(priority) {
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        
        if (priority === 'urgent') {
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(800, audioCtx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(300, audioCtx.currentTime + 0.3);
            gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.3);
        } else if (priority === 'high') {
            osc.type = 'sine';
            osc.frequency.setValueAtTime(600, audioCtx.currentTime);
            gain.gain.setValueAtTime(0.05, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.2);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.2);
        } else {
            osc.type = 'sine';
            osc.frequency.setValueAtTime(400, audioCtx.currentTime);
            gain.gain.setValueAtTime(0.02, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.1);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.1);
        }
    }

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

    const map = L.map("map", { zoomControl: false }).setView([20, 0], 2);
    L.control.zoom({ position: "topleft" }).addTo(map);
    const markerLayer = L.layerGroup().addTo(map);

    const mapLayers = {
        terrain: L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }),
        light: L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        }),
        dark: L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        }),
    };

    let activeLayer = null;

    function setMapLayer(layerName) {
        if (activeLayer) {
            map.removeLayer(activeLayer);
        }
        activeLayer = mapLayers[layerName] || mapLayers.terrain;
        activeLayer.addTo(map);
        state.mapStyle = layerName;
        addFeedEntry(`Map layer set to ${layerName}.`, "ok");
    }

    function formatNow() {
        return new Date().toLocaleTimeString();
    }

    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function addFeedEntry(text, type = "info") {
        const li = document.createElement("li");
        li.className = `feed-item feed-${type}`;
        li.innerHTML = `
            <span class="feed-time">${formatNow()}</span>
            <span class="feed-text typewriter-text">${escapeHtml(text)}</span>
        `;
        elements.eventFeed.prepend(li);
        
        try { playAlertSound(type === "warn" || type === "error" ? "urgent" : "low"); } catch(e){}

        while (elements.eventFeed.children.length > 40) {
            elements.eventFeed.removeChild(elements.eventFeed.lastChild);
        }
    }

    function normalizeIncident(item) {
        return {
            id: item?.id || item?.ticket_id || "Unknown",
            message: item?.message || "No message available.",
            priority: String(item?.priority || "medium").toLowerCase(),
            lat: item?.lat,
            lon: item?.lon,
            submitted: Boolean(item?.submitted),
        };
    }

    function getPriorityColor(priority) {
        if (priority === "urgent") {
            return "#ff4545";
        }
        if (priority === "high") {
            return "#ff8a4d";
        }
        if (priority === "medium") {
            return "#ffc458";
        }
        return "#79f9b0";
    }

    function getFilteredIncidents() {
        const searchValue = state.search.trim().toLowerCase();

        return state.incidents.filter((incident) => {
            if (!state.showSubmitted && incident.submitted) {
                return false;
            }
            if (state.priorityFilter !== "all" && incident.priority !== state.priorityFilter) {
                return false;
            }
            if (!searchValue) {
                return true;
            }
            const haystack = `${incident.id} ${incident.message}`.toLowerCase();
            return haystack.includes(searchValue);
        });
    }

    function updateMetricCards() {
        const incidents = state.incidents;
        const urgent = incidents.filter((i) => i.priority === "urgent").length;
        const high = incidents.filter((i) => i.priority === "high").length;
        const submitted = incidents.filter((i) => i.submitted).length;

        elements.totalCount.textContent = String(incidents.length);
        elements.urgentCount.textContent = String(urgent);
        elements.highCount.textContent = String(high);
        elements.submittedCount.textContent = String(submitted);
        elements.score.textContent = Number(state.score).toFixed(3);
        elements.resources.textContent = `${Math.round(Number(state.resources) || 0)}%`;
        elements.liveStatus.textContent = state.liveMode ? "Live" : "Paused";
        elements.lastUpdate.textContent = formatNow();
    }

    function renderIncidentList(incidents) {
        elements.incidentList.innerHTML = "";

        if (!incidents.length) {
            const empty = document.createElement("li");
            empty.className = "empty-state";
            empty.textContent = "No incidents match the current filters.";
            elements.incidentList.appendChild(empty);
            return;
        }

        for (const incident of incidents) {
            const li = document.createElement("li");
            li.className = `incident-item priority-${incident.priority}`;
            const status = incident.submitted ? "Submitted" : "Active";
            const statusColor = incident.submitted ? "Submitted" : "Active";

            li.innerHTML = `
                <div class="incident-top">
                    <span class="incident-id">${escapeHtml(incident.id)}</span>
                    <span class="incident-priority">${escapeHtml(incident.priority)}</span>
                </div>
                <p class="incident-message">${escapeHtml(incident.message)}</p>
                <div class="incident-actions">
                    <button type="button" data-lat="${escapeHtml(incident.lat)}" data-lon="${escapeHtml(incident.lon)}">Locate</button>
                    <span class="incident-status">${escapeHtml(statusColor)}</span>
                </div>
            `;
            elements.incidentList.appendChild(li);
        }
    }

    function renderMap(incidents) {
        markerLayer.clearLayers();
        const latLngs = [];

        for (const incident of incidents) {
            const lat = Number(incident.lat);
            const lon = Number(incident.lon);
            if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
                continue;
            }

            latLngs.push([lat, lon]);

            const iconHtml = `<div class="marker-pin marker-${escapeHtml(incident.priority)}"><div class="marker-ring"></div></div>`;
            const customIcon = L.divIcon({
                html: iconHtml,
                className: '',
                iconSize: [16, 16],
                iconAnchor: [8, 8]
            });
            const marker = L.marker([lat, lon], { icon: customIcon }).addTo(markerLayer);

            marker.bindPopup(
                `<strong>${escapeHtml(incident.id)}</strong><br>${escapeHtml(incident.message)}<br><em>Priority: ${escapeHtml(incident.priority)}</em>`
            );
        }

        if (state.autoFit && latLngs.length > 0) {
            const bounds = L.latLngBounds(latLngs);
            map.fitBounds(bounds, { padding: [28, 28], maxZoom: 11 });
        }
    }

    function rerender() {
        const visibleIncidents = getFilteredIncidents();
        updateMetricCards();
        renderIncidentList(visibleIncidents);
        renderMap(visibleIncidents);
    }

    function applyPayload(payload, source) {
        if (typeof payload.score === "number") {
            state.score = payload.score;
        }
        if (typeof payload.resources === "number") {
            state.resources = payload.resources;
        }
        state.incidents = Array.isArray(payload.incidents)
            ? payload.incidents.map(normalizeIncident)
            : [];

        rerender();
        addFeedEntry(`${source} update received (${state.incidents.length} incidents).`, "ok");
    }

    async function loadBootstrap() {
        try {
            const response = await fetch(`/ui/bootstrap?task=${encodeURIComponent(state.task)}`);
            if (!response.ok) {
                throw new Error(`Bootstrap request failed (${response.status})`);
            }
            const payload = await response.json();
            applyPayload(payload, "Bootstrap");
        } catch (error) {
            addFeedEntry(`Bootstrap failed: ${error.message}`, "error");
        }
    }

    function disconnectSocket() {
        if (state.socket) {
            const socket = state.socket;
            state.socket = null;
            socket.close();
        }
    }

    function connectSocket() {
        if (!state.liveMode) {
            return;
        }

        const proto = window.location.protocol === "https:" ? "wss" : "ws";
        const socket = new WebSocket(`${proto}://${window.location.host}/ws`);
        state.socket = socket;

        socket.onopen = () => {
            addFeedEntry("Live stream connected.", "ok");
            elements.liveStatus.textContent = "Live";
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === "update" && data.payload) {
                    applyPayload(data.payload, "Live");
                    try {
                        const hasUrgent = data.payload.incidents && data.payload.incidents.some(i => i.priority === "urgent");
                        playAlertSound(hasUrgent ? "urgent" : "low");
                    } catch(e){}
                }
            } catch {
                addFeedEntry("Skipped malformed live payload.", "warn");
            }
        };

        socket.onerror = () => {
            addFeedEntry("Live stream error.", "error");
        };

        socket.onclose = () => {
            if (state.liveMode) {
                addFeedEntry("Live stream disconnected, reconnecting...", "warn");
                setTimeout(connectSocket, 1800);
            }
        };
    }

    function wireControls() {
        elements.taskSelect.value = state.task;
        elements.mapStyle.value = state.mapStyle;
        elements.showSubmitted.checked = state.showSubmitted;
        elements.autoFit.checked = state.autoFit;
        elements.liveMode.checked = state.liveMode;

        elements.taskSelect.addEventListener("change", async (event) => {
            state.task = event.target.value;
            const nextUrl = `${window.location.pathname}?task=${encodeURIComponent(state.task)}`;
            window.history.replaceState({}, "", nextUrl);
            await loadBootstrap();
        });

        elements.mapStyle.addEventListener("change", (event) => {
            setMapLayer(event.target.value);
            rerender();
        });

        elements.searchInput.addEventListener("input", (event) => {
            state.search = event.target.value;
            rerender();
        });

        elements.showSubmitted.addEventListener("change", (event) => {
            state.showSubmitted = event.target.checked;
            rerender();
        });

        elements.autoFit.addEventListener("change", (event) => {
            state.autoFit = event.target.checked;
            rerender();
        });

        elements.liveMode.addEventListener("change", (event) => {
            state.liveMode = event.target.checked;
            if (state.liveMode) {
                connectSocket();
            } else {
                disconnectSocket();
                elements.liveStatus.textContent = "Paused";
                addFeedEntry("Live stream paused by operator.", "warn");
            }
        });

        elements.reloadBtn.addEventListener("click", async () => {
            await loadBootstrap();
        });

        elements.clearFeedBtn.addEventListener("click", () => {
            elements.eventFeed.innerHTML = "";
            addFeedEntry("Feed cleared.", "info");
        });

        elements.priorityFilters.addEventListener("click", (event) => {
            const btn = event.target.closest("button[data-priority]");
            if (!btn) {
                return;
            }
            state.priorityFilter = btn.dataset.priority;

            const buttons = elements.priorityFilters.querySelectorAll("button[data-priority]");
            for (const item of buttons) {
                item.classList.toggle("active", item === btn);
            }
            rerender();
        });

        elements.incidentList.addEventListener("click", (event) => {
            const button = event.target.closest("button[data-lat][data-lon]");
            if (!button) {
                return;
            }

            const lat = Number(button.dataset.lat);
            const lon = Number(button.dataset.lon);
            if (Number.isFinite(lat) && Number.isFinite(lon)) {
                map.flyTo([lat, lon], 10, { duration: 0.7 });
            }
        });
    }

    setMapLayer(state.mapStyle);
    wireControls();
    loadBootstrap();
    connectSocket();
    addFeedEntry("Dashboard initialized.", "info");
});