# Reproducibility scope and workflow

## Public execution (no restricted data)

Python 3.12 with the direct dependency versions in `requirements.txt`. The released results were produced with exactly these versions; step 06 also used `mapclassify` 2.8.1 and `matplotlib-scalebar` 0.8.1. Runtime is a few minutes on a CPU. No GPU, credentials or network access are needed after installation.

1. **`python tools/run_final_models.py`** runs the final model code on the synthetic cells:
   - Table 3 summary;
   - Moran's I on the model cells;
   - pooled OLS with HC3 (Table 4);
   - residual Moran's I;
   - Jurong spatial lag model (Table 5).

   The functions are taken unchanged from `code/revision/01_rerun_models.py`, and the output CSVs have the same layout as `data/summary/`.
2. **`python tools/plot_public_results.py`** charts the released Table 5 coefficients with 95% intervals. It doesn't refit anything.
3. **`python tools/run_models.py`** runs the three original-submission model notebooks in `code/models/` on the synthetic cells (`--model <name>` selects one).
4. **`python tools/make_synthetic.py`** regenerates the synthetic input from seed 20261108.

## Final statistical conventions (revised paper)

- **Outcomes:**
  - log(F_h + 1) and log(D_h + 1);
  - F_h = number of activity clusters (one per device cluster) over the 36-day window;
  - D_h = summed cluster duration in seconds;
  - Appendix H also uses log(M_h), with M_h = D_h / F_h, on visited hexagons only.
- **Pooled OLS:** eleven predictors in original units plus park fixed effects (reference: Bishan–Ang Mo Kio Park), with HC3 standard errors.
- **Spatial weights:** Queen contiguity, row-standardised. Hexagons without a Queen neighbour are dropped from the spatial statistics. The 999-permutation tests use seed 20260419 on the modelled hexagons.
- **Appendix F's all-park-cell values** come from `code/methods/Figure4_Park_Use_LQ_Maps.ipynb`, which re-seeds 42 for each park and outcome.
- **Jurong spatial lag model:** `spreg.ML_Lag(method='full')`, with predictors standardised within Jurong Lake Gardens (sample SD, `ddof=1`).

## Re-running the revised analysis (restricted inputs)

`code/revision/README.md` lists the steps, their inputs and their outputs. The scripts expect the original workspace layout and the restricted device- and cell-level inputs. Keep every output of a private run outside this repository, because several outputs are cell- or device-level.

To run the model code on an authorised private model input through the original notebooks:

```bash
python tools/run_models.py --data /path/to/private/model_cells.geojson --output /path/to/private/results
```

## What cannot be reconstructed publicly

- **Device-level processing:** GPS cleaning, ST-DBSCAN clustering, residence inference and catchment routing.
- **Cell-level work:** the F_h recount, the closed-garden and near-home exclusions, the cell-level maps (Figure 4(d), Appendices D and F) and image-level model inference.
- **Model fits:** exact study model fits. The park- and model-level summaries can't be used to recover individual cells or the design matrix.
