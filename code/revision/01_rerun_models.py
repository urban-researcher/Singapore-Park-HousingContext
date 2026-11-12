"""Step 01: re-run the paper's hexagon-level statistics with and without the closed-garden hexagons.

Replicates, unchanged in method:
  Table 3 / Appendix E  visitation summary      (analysis/integrated_model/main.ipynb)
  Table 4               pooled OLS, HC3         (analysis/integrated_model/pooled_ols_estimates.ipynb)
  Moran's I (model grid)                        (analysis/integrated_model/spatialautocorrelation_test.ipynb)
  Table 5               Jurong spatial lag (ML) (analysis/integrated_model/jurong_spatial_lag_models.ipynb)

Variants: "original" (205 hexagons, must reproduce the paper) and "excl_closed" = the revised analysis
(output of step 00: closed-garden hexagons excluded, park services recounted from poi_all_parks, F_h recounted).
Spatial weights: Queen contiguity, row-standardised, as stated in the Methods. Hexagons with no Queen
neighbour (islands) are dropped from the spatial statistics only; the original data have none, while the
excluded Jurong set has one (grid 1197). Disconnected components are kept. (The notebooks would instead
switch to KNN k=8; step 02 shows that alternative.)

Also checks the printed Tables 4 and 5 of the current manuscript against the revised run.
Writes CSVs and paper_changes.md to ./outputs. Original notebooks, outputs and the manuscript are not touched.

Run with the geospatial env:  ~/.virtualenvs/geospatial/bin/python 01_rerun_models.py
"""
import html
import re
import warnings
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from esda.moran import Moran
from libpysal.weights import Queen
from spreg import ML_Lag

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)
MANUSCRIPT = ROOT / "writeup/manuscript.docx"  # current manuscript (file name generalised in the public copy)
VARIANTS = {
    "original": ROOT / "gis_files/hexagons/agg_attributes/parks_allthree_hex_agg_attributes_visits.geojson",
    "excl_closed": HERE / "parks_allthree_hex_agg_attributes_visits_excl_closed.geojson",
}
X_COLS = ["ps", "pl", "pb", "pm", "peg", "peo", "pep", "peps", "per", "pepw", "set"]
OUTCOMES = {"log_F_h1": "Frequency", "log_D_h1": "Duration"}
PARKS = ["amk", "jurong", "punggol"]
LABELS = {  # term -> row label used in the manuscript tables
    "C(park)[T.jurong]": "Jurong (ref. = AMK)", "C(park)[T.punggol]": "Punggol (ref. = AMK)",
    "ps": "Perceptual safety", "pl": "Perceptual liveliness", "pb": "Perceptual beauty", "pm": "Perceptual monotony",
    "peg": "Greenness", "peo": "Openness", "pep": "Park furniture", "peps": "Park services within 500 m",
    "per": "Internal road connectivity", "pepw": "Proximity to water",
    "set": "Inverted walking distance to nearest transportation hub",
    "Intercept": "Constant", "CONSTANT": "Constant", "rho": "Spatial lag",
}
T4_TERMS = ["C(park)[T.jurong]", "C(park)[T.punggol]"] + X_COLS + ["Intercept"]
T5_TERMS = ["pep", "peps", "ps", "pl", "pb", "pm", "peg", "peo", "per", "pepw", "set", "rho", "CONSTANT"]


def load(path):
    gdf = gpd.read_file(path)
    for col in X_COLS + ["F_h", "D_h"]:
        gdf[col] = pd.to_numeric(gdf[col], errors="coerce")
    gdf[["F_h", "D_h"]] = gdf[["F_h", "D_h"]].fillna(0)
    gdf["log_F_h1"] = np.log1p(gdf["F_h"])
    gdf["log_D_h1"] = np.log1p(gdf["D_h"])
    gdf["park"] = gdf["park"].astype(str).str.lower()
    return gdf


