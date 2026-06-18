import os
import sqlite3
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "taxi.db")


def query_db(sql, args=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.route("/api/trips")
def trips():
    borough = request.args.get("borough")
    time_of_day = request.args.get("time_of_day")

    sql = """
        SELECT t.pickup_datetime, t.trip_distance, t.fare_amount,
               t.total_amount, t.passenger_count, t.trip_duration_min,
               t.avg_speed_mph, t.fare_per_mile, t.time_of_day,
               pz.zone_name AS pu_zone, pb.borough_name AS pu_borough
        FROM trips t
        JOIN zones pz ON t.pu_zone_id = pz.zone_id
        JOIN boroughs pb ON pz.borough_id = pb.borough_id
        WHERE 1 = 1
    """
    args = []
    if borough:
        sql += " AND pb.borough_name = ?"
        args.append(borough)
    if time_of_day:
        sql += " AND t.time_of_day = ?"
        args.append(time_of_day)
    sql += " LIMIT 500"

    return jsonify(query_db(sql, args))


@app.route("/api/busiest-zones")
def busiest_zones():
    rows = query_db("""
        SELECT pz.zone_name AS zone
        FROM trips t
        JOIN zones pz ON t.pu_zone_id = pz.zone_id
    """)
    return jsonify(rank_busiest(rows))


@app.route("/api/fare-by-time")
def fare_by_time():
    return jsonify(query_db("""
        SELECT time_of_day, ROUND(AVG(fare_per_mile), 2) AS avg_fare_per_mile
        FROM trips
        WHERE fare_per_mile < 50
        GROUP BY time_of_day
    """))


@app.route("/api/speed-by-time")
def speed_by_time():
    return jsonify(query_db("""
        SELECT time_of_day, ROUND(AVG(avg_speed_mph), 1) AS avg_speed
        FROM trips
        WHERE avg_speed_mph BETWEEN 1 AND 60
        GROUP BY time_of_day
        ORDER BY avg_speed
    """))


def rank_busiest(rows):
    counts = {}
    for r in rows:
        zone = r["zone"]
        counts[zone] = counts.get(zone, 0) + 1

    items = list(counts.items())
    n = len(items)
    for i in range(n):
        biggest = i
        for j in range(i + 1, n):
            if items[j][1] > items[biggest][1]:
                biggest = j
        items[i], items[biggest] = items[biggest], items[i]

    return [{"zone": z, "trips": c} for z, c in items[:10]]


if __name__ == "__main__":
    app.run(debug=True)
