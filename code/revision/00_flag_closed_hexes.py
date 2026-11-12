"""Step 00: build the revised model input.

1. Flag Jurong Lake Gardens hexagons inside the Chinese and Japanese Gardens. The two gardens were closed
   for redevelopment from May 2019 to 8 Sep 2024, i.e. during the September 2022 GPS observation period,
   but open (redesigned) when the street-level imagery was collected in 2025. Hexagons with >= 50% of
   their area inside either garden are excluded.
2. Recount park services (peps) for all three parks from the most recent service-point file,
   gis_files/poi/poi_all_parks.geojson (Mar 2026; NParks facilities + Google Places; all points kept,
   decision 2026-11-11). Same method as analysis/intra-park/proximity_calculation/park_service.ipynb:
   points within 500 m of each hexagon's origin point. The stored peps came from an Oct 2025 POI file
   that no longer exists and cannot be reproduced.
3. Recount F_h (decision 2026-11-12, Reviewer R3-(4)). The duration notebook
   (gps_analysis/general_model/duration_analysis/main.ipynb) and the housing-type notebook
   (analysis/travel_pattern_by_neighbourhood/main.ipynb) count nunique('cluster') per hexagon, but ST-DBSCAN
   numbers clusters per device, so clusters of different devices with the same number merge. Corrected
   F_h = number of device clusters whose hull centroid lies in the hexagon (count, not nunique), overall and
   per housing group. D_h is unchanged. Corrected copies of the per-park cell files go to corrected_fh/;
   the upstream notebooks and files are not changed (the "original" variants still reproduce the paper).

Reads (unchanged):
  gis_files/hexagons/agg_attributes/parks_allthree_hex_agg_attributes_visits.geojson
  gis_files/jurong_lake/chinese_japanese_gardens_osm.geojson
  gis_files/poi/poi_all_parks.geojson, analysis/path_calculation/origins_{park}_coords.csv
  gis_files/hulls/{park}/breaks_hulls.geojson, gis_files/hexagons/segmented/{park}_hex_agg.geojson,
  gps_analysis/activities_identification_example/calibrated_residence_{park}_2022_updated.geojson,
  gps_analysis/general_model/duration_analysis/{park}_duration_analysis[_byhousingtypes].geojson
Writes (this folder):
  excluded_hexes.csv
  parks_allthree_hex_agg_attributes_visits_excl_closed.geojson
  corrected_fh/{park}_duration_analysis.geojson, corrected_fh/{park}_duration_analysis_byhousingtypes.geojson

Run with the geospatial env:  ~/.virtualenvs/geospatial/bin/python 00_flag_closed_hexes.py
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HEX_PATH = ROOT / "gis_files/hexagons/agg_attributes/parks_allthree_hex_agg_attributes_visits.geojson"
GARDENS_PATH = ROOT / "gis_files/jurong_lake/chinese_japanese_gardens_osm.geojson"
POI_PATH = ROOT / "gis_files/poi/poi_all_parks.geojson"
MIN_SHARE = 0.5  # share of hexagon area inside a closed garden
SERVICE_RADIUS_M = 500
DUR = ROOT / "gps_analysis/general_model/duration_analysis"
FIX = HERE / "corrected_fh"
GROUPS = {"hdb": ["HDB"], "landed": ["Landed"], "nolanded": ["Non-Landed", "EC"]}  # as the housing-type notebook


def recount_fh(park):
    """Corrected F_h per hexagon of the park grid, overall and per housing group; checks the join against the stored files."""
    hulls = gpd.read_file(ROOT / f"gis_files/hulls/{park}/breaks_hulls.geojson").to_crs(3414)
    hulls["device"] = hulls["layer"].str.replace("clusters_convex_hulls_", "")
    hulls["geometry"] = hulls.geometry.centroid
    grid = gpd.read_file(ROOT / f"gis_files/hexagons/segmented/{park}_hex_agg.geojson")[["grid_id", "geometry"]]
    j = gpd.sjoin(grid, hulls[["device", "cluster", "duration", "geometry"]], how="left", predicate="intersects")
    res = gpd.read_file(ROOT / f"gps_analysis/activities_identification_example/calibrated_residence_{park}_2022_updated.geojson")
    j["group"] = None
    for grp, types in GROUPS.items():
        j.loc[j["device"].isin(res.loc[res["PROP_TYPE"].isin(types), "id"].astype(str)), "group"] = grp

    def counts(rows, suffix=""):
        g = rows.groupby("grid_id")
        return pd.DataFrame({f"F_h{suffix}": g["cluster"].count(), f"old_F_h{suffix}": g["cluster"].nunique(),
                             f"D_h{suffix}": g["duration"].sum()})

    new = pd.concat([counts(j)] + [counts(j[j["group"] == grp], f"_{grp}") for grp in GROUPS], axis=1)
    new = new.reindex(grid["grid_id"]).fillna(0)
    FIX.mkdir(exist_ok=True)
    for name, cols in [("", ["F_h"]), ("_byhousingtypes", [f"F_h_{grp}" for grp in GROUPS])]:
        stored = gpd.read_file(DUR / f"{park}_duration_analysis{name}.geojson")
        n = new.loc[stored["grid_id"]].reset_index(drop=True)
        for col in cols:  # the join must reproduce the stored nunique counts and D_h before F_h is replaced
            assert (stored[col].to_numpy() == n[f"old_{col}"].to_numpy()).all(), f"{park}{name} {col}: join differs"
            assert np.allclose(stored[col.replace("F_h", "D_h")], n[col.replace("F_h", "D_h")]), f"{park}{name}: D_h differs"
            stored[col] = n[col].astype(int).to_numpy()
        stored.to_file(FIX / f"{park}_duration_analysis{name}.geojson", driver="GeoJSON")
    return new["F_h"].astype(int)

hexes = gpd.read_file(HEX_PATH)

# park services: count service points within 500 m of each hexagon's origin point, per park
pois = gpd.read_file(POI_PATH).to_crs(3414)
old_mean = hexes.groupby("park")["peps"].mean()
for park in hexes["park"].unique():
    o = pd.read_csv(ROOT / f"analysis/path_calculation/origins_{park}_coords.csv")
    buffers = gpd.GeoDataFrame(o[["grid_id"]], geometry=gpd.points_from_xy(o.lon, o.lat), crs=4326).to_crs(3414)
    buffers["geometry"] = buffers.buffer(SERVICE_RADIUS_M)
    counts = gpd.sjoin(buffers, pois[["geometry"]], predicate="intersects").groupby("grid_id").size()
    sel = hexes["park"] == park
    assert hexes.loc[sel, "grid_id"].isin(o["grid_id"]).all(), f"{park}: hexagon without an origin point"
    hexes.loc[sel, "peps"] = hexes.loc[sel, "grid_id"].map(counts).fillna(0).astype(hexes["peps"].dtype)
print("Park services, mean count per hexagon (stored Oct 2025 -> poi_all_parks Mar 2026):",
      {p: f"{old_mean[p]:.1f} -> {m:.1f}" for p, m in hexes.groupby("park")["peps"].mean().items()})

# F_h: replace the stored (nunique) count of every model hexagon with the corrected count
hexes["F_h"] = pd.to_numeric(hexes["F_h"], errors="coerce").fillna(0).astype("int64")
for park in hexes["park"].unique():
    fixed = recount_fh(park)
    sel = hexes["park"] == park
    stored = pd.to_numeric(hexes.loc[sel, "F_h"], errors="coerce").fillna(0)
    assert hexes.loc[sel, "grid_id"].isin(fixed.index).all(), f"{park}: model hexagon not in the park grid"
    hexes.loc[sel, "F_h"] = hexes.loc[sel, "grid_id"].map(fixed).to_numpy()
    print(f"F_h {park}: total {int(stored.sum()):,} -> {int(hexes.loc[sel, 'F_h'].sum()):,} clusters on the model hexagons")

gardens = gpd.read_file(GARDENS_PATH).to_crs(hexes.crs)
closed = gardens.geometry.union_all()

jurong = hexes["park"] == "jurong"
share = hexes.geometry.intersection(closed).area / hexes.geometry.area
hexes["closed_share"] = share.where(jurong, 0.0)
for name in gardens["name"]:
    poly = gardens.loc[gardens["name"] == name].geometry.union_all()
    hexes[f"share_{name.split()[0].lower()}"] = (hexes.geometry.intersection(poly).area / hexes.geometry.area).where(jurong, 0.0)
excluded = hexes["closed_share"] >= MIN_SHARE

cols = ["grid_id", "park", "closed_share", "share_chinese", "share_japanese", "F_h", "D_h"]
hexes.loc[excluded, cols].sort_values("grid_id").round(3).to_csv(HERE / "excluded_hexes.csv", index=False)
hexes.loc[~excluded].drop(columns=["closed_share", "share_chinese", "share_japanese"]).to_file(
    HERE / "parks_allthree_hex_agg_attributes_visits_excl_closed.geojson", driver="GeoJSON"
)

n_j = int(jurong.sum())
print(f"Jurong hexagons: {n_j}; excluded (>= {MIN_SHARE:.0%} inside closed gardens): {int(excluded.sum())}; "
      f"any overlap: {int((hexes['closed_share'] > 0).sum())}; remaining Jurong: {n_j - int(excluded.sum())}")
print(f"Total hexagons: {len(hexes)} -> {int((~excluded).sum())}")
assert excluded.sum() == 20, "expected 20 excluded hexagons (as in the 2026-11-10 check); polygons or hex file changed?"
