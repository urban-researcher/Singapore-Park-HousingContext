"""Step 09: robustness of Tables 4-5 to near-home stays.

Some activity clusters may be residents' stays at or next to home, recorded inside the park because the park
borders housing or because of GPS error (e.g. Punggol hexagon 22927: 72% of its clusters come from devices whose
inferred home is within 100 m). This step drops every cluster whose device's inferred home lies within 100 m of
the hexagon, recomputes F_h (count) and D_h for the modelled hexagons, and re-estimates Table 4 (pooled OLS, HC3)
and Table 5 (Jurong spatial lag, Queen, island dropped) exactly as step 01. Devices without an inferred home are
kept. Same data as the revised analysis (step 00 output).

Writes outputs/robustness_near_home.csv (coefficients), outputs/robustness_near_home_fit.csv (n, fit, clusters
removed per park). Run with the geospatial env:  ~/.virtualenvs/geospatial/bin/python 09_near_home_robustness.py
"""
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from libpysal.weights import Queen
from spreg import ML_Lag

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "outputs"
X_COLS = ["ps", "pl", "pb", "pm", "peg", "peo", "pep", "peps", "per", "pepw", "set"]
OUTCOMES = {"log_F_h1": "Frequency", "log_D_h1": "Duration"}
NEAR_HOME_M = 100


def queen_without_islands(sub):  # same rule as step 01
    sub = sub.reset_index(drop=True)
    w = Queen.from_dataframe(sub, use_index=True)
    if w.islands:
        sub = sub.drop(index=w.islands).reset_index(drop=True)
        w = Queen.from_dataframe(sub, use_index=True)
    w.transform = "R"
    return sub, w


def counts(park, model_ids):
    """Per modelled hexagon: F_h and D_h from all clusters, and without clusters of devices living within 100 m."""
    h = gpd.read_file(ROOT / f"gis_files/hulls/{park}/breaks_hulls.geojson").to_crs(3414)
    h["device"] = h["layer"].str.replace("clusters_convex_hulls_", "")
    h["geometry"] = h.geometry.centroid
    grid = gpd.read_file(ROOT / f"gis_files/hexagons/segmented/{park}_hex_agg.geojson")[["grid_id", "geometry"]].to_crs(3414)
    grid = grid[grid["grid_id"].isin(model_ids)]
    j = gpd.sjoin(grid, h[["device", "cluster", "duration", "geometry"]], how="inner", predicate="intersects")
    res = gpd.read_file(ROOT / f"gps_analysis/activities_identification_example/calibrated_residence_{park}_2022_updated.geojson")
    home = res.to_crs(3414).assign(id=res["id"].astype(str)).set_index("id").geometry
    hex_geom = grid.set_index("grid_id").geometry
    j["near_home"] = [d in home.index and home[d].distance(hex_geom[g]) < NEAR_HOME_M for d, g in zip(j["device"], j["grid_id"])]
    out = pd.DataFrame({"F_all": j.groupby("grid_id").size(), "D_all": j.groupby("grid_id")["duration"].sum(),
                        "F_h": j[~j.near_home].groupby("grid_id").size(),
                        "D_h": j[~j.near_home].groupby("grid_id")["duration"].sum()}).reindex(model_ids).fillna(0)
    return out.rename_axis("grid_id").reset_index().assign(park=park), j["near_home"].mean()


d = gpd.read_file(HERE / "parks_allthree_hex_agg_attributes_visits_excl_closed.geojson")
d["park"] = d["park"].astype(str).str.lower()
for col in X_COLS + ["F_h", "D_h"]:
    d[col] = pd.to_numeric(d[col], errors="coerce")
d[["F_h", "D_h"]] = d[["F_h", "D_h"]].fillna(0)

parts, removed = [], {}
for park in ["amk", "jurong", "punggol"]:
    c, share = counts(park, d.loc[d["park"] == park, "grid_id"].tolist())
    parts.append(c)
    removed[park] = share
