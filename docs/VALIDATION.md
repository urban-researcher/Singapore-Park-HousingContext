# Validation record

## Release candidate 0.2.0 — 12 November 2026 (revised paper)

**Contents:**
- Added the revision pipeline `code/revision/` (steps 00–09) and `tools/run_final_models.py`.
- Replaced the 11 pre-revision summary tables with 15 tables from the revised analysis.
- Updated the documentation and the data statement.

**Provenance:**
- **Result tables:** every released table is byte-identical to its source output; the SHA-256 values are in `SOURCE_PROVENANCE.csv`.
- **Scripts:** every script in `code/revision/` is byte-identical to the script that was run, except the generalised manuscript file name in `01_rerun_models.py`.
- **Reproduction checks:** within the original workspace, each step's assert-based self-checks passed on the final run.
  - Step 01 confirms that the `original` variant reproduces the published Tables 3–5 and Moran's I.
  - Step 00 confirms that its spatial join reproduces the stored counts and D_h before replacing F_h.
  - Steps 05 and 09 confirm that their unrestricted rows reproduce step 01.

**Demo code = study code:**
- `tools/run_final_models.py` extracts the model functions from `code/revision/01_rerun_models.py`.
- Run privately, outside this package, on the real revised input, it reproduced the released `table4_pooled_ols.csv` and `table5_jurong_slm.csv` with a maximum absolute difference < 1e-15 in estimates and standard errors.
- No output of that run is included.

**Public workflows (Linux, Python 3.12.3, the analysis environment, whose versions equal `requirements.txt`):**
- `check_release.py` passed on the clean snapshot.
- `run_final_models.py`, `plot_public_results.py` and `run_models.py` (all three notebooks) ran on the synthetic data.
- `make_synthetic.py` regenerated a byte-identical synthetic file.
- The checker rejected the snapshot once `outputs/` existed, as intended.

**Privacy and anonymity:**
- **Identifying strings:** the package was searched for author and institution names, e-mail addresses and machine-specific paths; none were found.
- **Withheld outputs:** the device-level and cell-level revision outputs are excluded (`PRIVACY_AND_SELECTION.md`).

**Not run here:**
- the restricted-data steps outside the original workspace;
- the upstream method notebooks;
- the OneFormer wrappers;
- production GPS clustering;
- Windows and macOS installs.

## Release candidate 0.1.0 — 8 November 2026

The first candidate packaged the original-submission model notebooks, the method references and 11 pre-revision summary tables.
- **Tests:**
  - The three notebooks ran on the synthetic data.
  - A clean install from `requirements.txt` was tested; scipy and jinja2 were pinned after it.
  - The checker passed nine negative tests (unexpected files, changed checksums, symlinks, notebook outputs, credential literals, truncated CSV rows, and private-output redirection).
- **Figure 4 notebook:** run on the private housing-group inputs, it reproduced the six Moran's I values printed in the original submission.
- **Superseded:** those tables and their alignment notes are replaced by the revised analysis. The earlier version can be recovered from the 0.1.0 snapshot if it was archived.
