import argparse
import json

import pandas as pd
import numpy as np
import pickle

from utils import get_games_dataframe, get_league_stats_dataframes
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.linear_model import RidgeCV

import sklearn.datasets
import sklearn.model_selection
from  sklearn.pipeline import Pipeline

from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import PolynomialFeatures
from sklearn.compose import ColumnTransformer
from create_dataset import create_dataset
parser = argparse.ArgumentParser()
parser.add_argument("dataset_created",default=0, type=int) #TODO: naucit se jak parsovat bool, misto pouzivani intu
parser.add_argument("games_df_created",default=0, type=int)



def main(args: argparse.Namespace):
    # scores graph
    if args.games_df_created:
        game_stats = pd.read_csv(open("../data/game_stats.csv","r"))
    else:
        game_stats = get_games_dataframe("../data/all_players.json")
        game_stats.to_csv("../data/game_stats.csv",index=False)


    if args.dataset_created:
        data, target, col_names = np.load(open("dataset/data.npy", "rb"),allow_pickle=True), \
                                np.load(open("dataset/target.npy", "rb"),allow_pickle=True), \
                                pickle.load(open("dataset/col_names","rb"))
    else:
        league_stats = get_league_stats_dataframes("../data/league_stats")
        clubs = json.load(open("../data/all_clubs.json"))
        club_mappings = json.load(open("../data/club_names_mapping.json"))
        dataset = create_dataset(game_stats, league_stats,clubs,club_mappings, save_file=True)
        data, target, col_names = dataset["data"], dataset["target"], dataset["col_names"]

    def get_indices(data,length):
        ind = []
        for i,row in enumerate(data):
            if len(row) == length:
                ind.append(i)
        return ind


    group_indices = get_indices(data,322)# take one group of data
    data = [x for x in data[group_indices]]
    target = target[group_indices]


    ohe = OneHotEncoder(sparse=False,handle_unknown="ignore")
    scaler = StandardScaler()
    non_numerical = [316,320,321]
    col_trans = ColumnTransformer(
        [("scaler", scaler, [i for i in range(322) if i not in non_numerical]),
            ("ohe",ohe,non_numerical)
        ]
    )
    pipe = Pipeline([('columnTransformer', col_trans)])
    pipe.fit_transform(data)
    data = col_trans.fit_transform(data)


    t_data = np.array(data,dtype=float)
    ind = np.isnan(t_data)
    t_data[ind] = 0


    model = RidgeCV(normalize=True)
    x_train, x_test, t_train, t_test = train_test_split(t_data, target, train_size=0.93, shuffle=True)
    model.fit(x_train,t_train)
    prediction = model.predict(x_test)
    all_games_avg = 44.19402556157021
    simple_pred = [all_games_avg] * len(prediction)


    print("my prediction:",mean_squared_error(t_test,prediction,squared=False))
    print("predicting the global average:", mean_squared_error(t_test, simple_pred, squared=False))



if __name__ == "__main__":
    args = parser.parse_args([] if "__file__" not in globals() else None)
    pd.set_option('display.max_columns', None)
    main(args)