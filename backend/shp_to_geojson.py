"""Convert data/taxi_zones.shp (NY State Plane EPSG:2263) to data/taxi_zones.geojson (WGS84).
Run once: python backend/shp_to_geojson.py
"""
import shapefile
import json
import os
from pyproj import Transformer

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
SHP  = os.path.join(DATA, "taxi_zones.shp")
OUT  = os.path.join(DATA, "taxi_zones.geojson")

xform = Transformer.from_crs("EPSG:2263", "EPSG:4326", always_xy=True)

def convert_ring(ring):
    return [list(xform.transform(x, y)) for x, y in ring]

def shp_to_geojson():
    sf = shapefile.Reader(SHP)
    fields = [f[0] for f in sf.fields[1:]]
    features = []
    for sr in sf.iterShapeRecords():
        rec   = dict(zip(fields, sr.record))
        shape = sr.shape
        if shape.shapeType not in (5, 15):
            continue
        parts = list(shape.parts) + [len(shape.points)]
        rings = [shape.points[parts[i]:parts[i+1]] for i in range(len(parts)-1)]
        coords = [convert_ring(r) for r in rings]
        features.append({
            "type": "Feature",
            "properties": {
                "location_id": int(rec["LocationID"]),
                "zone":        rec["zone"],
                "borough":     rec["borough"],
            },
            "geometry": {"type": "Polygon", "coordinates": coords},
        })

    fc = {"type": "FeatureCollection", "features": features}
    with open(OUT, "w") as fh:
        json.dump(fc, fh, separators=(",", ":"))
    print(f"Written {len(features)} zones to {OUT}")

if __name__ == "__main__":
    shp_to_geojson()
