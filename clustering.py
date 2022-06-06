import argparse

import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

# Cluster the data from a fantasy football game (sorare.com)

parser = argparse.ArgumentParser()
parser.add_argument("--n_clusters", default=15, type=int, help="Number of clusters")


def prepare_df(df):
    cols = [0, 1, 2, 8, 13]
    df.drop(df.columns[cols], axis=1, inplace=True)
    df.fillna(0, inplace=True)


def main(args: argparse.Namespace):
    # Prepare the data
    df = pd.read_csv("../data/all_players_simple.csv")

    prepare_df(df)

    # Run the KMeans algo
    n_clusters = args.n_clusters
    kmeans = KMeans(n_clusters=n_clusters)
    kmeans.fit(df)
    y_kmeans = kmeans.predict(df)
    centers = kmeans.cluster_centers_

    # Choose 2 of the most important features using PCA to graph the cluster centers
    pca = PCA(n_components=13)
    pca.fit(df)

    first_component_name = df.columns[list(pca.components_[0]).index(max(abs(pca.components_[0])))]
    second_component_name = df.columns[list(pca.components_[1]).index(max(abs(pca.components_[1])))]
    # PCA chose subs (which is a players popularity) and limited (number of copies of the players card) as the most important features
    X_pca = pca.transform(df)

    # Graph the cluster centers inside the data transformed by PCA
    centers_pca = pca.transform(centers)
    plt.scatter(X_pca[:, 0], X_pca[:, 1], c=y_kmeans, s=10, cmap='viridis')
    plt.xlabel(first_component_name)
    plt.ylabel(second_component_name)
    plt.title('PCA with {} clusters'.format(n_clusters))

    plt.scatter(centers_pca[:, 0], centers_pca[:, 1], c='black', s=200, alpha=0.5)
    plt.show()


if __name__ == "__main__":
    args = parser.parse_args([] if "__file__" not in globals() else None)
    main(args)
