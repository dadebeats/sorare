import os
import pandas as pd
import numpy as np
from docutils.nodes import date
import pickle

from utils import get_card_prices_for_each_player
from time import time


def get_row_for_each_target():
    return None


def filter_league_stats(df, *, team_name=None, date_before=None, date_after=None):
    filtered = df
    home = "HomeTeam"
    away = "AwayTeam"
    if team_name is not None:
        filtered = filtered[((filtered[home] == team_name) | (filtered[away] == team_name))]
    if date_before is not None:
        filtered = filtered[filtered.index < date_before]
    if date_after is not None:
        filtered = filtered[filtered.index > date_after]
    return filtered


def build_league_stats(df, date_before, date_after):
    relevant_stats = filter_league_stats(df, date_before=date_before, date_after=date_after)
    home_col_name = "HomeTeam"
    away_col_name = "AwayTeam"
    result_col_name = "FTR"
    away_goals_col_name = "FTAG"
    home_goals_col_name = "FTHG"

    teams = {team for team in relevant_stats[home_col_name]}.union({team for team in relevant_stats[away_col_name]})
    table = {}
    for team in teams:
        team_stats = {}

        def count_stat(df, team, statname):
            if statname == "win":
                home_wins = len(df[(df[home_col_name] == team) & (df[result_col_name] == "H")].index)
                away_wins = len(df[(df[away_col_name] == team) & (df[result_col_name] == "A")].index)
                return home_wins + away_wins
            elif statname == "loses":
                home_losses = len(df[(df[home_col_name] == team) & (df[result_col_name] == "A")].index)
                away_losses = len(df[(df[away_col_name] == team) & (df[result_col_name] == "H")].index)
                return home_losses + away_losses
            elif statname == "draws":
                home_draws = len(df[(df[home_col_name] == team) & (df[result_col_name] == "D")].index)
                away_draws = len(df[(df[away_col_name] == team) & (df[result_col_name] == "D")].index)
                return home_draws + away_draws
            elif statname == "gc":
                home_gc = df[(df[home_col_name] == team)][
                    away_goals_col_name].sum()  # TODO: zcheckovat jestli tohle opravud vraci jen 1 cislo
                away_gc = df[(df[away_col_name] == team)][home_goals_col_name].sum()
                return home_gc + away_gc
            elif statname == "gs":
                home_gs = df[(df[home_col_name] == team)][home_goals_col_name].sum()
                away_gs = df[(df[away_col_name] == team)][away_goals_col_name].sum()
                return home_gs + away_gs

        team_stats["wins"] = count_stat(relevant_stats, team, "win")
        team_stats["points"] = team_stats["wins"] * 3
        team_stats["loses"] = count_stat(relevant_stats, team, "loses")
        team_stats["draws"] = count_stat(relevant_stats, team, "draws")
        team_stats["goals_conceded"] = count_stat(relevant_stats, team, "gc")
        team_stats["goals_scored"] = count_stat(relevant_stats, team, "gs")

        table[team] = team_stats

    return pd.DataFrame(table)


def get_features_for_pump(data_pumpu, n=15):
    features_ktery_muzou_za_pump = None
    return features_ktery_muzou_za_pump[:n]


# kdyz robo stoji 0.2 v liverpoolu, tak ho chceme detekovat
def get_cluster_info(players_data, main_feature, top_percentage):
    # vybrat z cluster top % podle urcite feature
    # udela average pres nejakou feature
    # TODO: vybrat clustering algo + metriku
    def form_clusters(players_data, irl=True):
        """

        :param players_data:
        :param irl: whether to consider irl stats for clustering or sorare
        :return:
        """
        pass


def get_league_table(league_tables, league_stats, league_name, date_of_game, last_season_start):
    """
    Dynamic programming. Caching already computed tables.
    :param league_tables:
    :param league_stats:
    :param league_name:
    :param date_of_game:
    :param last_season_start:
    :return:
    """
    if league_tables[league_name].get(date_of_game) is None:
        table = build_league_stats(league_stats, date_before=date_of_game, date_after=last_season_start)
        league_tables[league_name][date_of_game] = table
        return table
    else:
        return league_tables[league_name][date_of_game]


