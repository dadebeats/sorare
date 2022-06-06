import difflib
import itertools
import json
import numpy as np
import csv
import io
import random
import string
import os
import pandas as pd
import re
from json import JSONDecoder, JSONDecodeError


def flatten_json(y):
    out = {}

    def flatten(x, name=''):

        # If the Nested key-value
        # pair is of dict type
        if type(x) is dict:

            for a in x:
                flatten(x[a], name + a + '_')

        # If the Nested key-value
        # pair is of list type
        elif type(x) is list:

            i = 0

            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out


def extract_player_slugs_to_csv(from_filepath, to_filepath):
    # open and iterate over json file, extract player slugs in this case and write them to csv file
    f = open(from_filepath)
    w = open(to_filepath, "w")
    w.write("slugs")
    all_teams = json.load(f)
    all_teams = flatten_json(all_teams)
    for key, playerSlug in all_teams.items():
        w.write("\n" + playerSlug)


def trim_json(from_filepath, to_filepath):
    jsonFile = open(from_filepath, "r")  # Open the JSON file for reading
    data = json.load(jsonFile)  # Read the JSON into the buffer
    jsonFile.close()  # Close the JSON file

    ## Save our changes to JSON file
    jsonFile = open(to_filepath, "w+")
    jsonFile.write(json.dumps(data, indent=False, separators=(',', ':')))

    jsonFile.close()


def decode_stacked(document, pos=0, decoder=JSONDecoder()):
    """
    use as:
    with open("../data/all_cards.json", "r") as data:
    for obj in decode_stacked(data.readlines()[0]):
        print(obj)

    """

    not_whitespace = re.compile(r'[^\s]')
    while True:
        match = not_whitespace.search(document, pos)
        if not match:
            return
        pos = match.start()

        try:
            obj, pos = decoder.raw_decode(document, pos)
        except JSONDecodeError:
            # do something sensible if there's some error
            raise
        yield obj


def extract_data_to_csv(from_filepath, to_filepath_csv):
    # TODO: prepsat tu funkci, je to tezky rozklicovat zpetne, co se tam deje + jsem tam puvodne mel bug, ze jsem nezapisoval posledniho hrace z kazdeho klubu
    input_file = open(from_filepath, "r")
    data = json.load(input_file)
    input_file.close()

    not_simple = ["allSo5Scores"]
    player_stats_count = len(data[0]["club"]["activePlayers"]["nodes"][0]) - len(not_simple)

    out_file_csv = open(to_filepath_csv, "w", newline="")
    csv_writer = csv.writer(out_file_csv, delimiter=',')
    csv_writer.writerow(["slug", "club", "position", "age", "subscriptionsCount", "height", "weight", "appearances",
                         "playingStatus", "lastFiveSo5Appearances", "lastFiveSo5AverageScore",
                         "lastFifteenSo5Appearances",
                         "lastFifteenSo5AverageScore", "country", "limited", "rare", "super_rare", "unique"])

    for club in data:
        players_in_club = club["club"]["activePlayers"]["nodes"]
        csv_ready = [player[stat] for player in players_in_club for stat in player if stat not in not_simple]

        csv_stats = []
        for i in range(len(csv_ready)):
            if i%player_stats_count == 0:
                if csv_ready[i] == "daouda-karamoko-bamba":
                    print("daouda-karamoko-bamba")
            if i % player_stats_count == 1:  # gets the most recent club
                csv_ready[i] = club["club"]["slug"]
            if i % player_stats_count == 8:  # get the so5 stats from playing status
                for stat in csv_ready[i]:
                    csv_stats.append(csv_ready[i][stat])
            if i % player_stats_count == 9:  # get the country code
                csv_ready[i] = csv_ready[i]["code"]
            if i % player_stats_count == 10:
                if len(csv_ready[i]) > 0:  # get the card quantities for each rarity
                    for card_count in csv_ready[i][0]:
                        csv_stats.append(csv_ready[i][0][card_count])
            if i % player_stats_count == 0 and len(csv_stats) != 0:
                csv_writer.writerow(csv_stats)
                csv_stats = [csv_ready[i]]
            elif i % player_stats_count not in [8, 10]:
                csv_stats.append(csv_ready[i])

        if len(csv_stats) != 0:
            csv_writer.writerow(csv_stats)
    out_file_csv.close()


