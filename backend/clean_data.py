import pandas as pd
import shapefile
import os
import sys

# ── paths ─────────────────────────────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(_HERE, '..', 'data'))

PARQUET   = os.environ.get('TAXI_PARQUET',
            os.path.join(DATA_DIR, 'yellow_tripdata.parquet'))
ZONES_CSV = os.environ.get('TAXI_ZONES',
            os.path.join(DATA_DIR, 'taxi_zone_lookup.csv'))
ZONES_SHP = os.environ.get('TAXI_ZONES_SHP',
            os.path.join(DATA_DIR, 'taxi_zones.shp'))

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
    for path, var in [(PARQUET, 'TAXI_PARQUET'), (ZONES_CSV, 'TAXI_ZONES'),
                      (ZONES_SHP, 'TAXI_ZONES_SHP')]:
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

    # read the shapefile to get location IDs that have valid spatial boundaries
    sf = shapefile.Reader(ZONES_SHP)
    loc_field = [f[0] for f in sf.fields[1:]].index('LocationID')
    spatial_ids = {int(rec[loc_field]) for rec in sf.records()}

    return trips, zones, spatial_ids


def clean(trips, zones, spatial_ids):
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

    # 4. trips where the pickup zone has no spatial boundary in the GeoJSON
    no_spatial = ~trips['PULocationID'].isin(spatial_ids)
    trips = exclude(no_spatial, 'no_spatial_boundary')

    # 5. rename raw parquet columns to the agreed contract names
    trips = trips.rename(columns={
        'tpep_pickup_datetime' : 'pickup_datetime',
        'tpep_dropoff_datetime': 'dropoff_datetime',
        'PULocationID'         : 'pu_location_id',
        'DOLocationID'         : 'do_location_id',
    })

    # 6. join zone names (left join keeps trips even if zone id is unknown)
    z  = zones.rename(columns={'LocationID': 'loc_id',
                                'Borough': 'borough', 'Zone': 'zone'})
    pu = z.rename(columns={'loc_id': 'pu_location_id',
                            'borough': 'pu_borough', 'zone': 'pu_zone'})
    do = z.rename(columns={'loc_id': 'do_location_id',
                            'borough': 'do_borough', 'zone': 'do_zone'})
    trips = trips.merge(pu, on='pu_location_id', how='left')
    trips = trips.merge(do, on='do_location_id', how='left')

    # 7. derived feature 1 — trip_duration_min
    trips['pickup_datetime']  = pd.to_datetime(trips['pickup_datetime'])
    trips['dropoff_datetime'] = pd.to_datetime(trips['dropoff_datetime'])
    trips['trip_duration_min'] = (
        (trips['dropoff_datetime'] - trips['pickup_datetime'])
        .dt.total_seconds() / 60
    )
    trips = exclude(trips['trip_duration_min'] <= 0, 'zero_or_negative_duration')

    # 8. derived feature 2 — avg_speed_mph
    trips['avg_speed_mph'] = (
        trips['trip_distance'] / (trips['trip_duration_min'] / 60)
    )
    # 70 mph is physically impossible in NYC street traffic
    trips = exclude(trips['avg_speed_mph'] >= 70, 'impossible_speed_ge_70mph')

    # 9. derived feature 3 — fare_per_mile
    trips['fare_per_mile'] = trips['fare_amount'] / trips['trip_distance']

    trips['passenger_count'] = trips['passenger_count'].astype(int)

    excl_df = pd.concat(excl_parts, ignore_index=True) if excl_parts else pd.DataFrame()
    return trips[CONTRACT], excl_df, total_raw


def main():
    print("Loading raw data ...")
    trips, zones, spatial_ids = load_raw()
    print(f"  Raw rows     : {len(trips):,}")
    print(f"  Spatial zones: {len(spatial_ids)} valid zone boundaries loaded")

    print("Cleaning ...")
    clean_df, excl_df, total_raw = clean(trips, zones, spatial_ids)

    clean_df.to_csv(CLEAN_CSV, index=False)
    excl_df.to_csv(EXCL_CSV,   index=False)

    kept = len(clean_df)
    print(f"  Kept         : {kept:,}")
    print(f"  Excluded     : {total_raw - kept:,}")
    print()
    print("Exclusion breakdown:")
    if not excl_df.empty:
        for reason, count in excl_df['exclusion_reason'].value_counts().items():
            print(f"  {reason:<35} {count:>8,}")
    print(f"  output       : {CLEAN_CSV}")
    print(f"  log          : {EXCL_CSV}")


if __name__ == '__main__':
    main()
