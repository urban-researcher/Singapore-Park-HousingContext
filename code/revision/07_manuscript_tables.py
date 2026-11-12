"""Step 07: the revised tables in the manuscript's layout, ready to copy into Word.

Builds Table 3 (and the visitation rows of Appendix E), Table 4, Table 5 and Appendix H Tables H1-H2 from the
CSVs of steps 01 and 05, with the manuscript's row order, labels (R3-(5) label for park services) and cell format
"0.585 * (0.313)", plus the revised notes (paper_changes.md 9.3 and 10.4).
Writes outputs/manuscript_tables.html: open it in Word (or a browser) and copy each table.

Run with the geospatial env:  ~/.virtualenvs/geospatial/bin/python 07_manuscript_tables.py
"""
import html
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "outputs"
STARS = [(0.001, "***"), (0.01, "**"), (0.05, "*"), (0.10, "†")]
LABEL = {
    "C(park)[T.jurong]": "Jurong (ref. = AMK)", "C(park)[T.punggol]": "Punggol (ref. = AMK)",
    "ps": "Perceptual safety", "pl": "Perceptual liveliness", "pb": "Perceptual beauty", "pm": "Perceptual monotony",
    "peg": "Greenness", "peo": "Openness", "pep": "Park furniture", "peps": "Park services within 500 m",
    "per": "Internal road connectivity", "pepw": "Proximity to water",
    "set": "Inverted walking distance to nearest transportation hub",
    "rho": "Spatial lag", "Intercept": "Constant", "CONSTANT": "Constant",
}
T4_ROWS = ["C(park)[T.jurong]", "C(park)[T.punggol]", "ps", "pl", "pb", "pm", "peg", "peo", "pep", "peps", "per",
           "pepw", "set", "Intercept"]  # printed order of Table 4
T5_ROWS = ["pep", "peps", "ps", "pl", "pb", "pm", "peg", "peo", "per", "pepw", "set", "rho", "CONSTANT"]  # Table 5
PARKS = {"amk": "Bishan-Ang Mo Kio Park", "jurong": "Jurong Lake Gardens", "punggol": "Punggol Waterway Park"}
STAR_LINE = "† p < 0.10, * p < 0.05, ** p < 0.01, *** p < 0.001."


def cell(r):
    star = next((s for cut, s in STARS if r.p < cut), "")
    return f"{r.estimate:.3f}{' ' + star if star else ''} ({r.se:.3f})".replace("-", "−")


def coef_rows(df, order, outcomes):
    d = df.set_index(["outcome", "term"])
    return [[LABEL[t]] + [cell(d.loc[(o, t)]) if (o, t) in d.index else "—" for o in outcomes] for t in order]


def table(caption, header, rows, note=None):
    # labels and cells are our own strings and may carry <sub>; only the notes are escaped
    th = "".join(f"<th>{h}</th>" for h in header)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    note = f'<p class="note">{html.escape(note)}</p>' if note else ""
    return f"<p class='cap'>{caption}</p><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>{note}"


# ---- inputs (revised variant = closed gardens excluded, services recounted, F_h recounted) ----------------
t3 = pd.read_csv(OUT / "table3_summary.csv").query("variant == 'excl_closed'").set_index("park")
t4 = pd.read_csv(OUT / "table4_pooled_ols.csv").query("variant == 'excl_closed'")
t4f = pd.read_csv(OUT / "table4_fit.csv").query("variant == 'excl_closed'").set_index("outcome")
t5 = pd.read_csv(OUT / "table5_jurong_slm.csv").query("variant == 'excl_closed'")
t5f = pd.read_csv(OUT / "table5_fit.csv").query("variant == 'excl_closed'").set_index("outcome")
h1 = pd.read_csv(OUT / "r3_4_mean_dwell_summary.csv").set_index("park")
h4 = pd.read_csv(OUT / "r3_4_table4.csv").query("outcome == 'Mean dwell'").assign(outcome="(a)")
h5 = pd.read_csv(OUT / "r3_4_table5.csv").query("outcome == 'Mean dwell'").assign(outcome="(b)")
hf = pd.read_csv(OUT / "r3_4_fit.csv").query("outcome == 'Mean dwell'").set_index("table")
rm = pd.read_csv(OUT / "residual_moran.csv").query("variant == 'excl_closed'").set_index(["scope", "outcome"])
OUTCOME_TEXT = {"Frequency": "frequency", "Duration": "cumulative dwell time"}


