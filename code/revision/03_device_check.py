"""Step 03: how many Jurong devices were observed in the park ONLY inside the closed gardens?

Informs whether the device counts (6,792 devices; 4,942 with an inferred home; Appendix B; HI indices)
need revising. Uses the same stay-point file and centroid-in-hexagon rule as
gps_analysis/general_model/duration_analysis/main.ipynb. Writes outputs/devices_only_in_closed_gardens.csv.

Run with the geospatial env:  ~/.virtualenvs/geospatial/bin/python 03_device_check.py
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

stays = gpd.read_file(ROOT / "gis_files/hulls/jurong/breaks_hulls.geojson").to_crs(3414)
stays["device"] = stays["layer"].str.replace("clusters_convex_hulls_", "", regex=False)
stays["geometry"] = stays.geometry.centroid
hexes = gpd.read_file(ROOT / "gis_files/hexagons/agg_attributes/parks_allthree_hex_agg_attributes_visits.geojson")
hexes = hexes[hexes["park"] == "jurong"]
excluded = set(pd.read_csv(HERE / "excluded_hexes.csv")["grid_id"])

in_park = gpd.sjoin(stays, hexes[["grid_id", "geometry"]], predicate="within")
hex_sets = in_park.groupby("device")["grid_id"].apply(set)
only_closed = hex_sets[hex_sets.apply(lambda s: s <= excluded)].index

homes = json.loads((ROOT / "gps_analysis/activities_identification_example/"
                    "calibrated_residence_jurong_2022_updated.geojson").read_text())["features"]
home_type = {f["properties"]["id"]: f["properties"].get("PROP_TYPE") for f in homes}
out = pd.DataFrame({"device": only_closed, "home_type": [home_type.get(d) for d in only_closed]})
out.to_csv(HERE / "outputs/devices_only_in_closed_gardens.csv", index=False)

print(f"Devices in Jurong sample (paper: 6,792): {stays['device'].nunique():,}")
print(f"Devices with >=1 stay in the 107 study hexagons: {len(hex_sets):,}")
print(f"  ...of which ONLY in the 20 closed-garden hexagons: {len(out):,}")
print(f"  ...with an inferred home: {out['home_type'].notna().sum():,}  {out['home_type'].value_counts().to_dict()}")