def get_row_and_update_col_names(team_games_before_date, games_stats_before_date, league_table, simple, player_slug,
                                 team_name, enemy_team_name, col_names):
    if "Season" in team_games_before_date.columns:
        team_games_before_date.drop(columns=["Season"],inplace=True)

    team_stats_mean = team_games_before_date.mean()
    # TODO: tady bude v dalsich verzich TypeError(protoze jsou tam non numeric cols) -> musim manualne vybrat
    player_stats_mean = games_stats_before_date.mean()
    team_stats_std = team_games_before_date.std()
    player_stats_std = games_stats_before_date.std()
    enemy_team_table_stats = league_table[enemy_team_name]
    team_table_stats = league_table[team_name]
    relevant_cols_from_simple = ["slug", "age", "weight", "height", "position", "country"]
    player_simple_stats = simple[simple["slug"] == player_slug][relevant_cols_from_simple].to_numpy().reshape(
        -1, )

    row = np.hstack((player_simple_stats, team_table_stats.to_numpy(), team_stats_mean.to_numpy(), team_stats_std.to_numpy(),
                     player_stats_mean.to_numpy(), player_stats_std.to_numpy(), enemy_team_table_stats.to_numpy()))

    if col_names.get(len(row)) is None:

        col_names_for_this_row = relevant_cols_from_simple + \
                                 [x + "_mean" for x in list(team_stats_mean.index)] + \
                                 [x + "_mean" for x in list(player_stats_mean.index)] + \
                                 [x + "_std" for x in list(team_stats_std.index)] + \
                                 [x + "_std" for x in list(player_stats_std.index)] + \
                                 [x + "_enemy" for x in list(enemy_team_table_stats.index)] + \
                                 [x + "_our" for x in list(team_table_stats.index)]




        col_names[len(row)] = col_names_for_this_row
    return row


