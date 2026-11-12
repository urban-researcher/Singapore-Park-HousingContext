"""Step 04: regenerate the manuscript figures that contain Jurong hexagons, without the closed gardens.

Figure 4, Appendix D(a) and Appendix F use ALL 365 Jurong cells of the hexagon grid; the models use the
107 cells covered by the street-level imagery (same grid_ids). 30 of the 365 cells are excluded here, a
superset of step 00's 20.
- Figure 4 (panels a-d) and the Appendix F LISA figure: runs the code of Figure4_Park_Use_LQ_Maps.ipynb
  unchanged, with the inputs swapped for step 00's corrected-F_h copies (corrected_fh/; Jurong also filtered)
  and the output folder redirected to outputs/figures (the original figures/ folder is not touched).
- Appendix D(b) box plots: same plt.boxplot call as analysis/integrated_model/main.ipynb, on step 00's data.
- jurong_duration_analysis_excl_closed.geojson: corrected, filtered Jurong cells for Appendix D(a) (step 06).
The "original" statistics use the stored files and must reproduce the published Appendix F.

Writes outputs/figures/*, outputs/fig4_appendixF_stats.csv (appendixF_figure rows = the I and p printed in
fig_lisa_frequency_duration_integrated.svg), excluded_hexes_all_cells.csv.
Run with the geospatial env:  ~/.virtualenvs/geospatial/bin/python 04_figures.py
"""
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIG = HERE / "outputs/figures"
FIG.mkdir(parents=True, exist_ok=True)
NB = ROOT / "Figure4_Park_Use_LQ_Maps.ipynb"
STORED = {p: f"gps_analysis/general_model/duration_analysis/{p}_duration_analysis_byhousingtypes.geojson"
          for p in ["amk", "jurong", "punggol"]}  # as in the notebook's FILES
FIXED = {p: HERE / f"corrected_fh/{p}_duration_analysis_byhousingtypes.geojson" for p in STORED}  # step 00
FINE_IN = FIXED["jurong"]
FINE_OUT = HERE / "jurong_duration_analysis_byhousingtypes_excl_closed.geojson"
GARDENS = ROOT / "gis_files/jurong_lake/chinese_japanese_gardens_osm.geojson"
MIN_SHARE = 0.5  # same rule as step 00

# 1) filter the 365-hexagon grid used by Figure 4 / Appendix F / Appendix D(a)
fine = gpd.read_file(FINE_IN)
closed = gpd.read_file(GARDENS).to_crs(fine.crs).geometry.union_all()
share = fine.geometry.intersection(closed).area / fine.geometry.area
fine.loc[share >= MIN_SHARE].drop(columns="geometry").assign(closed_share=share.round(3)).to_csv(
    HERE / "excluded_hexes_all_cells.csv", index=False)
fine.loc[share < MIN_SHARE].to_file(FINE_OUT, driver="GeoJSON")
excluded_ids = set(fine.loc[share >= MIN_SHARE, "grid_id"])
print(f"Full park grid: {len(fine)} Jurong hexagons, {len(excluded_ids)} excluded")
model_ids = set(pd.read_csv(HERE / "excluded_hexes.csv")["grid_id"])
assert model_ids <= excluded_ids, "model-grid exclusions should be a subset of the full-grid exclusions"
# filtered copy of the Appendix D(a) layer (same grid, all 365 cells), corrected F_h
visits = gpd.read_file(HERE / "corrected_fh/jurong_duration_analysis.geojson")
visits[~visits["grid_id"].isin(excluded_ids)].to_file(HERE / "jurong_duration_analysis_excl_closed.geojson", driver="GeoJSON")

# 2) run the Figure 4 notebook code with the filtered Jurong file and a redirected output folder
code = "\n\n".join("".join(c["source"]) for c in json.loads(NB.read_text())["cells"] if c["cell_type"] == "code")
assert not any(line.lstrip().startswith(("%", "!")) for line in code.splitlines()), "notebook magics need handling"
swaps = [(f'"{STORED[p]}"', repr(str(FINE_OUT if p == "jurong" else FIXED[p]))) for p in STORED]
for old, new in swaps + [('OUTDIR = Path("figures")', f"OUTDIR = Path({str(FIG)!r})")]:
    assert code.count(old) == 1, f"notebook changed; cannot patch {old!r}"
    code = code.replace(old, new)
os.chdir(ROOT)  # notebook paths are relative to the project root
ns = {"__name__": "__fig4__"}
exec(compile(code, str(NB), "exec"), ns)
plt.close("all")

# 3) Figure 4 (a-c) numbers and Appendix F (fine-grid) Moran's I, original vs excluded
orig_parks = ns["load_parks"](STORED)
orig_parks = {k: ns["add_location_quotients"](v) for k, v in orig_parks.items()}
rows = []
for variant, parks in [("original", orig_parks), ("excl_closed", ns["parks"])]:
    s = ns["summary_table"](parks, "all").assign(variant=variant, stat="fig4_summary")
    m = ns["global_moran_table"](parks).assign(variant=variant, stat="appendixF_moran")
    # same call and seed as plot_lisa_integrated, so these are the values printed in the figure
    fig_m = pd.DataFrame([dict(park=pk, metric=mt, n=len(parks[pk]), I=mi.I, p_sim=mi.p_sim)
                          for pk in parks for mt in ["freq", "dur"]
                          for _, mi, _ in [ns["_lisa_clusters_and_moran"](parks[pk], mt)]])
    rows += [s, m, fig_m.assign(variant=variant, stat="appendixF_figure")]
stats = pd.concat(rows, ignore_index=True)
stats.to_csv(HERE / "outputs/fig4_appendixF_stats.csv", index=False)
orig_I = stats.query("variant == 'original' and park == 'jurong' and metric == 'freq' and stat == 'appendixF_figure'")["I"].item()
assert round(orig_I, 3) == 0.330, "original fine-grid Moran's I should match Appendix F (0.330)"
svg = (FIG / "fig_lisa_frequency_duration_integrated.svg").read_text(encoding="utf-8")
for r in stats.query("variant == 'excl_closed' and stat == 'appendixF_figure'").itertuples():
    assert f"I={r.I:.3f}" in svg, f"{r.park} {r.metric}: I={r.I:.3f} not printed in the integrated LISA figure"

# 4) Appendix D(b) box plots on the model grid (step 00 output), as in main.ipynb
gdf = gpd.read_file(HERE / "parks_allthree_hex_agg_attributes_visits_excl_closed.geojson")
parks = sorted(gdf["park"].dropna().unique())
for col in ["F_h", "D_h"]:
    vals = pd.to_numeric(gdf[col], errors="coerce").fillna(0)
    plt.figure()
    plt.boxplot([vals[gdf["park"] == p].values for p in parks], labels=parks, showfliers=False)
    plt.xlabel("park")
    plt.ylabel(col)
    plt.tight_layout()
    for ext in ["png", "svg"]:
        plt.savefig(FIG / f"appendixD_boxplot_{col}.{ext}", dpi=300)
    plt.close()

pd.set_option("display.width", 200)
print("\nFigure 4 (a-c) summary, original vs excluded:")
print(stats[stats.stat == "fig4_summary"][["variant", "park", "n_hex", "share_visited", "mean_F", "median_F", "mean_D"]]
      .assign(mean_D_hours=lambda d: (d.mean_D / 3600).round(1)).to_string(index=False))
print("\nAppendix F (fine-grid) Moran's I, original vs excluded:")
print(stats[stats.stat == "appendixF_moran"][["variant", "park", "metric", "n", "I", "z", "p_sim"]].to_string(index=False))
print(f"\nFigures written to {FIG}")
