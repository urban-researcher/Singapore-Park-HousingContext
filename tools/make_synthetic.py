"""Generate wholly artificial values and geometry; never reads study data."""
from pathlib import Path
import numpy as np
import geopandas as gpd
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]

def main():
    rng = np.random.default_rng(20261108)
    rows = []
    predictors = ['ps', 'pl', 'pb', 'pm', 'peg', 'peo', 'pep', 'peps', 'per', 'pepw', 'set']
    for k, park in enumerate(['amk', 'jurong', 'punggol']):
        for i in range(64):
            x, y = i % 8, i // 8
            row = dict(zip(predictors, rng.uniform(0.2, 3, len(predictors))))
            frequency = int(rng.poisson(np.exp(0.4 + 0.2 * row['peps'] + 0.06*x)))
            row.update(grid_id=i, park=park, F_h=frequency,
                       D_h=float(frequency*rng.uniform(10, 70)),
                       geometry=box(k*2000+x*100, y*100, k*2000+(x+1)*100, (y+1)*100))
            rows.append(row)
    path = ROOT/'data/synthetic/model_cells.geojson'
    gpd.GeoDataFrame(rows, crs='EPSG:3414').to_file(path, driver='GeoJSON', index=False)
    print('Wrote 192 SYNTHETIC square cells; no actual park locations or observations:', path.name)

if __name__ == '__main__':
    main()