def create_dataset(game_stats, all_leagues_stats, clubs, club_mappings, save_file=False) -> dict:
    """! doxygen  - dozavinacovat

    @param all_leagues_stats: dict of league:dataframe for the league
    @param game_stats: dataframe of game stats for each player,match
    @param save_file: True if save the final dataset as .npy file
    @param clubs:
    @param club_mappings:

    @return: dict with keys: data,target,col_names and values of np.arrays

    """
    # player_prices = get_card_prices_for_each_player("../data/all_cards.json")  # price graph
    simple = pd.read_csv(open("../data/all_players_simple.csv", "r"))

    # print(player_prices)

    cols = game_stats.columns.tolist()
    cols = cols[-5:] + cols[:-5]
    game_stats = game_stats[cols]
    game_stats = game_stats[game_stats["totalScore"] != 0]
    game_stats['date'] = pd.to_datetime(game_stats['date'], format='%Y-%m-%d')
    game_stats.set_index(['date'], inplace=True)

    potential_targets = game_stats["totalScore"].to_numpy()
    game_stats.drop(columns=["gameWeek"], inplace=True)
    data = []

    dropped_data_count = 0
    target = []
    league_tables = {x: {} for x in all_leagues_stats.keys()}
    col_names = {}
    second, row_building, league_building, = 0, 0, 0
    game_stats_groups = game_stats.groupby("slug")
    last_season_start = "2021-7-1"

    def trim_and_group_league_stats(all_league_stats):
        final = {}
        for name,df in all_league_stats.items():
            result = df[df.index > last_season_start]
            result = {"Home":result.groupby("HomeTeam") , "Away":result.groupby("AwayTeam")}
            final[name] = result
        return final

    league_stats_groups = trim_and_group_league_stats(all_leagues_stats)

    for i in range(len(potential_targets)):
        if i % 1000 == 0:
            print(i, row_building, league_building, second)

        player_slug = game_stats.iloc[i].slug
        date_of_game = str(game_stats.iloc[i].name.date())
        if len(simple[simple["slug"] == player_slug]["club"].values) != 1:
            dropped_data_count += 1  # TODO: hrac, ktery ma zapas za nejaky klub, ale uz z nej odesel -> nenajdu ten klub v simple datech
            continue

        club_slug = simple[simple["slug"] == player_slug]["club"].values[0]

        club_competitions = next(club["activeCompetitions"]
                                 for club in clubs["data"]["clubsReady"] if club["slug"] == club_slug)

        league_name_in_stats_list = [path for comp in club_competitions for path in all_leagues_stats.keys() if
                                     comp["slug"] in path]
        if not league_name_in_stats_list:
            # print("Don't have stats for any of these leagues:",club_competitions)
            dropped_data_count += 1
            continue
            #   TODO: nejak vyhandlovat co udelat, kdyz nebudeou stats

        league_name_in_stats = league_name_in_stats_list[0]
        league_stats = all_leagues_stats[league_name_in_stats]

        if date_of_game not in league_stats.index:
            # print("chybí zápas v datu:", date_of_game)
            dropped_data_count += 1
            continue  # TODO: downloadnout data, vzdy by mela byt

        home_col_name = "HomeTeam"
        away_col_name = "AwayTeam"

        team_name = club_mappings.get(club_slug)
        if team_name is None:
            dropped_data_count += 1
            continue

        players_games = game_stats_groups.get_group(player_slug)
        player_games_stats_before_date = players_games[players_games.index < date_of_game]
        if player_games_stats_before_date.empty:
            # TODO: CO DĚLAT KDYŽ HRÁČ NEMÁ ŽÁDNÉ PŘEDCHOZÍ ZÁPASY?
            continue

        start = time()
        """
        home_games = league_stats_groups[league_name_in_stats]["Home"].get_group(team_name)
        home_games_before_date = home_games[home_games.index < date_of_game]
        away_games = league_stats_groups[league_name_in_stats]["Away"].get_group(team_name)
        away_games_before_date = away_games[away_games.index <date_of_game]
        team_games_before_date = pd.concat([home_games_before_date,away_games_before_date])
        """

        team_games_before_date = filter_league_stats(league_stats,team_name=team_name,date_before=date_of_game,date_after=last_season_start)

        end = time()

        second += end - start

        start = time()
        league_table = get_league_table(league_tables, league_stats, league_name_in_stats, date_of_game,
                                        last_season_start)

        current_match = league_stats[(league_stats.index == date_of_game) &
                                     ((league_stats[home_col_name] == team_name) | (
                                             league_stats[away_col_name] == team_name))]
        end = time()
        league_building += end - start

        if len(current_match.index) == 0:
            # TODO: potreba vyresit co delat, kdyz hrac hral ma zapasy, kde hral jeste za jiny tym: Adam montgomery celtic -> aberdeen napr.
            dropped_data_count += 1
            continue

        enemy_team_name = current_match[away_col_name].item() \
            if current_match[home_col_name].item() == team_name \
            else current_match[home_col_name].item()

        if league_table.get(enemy_team_name) is None or league_table.get(team_name) is None:
            # TODO: NASTAva protoze se tymy jmenujou jinak, napr samara se jmenuje: Krylya Sovetov i FK Krylya Sovetov
            dropped_data_count += 1
            continue

        start = time()
        # Data point was valid -> create row and append the target
        row = get_row_and_update_col_names(team_games_before_date, player_games_stats_before_date, league_table, simple,
                                           player_slug, team_name, enemy_team_name, col_names)
        end = time()
        row_building += end - start
        data.append(row)
        target.append(potential_targets[i])

    print(dropped_data_count / len(potential_targets))

    if save_file:
        np.save(open("dataset/data.npy", "wb"), np.array(data))
        np.save(open("dataset/target.npy", "wb"), target)
        pickle.dump(col_names,open("dataset/col_names", "wb"))

    return {"data": data, "target": np.array(target), "col_names": col_names}
