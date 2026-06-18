from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)


def query_db(sql, args=()):
    conn = sqlite3.connect("data/taxi.db")
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.route("/api/trips")
def trips():
    borough = request.args.get("borough")
    tod     = request.args.get("time_of_day")
    sql, args = "SELECT * FROM trips WHERE 1=1", []
    if borough:
        sql += (" AND pu_zone_id IN "
                "(SELECT z.zone_id FROM zones z "
                "JOIN boroughs b ON z.borough_id = b.borough_id "
                "WHERE b.borough_name = ?)")
        args.append(borough)
    if tod:
        sql += " AND time_of_day = ?"
        args.append(tod)
    sql += " LIMIT 500"
    return jsonify(query_db(sql, args))


@app.route("/api/busiest-zones")
def busiest_zones():
    rows = query_db("SELECT pu_zone_id FROM trips")
    return jsonify(rank_busiest(rows))


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


if __name__ == "__main__":
    app.run(debug=True)
