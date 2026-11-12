"""Step 06: redraw Appendix D in Python (replaces the QGIS re-export).

(a) Maps of F_h and D_h on all park cells, as in the QGIS layout "Three parks_Visitation"
    (qgis_files/three_parks_sg_visitation.qgz). Class breaks, colours and labels are read from that project,
    so the legends are identical to the published figure; hexagons have white edges, parks a black outline.
(b) Box plots on the modelled hexagons, as in 04_figures.py (plt.boxplot, no fliers).

Writes outputs/figures/appendixD_revised.{svg,png} (corrected F_h from step 00, Jurong without the closed
gardens) and appendixD_original.{svg,png} (stored files; compare with the published Appendix D to check the redraw).
In the revised maps all classes are recomputed with one rule: Fisher-Jenks natural breaks of log(value + 1), with
the project's number of classes and colours. The corrected counts exceed the published F_h classes, and the
published (QGIS) breaks cannot be reproduced, so one stated rule keeps the six maps comparable. The original
variant keeps the QGIS classes, to check the redraw against the published figure.

Run with the geospatial env:  ~/.virtualenvs/geospatial/bin/python 06_appendixD.py
"""
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import geopandas as gpd
import mapclassify
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from matplotlib_scalebar.scalebar import ScaleBar

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIG = HERE / "outputs/figures"
QGZ = ROOT / "qgis_files/three_parks_sg_visitation.qgz"
DUR = ROOT / "gps_analysis/general_model/duration_analysis"
PARKS = {"amk": "Bishan-Ang Mo Kio Park", "jurong": "Jurong Lake Gardens", "punggol": "Punggol Waterway Park"}
BOX_LABELS = {"amk": "Bishan–AMK", "jurong": "Jurong", "punggol": "Punggol"}
ROWS = {"F_h": "Visiting frequency ($F_h$)", "D_h": "Cumulative dwell time ($D_h$)"}
# QGIS layer holding each map (the "copy" layers carry the D_h symbology)
LAYER = {"F_h": "{}_duration_analysis", "D_h": "{}_duration_analysis copy"}
VARIANTS = {
    "revised": {"cells": {"amk": HERE / "corrected_fh/amk_duration_analysis.geojson",
                          "jurong": HERE / "jurong_duration_analysis_excl_closed.geojson",
                          "punggol": HERE / "corrected_fh/punggol_duration_analysis.geojson"},
                "model": HERE / "parks_allthree_hex_agg_attributes_visits_excl_closed.geojson", "new_breaks": True},
    "original": {"cells": {},
                 "model": ROOT / "gis_files/hexagons/agg_attributes/parks_allthree_hex_agg_attributes_visits.geojson"},
}


def qgis_classes():
    """{(layer name, attribute): [(lower, upper, label, colour), ...]} from the project's graduated renderers."""
    with zipfile.ZipFile(QGZ) as z:
        root = ET.fromstring(z.read(next(n for n in z.namelist() if n.endswith(".qgs"))))
    out = {}
    for ml in root.iter("maplayer"):
        rend = ml.find("renderer-v2")
        if rend is None or rend.get("type") != "graduatedSymbol":
            continue
        fills = {}
        for s in rend.find("symbols"):
            # direct options of the fill layer only; nested data-defined options carry a default red
            opts = {o.get("name"): o.get("value") for o in s.find("layer").find("Option")}
            fills[s.get("name")] = tuple(int(c) / 255 for c in opts["color"].split(",")[:3])
        out[(ml.findtext("layername"), rend.get("attr"))] = [
            (float(r.get("lower")), float(r.get("upper")), r.get("label"), fills[r.get("symbol")])
            for r in rend.find("ranges")]
    return out


def classify(values, classes):
    """QGIS rule: a value belongs to the first class whose upper bound is >= the value."""
    idx = np.searchsorted([c[1] for c in classes], values, side="left")
    assert (values >= classes[0][0]).all() and (idx < len(classes)).all(), "value outside the QGIS classes"
    return [classes[i][3] for i in idx]


def jenks_classes(values, template):
    """Fisher-Jenks natural breaks of log(value + 1), with the template's number of classes and colours, labelled as
    QGIS does. On the raw, highly skewed values most cells would fall in the lowest class."""
    bins = np.expm1(mapclassify.FisherJenks(np.log1p(values), k=len(template)).bins).round()
    lows = [values.min(), *bins[:-1]]
    return [(lo, hi, f"{hi:.0f}" if lo == hi else f"{lo:.0f} - {hi:.0f}", t[3]) for lo, hi, t in zip(lows, bins, template)]


LEGEND_PAD = {"jurong": 0.45}  # Jurong fills its panel: widen it on the left so the legend sits beside the park


