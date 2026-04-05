document.addEventListener('DOMContentLoaded', () => {
    const map = L.map('map').setView([20, 0], 2);
    const markerLayer = L.layerGroup().addTo(map);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    const incidentList = document.getElementById('incident-list');
    const scoreEl = document.getElementById('score');
    const resourcesEl = document.getElementById('resources');

    const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${wsProto}://${window.location.host}/ws`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'update') {
            updateUI(data.payload);
        }
    };

    function updateUI(data) {
        scoreEl.textContent = data.score;
        resourcesEl.textContent = `${data.resources}%`;
        markerLayer.clearLayers();

        const latLngs = [];

        incidentList.innerHTML = '';
        data.incidents.forEach(incident => {
            const li = document.createElement('li');
            li.className = `incident ${incident.priority}`;
            li.innerHTML = `
                <h3>${incident.id}</h3>
                <p>${incident.message}</p>
            `;
            incidentList.appendChild(li);

            const lat = Number(incident.lat);
            const lon = Number(incident.lon);
            if (Number.isFinite(lat) && Number.isFinite(lon)) {
                latLngs.push([lat, lon]);
                L.marker([lat, lon]).addTo(markerLayer)
                    .bindPopup(`<b>${incident.id}</b><br>${incident.message}`);
            }
        });

        if (latLngs.length > 0) {
            const bounds = L.latLngBounds(latLngs);
            map.fitBounds(bounds, { padding: [24, 24], maxZoom: 11 });
        }
    }
});