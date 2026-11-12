# Before making the repository public

Nothing has been uploaded or published from this folder.

**During double-anonymised review:**
- Keep the GitHub repository **private**, or share an anonymised view, for example https://anonymous.4open.science.
- A public repository under a personal account would reveal the authors.
- The manuscript says the link is withheld for review.

**At acceptance:**
- **Citation details:** add the full author list, repository URL and release version to `CITATION.cff`, and an author line to `LICENSE` if wanted.
- **Archive:** make the repository public and archive a tagged release (e.g. GitHub–Zenodo integration) to obtain a DOI.
- **Data statement:** fill the URL and DOI into `DATA_AVAILABILITY.md` and the manuscript, together with the imagery DOI.
- **Rights:** confirm with co-authors and institutions that the code can be released under MIT and the summaries under CC BY 4.0. Excluded provider datasets keep their own terms.
- **Journal:** check the current Urban Forestry & Urban Greening Guide for Authors.

**Before every upload:**
- Run `python tools/check_release.py` on the exact clean snapshot being uploaded.
  - It fails on any unreviewed addition or change, including generated `outputs/` and virtual environments.
  - After an intentional change, review it for privacy, then regenerate `MANIFEST.sha256`.
- Never add restricted inputs or outputs of private runs. That means cell-level files, device-level files and maps.
- Upload this folder alone, as a new repository. Do not copy the parent workspace or its Git history.