def queen_without_islands(sub):
    sub = sub.reset_index(drop=True)
    w = Queen.from_dataframe(sub, use_index=True)
    if w.islands:
        sub = sub.drop(index=w.islands).reset_index(drop=True)
        w = Queen.from_dataframe(sub, use_index=True)
    w.transform = "R"
    return sub, w


def stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "†" if p < 0.10 else ""


def table3(gdf, variant):
    g = gdf.groupby("park")
    return pd.DataFrame({
        "variant": variant, "n_hex": g.size(), "mean_F_h": g["F_h"].mean(), "median_F_h": g["F_h"].median(),
        "share_visited": g["F_h"].apply(lambda s: (s > 0).mean()), "mean_D_h": g["D_h"].mean(),
    }).reset_index()


def pooled_ols(gdf, variant):
    data = gdf.dropna(subset=X_COLS + list(OUTCOMES)).copy()
    rows, fits = [], []
    for y, label in OUTCOMES.items():
        m = smf.ols(f"{y} ~ {' + '.join(X_COLS)} + C(park)", data=data).fit(cov_type="HC3")
        for term in m.params.index:
            rows.append({"variant": variant, "outcome": label, "term": term, "estimate": m.params[term],
                         "se": m.bse[term], "p": m.pvalues[term]})
        fits.append({"variant": variant, "outcome": label, "n": int(m.nobs), "r2": m.rsquared, "adj_r2": m.rsquared_adj})
        data[f"resid_{label}"] = m.resid
    return pd.DataFrame(rows), pd.DataFrame(fits), data


def residual_moran(data, variant, seed=20260419):
    """Moran's I of the pooled OLS residuals: all parks together (block-diagonal Queen) and per park."""
    data = data.sort_values(["park", "grid_id"]).reset_index(drop=True)
    rows = []
    for scope in ["all parks"] + PARKS:
        sub, w = queen_without_islands(data if scope == "all parks" else data[data["park"] == scope])
        for label in OUTCOMES.values():
            np.random.seed(seed)
            mi = Moran(sub[f"resid_{label}"].to_numpy(float), w, permutations=999)
            rows.append({"variant": variant, "model": "pooled OLS", "scope": scope, "outcome": label, "n": w.n,
                         "I": mi.I, "z_norm": mi.z_norm, "p_sim": mi.p_sim})
    return pd.DataFrame(rows)


def moran(gdf, variant, seed=20260419):
    gdf = gdf.sort_values(["park", "grid_id"]).reset_index(drop=True)  # same ordering as the notebook
    rows = []
    for park in PARKS:
        sub, w = queen_without_islands(gdf[gdf["park"] == park])
        for y, label in OUTCOMES.items():
            np.random.seed(seed)
            mi = Moran(sub[y].to_numpy(float), w, permutations=999)
            rows.append({"variant": variant, "park": park, "outcome": label, "n_hex": w.n,
                         "components": w.n_components, "I": mi.I, "EI": mi.EI, "z_norm": mi.z_norm,
                         "p_norm": mi.p_norm, "p_sim": mi.p_sim})
    return pd.DataFrame(rows)


def jurong_slm(gdf, variant):
    data, w = queen_without_islands(gdf[gdf["park"] == "jurong"].dropna(subset=X_COLS + list(OUTCOMES)))
    X = data[X_COLS].to_numpy(float)
    # ddof=1 reproduces the published Table 5; the notebook's saved CSV uses ddof=0 (all values / 1.0047, same p)
    X = (X - X.mean(axis=0)) / X.std(axis=0, ddof=1)
    rows, fits = [], []
    for y, label in OUTCOMES.items():
        m = ML_Lag(y=data[[y]].to_numpy(float), x=X, w=w, name_y=y, name_x=X_COLS, method="full")
        for i, term in enumerate(m.name_x):
            term = "rho" if term.startswith("W_") else term
            rows.append({"variant": variant, "outcome": label, "term": term, "estimate": float(m.betas[i, 0]),
                         "se": float(m.std_err[i]), "p": float(m.z_stat[i][1])})
        np.random.seed(20260419)
        mi = Moran(m.u.flatten(), w, permutations=999)  # residuals left after the spatial lag
        fits.append({"variant": variant, "outcome": label, "n": int(m.n), "components": w.n_components,
                     "aic": m.aic, "pseudo_r2": m.pr2, "rho": float(m.rho),
                     "resid_moran_I": mi.I, "resid_moran_z": mi.z_norm, "resid_moran_p_sim": mi.p_sim})
    return pd.DataFrame(rows), pd.DataFrame(fits)