c = pd.concat(parts)
base = d.merge(c, on=["park", "grid_id"], validate="1:1", suffixes=("", "_nh"))
# self-check: the same join without the exclusion reproduces the revised F_h and D_h (step 00)
assert (base["F_all"] == base["F_h"]).all() and np.allclose(base["D_all"], base["D_h"]), "join differs from step 00"

rows, fits = [], []
for variant, fcol, dcol in [("revised", "F_h", "D_h"), ("near_home_excluded", "F_h_nh", "D_h_nh")]:
    data = base.assign(log_F_h1=np.log1p(base[fcol]), log_D_h1=np.log1p(base[dcol]))
    for y, label in OUTCOMES.items():
        m = smf.ols(f"{y} ~ {' + '.join(X_COLS)} + C(park)", data=data).fit(cov_type="HC3")
        rows += [{"variant": variant, "table": "Table 4", "outcome": label, "term": t, "estimate": m.params[t],
                  "se": m.bse[t], "p": m.pvalues[t]} for t in m.params.index]
        fits.append({"variant": variant, "table": "Table 4", "outcome": label, "n": int(m.nobs), "r2": m.rsquared})
        sub, w = queen_without_islands(data[data["park"] == "jurong"])
        X = sub[X_COLS].to_numpy(float)
        X = (X - X.mean(axis=0)) / X.std(axis=0, ddof=1)  # ddof=1 as Table 5
        s = ML_Lag(y=sub[[y]].to_numpy(float), x=X, w=w, name_y=y, name_x=X_COLS, method="full")
        rows += [{"variant": variant, "table": "Table 5", "outcome": label, "term": "rho" if t.startswith("W_") else t,
                  "estimate": float(s.betas[i, 0]), "se": float(s.std_err[i]), "p": float(s.z_stat[i][1])}
                 for i, t in enumerate(s.name_x)]
        fits.append({"variant": variant, "table": "Table 5", "outcome": label, "n": int(s.n), "pseudo_r2": s.pr2})
rows, fits = pd.DataFrame(rows), pd.DataFrame(fits)

# self-check: the "revised" rows must reproduce step 01
ref = pd.read_csv(OUT / "table4_pooled_ols.csv").query("variant == 'excl_closed'").set_index(["outcome", "term"])["estimate"]
mine = rows.query("variant == 'revised' and table == 'Table 4'").set_index(["outcome", "term"])["estimate"]
assert np.allclose(mine.loc[ref.index], ref), "revised Table 4 differs from step 01"
ref = pd.read_csv(OUT / "table5_jurong_slm.csv").query("variant == 'excl_closed'").set_index(["outcome", "term"])["estimate"]
mine = rows.query("variant == 'revised' and table == 'Table 5'").set_index(["outcome", "term"])["estimate"]
assert np.allclose(mine.loc[ref.index], ref), "revised Table 5 differs from step 01"

g = base.groupby("park")
summary = pd.DataFrame({"share_clusters_removed": pd.Series(removed),
                        "mean_F_h_revised": g["F_h"].mean(), "mean_F_h_near_home_excluded": g["F_h_nh"].mean(),
                        "median_F_h_near_home_excluded": g["F_h_nh"].median(),
                        "max_F_h_near_home_excluded": g["F_h_nh"].max()})
rows.to_csv(OUT / "robustness_near_home.csv", index=False)
pd.concat([fits, summary.reset_index().rename(columns={"index": "park"}).assign(table="clusters")]).to_csv(
    OUT / "robustness_near_home_fit.csv", index=False)

stars = lambda p: "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "†" if p < 0.10 else ""
rows["cell"] = [f"{e:.3f}{stars(p)}" for e, p in zip(rows.estimate, rows.p)]
pd.set_option("display.width", 220)
print("Self-check passed: revised rows reproduce step 01.\n")
print(summary.round(3).to_string(), "\n")
print(rows.pivot_table(index=["table", "term"], columns=["outcome", "variant"], values="cell", aggfunc="first").to_string())
print(fits.round(3).to_string(index=False))