def get_card_prices_for_each_player(all_cards_filepath):
    """

    :param all_cards_filepath: 
    :return: dict where keys are the player's slug and rarity and value is the list of prices for that player slug&rarity.
    """
    with open(all_cards_filepath, "r") as data:
        all_cards = decode_stacked(data.readlines()[0])
    player_prices = {}
    for obj in all_cards:
        page = obj["allCards"]["edges"]
        for x in page:
            card = x["node"]
            if len(card["notContractOwners"]) == 0:
                continue
            transfers = card["notContractOwners"]
            for transfer in transfers:
                if transfer["transferType"] != "reward":

                    slug = card["player"]["slug"]
                    rarity = card["rarity"]
                    price = int(transfer["price"]) / 10e17
                    date = transfer["from"]

                    if slug not in player_prices:
                        player_prices[slug] = {"limited": [], "rare": [], "super_rare": [], "unique": []}

                    player_prices[slug][rarity].append((price, date))
    return player_prices


def get_league_stats_dataframes(filepath_to_folder) -> dict:
    """
    :param filepath_to_folder: folder with stats
    :return: dict where key is the league slug and value is the dataframe
    """
    league_stat_dataframes = {}
    for (dirpath, dirnames, filenames) in os.walk(filepath_to_folder):
        if len(dirnames) == 0:
            for filename in filenames:
                full_path = dirpath + "/" + filename
                df = pd.read_csv(open(full_path, "r"))

                date_format = '%d/%m/%Y' # if filename != "russian-premier-league.csv" else '%m/%d/%Y'
                df['Date'] = pd.to_datetime(df['Date'], format=date_format)
                df.set_index(['Date'], inplace=True)
                league_stat_dataframes[full_path.split("/")[-1].replace(".csv","")] = df
    return league_stat_dataframes


def get_games_dataframe(filepath):
    """
    Creates dataframe of all games by parsing the big json file from sorareAPI.
    :param filepath: path to all_games.json
    :return: dataframe of all games
    """
    data = json.load(open(filepath, "r"))
    games_data = {player["slug"]: player["allSo5Scores"]["nodes"]
                  for x in data
                  for player in x["club"]["activePlayers"]["nodes"]}

    # TODO: moznost nenacitat cely slovnik, ale streamovat hrace po hraci
    slugs, gws, dates, total_scores, decisive_scores, all_arounds, positives, negatives = ([] for _ in range(8))

    stat_names = list({stat["stat"] for player in games_data for game in games_data[player] for stat in
                       game["allAroundStats"]})
    positive_names = list({stat["stat"] for player in games_data for game in games_data[player] for stat in
                           game["positiveDecisiveStats"]})
    negative_names = list({stat["stat"] for player in games_data for game in games_data[player] for stat in
                           game["negativeDecisiveStats"]})

    for player in games_data:
        for game in games_data[player]:
            slugs.append(player)
            if game["game"]["so5Fixture"] is None:
                gws.append(None)
            else:
                gws.append(game["game"]["so5Fixture"]["gameWeek"])
            dates.append(game["game"]["date"])
            score = game.get("score", 0)
            if score is not None:
                total_scores.append(score)
            else:
                total_scores.append(0)
            decisive_scores.append(game["decisiveScore"]["totalScore"])

            def get_stats_from_nested(stats_type, stats):
                """

                :param stats_type: type of the stats - enum
                :param stats: set of stat names - set
                :return: vector of stats for a given stat type
                """
                if len(game[stats_type]) == 0:
                    return [0 for _ in stats]
                res = []
                for stat in stats:
                    dict_with_stat = next((item for item in game[stats_type] if item["stat"] == stat), None)
                    if dict_with_stat is None:
                        stat_value = 0
                    else:
                        stat_value = dict_with_stat["statValue"]
                    res.append(stat_value)
                return res

            all_arounds.append(get_stats_from_nested("allAroundStats", stat_names))
            positives.append(get_stats_from_nested("positiveDecisiveStats", positive_names))
            negatives.append(get_stats_from_nested("negativeDecisiveStats", negative_names))

    col_names = ["slug", "gameWeek", "date", "totalScore", "decisiveScore"]
    simple_data = [slugs, gws, dates, total_scores, decisive_scores]

    dict_of_simple_cols = {name: pd.Series(simple_data[i])
                           for i, name in enumerate(col_names)}
    dict_of_stat_cols = {name: pd.Series([x[i] for x in all_arounds])
                         for i, name in enumerate(stat_names)}
    dict_of_positive_cols = {name: pd.Series([x[i] for x in positives])
                             for i, name in enumerate(positive_names)}
    dict_of_negative_cols = {name: pd.Series([x[i] for x in negatives])
                             for i, name in enumerate(negative_names)}

    joined_dicts = dict_of_negative_cols | dict_of_positive_cols | dict_of_stat_cols | dict_of_simple_cols

    return pd.DataFrame(joined_dicts)


