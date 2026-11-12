"""Run the final (revised) model code on the synthetic cells: Table 3 summary, Moran's I, pooled OLS (Table 4),
residual Moran's I and the Jurong spatial lag model (Table 5).

The functions are taken unchanged from code/revision/01_rerun_models.py (imports, constants and function
definitions only; its data paths and report writing are skipped), so this demo runs the same statistical code
that produced the released result tables. Synthetic results are NOT paper findings.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "code/revision/01_rerun_models.py"
CONSTANTS = {"X_COLS", "OUTCOMES", "PARKS", "LABELS", "T4_TERMS", "T5_TERMS"}


def final_model_code():
    """Namespace with 01_rerun_models.py's imports, model constants and functions."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    keep = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef))
            or (isinstance(n, ast.Assign) and all(isinstance(t, ast.Name) and t.id in CONSTANTS for t in n.targets))]
    ns = {"__name__": "final_models"}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SOURCE), "exec"), ns)
    missing = {"load", "table3", "moran", "pooled_ols", "residual_moran", "jurong_slm"} - set(ns)
    assert not missing, f"{SOURCE.name} no longer defines {missing}"
    return ns


def main():
    ns = final_model_code()
    ns["warnings"].filterwarnings("ignore")
    pd = ns["pd"]
    gdf = ns["load"](ROOT / "data/synthetic/model_cells.geojson")
    out = ROOT / "outputs/final_synthetic"
    out.mkdir(parents=True, exist_ok=True)
    coefs, fits, resid = ns["pooled_ols"](gdf, "synthetic")
    slm, slm_fit = ns["jurong_slm"](gdf, "synthetic")
    results = {"table3_summary": ns["table3"](gdf, "synthetic"), "moran_model_grid": ns["moran"](gdf, "synthetic"),
               "table4_pooled_ols": coefs, "table4_fit": fits, "residual_moran": ns["residual_moran"](resid, "synthetic"),
               "table5_jurong_slm": slm, "table5_fit": slm_fit}
    for name, df in results.items():
        df.to_csv(out / f"{name}.csv", index=False)
    pd.set_option("display.width", 200)
    print("SYNTHETIC DATA (artificial cells and values; not paper findings)\n")
    print(fits.round(3).to_string(index=False), "\n")
    print(slm_fit[["outcome", "n", "rho", "aic", "pseudo_r2"]].round(3).to_string(index=False))
    print(f"\nWrote {len(results)} CSVs to outputs/final_synthetic/ (same layout as data/summary/).")


if __name__ == "__main__":
    main()
