"""Step 05 (Reviewer R3-(4)): mean dwell time per activity cluster, M_h = D_h / F_h, on the revised model grid.

Also corrects how F_h is counted. The duration notebook (gps_analysis/general_model/duration_analysis/main.ipynb)
sets F_h = nunique('cluster') per hexagon, but ST-DBSCAN numbers clusters separately for each device (1, 2, ...),
so clusters of different devices that share a number are counted once, while D_h sums all of them.
Corrected F_h = number of device clusters (rows of breaks_hulls) whose hull centroid lies in the hexagon, so
M_h = D_h / F_h is the mean duration of those clusters.

Re-estimates Table 4 (pooled OLS, HC3) and Table 5 (Jurong spatial lag, Queen, islands dropped) exactly as step 01,
on the revised data (closed gardens excluded), with outcomes
  (1) log(F_h + 1), corrected count   (2) log(D_h + 1), unchanged   (3) log(M_h), visited hexagons only.
Writes outputs/r3_4_*.csv. Upstream files, step 01 outputs and the manuscript are not touched.

Run with the geospatial env:  ~/.virtualenvs/geospatial/bin/python 05_mean_dwell.py
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
PARKS = ["amk", "jurong", "punggol"]
OUTCOMES = {"log_F_h1": "Frequency", "log_D_h1": "Duration", "log_M_h": "Mean dwell"}


def stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "†" if p < 0.10 else ""


def queen_without_islands(sub):  # same rule as step 01
    sub = sub.reset_index(drop=True)
    w = Queen.from_dataframe(sub, use_index=True)
    if w.islands:
        sub = sub.drop(index=w.islands).reset_index(drop=True)
        w = Queen.from_dataframe(sub, use_index=True)
    w.transform = "R"
    return sub, w


def cluster_counts(park):
    """Per hexagon, as in the duration notebook: stored-method F_h, corrected F_h and D_h (s); plus the clusters' dates."""
    hulls = gpd.read_file(ROOT / f"gis_files/hulls/{park}/breaks_hulls.geojson").to_crs(epsg=3414)
    hulls["geometry"] = hulls.geometry.centroid
    hexes = gpd.read_file(ROOT / f"gis_files/hexagons/segmented/{park}_hex_agg.geojson")[["grid_id", "geometry"]]
    j = gpd.sjoin(hexes, hulls[["cluster", "duration", "start_time", "geometry"]], how="left", predicate="intersects")
    g = j.groupby("grid_id")
    counts = pd.DataFrame({"F_h_old": g["cluster"].nunique(), "F_h_new": g["cluster"].count(),
                           "D_h_check": g["duration"].sum()}).reset_index()
    counts["park"] = park
    return counts, pd.to_datetime(j["start_time"].dropna())


counts, starts = zip(*map(cluster_counts, PARKS))
starts = pd.concat(starts)
window_days = (starts.max().normalize() - starts.min().normalize()).days + 1

d = gpd.read_file(HERE / "parks_allthree_hex_agg_attributes_visits_excl_closed.geojson")
d["park"] = d["park"].astype(str).str.lower()
for col in X_COLS + ["F_h", "D_h"]:
    d[col] = pd.to_numeric(d[col], errors="coerce")
d[["F_h", "D_h"]] = d[["F_h", "D_h"]].fillna(0)
d = d.merge(pd.concat(counts), on=["park", "grid_id"], how="left", validate="1:1")
assert d["F_h_new"].notna().all(), "model hexagon missing from the park grid"
# stored F_h is the notebook's nunique count, or the corrected count once the notebook is fixed
assert ((d["F_h"] == d["F_h_old"]) | (d["F_h"] == d["F_h_new"])).all(), "stored F_h matches neither recount"
assert np.allclose(d["D_h"], d["D_h_check"]), "stored D_h differs from the recount"

d["log_F_h1"] = np.log1p(d["F_h_new"])
d["log_D_h1"] = np.log1p(d["D_h"])
d["M_h"] = (d["D_h"] / d["F_h_new"] / 60).where(d["F_h_new"] > 0)  # minutes per cluster
d["M_h_old"] = (d["D_h"] / d["F_h_old"] / 60).where(d["F_h_old"] > 0)  # what the stored F_h would give
d["log_M_h"] = np.log(d["M_h"])

