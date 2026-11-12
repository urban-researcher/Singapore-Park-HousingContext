import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

class ST_DBSCAN:
    """
    A class to perform ST-DBSCAN clustering on spatio-temporal data.

    ST-DBSCAN (Spatio-Temporal Density-Based Spatial Clustering of Applications with Noise)
    is a clustering algorithm that extends DBSCAN to handle both spatial and temporal dimensions.
    It groups together points that are close in space and time.

    Attributes:
        eps1 (float): The spatial radius (epsilon_1). Defines the search area in spatial dimensions.
        eps2 (int): The temporal radius in seconds (epsilon_2). Defines the search window in the time dimension.
        min_pts (int): The minimum number of points required to form a dense region (a core point).
        cluster_label (int): A counter for assigning unique cluster IDs.
        labels_ (np.array): An array to store the cluster label for each data point.
    """
    def __init__(self, eps1=0.01, eps2=60, min_pts=5):
        """
        Initializes the ST_DBSCAN instance with specified parameters.

        Args:
            eps1 (float): Spatial distance threshold. For GPS data (lat/lon), this is
                          typically in degrees. 1 degree is ~111km. So 0.01 is ~1.11km.
                          You should adjust this based on your data's scale.
            eps2 (int): Temporal distance threshold in seconds.
            min_pts (int): Minimum number of neighbors to be a core point.
        """
        self.eps1 = eps1
        self.eps2 = eps2
        self.min_pts = min_pts
        self.cluster_label = 0
        self.labels_ = None

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculates the Haversine distance between two points on Earth.
        Note: For performance on large datasets, a simpler Euclidean distance on projected
        coordinates might be faster, but Haversine is more accurate for lat/lon.
        This implementation uses a simplified Euclidean distance for speed, assuming
        small distances where the Earth's curvature has a minor effect.
        A more accurate conversion to meters would involve libraries like `geopy`.
        """
        # For simplicity and speed, we use Euclidean distance on degrees.
        # This is a reasonable approximation for small areas.
        return np.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)


    def _get_neighbors(self, index, X, X_time):
        """
        Finds all neighbors of a given point within the spatial and temporal thresholds.

        Args:
            index (int): The index of the point for which to find neighbors.
            X (np.array): The spatial data (e.g., [latitude, longitude]).
            X_time (pd.Series): The temporal data (timestamps).

        Returns:
            list: A list of indices of the neighboring points.
        """
        neighbors = []
        center_point = X[index]
        center_time = X_time.iloc[index]

        # Filter by temporal neighborhood first for efficiency
        time_diff = (X_time - center_time).abs()
        possible_neighbors_indices = time_diff[time_diff <= timedelta(seconds=self.eps2)].index

        # Filter by spatial neighborhood
        for i in possible_neighbors_indices:
            if i == index:
                continue # Don't include the point itself

            dist = self._haversine_distance(center_point[0], center_point[1], X[i, 0], X[i, 1])
            if dist <= self.eps1:
                neighbors.append(i)
        
        return neighbors

    def fit(self, df):
        """
        Performs ST-DBSCAN clustering on the provided DataFrame.

        Args:
            df (pd.DataFrame): A DataFrame with 'latitude', 'longitude', and 'timestamp' columns.
                               The 'timestamp' column must be of a datetime type.
        """
        # Extract spatial and temporal data
        X = df[['latitude', 'longitude']].values
        X_time = df['timestamp']
        n_points = X.shape[0]

        # Initialize labels: 0 for unvisited, -1 for noise
        self.labels_ = np.zeros(n_points, dtype=int)

        # Iterate through each point
        for i in range(n_points):
            if self.labels_[i] != 0:  # If point has already been visited/classified
                continue

            # Find neighbors for the current point
            neighbors = self._get_neighbors(i, X, X_time)

            if len(neighbors) < self.min_pts:
                # This point is currently considered noise
                self.labels_[i] = -1
            else:
                # This is a core point, start a new cluster
                self.cluster_label += 1
                self._expand_cluster(i, neighbors, X, X_time)
        
        # Add labels back to the DataFrame for convenience
        df['cluster'] = self.labels_
        return df

    def _expand_cluster(self, index, neighbors, X, X_time):
        """
        Expands a cluster from a core point by recursively finding all density-reachable points.

        Args:
            index (int): The index of the core point starting the cluster.
            neighbors (list): The list of neighbors of the core point.
            X (np.array): The spatial data.
            X_time (pd.Series): The temporal data.
        """
        # Assign current point to the new cluster
        self.labels_[index] = self.cluster_label
        
        # Use a queue to process neighbors
        i = 0
        while i < len(neighbors):
            neighbor_index = neighbors[i]

            if self.labels_[neighbor_index] == -1: # It was noise, now it's a border point
                self.labels_[neighbor_index] = self.cluster_label
            
            elif self.labels_[neighbor_index] == 0: # It's an unvisited point
                self.labels_[neighbor_index] = self.cluster_label
                
                # Find its neighbors to see if it's a core point
                new_neighbors = self._get_neighbors(neighbor_index, X, X_time)
                
                if len(new_neighbors) >= self.min_pts:
                    # It is a core point, add its neighbors to the queue
                    neighbors.extend(new_neighbors)
            
            i += 1


def generate_sample_data():
    """
    Generates a sample DataFrame with spatio-temporal clusters and noise.
    
    Returns:
        pd.DataFrame: A DataFrame with 'latitude', 'longitude', and 'timestamp' columns.
    """
    # Cluster 1: Office location
    c1_lat = np.random.normal(34.05, 0.001, 50)
    c1_lon = np.random.normal(-118.25, 0.001, 50)
    c1_time = pd.to_datetime('2025-06-26 09:00:00') + pd.to_timedelta(np.random.randint(0, 120, 50), unit='m')

    # Cluster 2: Home location
    c2_lat = np.random.normal(34.15, 0.001, 50)
    c2_lon = np.random.normal(-118.45, 0.001, 50)
    c2_time = pd.to_datetime('2025-06-26 19:00:00') + pd.to_timedelta(np.random.randint(0, 120, 50), unit='m')
    
    # Cluster 3: Cafe stop (shorter duration)
    c3_lat = np.random.normal(34.08, 0.001, 20)
    c3_lon = np.random.normal(-118.35, 0.001, 20)
    c3_time = pd.to_datetime('2025-06-26 13:00:00') + pd.to_timedelta(np.random.randint(0, 20, 20), unit='m')

    # Noise points
    noise_lat = np.random.uniform(34.0, 34.2, 30)
    noise_lon = np.random.uniform(-118.5, -118.2, 30)
    noise_time_base = pd.to_datetime('2025-06-26 00:00:00')
    noise_time = noise_time_base + pd.to_timedelta(np.random.randint(0, 24*60, 30), unit='m')

    # Combine into a DataFrame
    lat = np.concatenate([c1_lat, c2_lat, c3_lat, noise_lat])
    lon = np.concatenate([c1_lon, c2_lon, c3_lon, noise_lon])
    time = np.concatenate([c1_time, c2_time, c3_time, noise_time])
    
    df = pd.DataFrame({'latitude': lat, 'longitude': lon, 'timestamp': time})
    df = df.sort_values(by='timestamp').reset_index(drop=True)
    
    return df


def plot_clusters(df):
    """
    Plots the clustered data points on a 2D scatter plot.

    Args:
        df (pd.DataFrame): DataFrame with 'latitude', 'longitude', and 'cluster' columns.
    """
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Get unique cluster labels
    labels = df['cluster'].unique()
    
    # Define colors, ensuring noise (-1) is black
    colors = plt.cm.viridis(np.linspace(0, 1, len(labels)))
    
    for cluster_label in labels:
        cluster_data = df[df['cluster'] == cluster_label]
        
        if cluster_label == -1:
            # Noise points are black and smaller
            ax.scatter(cluster_data['longitude'], cluster_data['latitude'],
                       c='black', label='Noise', s=20, alpha=0.5)
        else:
            # Cluster points are colored
            ax.scatter(cluster_data['longitude'], cluster_data['latitude'],
                       c=[colors[cluster_label % len(colors)]], label=f'Cluster {cluster_label}', s=50)

    ax.set_title('ST-DBSCAN Clustering Results', fontsize=16)
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.legend()
    ax.grid(True)
    plt.show()


if __name__ == '__main__':
    # 1. Generate sample data
    print("Generating sample spatio-temporal data...")
    data = generate_sample_data()
    print(f"Generated {len(data)} data points.")
    print(data.head())
    
    # 2. Set ST-DBSCAN parameters
    # eps1: A value of 0.01 degrees is approx 1.11 km. Let's use something smaller.
    # We'll set it to capture points within about 200m of each other. 0.002 degrees ~ 222m
    spatial_threshold = 0.002 
    # eps2: Time in seconds. Let's say 30 minutes (1800 seconds)
    temporal_threshold = 1800 
    # min_pts: Minimum number of points to form a cluster
    min_points = 10
    
    print("\nInitializing ST-DBSCAN...")
    print(f"  - Spatial Threshold (eps1): {spatial_threshold} degrees")
    print(f"  - Temporal Threshold (eps2): {temporal_threshold} seconds")
    print(f"  - Minimum Points (min_pts): {min_points}")
    
    # 3. Initialize and run the algorithm
    st_dbscan = ST_DBSCAN(eps1=spatial_threshold, eps2=temporal_threshold, min_pts=min_points)
    
    print("\nFitting the model...")
    clustered_data = st_dbscan.fit(data)
    print("Clustering complete.")
    
    # 4. Display results
    print("\nClustering Results:")
    print(clustered_data['cluster'].value_counts())
    
    # 5. Plot the results
    print("\nPlotting clusters...")
    plot_clusters(clustered_data)
