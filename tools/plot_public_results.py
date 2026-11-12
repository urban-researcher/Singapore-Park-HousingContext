"""Chart the released Jurong spatial lag coefficients (Table 5, revised analysis) with 95% intervals; not a model refit.

Table 5 predictors are standardized within Jurong Lake Gardens, so coefficients are on a common per-SD scale.
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
LABELS = {'pep': 'Park furniture', 'peps': 'Park services within 500 m', 'ps': 'Perceived safety', 'pl': 'Perceived liveliness',
          'pb': 'Perceived beauty', 'pm': 'Perceived monotony', 'peg': 'Greenness', 'peo': 'Openness',
          'per': 'Internal road connectivity', 'pepw': 'Proximity to water', 'set': 'Proximity to MRT (inverse walking distance)'}


def main():
    df = pd.read_csv(ROOT/'data/summary/table5_jurong_slm.csv').query("variant == 'excl_closed' and term in @LABELS")
    fig, ax = plt.subplots(figsize=(9, 6))
    y = np.arange(len(LABELS))
    for j, (outcome, name) in enumerate([('Frequency', 'log(F_h + 1)'), ('Duration', 'log(D_h + 1), cumulative dwell time')]):
        sub = df[df.outcome == outcome].set_index('term').loc[list(LABELS)]
        ax.errorbar(sub.estimate, y + (j - .5) * .25, xerr=1.96 * sub.se, fmt='o', capsize=3, label=name)
    ax.set_yticks(y, list(LABELS.values()))
    ax.invert_yaxis()
    ax.axvline(0, color='grey', lw=1)
    ax.set_xlabel('Coefficient per predictor SD (95% interval)')
    ax.set_title('Released Jurong spatial lag model, revised analysis (not refitted)')
    ax.legend(loc='lower left')
    fig.tight_layout()
    out = ROOT/'outputs/public_results'
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out/'jurong_slm_coefficients.png', dpi=180)
    print('Created outputs/public_results/jurong_slm_coefficients.png')


if __name__ == '__main__':
    main()
