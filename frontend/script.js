const USE_MOCK = true;
const API = "http://127.0.0.1:5000/api";

const MOCK = {
  busiestZones: [
    { zone: "Midtown Center", trips: 25 },
    { zone: "Upper East Side South", trips: 14 },
    { zone: "Upper West Side South", trips: 11 },
    { zone: "JFK Airport", trips: 9 },
    { zone: "Times Sq / Theatre District", trips: 8 },
    { zone: "Murray Hill", trips: 6 },
    { zone: "Clinton East", trips: 5 },
  ],
  fareByTime: [
    { time_of_day: "morning", avg_fare_per_mile: 4.6 },
    { time_of_day: "afternoon", avg_fare_per_mile: 4.43 },
    { time_of_day: "evening", avg_fare_per_mile: 4.03 },
    { time_of_day: "night", avg_fare_per_mile: 3.8 },
  ],
  speedByTime: [
    { time_of_day: "morning", avg_speed: 7.3 },
    { time_of_day: "afternoon", avg_speed: 10.6 },
    { time_of_day: "evening", avg_speed: 11.3 },
    { time_of_day: "night", avg_speed: 14.1 },
  ],
  trips: [
    { pickup_datetime: "2024-01-15 08:12", pu_zone: "Midtown Center", trip_distance: 2.1, fare_amount: 12.5, avg_speed_mph: 7.7, time_of_day: "morning" },
    { pickup_datetime: "2024-01-15 13:40", pu_zone: "JFK Airport", trip_distance: 14.3, fare_amount: 52.0, avg_speed_mph: 22.5, time_of_day: "afternoon" },
    { pickup_datetime: "2024-01-15 18:55", pu_zone: "Times Sq / Theatre District", trip_distance: 1.4, fare_amount: 9.0, avg_speed_mph: 6.1, time_of_day: "evening" },
    { pickup_datetime: "2024-01-15 23:10", pu_zone: "Clinton East", trip_distance: 3.8, fare_amount: 16.5, avg_speed_mph: 15.2, time_of_day: "night" },
  ],
};

async function getData(path) {
  const res = await fetch(`${API}${path}`);
  return res.json();
}

async function loadBusiestZones() {
  return USE_MOCK ? MOCK.busiestZones : getData("/busiest-zones");
}

async function loadFareByTime() {
  return USE_MOCK ? MOCK.fareByTime : getData("/fare-by-time");
}

async function loadSpeedByTime() {
  return USE_MOCK ? MOCK.speedByTime : getData("/speed-by-time");
}

async function loadTrips(borough, timeOfDay) {
  if (USE_MOCK) return MOCK.trips;
  const params = new URLSearchParams();
  if (borough) params.set("borough", borough);
  if (timeOfDay) params.set("time_of_day", timeOfDay);
  return getData(`/trips?${params.toString()}`);
}

const palette = ["#14213d", "#1e3a6b", "#2f6df6", "#5b8bff", "#f5b301", "#ff8f6b", "#6ed0a8"];
const charts = {};

function drawBar(id, labels, values, label) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(document.getElementById(id), {
    type: "bar",
    data: {
      labels,
      datasets: [{ label, data: values, backgroundColor: palette, borderRadius: 6 }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
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
        backgroundColor: "rgba(47, 109, 246, 0.12)",
        fill: true,
        tension: 0.35,
      }],
    },
    options: { plugins: { legend: { display: false } } },
  });
}

function average(rows, key) {
  if (!rows.length) return 0;
  const total = rows.reduce((sum, r) => sum + r[key], 0);
  return total / rows.length;
}

function updateCards(trips) {
  document.getElementById("statTrips").textContent = trips.length;
  document.getElementById("statDistance").textContent = average(trips, "trip_distance").toFixed(1);
  document.getElementById("statFare").textContent = average(trips, "fare_amount").toFixed(2);
  document.getElementById("statSpeed").textContent = average(trips, "avg_speed_mph").toFixed(1);
}

function fillTable(trips) {
  const body = document.querySelector("#tripsTable tbody");
  body.innerHTML = "";
  for (const t of trips) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${t.pickup_datetime}</td>
      <td>${t.pu_zone}</td>
      <td>${t.trip_distance} mi</td>
      <td>$${t.fare_amount}</td>
      <td>${t.avg_speed_mph} mph</td>
      <td>${t.time_of_day}</td>`;
    body.appendChild(row);
  }
}

async function renderCharts() {
  const zones = await loadBusiestZones();
  drawBar("zonesChart", zones.map(z => z.zone), zones.map(z => z.trips), "Trips");

  const fare = await loadFareByTime();
  drawBar("fareChart", fare.map(f => f.time_of_day), fare.map(f => f.avg_fare_per_mile), "Fare per mile");

  const speed = await loadSpeedByTime();
  drawLine("speedChart", speed.map(s => s.time_of_day), speed.map(s => s.avg_speed), "Avg speed");
}

async function renderTrips() {
  const borough = document.getElementById("borough").value;
  const timeOfDay = document.getElementById("timeOfDay").value;
  const trips = await loadTrips(borough, timeOfDay);
  updateCards(trips);
  fillTable(trips);
}

document.getElementById("applyBtn").addEventListener("click", renderTrips);

renderCharts();
renderTrips();
