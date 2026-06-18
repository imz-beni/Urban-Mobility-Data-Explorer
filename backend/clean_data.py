import pandas as pd
import os
import sys

# ── paths ─────────────────────────────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(_HERE, '..', 'data'))

PARQUET   = os.environ.get('TAXI_PARQUET',
            os.path.join(DATA_DIR, 'yellow_tripdata.parquet'))
ZONES_CSV = os.environ.get('TAXI_ZONES',
            os.path.join(DATA_DIR, 'taxi_zone_lookup.csv'))

CLEAN_CSV = os.path.join(DATA_DIR, 'clean_trips.csv')
EXCL_CSV  = os.path.join(DATA_DIR, 'excluded_records.csv')


def load_raw():
    for path, var in [(PARQUET, 'TAXI_PARQUET'), (ZONES_CSV, 'TAXI_ZONES')]:
        if not os.path.exists(path):
            sys.exit(
                f"ERROR: file not found: {path}\n"
                f"  Copy the file there, or set env var {var}=<full path>"
            )

    trips = pd.read_parquet(PARQUET, columns=[
        'tpep_pickup_datetime', 'tpep_dropoff_datetime',
        'trip_distance', 'fare_amount', 'total_amount',
        'passenger_count', 'PULocationID', 'DOLocationID',
    ])
    zones = pd.read_csv(ZONES_CSV, usecols=['LocationID', 'Borough', 'Zone'])
    return trips, zones


def join_zones(trips, zones):
    trips = trips.rename(columns={
        'tpep_pickup_datetime' : 'pickup_datetime',
        'tpep_dropoff_datetime': 'dropoff_datetime',
        'PULocationID'         : 'pu_location_id',
        'DOLocationID'         : 'do_location_id',
    })

    z  = zones.rename(columns={'LocationID': 'loc_id',
                                'Borough': 'borough', 'Zone': 'zone'})
    pu = z.rename(columns={'loc_id': 'pu_location_id',
                            'borough': 'pu_borough', 'zone': 'pu_zone'})
    do = z.rename(columns={'loc_id': 'do_location_id',
                            'borough': 'do_borough', 'zone': 'do_zone'})

    trips = trips.merge(pu, on='pu_location_id', how='left')
    trips = trips.merge(do, on='do_location_id', how='left')
    return trips


def main():
    print("Loading raw data ...")
    trips, zones = load_raw()
    print(f"  Raw rows : {len(trips):,}")

    trips = join_zones(trips, zones)
    print(f"  Columns  : {trips.columns.tolist()}")
    print("Load and join complete.")


if __name__ == '__main__':
    main()
