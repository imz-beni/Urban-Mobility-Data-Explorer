# Urban Mobility Data Explorer

A fullstack web application that processes, stores, and visualises NYC Yellow Taxi trip data to reveal how the city moves — by location, time, fare, and speed.

**Video Walkthrough:** [Link here]

---

## Team

| Member | Role |
|---|---|
| Beni  | Database schema, build script, data loader |
| Axcel | Data cleaning pipeline and feature engineering |
| Derrick | Flask REST API and custom ranking algorithm |
| Dianah | Frontend dashboard and visualisations |
| Lancelot | SQL insight queries and technical report |

---

## How it works

```
yellow_tripdata.parquet          taxi_zone_lookup.csv
         │                               │
         └──────── clean_data.py ────────┘
                        │
                  clean_trips.csv
                        │
                   build_db.py
                        │
                    taxi.db (SQLite)
                        │
                    app.py (Flask API)
                        │
              frontend/index.html (Dashboard)
```

---

## Tech Stack

- **Backend:** Python 3, Flask, flask-cors
- **Database:** SQLite 3
- **Frontend:** HTML5, CSS3, Vanilla JavaScript, Chart.js 4
- **Data sources:** NYC TLC yellow_tripdata (.parquet), taxi_zone_lookup (.csv)

---

## Project Structure

```
Urban-Mobility-Data-Explorer/
├── backend/
│   ├── app.py            # Flask API — 4 routes + zone-ranking algorithm
│   ├── clean_data.py     # Cleans raw parquet data, engineers 3 features
│   ├── build_db.py       # Loads clean_trips.csv into normalised SQLite
│   ├── schema.sql        # 3-table schema with 6 indexes
│   └── requirements.txt
├── data/
│   ├── sample_trips.csv  # 100-row sample for local development
│   └── taxi_dump.sql     # Full SQLite database dump
├── docs/
│   ├── insights.sql      # 3 analytical SQL queries
│   └── run_insights.py   # Runs and prints insight results
└── frontend/
    ├── index.html        # Dashboard — filters, stat cards, charts, table
    ├── style.css         # Professional navy/amber theme
    └── script.js         # API calls, Chart.js charts, card updates
```

---

## Setup and Running

**Requirements:** Python 3.8+

### 1. Clone the repo
```bash
git clone https://github.com/imz-beni/Urban-Mobility-Data-Explorer.git
cd Urban-Mobility-Data-Explorer
```

### 2. Install dependencies
```bash
pip install -r backend/requirements.txt
```

### 3. Build the database
```bash
python backend/build_db.py
```
Automatically falls back to `data/sample_trips.csv` if no cleaned data is present.

> **To use real TLC data:** place `yellow_tripdata.parquet` and `taxi_zone_lookup.csv` in `data/`, then run:
> ```bash
> python backend/clean_data.py
> python backend/build_db.py
> ```

### 4. Start the API *(keep this terminal open)*
```bash
python backend/app.py
```
Runs at `http://127.0.0.1:5000`

### 5. Open the dashboard *(open a second terminal)*
```bash
cd frontend
python -m http.server 5500
```
Visit `http://localhost:5500` in your browser.

---

## API Endpoints

| Method | Route | Params | Returns |
|---|---|---|---|
| GET | `/api/trips` | `borough`, `time_of_day` | Filtered trip records with zone names |
| GET | `/api/busiest-zones` | — | Top 10 pickup zones by trip count |
| GET | `/api/fare-by-time` | — | Avg fare/mile per time-of-day bucket |
| GET | `/api/speed-by-time` | — | Avg speed per time-of-day bucket |

---

## Database Schema

Three normalised tables. `boroughs` → `zones` → `trips`, with 6 indexes on the most-queried columns.

```sql
boroughs  ( borough_id PK, borough_name UNIQUE )

zones     ( zone_id PK, location_id UNIQUE, zone_name,
            borough_id FK → boroughs )

trips     ( trip_id PK, pickup_datetime, dropoff_datetime,
            trip_distance, fare_amount, total_amount, passenger_count,
            pu_zone_id FK → zones, do_zone_id FK → zones,
            trip_duration_min, avg_speed_mph, fare_per_mile, time_of_day )

Indexes: pickup_datetime, time_of_day, pu_zone_id,
         do_zone_id, trip_distance, fare_amount
```

---

## Data Cleaning

`backend/clean_data.py` processes raw `.parquet` trip records through four stages:

1. **Remove duplicates** — exact row matches dropped
2. **Drop nulls** — any row missing datetime, distance, fare, or passenger count
3. **Remove logical outliers** — distance ≤ 0, fare < 0, passenger count 0 or > 6
4. **Remove impossible speeds** — trips where avg_speed_mph ≥ 70 after feature engineering

Excluded records are saved to `data/excluded_records.csv` with a reason column for transparency.

**Three derived features:**

| Feature | Calculation | Why |
|---|---|---|
| `trip_duration_min` | (dropoff − pickup) ÷ 60 seconds | Enables speed and time analysis |
| `avg_speed_mph` | distance ÷ (duration ÷ 60) | Proxy for traffic congestion |
| `fare_per_mile` | fare ÷ distance | Normalised cost comparison across zones and times |

---

## Custom Algorithm — `rank_busiest`

`backend/app.py` — manually counts trips per pickup zone with a dictionary, then ranks them using **selection sort** with no built-in sort functions.

```
count = {}
for each trip:
    count[zone_id] += 1

for i from 0 to n:
    find the index of the largest count from i onward
    swap it into position i

return top 10
```

**Time complexity:** O(n) to count + O(k²) to sort — k = number of unique zones  
**Space complexity:** O(k)

---

## Three Insights

All queries are in `docs/insights.sql`. Run them with:
```bash
python docs/run_insights.py
```

**Insight 1 — Where do trips start?**
Manhattan generates 83% of all pickups. Queens accounts for the remaining 17%. Taxi demand is almost entirely concentrated in Manhattan.

**Insight 2 — When is a ride most expensive per mile?**
Morning rides cost $5.29/mile on average — 39% more expensive than night rides ($3.80/mile). Short, slow morning trips in dense zones drive the price up per mile.

**Insight 3 — When is the city slowest?**
Morning average speed is 7.3 mph — the slowest period of the day, confirming peak rush-hour congestion. Evening is fastest at 13.5 mph.

---

## Dashboard Features

- **Borough filter** — filter all data by pickup borough
- **Time of day filter** — morning / afternoon / evening / night
- **4 stat cards** — trips shown, avg distance, avg fare, avg speed (update on filter)
- **Busiest pickup zones** — bar chart, top 10 zones by trip count
- **Fare per mile by time of day** — bar chart showing pricing patterns
- **Average speed by time of day** — line chart showing congestion patterns
- **Recent trips table** — pickup time, zone, distance, fare, speed, time of day
