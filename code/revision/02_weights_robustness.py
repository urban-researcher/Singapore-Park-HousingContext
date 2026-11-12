"""Step 02: separate the effect of excluding the closed gardens from the effect of the weights switch.

After exclusion the Jurong Queen graph splits into 5 components (one island, grid 1197). Step 01 keeps
Queen and drops the island (run D); the original notebooks would instead fall back to KNN(k=8) (run C).
This script fits the Jurong SLM and Moran's I under:
  A  original 107 hexagons, Queen   (= paper)
  B  original 107 hexagons, KNN k=8 (weights effect only)
  C  excluded 87 hexagons,  KNN k=8 (notebooks' fallback rule)
  D  excluded 86 hexagons,  Queen   (= step 01; disconnected components kept, island 1197 dropped)
Writes outputs/table5_weights_robustness.csv.

Run with the geospatial env:  ~/.virtualenvs/geospatial/bin/python 02_weights_robustness.py
"""
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from esda.moran import Moran
from libpysal.weights import KNN, Queen
from spreg import ML_Lag

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
X_COLS = ["ps", "pl", "pb", "pm", "peg", "peo", "pep", "peps", "per", "pepw", "set"]


def jurong(path):
    g = gpd.read_file(path)
    g = g[g["park"] == "jurong"].copy()
    for c in X_COLS + ["F_h", "D_h"]:
        g[c] = pd.to_numeric(g[c], errors="coerce")
    g["log_F_h1"] = np.log1p(g["F_h"].fillna(0))
    g["log_D_h1"] = np.log1p(g["D_h"].fillna(0))
    return g.dropna(subset=X_COLS).reset_index(drop=True)


def without_islands(g):
    q = Queen.from_dataframe(g, use_index=True)
    return g.drop(index=q.islands).reset_index(drop=True)


orig = jurong(ROOT / "gis_files/hexagons/agg_attributes/parks_allthree_hex_agg_attributes_visits.geojson")
excl = jurong(HERE / "parks_allthree_hex_agg_attributes_visits_excl_closed.geojson")
excl_q = without_islands(excl)
runs = {
    "A original, Queen (paper)": (orig, Queen.from_dataframe(orig, use_index=True)),
    "B original, KNN k=8": (orig, KNN.from_dataframe(orig, k=8)),
    "C excluded, KNN k=8 (notebook fallback)": (excl, KNN.from_dataframe(excl, k=8)),
    "D excluded, Queen (= step 01)": (excl_q, Queen.from_dataframe(excl_q, use_index=True)),
}

rows = []
for run, (data, w) in runs.items():
    w.transform = "R"
    X = data[X_COLS].to_numpy(float)
    X = (X - X.mean(axis=0)) / X.std(axis=0, ddof=1)  # as published Table 5
    for y, outcome in {"log_F_h1": "Frequency", "log_D_h1": "Duration"}.items():
        m = ML_Lag(y=data[[y]].to_numpy(float), x=X, w=w, name_x=X_COLS, method="full")
        np.random.seed(20260419)
        mi = Moran(data[y].to_numpy(float), w, permutations=999)
        base = {"run": run, "outcome": outcome, "n": len(data), "components": w.n_components,
                "moran_I": mi.I, "moran_EI": mi.EI, "moran_z_norm": mi.z_norm, "moran_p_norm": mi.p_norm,
                "moran_p_sim": mi.p_sim, "aic": m.aic, "pseudo_r2": m.pr2}
        for i, term in enumerate(["CONSTANT"] + X_COLS + ["rho"]):
            rows.append({**base, "term": term, "estimate": float(m.betas[i, 0]), "se": float(m.std_err[i]),
                         "p": float(m.z_stat[i][1])})

out = pd.DataFrame(rows)
out.to_csv(HERE / "outputs/table5_weights_robustness.csv", index=False)
a = out[(out.run.str.startswith("A")) & (out.term == "pep") & (out.outcome == "Frequency")]["estimate"].item()
assert round(a, 3) == 0.290, "run A should reproduce the published Table 5"
stars = lambda p: "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "†" if p < 0.10 else ""
out["cell"] = out.apply(lambda r: f"{r.estimate:.3f}{stars(r.p)}", axis=1)
print(out.pivot_table(index=["outcome", "term"], columns="run", values="cell", aggfunc="first").to_string())

# paper-ready Table 5 + Appendix G rows for run D (Queen, as in the Methods text)
d = out[out.run.str.startswith("D")].copy()
d["paper"] = d.apply(lambda r: f"{r.estimate:.3f} {stars(r.p)} ({r.se:.3f})".replace("  ", " "), axis=1)
print("\nRun D, Table 5 format:\n", d.pivot(index="term", columns="outcome", values="paper").to_string())
print("\nRun D fit / Moran:\n", d.drop_duplicates("outcome")[["outcome", "n", "aic", "pseudo_r2", "moran_I", "moran_EI",
      "moran_z_norm", "moran_p_norm", "moran_p_sim"]].round(4).to_string(index=False))