def mi(I, p):
    return f"{I:.3f} (p = {p:.3f})".replace("-", "−")


def resid_note():
    """Residual Moran sentence for the Table 4 note, from step 01 (only Jurong significant is checked, not assumed)."""
    sig = {s for (s, o), r in rm.iterrows() if s != "all parks" and r.p_sim < 0.05}
    assert sig == {"jurong"}, f"parks with significant residual dependence changed: {sig}"
    by = lambda s: "; ".join(mi(rm.loc[(s, o), "I"], rm.loc[(s, o), "p_sim"]).replace(" (", ", ")[:-1] for o in OUTCOME_TEXT)
    return (f"Moran's I of the residuals (Queen contiguity within parks, 999 permutations; one hexagon without "
            f"contiguous neighbours omitted, n = {rm.loc[('all parks', 'Frequency'), 'n']}): "
            + " and ".join(f"{mi(rm.loc[('all parks', o), 'I'], rm.loc[('all parks', o), 'p_sim'])} for {txt}"
                           for o, txt in OUTCOME_TEXT.items())
            + f"; by park, significant only in Jurong Lake Gardens ({by('jurong')}), not in Bishan–Ang Mo Kio Park "
              f"({by('amk')}) or Punggol Waterway Park ({by('punggol')}).")

# self-check against the revised values quoted in paper_changes.md (sections 6 and 9)
assert t4f.loc["Frequency", "n"] == 185 and t5f.loc["Frequency", "n"] == 86
assert round(t4.query("outcome == 'Frequency' and term == 'peps'")["estimate"].item(), 3) == 0.032  # corrected F_h
assert round(t5.query("outcome == 'Frequency' and term == 'rho'")["estimate"].item(), 3) == 0.334
assert int(h1.loc["jurong", "n_visited"]) == 80 and (hf["n"].tolist() == [148, 79])  # counts quoted in the H2 note

parts = []
parts.append(table("<b>Table 3.</b> Summary of visitation statistics", [""] + list(PARKS.values()), [
    ["Mean F<sub>h</sub>"] + [f"{t3.loc[p, 'mean_F_h']:.2f}" for p in PARKS],
    ["Median F<sub>h</sub>"] + [f"{t3.loc[p, 'median_F_h']:g}" for p in PARKS],
    ["Share visited*"] + [f"{t3.loc[p, 'share_visited']:.2f}" for p in PARKS],
    ["Mean D<sub>h</sub>"] + [f"{t3.loc[p, 'mean_D_h']:,.0f}" for p in PARKS],
], "Note: *: The proportion of hexagons that receive at least one visit. Visitation frequency is the number of "
   "activity clusters per hexagon; Mean D_h in seconds. Jurong Lake Gardens excludes the 20 hexagons in the Chinese "
   "and Japanese Gardens, closed during the observation period (26 August to 30 September 2022)."))
