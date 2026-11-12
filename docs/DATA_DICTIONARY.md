# Data dictionary

`CSV_COLUMNS.csv` describes every column of every released CSV. CSVs are UTF-8 with comma delimiters. Numbers keep full precision; empty cells are left empty.

## Released result tables (`data/summary/`)

All are copies of outputs of `code/revision/` (source paths and SHA-256 in `SOURCE_PROVENANCE.csv`).
- **Units:** each row is a park, an outcome, a model term or a test; none is a person or a real spatial cell.
- **`variant` values:** `original` = the published analysis reproduced exactly (205 modelled hexagons, stored F_h). `excl_closed` = the revised analysis (closed gardens excluded, services recounted, F_h recounted).

| File | Unit of observation | Manuscript item |
|---|---|---|
| `table3_summary.csv` | Park × variant | Table 3; Appendix E visitation rows |
| `table4_pooled_ols.csv` | Variant × outcome × term | Table 4 coefficients (HC3) |
| `table4_fit.csv` | Variant × outcome | Table 4 n, R², adjusted R² |
| `residual_moran.csv` | Variant × scope × outcome | Note to Table 4 (Moran's I of OLS residuals) |
| `table5_jurong_slm.csv` | Variant × outcome × term | Table 5 coefficients (standardised predictors) |
| `table5_fit.csv` | Variant × outcome | Table 5 n, AIC, pseudo R², ρ, residual Moran's I |
| `moran_model_grid.csv` | Variant × park × outcome | Moran's I on the modelled hexagons (Results) |
| `fig4_appendixF_stats.csv` | Variant × park × statistic | Figure 4(a)–(c) values; Moran's I on all park cells as printed in Appendix F (`stat = appendixF_figure`) |
| `table5_weights_robustness.csv` | Run × outcome × term | Queen vs KNN weights for the Jurong model |
| `r3_4_mean_dwell_summary.csv` | Park | Appendix H, Table H1 (M_h = D_h / F_h) |
| `r3_4_table4.csv`, `r3_4_table5.csv`, `r3_4_fit.csv` | Outcome × term / model | Appendix H, Table H2 (`outcome = Mean dwell`), plus the corrected-F_h models |
| `robustness_near_home.csv`, `robustness_near_home_fit.csv` | Variant × model × term; park | Appendix I, Table I1 (near-home stays removed) |

## Model input schema (synthetic or independently authorised private data)

Each row is one spatial cell in one park. The key is `(park, grid_id)`; a `grid_id` can repeat across parks. The synthetic file uses EPSG:3414 and an arbitrary square lattice, not the study's locations or grid. A private file must carry its true CRS.

| Field | Meaning |
|---|---|
| `park` | `amk` = Bishan–Ang Mo Kio Park; `jurong` = Jurong Lake Gardens; `punggol` = Punggol Waterway Park |
| `grid_id` | Spatial unit key, never a device identifier |
| `F_h` | Number of activity clusters (one per device cluster) over the observation window; not a count of distinct people |
| `D_h` | Cumulative dwell time: summed cluster durations, seconds |
| `ps`, `pl`, `pb`, `pm` | Perceived safety, liveliness, beauty and monotony scores |
| `peg`, `peo`, `pep` | Greenness, openness and park-furniture pixel percentages aggregated from images |
| `peps` | Number of park service points within 500 m (Euclidean) of the cell centroid |
| `per` | Internal road connectivity (mean closeness) |
| `pepw` | Proximity to water: 1 / distance in metres, 1 for cells touching water |
| `set` | Inverse walking distance to the nearest MRT station (1000 / metres) |
| `geometry` | Cell polygon; required for spatial weights |

Synthetic predictor values are generic values in 0.2–3, not calibrated to the real measurements. Synthetic F_h is a seeded Poisson draw and D_h an artificial sum-like outcome. No empirical inference is possible from them.