# --- Appendix H summary ------------------------------------------------------------------------------
g = d.groupby("park")
summary = pd.DataFrame({
    "n_hex": g.size(), "n_visited": g["F_h_new"].apply(lambda s: int((s > 0).sum())),
    "mean_F_h_stored": g["F_h_old"].mean(), "mean_F_h_corrected": g["F_h_new"].mean(),
    "median_F_h_corrected": g["F_h_new"].median(),
    "mean_F_h_corrected_per_day": g["F_h_new"].mean() / window_days,
    "mean_D_h_hours": g["D_h"].mean() / 3600,
    "M_h_median_min": g["M_h"].median(), "M_h_q1_min": g["M_h"].quantile(0.25), "M_h_q3_min": g["M_h"].quantile(0.75),
    "M_h_mean_min": g["M_h"].mean(), "M_h_stored_F_median_min": g["M_h_old"].median(),
}).reset_index()
summary.to_csv(OUT / "r3_4_mean_dwell_summary.csv", index=False)

# --- Tables 4 and 5 re-estimated ---------------------------------------------------------------------
t4, t5, fits = [], [], []
for y, label in OUTCOMES.items():
    data = d.dropna(subset=X_COLS + [y])
    m = smf.ols(f"{y} ~ {' + '.join(X_COLS)} + C(park)", data=data).fit(cov_type="HC3")
    t4 += [{"outcome": label, "term": t, "estimate": m.params[t], "se": m.bse[t], "p": m.pvalues[t]} for t in m.params.index]
    fits.append({"table": "Table 4", "outcome": label, "n": int(m.nobs), "r2": m.rsquared, "adj_r2": m.rsquared_adj})

    sub, w = queen_without_islands(data[data["park"] == "jurong"])
    X = sub[X_COLS].to_numpy(float)
    X = (X - X.mean(axis=0)) / X.std(axis=0, ddof=1)  # ddof=1 as the published Table 5
    s = ML_Lag(y=sub[[y]].to_numpy(float), x=X, w=w, name_y=y, name_x=X_COLS, method="full")
    t5 += [{"outcome": label, "term": "rho" if t.startswith("W_") else t, "estimate": float(s.betas[i, 0]),
            "se": float(s.std_err[i]), "p": float(s.z_stat[i][1])} for i, t in enumerate(s.name_x)]
    fits.append({"table": "Table 5", "outcome": label, "n": int(s.n), "aic": s.aic, "pseudo_r2": s.pr2})
t4, t5, fits = pd.DataFrame(t4), pd.DataFrame(t5), pd.DataFrame(fits)
for name, df in {"r3_4_table4": t4, "r3_4_table5": t5, "r3_4_fit": fits}.items():
    df.to_csv(OUT / f"{name}.csv", index=False)

# self-check: Duration does not depend on F_h, so it must reproduce step 01's revised estimates
for mine, ref in [(t4, "table4_pooled_ols.csv"), (t5, "table5_jurong_slm.csv")]:
    r = pd.read_csv(OUT / ref)
    r = r[(r["variant"] == "excl_closed") & (r["outcome"] == "Duration")].set_index("term")["estimate"]
    a = mine[mine["outcome"] == "Duration"].set_index("term")["estimate"]
    assert np.allclose(a.loc[r.index], r), f"Duration estimates differ from step 01 ({ref})"
print(f"Self-check passed: stored F_h and D_h match the recount; Duration reproduces step 01. Window: "
      f"{starts.min():%d %b %Y} to {starts.max():%d %b %Y} ({window_days} days).\n")

pd.set_option("display.width", 200)
print(summary.round(2).to_string(index=False), "\n")
for name, t in [("Table 4 (pooled OLS)", t4), ("Table 5 (Jurong SLM)", t5)]:
    t = t.assign(cell=[f"{e:.3f}{stars(p)} ({s:.3f})" for e, s, p in zip(t.estimate, t.se, t.p)])
    print(name); print(t.pivot(index="term", columns="outcome", values="cell")[list(OUTCOMES.values())].to_string(), "\n")
print(fits.round(3).to_string(index=False))
