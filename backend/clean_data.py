import os
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

RAW_TRIPS = os.path.join(DATA_DIR, "yellow_tripdata.parquet")
ZONE_LOOKUP = os.path.join(DATA_DIR, "taxi_zone_lookup.csv")
CLEAN_OUT = os.path.join(DATA_DIR, "clean_trips.csv")
EXCLUDED_OUT = os.path.join(DATA_DIR, "excluded_records.csv")


def load_and_join():
    trips = pd.read_parquet(RAW_TRIPS)
    trips = trips[[
        "tpep_pickup_datetime", "tpep_dropoff_datetime", "trip_distance",
        "fare_amount", "total_amount", "passenger_count",
        "PULocationID", "DOLocationID",
    ]]
    trips.columns = [
        "pickup_datetime", "dropoff_datetime", "trip_distance", "fare_amount",
        "total_amount", "passenger_count", "pu_location_id", "do_location_id",
    ]

    zones = pd.read_csv(ZONE_LOOKUP).rename(columns={"LocationID": "loc_id"})

    trips = trips.merge(
        zones[["loc_id", "Borough", "Zone"]],
        left_on="pu_location_id", right_on="loc_id", how="left",
    ).rename(columns={"Borough": "pu_borough", "Zone": "pu_zone"}).drop(columns="loc_id")

    trips = trips.merge(
        zones[["loc_id", "Borough", "Zone"]],
        left_on="do_location_id", right_on="loc_id", how="left",
    ).rename(columns={"Borough": "do_borough", "Zone": "do_zone"}).drop(columns="loc_id")

    return trips


def clean(trips):
    before = len(trips)

    trips = trips.drop_duplicates()
    trips = trips.dropna(subset=[
        "pickup_datetime", "dropoff_datetime", "trip_distance", "fare_amount",
    ])

    bad = trips[
        (trips.trip_distance <= 0)
        | (trips.fare_amount < 0)
        | (trips.passenger_count <= 0)
    ]
    bad.to_csv(EXCLUDED_OUT, index=False)
    trips = trips.drop(bad.index)

    return trips, before


def add_features(trips):
    trips["pickup_datetime"] = pd.to_datetime(trips["pickup_datetime"])
    trips["dropoff_datetime"] = pd.to_datetime(trips["dropoff_datetime"])

    duration = (trips.dropoff_datetime - trips.pickup_datetime).dt.total_seconds() / 60
    trips["trip_duration_min"] = duration.round(2)
    trips = trips[trips.trip_duration_min > 0]

    trips["avg_speed_mph"] = (trips.trip_distance / (trips.trip_duration_min / 60)).round(2)
    trips["fare_per_mile"] = (trips.fare_amount / trips.trip_distance).round(2)
    trips = trips[trips.avg_speed_mph < 70]

    return trips


def main():
    trips = load_and_join()
    trips, before = clean(trips)
    trips = add_features(trips)

    columns = [
        "pickup_datetime", "dropoff_datetime", "trip_distance", "fare_amount",
        "total_amount", "passenger_count", "pu_location_id", "do_location_id",
        "pu_borough", "pu_zone", "do_borough", "do_zone",
        "trip_duration_min", "avg_speed_mph", "fare_per_mile",
    ]
    trips[columns].to_csv(CLEAN_OUT, index=False)

    print(f"Kept {len(trips)} of {before} rows. Excluded {before - len(trips)}.")
    print(f"Clean data: {CLEAN_OUT}")
    print(f"Excluded log: {EXCLUDED_OUT}")


if __name__ == "__main__":
    main()