parts.append(table("<b>Table 4.</b> Pooled OLS estimates of hexagon-level associations between intra-park "
                   "characteristics and park use (Robust standard errors (HC3) in parentheses)",
                   ["Variable", "(1) Frequency", "(2) Cumulative dwell time"],
                   coef_rows(t4, T4_ROWS, ["Frequency", "Duration"]) + [
    ["Observations"] + [int(t4f.loc[o, "n"]) for o in ["Frequency", "Duration"]],
    ["R²"] + [f"{t4f.loc[o, 'r2']:.3f}" for o in ["Frequency", "Duration"]],
    ["Adjusted R²"] + [f"{t4f.loc[o, 'adj_r2']:.3f}" for o in ["Frequency", "Duration"]],
], f"Note: {STAR_LINE} Dependent variables are log(F_h + 1) in (1) and log(D_h + 1) in (2); n = "
   f"{int(t4f.loc['Frequency', 'n'])} hexagons. Predictors are in their original units; park fixed effects with "
   "Bishan–Ang Mo Kio Park as the reference. Robust (HC3) standard errors in parentheses. " + resid_note()))
parts.append(table("<b>Table 5.</b> Spatial lag models (SLM) for Jurong Lake Gardens",
                   ["Variable", "(1) Frequency", "(2) Cumulative dwell time"],
                   coef_rows(t5, T5_ROWS, ["Frequency", "Duration"]) + [
    ["Observations"] + [int(t5f.loc[o, "n"]) for o in ["Frequency", "Duration"]],
    ["AIC"] + [f"{t5f.loc[o, 'aic']:.1f}" for o in ["Frequency", "Duration"]],
    ["Pseudo R²"] + [f"{t5f.loc[o, 'pseudo_r2']:.3f}" for o in ["Frequency", "Duration"]],
], f"Note: {STAR_LINE} Dependent variables are log(F_h + 1) in (1) and log(D_h + 1) in (2). Predictors are "
   "standardized (z-scores) within Jurong Lake Gardens; coefficients are changes in the log outcome per standard "
   "deviation and are not directly comparable with Table 4. Maximum-likelihood estimation with a row-standardized "
   f"Queen contiguity matrix; one hexagon without contiguous neighbours omitted (n = {int(t5f.loc['Frequency', 'n'])}). "
   "Standard errors in parentheses. Moran's I of the residuals: " + " and ".join(
       f"{mi(t5f.loc[o, 'resid_moran_I'], t5f.loc[o, 'resid_moran_p_sim'])} for {txt}" for o, txt in OUTCOME_TEXT.items()) + "."))
parts.append(table("<b>Table H1.</b> Mean dwell time per activity cluster (M<sub>h</sub>), visited hexagons",
                   ["Park", "Visited hexagons", "Median M<sub>h</sub> (IQR), min", "Mean M<sub>h</sub>, min"], [
    [PARKS[p], f"{int(h1.loc[p, 'n_visited'])} of {int(h1.loc[p, 'n_hex'])}",
     f"{h1.loc[p, 'M_h_median_min']:.1f} ({h1.loc[p, 'M_h_q1_min']:.1f}–{h1.loc[p, 'M_h_q3_min']:.1f})",
     f"{h1.loc[p, 'M_h_mean_min']:.1f}"] for p in PARKS]))
parts.append(table("<b>Table H2.</b> Models of log(M<sub>h</sub>)",
                   ["Variable", "(a) Pooled OLS, all parks", "(b) Spatial lag, Jurong Lake Gardens"],
                   coef_rows(pd.concat([h4, h5.replace({"term": {"CONSTANT": "Intercept"}})]),
                             T4_ROWS[:-1] + ["rho", "Intercept"], ["(a)", "(b)"]) + [
    ["Observations", int(hf.loc["Table 4", "n"]), int(hf.loc["Table 5", "n"])],
    ["R² (adjusted) / pseudo R²", f"{hf.loc['Table 4', 'r2']:.3f} ({hf.loc['Table 4', 'adj_r2']:.3f})",
     f"{hf.loc['Table 5', 'pseudo_r2']:.3f}"],
], "Note: Dependent variable log(M_h), M_h in minutes. M_h is undefined for hexagons without visits, so only visited hexagons are included: 148 of 185 in (a) and 80 of 87 Jurong hexagons in (b). (a) As Table 4: predictors in "
   "original units, park fixed effects with Bishan–Ang Mo Kio Park as the reference, robust (HC3) standard errors. "
   "(b) As Table 5: predictors standardized within Jurong Lake Gardens, maximum likelihood with a row-standardized "
   "Queen contiguity matrix, one hexagon without contiguous neighbours omitted (n = 79). Standard errors in parentheses. "
   + STAR_LINE))