def printed_tables(docx_path):
    """Return {(table, row label, outcome): cell text} for Tables 4 and 5 of the manuscript."""
    xml = zipfile.ZipFile(docx_path).read("word/document.xml").decode("utf8")
    cell_text = lambda c: html.unescape(re.sub(r"<[^>]+>", "", c.replace("</w:p>", " "))).strip()
    found = []
    for tbl in re.findall(r"<w:tbl>.*?</w:tbl>", xml, flags=re.S):
        rows = [[cell_text(c) for c in re.findall(r"<w:tc>.*?</w:tc>", r, flags=re.S)]
                for r in re.findall(r"<w:tr[ >].*?</w:tr>", tbl, flags=re.S)]
        if rows and rows[0][:2] == ["Variable", "(1) Frequency"]:
            found.append(rows[1:])
    assert len(found) == 2, f"expected Tables 4 and 5 in {docx_path.name}, found {len(found)}"
    out = {}
    for table, rows in zip(["Table 4", "Table 5"], found):
        for r in rows:
            out[(table, r[0], "Frequency")], out[(table, r[0], "Duration")] = r[1], r[2]
    return out


CELL = re.compile(r"^(?P<lead>\**)\s*(?P<est>[−-]?\d+\.\d+)\s*(?P<stars>[*†]*)\s*\((?P<se>\d+\.\d+)\)$")


OLD_LABELS = {"peps": "Proximity to park services"}  # label still printed before the R3-(5) change


def check_printed(printed, table, coefs):
    """List mismatches between the printed cell and the revised estimate."""
    issues = []
    for r in coefs[coefs.variant == "excl_closed"].itertuples():
        key = next((k for k in [(table, LABELS[r.term], r.outcome), (table, OLD_LABELS.get(r.term), r.outcome)]
                    if k in printed), None)
        if key is None:
            continue
        m = CELL.match(printed[key].replace(" ", " "))
        if not m:
            issues.append((table, key[1], r.outcome, printed[key], "could not parse"))
            continue
        problems = []
        if m["lead"]:
            problems.append(f"stray '{m['lead']}' before the value")
        if abs(float(m["est"].replace("−", "-")) - r.estimate) > 0.0015 or abs(float(m["se"]) - r.se) > 0.0015:
            problems.append(f"value should be {r.estimate:.3f} ({r.se:.3f})")
        if m["stars"] != stars(r.p):
            problems.append(f"stars should be '{stars(r.p) or 'none'}' (p = {r.p:.4f})")
        if problems:
            issues.append((table, key[1], r.outcome, printed[key], "; ".join(problems)))
    return issues


t3, ols, ols_fit, rmor, mor, slm, slm_fit = [], [], [], [], [], [], []
for variant, path in VARIANTS.items():
    gdf = load(path)
    t3.append(table3(gdf, variant))
    c, f, resid = pooled_ols(gdf, variant); ols.append(c); ols_fit.append(f)
    rmor.append(residual_moran(resid, variant))
    mor.append(moran(gdf, variant))
    c, f = jurong_slm(gdf, variant); slm.append(c); slm_fit.append(f)
t3, ols, ols_fit, rmor, mor, slm, slm_fit = map(pd.concat, [t3, ols, ols_fit, rmor, mor, slm, slm_fit])

