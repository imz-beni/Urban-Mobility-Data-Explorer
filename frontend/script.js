const API = "http://127.0.0.1:5000/api";

const palette = ["#14213d", "#1e3a6b", "#2f6df6", "#5b8bff", "#f5b301", "#ff8f6b", "#6ed0a8"];
const charts = {};

async function get(path) {
    const res = await fetch(`${API}${path}`);
    return res.json();
}

function groupAvg(rows, groupKey, valueKey) {
    const buckets = {};
    for (const r of rows) {
        const key = r[groupKey];
        if (!buckets[key]) buckets[key] = { sum: 0, count: 0 };
        buckets[key].sum   += Number(r[valueKey]);
        buckets[key].count += 1;
    }
    const order = ["morning", "afternoon", "evening", "night"];
    return order
        .filter(k => buckets[k])
        .map(k => ({ label: k, value: +(buckets[k].sum / buckets[k].count).toFixed(2) }));
}

function average(rows, key) {
    if (!rows.length) return 0;
    return rows.reduce((s, r) => s + Number(r[key]), 0) / rows.length;
}

function drawBar(id, labels, values, label) {
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(document.getElementById(id), {
        type: "bar",
        data: {
            labels,
            datasets: [{ label, data: values, backgroundColor: palette, borderRadius: 6 }],
        },
        options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
    });
}

function drawLine(id, labels, values, label) {
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(document.getElementById(id), {
        type: "line",
        data: {
            labels,
            datasets: [{
                label,
                data: values,
                borderColor: "#2f6df6",
                backgroundColor: "rgba(47,109,246,0.12)",
                fill: true,
                tension: 0.35,
            }],
        },
        options: { plugins: { legend: { display: false } } },
    });
}

function updateCards(trips) {
    document.getElementById("statTrips").textContent    = trips.length;
    document.getElementById("statDistance").textContent = average(trips, "trip_distance").toFixed(1);
    document.getElementById("statFare").textContent     = average(trips, "fare_amount").toFixed(2);
    document.getElementById("statSpeed").textContent    = average(trips, "avg_speed_mph").toFixed(1);
}

function fillTable(trips) {
    const body = document.querySelector("#tripsTable tbody");
    body.innerHTML = "";
    for (const t of trips) {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${t.pickup_datetime}</td>
            <td>${t.pu_zone}</td>
            <td>${(+t.trip_distance).toFixed(1)} mi</td>
            <td>$${(+t.fare_amount).toFixed(2)}</td>
            <td>${(+t.avg_speed_mph).toFixed(1)} mph</td>
            <td>${t.time_of_day}</td>`;
        body.appendChild(row);
    }
}

async function loadBusiestZones() {
    const zones = await get("/busiest-zones");
    drawBar("zonesChart", zones.map(z => z.zone), zones.map(z => z.trips), "Trips");
}

async function render() {
    const borough   = document.getElementById("borough").value;
    const timeOfDay = document.getElementById("timeOfDay").value;
    const params    = new URLSearchParams();
    if (borough)   params.set("borough", borough);
    if (timeOfDay) params.set("time_of_day", timeOfDay);

    const trips = await get(`/trips?${params}`);

    updateCards(trips);
    fillTable(trips);

    const fareData  = groupAvg(trips, "time_of_day", "fare_per_mile");
    drawBar("fareChart", fareData.map(d => d.label), fareData.map(d => d.value), "$/mile");

    const speedData = groupAvg(trips, "time_of_day", "avg_speed_mph");
    drawLine("speedChart", speedData.map(d => d.label), speedData.map(d => d.value), "mph");
}

// ── Map ──────────────────────────────────────────────────────────────────────
const mapInstance = L.map("map", { zoomControl: true }).setView([40.73, -73.98], 11);

L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 19,
}).addTo(mapInstance);

let geoLayer = null;

function tripColor(count, max) {
    if (!count || count === 0) return "#eef1f8";
    const t = count / max;
    if (t < 0.25) return "#c6dbef";
    if (t < 0.5)  return "#6baed6";
    if (t < 0.75) return "#2171b5";
    return "#08306b";
}

async function loadMap() {
    const borough   = document.getElementById("borough").value;
    const timeOfDay = document.getElementById("timeOfDay").value;
    const params    = new URLSearchParams();
    if (borough)   params.set("borough", borough);
    if (timeOfDay) params.set("time_of_day", timeOfDay);

    const fc = await get(`/geojson?${params}`);
    if (!fc.features || fc.features.length === 0) return;

    const counts = fc.features.map(f => f.properties.trips || 0);
    const max    = Math.max(...counts) || 1;

    if (geoLayer) { mapInstance.removeLayer(geoLayer); geoLayer = null; }

    geoLayer = L.geoJSON(fc, {
        style(feature) {
            return {
                fillColor:   tripColor(feature.properties.trips, max),
                fillOpacity: 0.75,
                color:       "#ffffff",
                weight:      0.8,
            };
        },
        onEachFeature(feature, layer) {
            const p = feature.properties;
            layer.bindTooltip(
                `<strong>${p.zone}</strong><br>${p.borough}<br>${p.trips || 0} pickup${p.trips === 1 ? "" : "s"}`,
                { sticky: true, className: "map-tooltip" }
            );
        },
    }).addTo(mapInstance);
}

document.getElementById("applyBtn").addEventListener("click", () => { render(); loadMap(); });

loadBusiestZones();
render();
loadMap();
