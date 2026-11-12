# Revised analysis pipeline (steps 00–09)

These scripts produced every result table in `data/summary/` and the revised figures in the paper. They are exact copies of the scripts that were run. The one exception is the manuscript file name in `01_rerun_models.py`, which is generalised in this copy. They need the restricted study inputs, so they cannot run from this repository alone. To run the same model code on synthetic data, use `tools/run_final_models.py`.

## What the revision changed relative to the original submission

1. **Closed gardens excluded.** Jurong Lake Gardens' Chinese and Japanese Gardens were closed for redevelopment from May 2019 to 8 September 2024. That period covers the GPS observation window, 26 August to 30 September 2022. Hexagons with at least half of their area inside the two gardens are excluded:
   - 20 of the 107 modelled hexagons;
   - 30 of the 365 park cells used in Figure 4 and Appendices D and F.
2. **Park services recounted.** The services variable (`peps`) is the number of service points within 500 m of each hexagon centroid, recounted from the final compiled service-point file.
3. **F_h recounted.**
   - **The error:** the upstream duration notebook (`code/methods/gps_analysis__general_model__duration_analysis__main.ipynb`) and the housing-group notebook (`code/methods/analysis__travel_pattern_by_neighbourhood__main.ipynb`) count `nunique('cluster')` per hexagon. ST-DBSCAN numbers clusters separately for each device, so clusters of different devices that share a number were counted once.
   - **The fix:** step 00 counts every device cluster whose hull centroid lies in the hexagon. It asserts that the same spatial join reproduces the notebooks' counts and D_h before replacing F_h. D_h was unaffected.
   - **The notebooks** in `code/methods/` are kept as they were run, for provenance; do not use their F_h counts.
4. **Spatial weights.** Queen contiguity, row-standardised. Hexagons without a Queen neighbour (one in the revised Jurong set) are dropped from the spatial statistics. The original notebooks would instead fall back to KNN; step 02 compares the two.
5. **Spatial lag model standardisation.** Predictors are standardised within Jurong Lake Gardens with the sample SD (`ddof=1`), as in the published Table 5.

## Steps

| Step | Script | Produces |
|---|---|---|
| 00 | `00_flag_closed_hexes.py` | Revised model input: closed-garden hexagons excluded, services recounted, F_h recounted (overall and per housing group). |
| 01 | `01_rerun_models.py` | Table 3, Moran's I on the modelled hexagons, Table 4 (pooled OLS, HC3), residual Moran's I, Table 5 (Jurong spatial lag model). Writes both the original and revised versions, and asserts that the original reproduces the published values. |
| 02 | `02_weights_robustness.py` | Queen vs KNN weights for the Jurong spatial lag model (`table5_weights_robustness.csv`). |
| 03 | `03_device_check.py` | Check of device counts against the closed gardens (output is device-level and not released). |
| 04 | `04_figures.py` | Figure 4 and the Appendix F LISA figure, by running `code/methods/Figure4_Park_Use_LQ_Maps.ipynb` on the revised inputs (`fig4_appendixF_stats.csv`). |
| 05 | `05_mean_dwell.py` | Appendix H: mean dwell time per activity cluster, M_h = D_h / F_h, and Tables 4–5 re-estimated with log(M_h) (`r3_4_*.csv`). |
| 06 | `06_appendixD.py` | Appendix D maps and box plots. |
| 07 | `07_manuscript_tables.py` | Tables 3, 4, 5, H1, H2 and I1 formatted for the manuscript. |
| 08 | `08_perception_check.py` | Correlations, VIFs and the safety coefficient with and without the other perception scores (printed, quoted in the Results). |
| 09 | `09_near_home_robustness.py` | Appendix I: Tables 4–5 re-estimated without clusters of devices whose inferred home is within 100 m of the hexagon (`robustness_near_home*.csv`). |

Run in order 00 → 09. Each script contains assert-based self-checks and stops if an input or a reproduced value differs.

## Inputs and layout

The scripts expect the original research workspace layout: `ROOT` is three levels above this folder. They read:
- **Cluster hulls:** `gis_files/hulls/{park}/breaks_hulls.geojson`, the ST-DBSCAN activity clusters per device.
- **Grids:** `gis_files/hexagons/...`, the hexagon grids and aggregated attributes.
- **Residences:** `gps_analysis/activities_identification_example/calibrated_residence_{park}_2022_updated.geojson`, the inferred residences.
- **Service points:** `gis_files/poi/poi_all_parks.geojson`.
- **Garden outlines:** `gis_files/jurong_lake/chinese_japanese_gardens_osm.geojson`.
- **QGIS project:** `qgis_files/three_parks_sg_visitation.qgz`, used for the class breaks of the original Appendix D.

The device-level and cell-level inputs are restricted (see `DATA_AVAILABILITY.md`) and are not part of this repository.

**Outputs that are not released:**
- cell-level files: corrected cell counts, excluded-hexagon lists, figures;
- device-level files: `devices_only_in_closed_gardens.csv`.

Only the model- and park-level CSVs in `data/summary/` are released. Steps 01 and 07 also write an internal change log and formatted tables for the authors (`paper_changes.md`, `manuscript_tables.html`); these are not included.

## Environment

Python 3.12 with the versions in `requirements.txt`; step 06 also needs `mapclassify==2.8.1` and `matplotlib-scalebar==0.8.1`. The released results were produced with exactly these versions.
