# Selection and privacy boundaries

Only explicitly selected code and result tables are included. The research workspace and its Git history, hidden folders, PDFs, spreadsheets, images, model checkpoints, caches, credentials, downloaded provider data and intermediate outputs were not copied.

**Code:**
- **Notebooks** in `code/models/` and `code/methods/` were rebuilt from their code cells with empty outputs and fresh metadata. Machine-specific paths were removed.
- **Scripts** in `code/revision/` are exact copies of the scripts that were run. The one exception is the manuscript file name in `01_rerun_models.py`, generalised to remove an author name for double-anonymised review.
- **Excluded:** authentication/API acquisition notebooks and individual-trajectory examples.

**Released data:**
- **What it contains:** model coefficients, fit statistics, Moran's I statistics, park-level visitation summaries (`data/summary/`, 15 files), and synthetic demonstration data.
- **What it doesn't contain:** cell-level outcomes, cell IDs paired with outcomes, predictions or residuals.
- **Revision outputs left out:**
  - cell-level: corrected per-cell counts, excluded-hexagon lists with their F_h and D_h, figures and maps;
  - device-level: devices that stayed only inside the closed gardens;
  - author-facing: change logs and formatted tables.

**Why the hexagon table is withheld.** Aggregation alone does not make data disclosure-safe. The hexagon-level analysis table is withheld because no distinct-contributor support per cell has been verified, and frequency is not a count of distinct people. A later release of real spatial aggregates would need an assessment of:
- distinct contributors and repeated contributions;
- rare combinations and dominance;
- spatial detail and differencing across files;
- provider permission.

**Synthetic data** were generated from a fixed seed without reading any study data or geometry.

**What the checker does.** The release checker:
- verifies the exact file inventory and checksums;
- rejects symlinks and unexpected files;
- checks notebook outputs and metadata;
- scans code and text for common credential and local-path patterns;
- verifies every CSV against `CSV_COLUMNS.csv`.

These checks reduce accidental disclosure. They are not proof of zero re-identification risk or of redistribution rights. Publish only the checked snapshot, never the parent workspace.