for name, df in {"table3_summary": t3, "table4_pooled_ols": ols, "table4_fit": ols_fit, "residual_moran": rmor,
                 "moran_model_grid": mor, "table5_jurong_slm": slm, "table5_fit": slm_fit}.items():
    df.to_csv(OUT / f"{name}.csv", index=False)

# --- self-check: the "original" run must reproduce the published values -------------------------
o = lambda df, **kv: df[(df["variant"] == "original") & np.logical_and.reduce([df[k] == v for k, v in kv.items()])]
assert round(o(t3, park="jurong")["mean_F_h"].item(), 2) == 20.26
assert round(o(ols_fit, outcome="Frequency")["r2"].item(), 3) == 0.205
assert round(o(ols, outcome="Frequency", term="peps")["estimate"].item(), 3) == 0.049
assert round(o(mor, park="jurong", outcome="Frequency")["I"].item(), 4) == 0.3697
assert round(o(slm_fit, outcome="Frequency")["rho"].item(), 3) == 0.337
assert round(o(slm, outcome="Frequency", term="pep")["estimate"].item(), 3) == 0.290
print("Self-check passed: original run reproduces Tables 3-5 and the model-grid Moran's I.\n")

printed = printed_tables(MANUSCRIPT)
issues = check_printed(printed, "Table 4", ols) + check_printed(printed, "Table 5", slm)


# --- side-by-side report -------------------------------------------------------------------------
def fmt_coef(r):
    return f"{r.estimate:.3f} {stars(r.p)} ({r.se:.3f})".replace("  ", " ")


def coef_section(title, coefs, fits, fit_cols, term_order):
    lines = [f"### {title}", "", "| Variable | Outcome | Paper (reproduced) | Revised | Note |",
             "|---|---|---|---|---|"]
    for outcome in OUTCOMES.values():
        for term in term_order:
            a = coefs[(coefs.variant == "original") & (coefs.outcome == outcome) & (coefs.term == term)].iloc[0]
            b = coefs[(coefs.variant == "excl_closed") & (coefs.outcome == outcome) & (coefs.term == term)].iloc[0]
            note = "**significance changed**" if stars(a.p) != stars(b.p) else ""
            if np.sign(a.estimate) != np.sign(b.estimate) and (a.p < 0.1 or b.p < 0.1):
                note += " **sign flipped**"
            lines.append(f"| {LABELS[term]} | {outcome} | {fmt_coef(a)} | {fmt_coef(b)} | {note} |")
        for col in fit_cols:
            a = fits[(fits.variant == "original") & (fits.outcome == outcome)][col].item()
            b = fits[(fits.variant == "excl_closed") & (fits.outcome == outcome)][col].item()
            fa, fb = (f"{a}", f"{b}") if isinstance(a, (int, np.integer)) else (f"{a:.3f}", f"{b:.3f}")
            lines.append(f"| {col} | {outcome} | {fa} | {fb} | |")
    return lines + [""]


md = ["## 6. Tables (generated by `01_rerun_models.py`; edit the script, not this block)", "",
      "20 Jurong hexagons with >= 50% area inside the gardens removed (see `excluded_hexes.csv`). Spatial "
      "statistics use Queen weights; the isolated hexagon 1197 left after exclusion is dropped from them (n = 86). "
      "Revised = closed gardens excluded, park services recounted from `gis_files/poi/poi_all_parks.geojson` (Mar 2026), "
      "and F_h recounted (one per device cluster; section 7.1). Paper (reproduced) = the published analysis. "
      "Stars: † p<0.10, * p<0.05, ** p<0.01, *** p<0.001.", "",
      "### Table 3 and Appendix E (visitation rows, all three parks)", "",
      "| Park | Statistic | Paper (reproduced) | Revised |", "|---|---|---|---|"]
