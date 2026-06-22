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


def build_filters(alias=""):
    """Read the shared ?borough= and ?time_of_day= query params and turn them
    into a SQL fragment + bound args. Every data route uses this so the table,
    the stat cards AND the charts all respond to the same filters.

    `alias` is an optional table prefix (e.g. "t.") for queries that alias the
    trips table. The fragment is meant to follow a `WHERE 1=1`, so it always
    begins with " AND ..." (or is empty when no filters are set).
    """
    borough = request.args.get("borough")
    tod     = request.args.get("time_of_day")
    sql, args = "", []
    if borough:
        sql += (f" AND {alias}pu_zone_id IN "
                "(SELECT z.zone_id FROM zones z "
                "JOIN boroughs b ON z.borough_id = b.borough_id "
                "WHERE b.borough_name = ?)")
        args.append(borough)
    if tod:
        sql += f" AND {alias}time_of_day = ?"
        args.append(tod)
    return sql, args


@app.route("/api/trips")
def trips():
    where, args = build_filters(alias="t.")
    sql = ("SELECT t.*, "
           "puz.zone_name AS pu_zone, "
           "pub.borough_name AS pu_borough, "
           "doz.zone_name AS do_zone, "
           "dob.borough_name AS do_borough "
           "FROM trips t "
           "JOIN zones puz ON t.pu_zone_id = puz.zone_id "
           "JOIN boroughs pub ON puz.borough_id = pub.borough_id "
           "JOIN zones doz ON t.do_zone_id = doz.zone_id "
           "JOIN boroughs dob ON doz.borough_id = dob.borough_id "
           "WHERE 1=1" + where + " LIMIT 500")
    return jsonify(query_db(sql, args))


@app.route("/api/busiest-zones")
def busiest_zones():
    where, args = build_filters()
    rows = query_db("SELECT pu_zone_id FROM trips WHERE 1=1" + where, args)
    ranked = rank_busiest(rows)
    # swap the zone IDs for names (chart labels), algorithm itself untouched
    names = {z["zone_id"]: z["zone_name"]
             for z in query_db("SELECT zone_id, zone_name FROM zones")}
    for item in ranked:
        item["zone"] = names.get(item["zone"], "Unknown")
    return jsonify(ranked)


def rank_busiest(rows):
    """Rank pickup zones by trip volume — custom, no built-in helpers.

    Pseudo-code
    -----------
        function rank_busiest(rows):
            counts = empty map
            for each row in rows:                 # manual count, no Counter
                z = row.pu_zone_id
                counts[z] = counts[z] + 1         # default 0 if unseen

            items = list of (zone, count) pairs from counts
            n = length(items)

            for i from 0 to n-1:                  # selection sort, descending
                biggest = i
                for j from i+1 to n-1:
                    if items[j].count > items[biggest].count:
                        biggest = j
                swap items[i] and items[biggest]

            return first 10 of items as {zone, trips}

    Complexity
    ----------
        Time : O(n + k^2)  — O(n) counting pass over n trips, then an
               O(k^2) selection sort over k distinct zones.
        Space: O(k)        — the counts map plus the items list.

    k (distinct NYC taxi zones) is small and bounded (~260), so the k^2
    sort is effectively constant; the linear counting pass dominates.
    Full write-up and design justification in docs/algorithm.md.
    """
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
    where, args = build_filters()
    return jsonify(query_db(
        "SELECT time_of_day, "
        "ROUND(AVG(fare_per_mile), 2) AS avg_fare_per_mile, "
        "COUNT(*) AS trips "
        "FROM trips WHERE 1=1" + where +
        " GROUP BY time_of_day ORDER BY " + _TOD_ORDER, args
    ))


@app.route("/api/speed-by-time")
def speed_by_time():
    where, args = build_filters()
    return jsonify(query_db(
        "SELECT time_of_day, "
        "ROUND(AVG(avg_speed_mph), 2) AS avg_speed, "
        "COUNT(*) AS trips "
        "FROM trips WHERE 1=1" + where +
        " GROUP BY time_of_day ORDER BY " + _TOD_ORDER, args
    ))


if __name__ == "__main__":
    app.run(debug=True)
