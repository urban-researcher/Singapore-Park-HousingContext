"""Execute sanitized model code on synthetic data, or an explicitly supplied private input."""
import argparse
import json
import os
from pathlib import Path
import matplotlib
matplotlib.use('Agg')

ROOT = Path(__file__).resolve().parents[1]
MODELS = ['spatialautocorrelation_test', 'pooled_ols_estimates', 'jurong_spatial_lag_models']

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model', choices=MODELS + ['all'], default='all')
    p.add_argument('--data', type=Path, help='Explicit authorized model input; omitted = synthetic')
    p.add_argument('--output', type=Path, help='Required external private directory when --data is used')
    args = p.parse_args()
    if args.data:
        if not args.output or args.output.resolve().is_relative_to(ROOT):
            p.error('--data requires --output outside this Public folder to keep real predictions private')
        if not args.data.is_file():
            p.error('Input file does not exist')
    data = args.data.resolve() if args.data else ROOT/'data/synthetic/model_cells.geojson'
    output = args.output.resolve() if args.output else ROOT/'outputs/synthetic'
    os.environ.update(UFUG_PUBLIC_ROOT=str(ROOT), UFUG_MODEL_DATA=str(data), UFUG_OUTPUT_ROOT=str(output))
    # Override inherited paths deliberately; never auto-discover private source data.
    for name in MODELS if args.model == 'all' else [args.model]:
        if args.data and (output / name).resolve().is_relative_to(ROOT):
            p.error('A model output directory resolves inside Public; remove the redirect or use another private output directory')
        nb = json.loads((ROOT/'code/models'/f'{name}.ipynb').read_text(encoding='utf-8'))
        code = '\n\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code')
        print('Running', name, 'on', 'AUTHORIZED INPUT' if args.data else 'SYNTHETIC DATA')
        exec(compile(code, name, 'exec'), {'__name__':'__main__'})
    print('Completed. Synthetic runs are demonstrations. Exact paper reproduction additionally requires the documented sample, variable and scaling conventions.')

if __name__ == '__main__':
    main()