# Appendix I: Tables 4 and 5 without near-home stays (step 09)
nh = pd.read_csv(OUT / "robustness_near_home.csv").query("variant == 'near_home_excluded'")
nhf = pd.read_csv(OUT / "robustness_near_home_fit.csv")
I1 = {("Table 4", "Frequency"): "(1)", ("Table 4", "Duration"): "(2)", ("Table 5", "Frequency"): "(3)", ("Table 5", "Duration"): "(4)"}
nh = nh.assign(outcome=[I1[k] for k in zip(nh["table"], nh["outcome"])]).replace({"term": {"CONSTANT": "Intercept"}})
fit = {I1[(r.table, r.outcome)]: r for r in nhf.query("variant == 'near_home_excluded'").itertuples()}
gone = nhf.query("table == 'clusters'").set_index("park")["share_clusters_removed"]
parts.append(table("<b>Table I1.</b> Pooled OLS and spatial lag models re-estimated without near-home stays",
                   ["Variable", "(1) OLS, frequency", "(2) OLS, cumulative dwell time", "(3) SLM, frequency",
                    "(4) SLM, cumulative dwell time"],
                   coef_rows(nh, T4_ROWS[:-1] + ["rho", "Intercept"], list(I1.values())) + [
    ["Observations"] + [int(fit[c].n) for c in I1.values()],
    ["R² / pseudo R²"] + [f"{fit[c].r2:.3f}" if c in ("(1)", "(2)") else f"{fit[c].pseudo_r2:.3f}" for c in I1.values()],
], f"Note: {STAR_LINE} As Tables 4 and 5, after removing every activity cluster whose device's inferred home lies "
   f"within 100 m of the hexagon ({gone['amk']:.0%} of the clusters in the modelled hexagons of Bishan–Ang Mo Kio Park, "
   f"{gone['jurong']:.0%} in Jurong Lake Gardens and {gone['punggol']:.0%} in Punggol Waterway Park); devices without an "
   "inferred home are kept. (1)–(2): pooled OLS with park fixed effects (Bishan–Ang Mo Kio Park as the reference), "
   "predictors in original units, robust (HC3) standard errors. (3)–(4): spatial lag model for Jurong Lake Gardens, "
   "predictors standardized, row-standardized Queen contiguity matrix. Standard errors in parentheses."))
assert [int(fit[c].n) for c in I1.values()] == [185, 185, 86, 86]

style = ("body{font-family:'Times New Roman',serif;font-size:11pt;max-width:900px;margin:24px auto;padding:0 16px}"
         "table{border-collapse:collapse;margin:6px 0}th,td{padding:2px 10px;text-align:left}"
         "thead tr{border-top:1.5px solid #000;border-bottom:1px solid #000}tbody tr:last-child{border-bottom:1.5px solid #000}"
         "td:not(:first-child),th:not(:first-child){text-align:center}.cap{margin-top:28px}.note{font-size:10pt}")
head = ("<p><b>Revised tables</b>: closed Chinese and Japanese Gardens excluded, park services recounted, F<sub>h</sub> "
        "recounted (one per device cluster). Made by 07_manuscript_tables.py from the step 01 and 05 outputs. "
        "Appendix E's visitation rows use the Table 3 values.</p>")
(OUT / "manuscript_tables.html").write_text(
    f"<!doctype html><html><head><meta charset='utf-8'><title>Manuscript tables</title><style>{style}</style></head>"
    f"<body>{head}{''.join(parts)}</body></html>", encoding="utf-8")
print(f"Self-check passed. Written: {OUT / 'manuscript_tables.html'}")