for park in PARKS:
    a, b = (t3[(t3.variant == v) & (t3.park == park)].iloc[0] for v in VARIANTS)
    md += [f"| {park} | Hexagons | {a.n_hex} | {b.n_hex} |",
           f"| {park} | Mean F_h | {a.mean_F_h:.2f} | {b.mean_F_h:.2f} |",
           f"| {park} | Median F_h | {a.median_F_h:g} | {b.median_F_h:g} |",
           f"| {park} | Share visited | {a.share_visited:.3f} | {b.share_visited:.3f} |",
           f"| {park} | Mean D_h | {a.mean_D_h:,.2f} | {b.mean_D_h:,.2f} |"]
md += [""]
md += ["### Moran's I on the modelled hexagons (all parks; justifies the Jurong-only spatial lag model)", "",
       "| Park | Outcome | Variant | n | Components | I | E[I] | z_norm | p_norm | p_sim |", "|---|---|---|---|---|---|---|---|---|---|"]
for r in mor.sort_values(["park", "outcome", "variant"], ascending=[True, False, False]).itertuples():
    md.append(f"| {r.park} | {r.outcome} | {r.variant} | {r.n_hex} | {r.components} | {r.I:.4f} | {r.EI:.5f} | {r.z_norm:.3f} | "
              f"{r.p_norm:.4f} | {r.p_sim:.3f} |")
md += [""]
md += coef_section("Table 4: pooled OLS (all three parks)", ols, ols_fit, ["n", "r2", "adj_r2"], T4_TERMS)
md += coef_section("Table 5: Jurong spatial lag model", slm, slm_fit, ["n", "components", "aic", "pseudo_r2"], T5_TERMS)
md += ["### Residual Moran's I (for the notes to Tables 4 and 5)", "",
       "Queen contiguity (row-standardised, islands dropped), 999 permutations. Parks do not touch, so the "
       "all-parks weights are block-diagonal.", "",
       "| Model | Scope | Outcome | n | Paper version: I (p_sim) | Revised: I (p_sim) |", "|---|---|---|---|---|---|"]
for (scope, outcome), g in rmor.groupby(["scope", "outcome"], sort=False):
    a, b = (g[g.variant == v].iloc[0] for v in VARIANTS)
    md.append(f"| pooled OLS | {scope} | {outcome} | {a.n} → {b.n} | {a.I:.3f} ({a.p_sim:.3f}) | {b.I:.3f} ({b.p_sim:.3f}) |")
for outcome in OUTCOMES.values():
    a, b = (slm_fit[(slm_fit.variant == v) & (slm_fit.outcome == outcome)].iloc[0] for v in VARIANTS)
    md.append(f"| Jurong SLM | jurong | {outcome} | {a.n} → {b.n} | {a.resid_moran_I:.3f} ({a.resid_moran_p_sim:.3f}) | "
              f"{b.resid_moran_I:.3f} ({b.resid_moran_p_sim:.3f}) |")
md += [""]
md += ["### Printed Tables 4 and 5 that differ from the revised run", "",
       f"Checked against `{MANUSCRIPT.name}`; rounding differences of 0.001 are ignored. Each row is a cell to update.", "",
       "| Table | Row | Outcome | Printed | Fix |", "|---|---|---|---|---|"]
md += [f"| {t} | {row} | {oc} | `{txt}` | {fix} |" for t, row, oc, txt, fix in issues] or ["| none | | | | |"]
# paper_changes.md = hand-written sections + this generated block between the markers
START, END = "<!-- BEGIN GENERATED: 01_rerun_models.py -->", "<!-- END GENERATED -->"
path = OUT / "paper_changes.md"
block = f"{START}\n" + "\n".join(md) + f"\n{END}"
text = path.read_text(encoding="utf-8") if path.exists() else ""
text = text.split(START)[0] + block + text.split(END, 1)[1] if START in text and END in text else block + "\n"
path.write_text(text, encoding="utf-8")
print("\n".join(md))
