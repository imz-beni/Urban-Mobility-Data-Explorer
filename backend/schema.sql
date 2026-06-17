-- schema.sql
-- Beni: normalized schema for the taxi.db

CREATE TABLE IF NOT EXISTS boroughs (
    borough_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    borough_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS zones (
    zone_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL UNIQUE,
    zone_name   TEXT NOT NULL,
    borough_id  INTEGER NOT NULL,
    FOREIGN KEY (borough_id) REFERENCES boroughs(borough_id)
);

CREATE TABLE IF NOT EXISTS trips (
    trip_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pickup_datetime   TEXT NOT NULL,
    dropoff_datetime  TEXT NOT NULL,
    trip_distance     REAL NOT NULL,
    fare_amount       REAL NOT NULL,
    total_amount      REAL NOT NULL,
    passenger_count   INTEGER NOT NULL,
    pu_zone_id        INTEGER NOT NULL,
    do_zone_id        INTEGER NOT NULL,
    trip_duration_min REAL NOT NULL,
    avg_speed_mph     REAL NOT NULL,
    fare_per_mile     REAL NOT NULL,
    time_of_day       TEXT NOT NULL,
    FOREIGN KEY (pu_zone_id) REFERENCES zones(zone_id),
    FOREIGN KEY (do_zone_id) REFERENCES zones(zone_id)
);

-- indexes to make the API queries fast
CREATE INDEX IF NOT EXISTS idx_pickup_dt   ON trips(pickup_datetime);
CREATE INDEX IF NOT EXISTS idx_time_of_day ON trips(time_of_day);
CREATE INDEX IF NOT EXISTS idx_pu_zone     ON trips(pu_zone_id);
CREATE INDEX IF NOT EXISTS idx_do_zone     ON trips(do_zone_id);
CREATE INDEX IF NOT EXISTS idx_distance    ON trips(trip_distance);
CREATE INDEX IF NOT EXISTS idx_fare        ON trips(fare_amount);
