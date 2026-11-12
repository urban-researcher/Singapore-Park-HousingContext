# Manuscript–code alignment

Reference: the revised manuscript (November 2026). The first release candidate (8 November 2026) recorded several discrepancies between the draft and the code. The revision resolved them as follows.

| Item | Status in the revised paper | Evidence in this repository |
|---|---|---|
| Table 3 / Appendix E visitation rows | Released. Means, medians, shares visited and D_h for the 185 modelled hexagons. | `table3_summary.csv` |
| Table 4, pooled OLS | Re-estimated on the revised data: closed gardens excluded, services recounted, F_h recounted. The `original` variant reproduces the published table exactly. | `table4_*.csv`; `code/revision/01_rerun_models.py` |
| Table 5, Jurong spatial lag model | Re-estimated as above. Predictors are standardised with the sample SD (`ddof=1`), as printed; the original-submission notebook used `ddof=0`, which scales coefficients by 1.0047. | `table5_*.csv`; step 01 |
| Moran's I: which cells | The Results now report both. All park cells (n = 112/335/43) come from the Figure 4 notebook; the outcome is the sum over housing groups. The modelled hexagons (n = 77/86/21) are the ones the regressions use. Only Jurong Lake Gardens is significant among the modelled hexagons. | `fig4_appendixF_stats.csv` (rows `appendixF_figure` are the printed values); `moran_model_grid.csv` |
| Residual Moran's I for the pooled OLS | Now computed and reported in the note to Table 4. Significant only in Jurong Lake Gardens, and removed by the spatial lag model. | `residual_moran.csv`, `table5_fit.csv` |
| Services variable (`peps`) | Described as a count of service points within 500 m, and recounted from the final service-point file. | step 00; `code/methods/analysis__intra-park__proximity_calculation__park_service.ipynb` |
| F_h uniqueness | **Resolved: the original count was wrong.** The upstream notebooks count `nunique('cluster')`, but cluster numbers repeat across devices. F_h is now the number of device clusters. Jurong's total rose 3.0× and Punggol's 4.8×; Bishan–Ang Mo Kio was unchanged. D_h was unaffected. | step 00 (asserts the join reproduces the old counts before replacing them) |
| Spatial weights | Queen contiguity, row-standardised. The single island in the revised Jurong set is dropped from spatial statistics. The KNN alternative is reported as a robustness check. | step 02; `table5_weights_robustness.csv` |
| Cumulative dwell time | D_h is the sum of cluster durations in seconds. Appendix H adds mean dwell per cluster, M_h = D_h / F_h. | step 05; `r3_4_*.csv` |
| Imagery dates and facility changes | Reported in the Methods (July–August 2025). The closed gardens are excluded; no other in-park redevelopment was found. | step 00 |
| Near-home stays | New robustness check (Appendix I): clusters of devices whose inferred home is within 100 m of the hexagon are removed. | step 09; `robustness_near_home*.csv` |
| Spatial grid | The manuscript describes a 100 m H3 hexagonal grid. `code/methods/create_fishnet.py` is a legacy planar-hexagon generator; the production grid files are not released. | not reproducible here |
| Table 2 / Appendix G (housing-index sensitivity) | Computed from catchment land-use shares; not reproduced in this repository. | — |

**Remaining limits:**
- Cell-level maps (Figure 4(d), Appendices D and F) and device-level steps can't be rebuilt from public data.
- The upstream method notebooks in `code/methods/` are kept as they were run. Their F_h counts are superseded by step 00.
