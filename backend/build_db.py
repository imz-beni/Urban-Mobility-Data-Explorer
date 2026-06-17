import sqlite3
import csv
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
CSV_PATH = os.path.join(DATA_DIR, 'clean_trips.csv')
DB_PATH  = os.path.join(DATA_DIR, 'taxi.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')


def get_time_of_day(dt_str):
    # dt_str looks like "2024-01-15 08:03:00"
    try:
        hour = int(dt_str[11:13])
    except (ValueError, IndexError):
        return 'unknown'
    if 5 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 17:
        return 'afternoon'
    elif 17 <= hour < 21:
        return 'evening'
    else:
        return 'night'


def build():
    if not os.path.exists(CSV_PATH):
        # fall back to sample if real file not here yet
        sample = os.path.join(DATA_DIR, 'sample_trips.csv')
        if os.path.exists(sample):
            print(f"clean_trips.csv not found, using sample: {sample}")
            src = sample
        else:
            print("ERROR: no CSV found in data/")
            sys.exit(1)
    else:
        src = CSV_PATH

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    with open(SCHEMA_PATH, 'r') as f:
        cur.executescript(f.read())

    borough_cache = {}
    zone_cache    = {}

    def get_or_create_borough(name):
        if name in borough_cache:
            return borough_cache[name]
        cur.execute('INSERT OR IGNORE INTO boroughs (borough_name) VALUES (?)', (name,))
        cur.execute('SELECT borough_id FROM boroughs WHERE borough_name = ?', (name,))
        bid = cur.fetchone()[0]
        borough_cache[name] = bid
        return bid

    def get_or_create_zone(location_id, zone_name, borough_name):
        key = int(location_id)
        if key in zone_cache:
            return zone_cache[key]
        bid = get_or_create_borough(borough_name)
        cur.execute(
            'INSERT OR IGNORE INTO zones (location_id, zone_name, borough_id) VALUES (?,?,?)',
            (key, zone_name, bid)
        )
        cur.execute('SELECT zone_id FROM zones WHERE location_id = ?', (key,))
        zid = cur.fetchone()[0]
        zone_cache[key] = zid
        return zid

    rows_loaded = 0
    rows_skipped = 0

    with open(src, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                pu_zid = get_or_create_zone(
                    row['pu_location_id'], row['pu_zone'], row['pu_borough']
                )
                do_zid = get_or_create_zone(
                    row['do_location_id'], row['do_zone'], row['do_borough']
                )
                tod = get_time_of_day(row['pickup_datetime'])
                cur.execute('''
                    INSERT INTO trips (
                        pickup_datetime, dropoff_datetime, trip_distance,
                        fare_amount, total_amount, passenger_count,
                        pu_zone_id, do_zone_id,
                        trip_duration_min, avg_speed_mph, fare_per_mile,
                        time_of_day
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ''', (
                    row['pickup_datetime'],
                    row['dropoff_datetime'],
                    float(row['trip_distance']),
                    float(row['fare_amount']),
                    float(row['total_amount']),
                    int(row['passenger_count']),
                    pu_zid,
                    do_zid,
                    float(row['trip_duration_min']),
                    float(row['avg_speed_mph']),
                    float(row['fare_per_mile']),
                    tod
                ))
                rows_loaded += 1
            except (ValueError, KeyError) as e:
                rows_skipped += 1
                continue

    conn.commit()

    # dump schema + data to taxi_dump.sql
    dump_path = os.path.join(DATA_DIR, 'taxi_dump.sql')
    with open(dump_path, 'w', encoding='utf-8') as dump_file:
        for line in conn.iterdump():
            dump_file.write(line + '\n')

    conn.close()
    print(f"Done. Loaded {rows_loaded} rows, skipped {rows_skipped}.")
    print(f"DB:   {DB_PATH}")
    print(f"Dump: {dump_path}")


if __name__ == '__main__':
    build()
