from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)          # allow the frontend (different origin) to fetch these routes

# resolve relative to this file so the API runs from any working directory
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "taxi.db")


def query_db(sql, args=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.route("/api/trips")
def trips():
    borough = request.args.get("borough")
    tod     = request.args.get("time_of_day")
    sql = ("SELECT t.*, "
           "puz.zone_name AS pu_zone_name, "
           "doz.zone_name AS do_zone_name "
           "FROM trips t "
           "JOIN zones puz ON t.pu_zone_id = puz.zone_id "
           "JOIN zones doz ON t.do_zone_id = doz.zone_id "
           "WHERE 1=1")
    args = []
    if borough:
        sql += (" AND t.pu_zone_id IN "
                "(SELECT z.zone_id FROM zones z "
                "JOIN boroughs b ON z.borough_id = b.borough_id "
                "WHERE b.borough_name = ?)")
        args.append(borough)
    if tod:
        sql += " AND t.time_of_day = ?"
        args.append(tod)
    sql += " LIMIT 500"
    return jsonify(query_db(sql, args))


@app.route("/api/busiest-zones")
def busiest_zones():
    rows = query_db("SELECT pu_zone_id FROM trips")
    ranked = rank_busiest(rows)
    # attach human-readable names without touching the ranking algorithm
    names = {z["zone_id"]: z["zone_name"]
             for z in query_db("SELECT zone_id, zone_name FROM zones")}
    for item in ranked:
        item["zone_name"] = names.get(item["zone"], "Unknown")
    return jsonify(ranked)


def rank_busiest(rows):
    # 1) count trips per zone by hand
    counts = {}
    for r in rows:
        z = r["pu_zone_id"]
        counts[z] = counts.get(z, 0) + 1
    # 2) selection sort, descending, by count
    items = list(counts.items())          # [(zone, count), ...]
    n = len(items)
    for i in range(n):
        biggest = i
        for j in range(i + 1, n):
            if items[j][1] > items[biggest][1]:
                biggest = j
        items[i], items[biggest] = items[biggest], items[i]
    return [{"zone": z, "trips": c} for z, c in items[:10]]


# put the four buckets in real-world order instead of alphabetical
_TOD_ORDER = ("CASE time_of_day "
              "WHEN 'morning' THEN 1 WHEN 'afternoon' THEN 2 "
              "WHEN 'evening' THEN 3 WHEN 'night' THEN 4 ELSE 5 END")


@app.route("/api/fare-by-time")
def fare_by_time():
    return jsonify(query_db(
        "SELECT time_of_day, "
        "ROUND(AVG(fare_amount), 2) AS avg_fare, "
        "COUNT(*) AS trips "
        "FROM trips GROUP BY time_of_day ORDER BY " + _TOD_ORDER
    ))


@app.route("/api/speed-by-time")
def speed_by_time():
    return jsonify(query_db(
        "SELECT time_of_day, "
        "ROUND(AVG(avg_speed_mph), 2) AS avg_speed, "
        "COUNT(*) AS trips "
        "FROM trips GROUP BY time_of_day ORDER BY " + _TOD_ORDER
    ))


if __name__ == "__main__":
    app.run(debug=True)