def draw_map(ax, cells, col, classes, park):
    cells.plot(ax=ax, color=classify(cells[col].to_numpy(float), classes), edgecolor="white", linewidth=0.5)
    cells.dissolve().boundary.plot(ax=ax, color="black", linewidth=0.8)
    x0, x1 = ax.get_xlim()
    ax.set_xlim(x0 - LEGEND_PAD.get(park, 0) * (x1 - x0), x1)
    leg = ax.legend(handles=[Patch(facecolor=c[3], edgecolor="#999999", linewidth=0.3, label=c[2]) for c in classes],
                    loc="lower left", fontsize=5, frameon=False, handlelength=1.2, handleheight=0.9, borderaxespad=0.1)
    ax.add_artist(ScaleBar(1, "m", location="upper right", length_fraction=0.25, box_alpha=0, font_properties={"size": 6},
                           width_fraction=0.012, scale_loc="top"))
    ax.set_aspect("equal")
    ax.set_axis_off()
    return leg


def north_arrow_above(ax, leg):
    """North arrow just above the legend; needs the final axes size, so call it once all panels exist."""
    ax.apply_aspect()
    top = leg.get_window_extent(ax.figure.canvas.get_renderer()).transformed(ax.transAxes.inverted()).y1
    length = 16 * ax.figure.dpi / 72 / ax.get_window_extent().height  # 16 pt in every panel
    ax.annotate("N", xy=(0.05, top + 0.04 + length), xytext=(0.05, top + 0.04), xycoords="axes fraction",
                ha="center", va="bottom", fontsize=6, arrowprops=dict(arrowstyle="-|>", color="black", lw=0.8))


def render(variant, spec, classes):
    fig = plt.figure(figsize=(12, 5.6))
    # column 3 is an empty spacer that keeps the box-plot axis label off the Punggol maps
    gs = fig.add_gridspec(2, 5, width_ratios=[1, 1, 1, 0.12, 0.85], wspace=0.08, hspace=0.12,
                          left=0.04, right=0.99, top=0.93, bottom=0.11)
    model = gpd.read_file(spec["model"])
    parks = list(PARKS)
    maps = []
    for r, col in enumerate(ROWS):
        for c, park in enumerate(parks):
            cells = gpd.read_file(spec["cells"].get(park, DUR / f"{park}_duration_analysis.geojson"))
            assert cells[col].notna().all(), f"{park} {col}: QGIS would not draw NaN cells"
            ax = fig.add_subplot(gs[r, c])
            cls = classes[(LAYER[col].format(park), col)]
            if spec.get("new_breaks"):  # one rule for all six revised maps, so F_h and D_h maps are comparable
                cls = jenks_classes(cells[col].to_numpy(float), cls)
                print(f"{variant} {park} {col} classes: {[c[2] for c in cls]}")
            maps.append((ax, draw_map(ax, cells, col, cls, park)))
            if r == 0:  # titles on the grid cell, not the axes, so they line up although map heights differ
                box = gs[r, c].get_position(fig)
                fig.text((box.x0 + box.x1) / 2, box.y1 + 0.015, PARKS[park], ha="center", fontsize=9)
            if c == 0:
                ax.text(-0.06, 0.5, ROWS[col], rotation=90, va="center", ha="center", fontsize=9, transform=ax.transAxes)
        ax = fig.add_subplot(gs[r, 4])
        vals = pd.to_numeric(model[col], errors="coerce").fillna(0)
        ax.boxplot([vals[model["park"] == p].values for p in parks], showfliers=False)
        ax.set_xticks(range(1, 4), [BOX_LABELS[p] for p in parks], fontsize=7)
        ax.set_ylabel(f"${col[0]}_h$" + (" (s)" if col == "D_h" else ""), fontsize=8)
        ax.tick_params(axis="y", labelsize=7)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.spines[["top", "right"]].set_visible(False)
    for ax, leg in maps:
        north_arrow_above(ax, leg)
    fig.text(0.40, 0.03, "(a) Spatial distribution of aggregated visitation features", ha="center", fontsize=9)
    fig.text(0.895, 0.03, "(b) Box plot (modelled cells)", ha="center", fontsize=9)
    for ext in ["svg", "png"]:
        fig.savefig(FIG / f"appendixD_{variant}.{ext}", dpi=300)
    plt.close(fig)


classes = qgis_classes()
# self-check: the project's top classes end at the original data maxima (natural breaks on these files)
for park in PARKS:
    full = gpd.read_file(DUR / f"{park}_duration_analysis.geojson")
    for col in ROWS:
        assert classes[(LAYER[col].format(park), col)][-1][1] == full[col].max(), f"{park} {col}: classes don't fit data"
for variant, spec in VARIANTS.items():
    render(variant, spec, classes)
print(f"Self-check passed: QGIS classes match the data. Written: {FIG}/appendixD_revised.svg/.png and appendixD_original.svg/.png")
