# Mapping Urban Park Use — code and public summary data

Companion repository for *Mapping Urban Park Use: Mobile Data Evidence on Housing Context and Design Effects in Singapore* (revised manuscript, November 2026).

The study covers three parks:
- Bishan–Ang Mo Kio Park (`amk`);
- Jurong Lake Gardens (`jurong`);
- Punggol Waterway Park (`punggol`).

It uses mobile GPS observations from 26 August to 30 September 2022, aggregated to hexagons.

**What this repository contains:**
- the analysis code;
- the real model- and park-level result tables of the revised paper;
- entirely synthetic demonstration data.

**What it does not contain:** raw GPS, device-level records, inferred homes, cell-level mobility outcomes, imagery, or routing responses (see `DATA_AVAILABILITY.md`).

## Quick start

Use Python 3.12 in a new environment, created outside this folder:

```bash
python -m venv ../ufug-public-venv
# Linux/macOS:
source ../ufug-public-venv/bin/activate
# Windows PowerShell instead: ..\ufug-public-venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python tools/check_release.py        # verify the snapshot (run before generating outputs)
python tools/run_final_models.py     # final model code (Tables 3-5) on synthetic data
python tools/plot_public_results.py  # chart of the released Table 5 coefficients
python tools/run_models.py           # original-submission model notebooks on synthetic data
```

**Synthetic results are not paper findings.** The demonstration uses 192 artificial square cells with generated values, so its numbers have no empirical meaning. Outputs go to `outputs/`, which is excluded from version control.

`check_release.py` rejects any file not in `MANIFEST.sha256`, including generated `outputs/`. Run it on a clean copy.

## Contents

| Path | What it is |
|---|---|
| `code/revision/` | The scripts that produced the revised results (steps 00–09), with their own README: closed-garden exclusion, services recount, F_h recount, Tables 3–5, Moran's I, residual Moran's I, Appendices D, F, H and I. They need the restricted inputs. |
| `code/models/` | The original-submission model notebooks: pooled OLS with park fixed effects and HC3, Moran's I and LISA, Jurong spatial lag model. They run on the synthetic data through `tools/run_models.py`. |
| `code/methods/` | Upstream method notebooks and scripts: residence inference, stay-to-grid aggregation, housing-group counts, environmental measures, proximity, road connectivity, land use, ST-DBSCAN, OneFormer wrappers, and the Figure 4 notebook. Reference copies; they need private inputs and are not a runnable pipeline. |
| `data/summary/` | 15 released result tables from the revised analysis. No row is a person or a real spatial cell. |
| `data/synthetic/` | The synthetic model input; generator in `tools/make_synthetic.py`. |
| `tools/` | Release checker, demonstration runners, plot, synthetic-data generator. |
| `docs/` | Data dictionary, column descriptions (`CSV_COLUMNS.csv`), reproducibility scope, manuscript–code alignment, privacy and selection, provenance, validation record. |

**Where each manuscript item comes from:**

| Manuscript item | Released table |
|---|---|
| Table 3 / Appendix E visitation rows | `table3_summary.csv` |
| Table 4 | `table4_pooled_ols.csv`, `table4_fit.csv`, `residual_moran.csv` |
| Table 5 | `table5_jurong_slm.csv`, `table5_fit.csv` |
| Moran's I in the Results | `moran_model_grid.csv` (modelled hexagons), `fig4_appendixF_stats.csv` (all park cells, as printed in Appendix F) |
| Figure 4 (a)–(c) | `fig4_appendixF_stats.csv` |
| Appendix H | `r3_4_*.csv` |
| Appendix I | `robustness_near_home*.csv` |

Every table has an `original` variant (the published analysis, reproduced exactly) and a revised variant (`excl_closed`, or `revised` in the Appendix I tables).

## Reuse and citation

Code is MIT licensed. The released summary data, synthetic data and documentation are CC BY 4.0. See `LICENSE`, `DATA_LICENSE.md` and `THIRD_PARTY_NOTICES.md`; these terms grant no rights to excluded source datasets, model weights or other third-party resources.

Cite the paper and the archived release DOI once assigned (`CITATION.cff`). The street-level imagery is archived separately on Zenodo; its DOI is withheld during double-anonymised review.

## Interpretation limit

This is a **partial reproducibility** package. The released tables, and the code that produced them, can be inspected, and the model code can be run on synthetic data. Re-estimating the study's results requires the restricted inputs (`docs/REPRODUCIBILITY.md`).
