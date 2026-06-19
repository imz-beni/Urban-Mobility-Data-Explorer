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

# agreed data contract — do not change without team agreement
CONTRACT = [
    'pickup_datetime', 'dropoff_datetime', 'trip_distance', 'fare_amount',
    'total_amount', 'passenger_count', 'pu_location_id', 'do_location_id',
    'pu_borough', 'pu_zone', 'do_borough', 'do_zone',
    'trip_duration_min', 'avg_speed_mph', 'fare_per_mile',
]


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


def clean(trips, zones):
    total_raw  = len(trips)
    excl_parts = []

    def exclude(mask, reason):
        excl_parts.append(trips[mask].assign(exclusion_reason=reason))
        return trips[~mask].copy()

    # 1. exact duplicates
    trips = exclude(trips.duplicated(), 'duplicate')

    # 2. nulls in any column we depend on for cleaning or features
    null_mask = trips[[
        'tpep_pickup_datetime', 'tpep_dropoff_datetime',
        'trip_distance', 'fare_amount', 'passenger_count',
    ]].isnull().any(axis=1)
    trips = exclude(null_mask, 'null_in_critical_field')

    # 3. logically impossible values before we derive features
    bad = (
        (trips['trip_distance']   <= 0) |
        (trips['fare_amount']     <  0) |
        (trips['passenger_count'] <= 0) |
        (trips['passenger_count'] >  6)
    )
    trips = exclude(bad, 'logical_outlier')

    # 4. rename raw parquet columns to the agreed contract names
    trips = trips.rename(columns={
        'tpep_pickup_datetime' : 'pickup_datetime',
        'tpep_dropoff_datetime': 'dropoff_datetime',
        'PULocationID'         : 'pu_location_id',
        'DOLocationID'         : 'do_location_id',
    })

    # 5. join zone names (left join keeps trips even if zone id is unknown)
    z  = zones.rename(columns={'LocationID': 'loc_id',
                                'Borough': 'borough', 'Zone': 'zone'})
    pu = z.rename(columns={'loc_id': 'pu_location_id',
                            'borough': 'pu_borough', 'zone': 'pu_zone'})
    do = z.rename(columns={'loc_id': 'do_location_id',
                            'borough': 'do_borough', 'zone': 'do_zone'})
    trips = trips.merge(pu, on='pu_location_id', how='left')
    trips = trips.merge(do, on='do_location_id', how='left')

    # 6. derived feature 1 — trip_duration_min
    trips['pickup_datetime']  = pd.to_datetime(trips['pickup_datetime'])
    trips['dropoff_datetime'] = pd.to_datetime(trips['dropoff_datetime'])
    trips['trip_duration_min'] = (
        (trips['dropoff_datetime'] - trips['pickup_datetime'])
        .dt.total_seconds() / 60
    )
    trips = exclude(trips['trip_duration_min'] <= 0, 'zero_or_negative_duration')

    # 7. derived feature 2 — avg_speed_mph
    trips['avg_speed_mph'] = (
        trips['trip_distance'] / (trips['trip_duration_min'] / 60)
    )
    # 70 mph is physically impossible in NYC street traffic
    trips = exclude(trips['avg_speed_mph'] >= 70, 'impossible_speed_ge_70mph')

    # 8. derived feature 3 — fare_per_mile
    trips['fare_per_mile'] = trips['fare_amount'] / trips['trip_distance']

    trips['passenger_count'] = trips['passenger_count'].astype(int)

    excl_df = pd.concat(excl_parts, ignore_index=True) if excl_parts else pd.DataFrame()
    return trips[CONTRACT], excl_df, total_raw


def main():
    print("Loading raw data ...")
    trips, zones = load_raw()
    print(f"  Raw rows : {len(trips):,}")

    print("Cleaning ...")
    clean_df, excl_df, total_raw = clean(trips, zones)

    clean_df.to_csv(CLEAN_CSV, index=False)
    excl_df.to_csv(EXCL_CSV,   index=False)

    kept = len(clean_df)
    print(f"  Kept     : {kept:,}")
    print(f"  Excluded : {total_raw - kept:,}")
    print(f"  output   : {CLEAN_CSV}")
    print(f"  log      : {EXCL_CSV}")


if __name__ == '__main__':
    main()