def get_all_clubs_mapping(all_clubs,league_stats):
    """ funkce neni schopna poznat vse (napr nedava atletico-madrid-madrid na Ath Madrid, je nutne vysledek manualne doupravit
    @param all_clubs: all clubs that are inside the stat files
    @param league_stats: df with stats for matches
    :return: dict of slug:name in stat file
    """

    def get_close_matches(slug,set_of_clubs,delim):
        parts = slug.split(delim)
        final_club = ""
        max_so_far = 0
        for club in set_of_clubs:
            counter = 0
            for part in parts:
                if part in club.lower().split():
                    counter += 1
            if counter > max_so_far:
                final_club = club
                max_so_far = counter
        return final_club

    all_club_names = set()
    for df in league_stats.values():
        all_club_names.update(set(df.HomeTeam))
        all_club_names.update(set(df.AwayTeam))

    final = {}
    for club in all_clubs["data"]["clubsReady"]:
        club_slug = club["slug"]
        club_name = club["name"]
        match1 = get_close_matches(club_slug,all_club_names,"-")
        match2 = get_close_matches(club_name,all_club_names," ")
        if match1:
            final[club_slug] = match1
        elif match2:
            final[club_name] = match2
        else:
            print(club_slug,club_name)


    #region manuální oprava:
    final["incheon-united-incheon"] = final["jeju-united-seogwipo-jeju-do"] = ""
    final["sj-earthquakes-santa-clara-california"] = "San Jose Earthquakes"
    final["spartak-moskva-moskva"] = "Spartak Moscow"
    final["sporting-cp-lisboa"] = "Sp Lisbon"
    final["real-sociedad-donostia-san-sebastian"] = "Sociedad"
    final["real-betis-sevilla"] = "Betis"
    final["rayo-vallecano-madrid"] = "Vallecano"
    final["new-york-rb-secaucus-new-jersey"] = "New York Red Bulls"
    final["newell-s-old-boys-rosario-santa-fe"] = "Newells Old Boys"
    final["istanbul-basaksehir-istanbul"] = "Buyuksehyr"
    final["internazionale-milano"] = "Inter"
    final["hertha-bsc-berlin"] = "Hertha"
    final["goztepe-izmir"] = "Goztep"
    final["gimnasia-la-plata-la-plata-provincia-de-buenos-aires"] = "Gimnasia L.P."
    final["espanyol-barcelona"] = "Espanol"
    final["celta-de-vigo-vigo"] = "Celta"
    final["borussia-m-gladbach-monchengladbach"] = "M'gladbach"
    final["atletico-madrid-madrid"] = "Ath Madrid"
    final["athletic-club-bilbao"] = "Ath Bilbao"
    final["atletico-mineiro-belo-horizonte-minas-gerais"] = "Atletico-MG"
    #endregion

    return final

def standardize_csv_format(filepath_to_folder):
    """!
    Function that takes all csvs, that don't match the standard format and standardizes them
    @param filepath_to_folder:
    """
    # TODO: rozsirit na to, ze funkce jeste prejmenuje files na slugs jednotlivych lig e.g. JPN -> j1-league
    for (dirpath, dirnames, filenames) in os.walk(filepath_to_folder):
        for filename in filenames:
            path = dirpath + "/" + filename
            with open(path,"r+") as file:
                first_line = file.readline()
                if all(  w in first_line for w in ["HomeTeam", "AwayTeam","FTHG","FTAG","FTR"]):
                    # skip file if it has already been standardized
                    continue

                first_line = first_line.replace("Home","HomeTeam").replace("Away","AwayTeam").replace("HG","FTHG").replace("AG","FTAG").replace("Res","FTR")

                rest = file.read()
                file.seek(0)
                file.write(first_line+rest)
                file.truncate()


def delete_last_comma():
    faulty_files = ["../data/league_stats/21_22/jupiler-pro-league.csv"]

    for path in faulty_files:
        lines = ""
        with open(path, "r+") as file:
            for line in file.readlines():
                line = line[:-2]
                lines += line +"\n"


            file.seek(0)
            file.write(lines)
            file.truncate()

def main():
    # z dictionary vyrobit dataframe:
    # chci jeden dataframe radek pro jednu hru pro jednoho hrace, kde bude:
    # jmeno hrace, datum zapasu, <nejaky prumery ze vsech decisiveScore, allAround> , <nejaky enemy team stats>, <nejaky enemy players stats>
    #extract_data_to_csv("../data/all_players.json", "../data/all_players_simple.csv")

    #x = get_all_clubs_mapping(json.load(open("../data/all_clubs.json","r")),get_league_stats_dataframes("../data/league_stats"))
    #json.dump(x,open("../data/club_names_mapping.json","w"),indent=True)

    #standardize_csv_format("../data/league_stats/alltime")
    delete_last_comma()





if __name__ == "__main__":
    main()
