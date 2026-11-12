import numpy as np
import polars as pl
import matplotlib.pyplot as plt

class ST_DBSCAN:
    """
    Spatio-temporal DBSCAN for data with latitude, longitude, and timestamp.
    Uses Euclidean distance on degrees for speed and epoch seconds for time.
    """

    def __init__(self, eps1=0.01, eps2=60, min_pts=5):
        self.eps1 = float(eps1)          # spatial threshold in degrees
        self.eps2 = int(eps2)            # temporal threshold in seconds
        self.min_pts = int(min_pts)
        self.cluster_label = 0
        self.labels_ = None

    @staticmethod
    def _euclidean_deg(lat1, lon1, lat2, lon2):
        return np.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)

    def _get_neighbors(self, index, X, tsec):
        """
        Return indices of neighbours within eps1 (space) and eps2 (time).
        X: np.ndarray of shape (n, 2) with [lat, lon]
        tsec: np.ndarray of epoch seconds (int64) per row
        """
        neighbours = []
        clat, clon = X[index]
        ct = tsec[index]

        # temporal filter first
        time_mask = np.abs(tsec - ct) <= self.eps2
        candidate_idx = np.nonzero(time_mask)[0]

        # spatial check
        for i in candidate_idx:
            if i == index:
                continue
            d = self._euclidean_deg(clat, clon, X[i, 0], X[i, 1])
            if d <= self.eps1:
                neighbours.append(i)
        return neighbours

    def fit(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        df must have columns: 'latitude' (f64), 'longitude' (f64), 'timestamp' (Datetime)
        Returns a new DataFrame with a 'cluster' column of ints (-1 = noise).
        """
        # Ensure expected dtypes
        if df.schema.get('timestamp') != pl.Datetime:
            df = df.with_columns(pl.col('timestamp').cast(pl.Datetime))

        X = df.select(['latitude', 'longitude']).to_numpy()
        # epoch seconds from polars datetime (datetime is microseconds internally)
        tsec = df.select(pl.col('timestamp').dt.epoch('s')).to_numpy().reshape(-1).astype(np.int64)

        n = X.shape[0]
        self.labels_ = np.zeros(n, dtype=np.int64)  # 0 = unvisited, -1 = noise

        for i in range(n):
            if self.labels_[i] != 0:
                continue

            neighbours = self._get_neighbors(i, X, tsec)

            if len(neighbours) < self.min_pts:
                self.labels_[i] = -1
            else:
                self.cluster_label += 1
                self._expand_cluster(i, neighbours, X, tsec)

        # attach labels
        out = df.with_columns(pl.Series('cluster', self.labels_))
        return out

    def _expand_cluster(self, index, neighbours, X, tsec):
        self.labels_[index] = self.cluster_label

        i = 0
        while i < len(neighbours):
            nb = neighbours[i]

            if self.labels_[nb] == -1:
                self.labels_[nb] = self.cluster_label
            elif self.labels_[nb] == 0:
                self.labels_[nb] = self.cluster_label
                new_nb = self._get_neighbors(nb, X, tsec)
                if len(new_nb) >= self.min_pts:
                    neighbours.extend(new_nb)
            i += 1


def generate_sample_data() -> pl.DataFrame:
    """
    Build a synthetic spatio-temporal dataset as a Polars DataFrame.
    """
    rng = np.random.default_rng()

    def block(lat_mu, lon_mu, n, base_iso, max_minutes):
        lat = rng.normal(lat_mu, 0.001, n)
        lon = rng.normal(lon_mu, 0.001, n)
        base = np.datetime64(base_iso)
        offsets = rng.integers(0, max_minutes, n).astype('timedelta64[m]')
        ts = base + offsets
        return lat, lon, ts

    # clusters
    c1_lat, c1_lon, c1_ts = block(34.05, -118.25, 50, '2025-06-26T09:00:00', 120)
    c2_lat, c2_lon, c2_ts = block(34.15, -118.45, 50, '2025-06-26T19:00:00', 120)
    c3_lat, c3_lon, c3_ts = block(34.08, -118.35, 20, '2025-06-26T13:00:00', 20)

    # noise
    noise_lat = rng.uniform(34.0, 34.2, 30)
    noise_lon = rng.uniform(-118.5, -118.2, 30)
    noise_base = np.datetime64('2025-06-26T00:00:00')
    noise_offsets = rng.integers(0, 24 * 60, 30).astype('timedelta64[m]')
    noise_ts = noise_base + noise_offsets

    lat = np.concatenate([c1_lat, c2_lat, c3_lat, noise_lat])
    lon = np.concatenate([c1_lon, c2_lon, c3_lon, noise_lon])
    ts = np.concatenate([c1_ts, c2_ts, c3_ts, noise_ts])

    # Convert numpy datetime64 to microseconds (Polars default) then to Datetime
    ts_us = ts.astype('datetime64[us]')

    df = pl.DataFrame({
        'latitude': lat,
        'longitude': lon,
        'timestamp': pl.Series(ts_us).cast(pl.Datetime),
    }).sort('timestamp')

    return df


def plot_clusters(df: pl.DataFrame):
    """
    Scatter plot of clusters. Converts to NumPy for plotting.
    """
    fig, ax = plt.subplots(figsize=(12, 10))

    labels = df.get_column('cluster').to_numpy()
    unique_labels = np.unique(labels)

    # colour map for clusters (noise in black)
    colours = plt.cm.viridis(np.linspace(0, 1, max(1, len(unique_labels) - (1 if -1 in unique_labels else 0))))

    # map cluster id -> colour index (skip noise)
    colour_map = {}
    cidx = 0
    for cl in unique_labels:
        if cl == -1:
            continue
        colour_map[cl] = colours[cidx % len(colours)]
        cidx += 1

    for cl in unique_labels:
        mask = labels == cl
        xs = df.filter(mask).get_column('longitude').to_numpy()
        ys = df.filter(mask).get_column('latitude').to_numpy()

        if cl == -1:
            ax.scatter(xs, ys, c='black', label='Noise', s=20, alpha=0.5)
        else:
            ax.scatter(xs, ys, c=[colour_map[cl]], label=f'Cluster {cl}', s=50)

    ax.set_title('ST-DBSCAN Clustering Results', fontsize=16)
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.legend()
    ax.grid(True)
    plt.show()


if __name__ == '__main__':
    print("Generating sample spatio-temporal data...")
    data = generate_sample_data()
    print(f"Generated {data.height} data points.")
    print(data.head(5))

    spatial_threshold = 0.002   # ~200m in degrees
    temporal_threshold = 1800   # 30 minutes in seconds
    min_points = 10

    print("\\nInitializing ST-DBSCAN...")
    print(f"  - Spatial Threshold (eps1): {spatial_threshold} degrees")
    print(f"  - Temporal Threshold (eps2): {temporal_threshold} seconds")
    print(f"  - Minimum Points (min_pts): {min_points}")

    st_dbscan = ST_DBSCAN(eps1=spatial_threshold, eps2=temporal_threshold, min_pts=min_points)

    print("\\nFitting the model...")
    clustered = st_dbscan.fit(data)
    print("Clustering complete.")

    print("\\nClustering Results:")
    # count clusters
    labels, counts = np.unique(clustered.get_column('cluster').to_numpy(), return_counts=True)
    for l, c in zip(labels, counts):
        print(f"Cluster {l}: {c} points")

    print("\\nPlotting clusters...")
    plot_clusters(clustered)