"""Step 08: why perceived safety is negative in the revised Jurong spatial lag model (Table 5).

Correlations among the four perception scores, VIFs of the Table 5 predictors, and the safety coefficient when the
other perception scores are left out. Same data, weights and standardization as step 01 (revised variant).
The numbers are quoted in paper_changes.md section 11 (Results, Table 5 paragraph).

Run with the geospatial env:  ~/.virtualenvs/geospatial/bin/python 08_perception_check.py
"""
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from libpysal.weights import Queen
from spreg import ML_Lag

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
X = ["ps", "pl", "pb", "pm", "peg", "peo", "pep", "peps", "per", "pepw", "set"]
PERCEPTION = ["ps", "pl", "pb", "pm"]

d = gpd.read_file(HERE / "parks_allthree_hex_agg_attributes_visits_excl_closed.geojson")
j = d[d["park"].str.lower() == "jurong"].reset_index(drop=True)
for c in X + ["F_h", "D_h"]:
    j[c] = pd.to_numeric(j[c], errors="coerce")
j[["F_h", "D_h"]] = j[["F_h", "D_h"]].fillna(0)
w = Queen.from_dataframe(j, use_index=True)  # drop islands as in step 01
j = j.drop(index=w.islands).reset_index(drop=True)
w = Queen.from_dataframe(j, use_index=True)
w.transform = "R"
Z = (j[X] - j[X].mean()) / j[X].std()  # ddof=1 as Table 5

print(f"n = {len(j)}\n", j[PERCEPTION].corr().round(2), sep="")
print("VIF:", pd.Series(np.diag(np.linalg.inv(Z.corr().to_numpy())), index=X).round(1).to_dict())

TABLE5_SAFETY = {"F_h": -0.517, "D_h": -0.966}  # revised Table 5 (corrected F_h)
for y in ["F_h", "D_h"]:
    yy = np.log1p(j[[y]].to_numpy(float))
    for label, xs in [("full model", X), *[(f"without {p}", [c for c in X if c != p]) for p in PERCEPTION[1:]],
                      ("without the other three scores", [c for c in X if c not in PERCEPTION[1:]])]:
        s = ML_Lag(y=yy, x=Z[xs].to_numpy(float), w=w, name_x=xs, method="full")
        i = s.name_x.index("ps")
        b, p = float(s.betas[i, 0]), float(s.z_stat[i][1])
        if label == "full model":
            assert round(b, 3) == TABLE5_SAFETY[y], f"{y}: does not reproduce Table 5"
        print(f"{y}  {label:32s} safety {b:+.3f}  p = {p:.3f}")
