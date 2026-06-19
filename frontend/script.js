const API = "http://127.0.0.1:5000/api";

const palette = ["#14213d", "#1e3a6b", "#2f6df6", "#5b8bff", "#f5b301", "#ff8f6b", "#6ed0a8"];
const charts = {};

async function get(path) {
    const res = await fetch(`${API}${path}`);
    return res.json();
}

function average(rows, key) {
    if (!rows.length) return 0;
    return rows.reduce((s, r) => s + r[key], 0) / rows.length;
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

async function renderCharts() {
    const zones = await get("/busiest-zones");
    drawBar("zonesChart", zones.map(z => z.zone), zones.map(z => z.trips), "Trips");

    const fare = await get("/fare-by-time");
    drawBar("fareChart", fare.map(f => f.time_of_day), fare.map(f => f.avg_fare_per_mile), "$/mile");

    const speed = await get("/speed-by-time");
    drawLine("speedChart", speed.map(s => s.time_of_day), speed.map(s => s.avg_speed), "mph");
}

async function renderTrips() {
    const borough   = document.getElementById("borough").value;
    const timeOfDay = document.getElementById("timeOfDay").value;
    const params    = new URLSearchParams();
    if (borough)   params.set("borough", borough);
    if (timeOfDay) params.set("time_of_day", timeOfDay);

    const trips = await get(`/trips?${params}`);
    updateCards(trips);
    fillTable(trips);
}

document.getElementById("applyBtn").addEventListener("click", renderTrips);

renderCharts();
renderTrips();
