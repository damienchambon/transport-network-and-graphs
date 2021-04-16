#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import peartree as pt
import pandas as pd
import networkx as nx
from src.utils import get_distance_stops
from itertools import permutations


def converting_data_to_graph(folder_path_data_filtered):
    '''
    Transforms GTFS data to a graph using the peartree package

    Parameters
    ----------
    folder_path_data_filtered : string
        Path of the folder containing the zip file comprising
        the cleaned GTFS data.

    Returns
    -------
    G : Graph
        Graph containing all the data from the GTFS files.

    '''
    path = folder_path_data_filtered+'filtered_dfs.zip'

    # Automatically identify the busiest day and
    # read that in as a Partridge feed
    feed = pt.get_representative_feed(path)

    # Set a target time period to
    # use to summarize impedance
    start = 1*60*60  # 1:00 AM
    end = 23*60*60  # 11:00 PM

    # Converts feed subset into a directed
    # network multigraph
    G = pt.load_feed_as_graph(feed, start, end, name='RATP',
                              use_multiprocessing=True,
                              impute_walk_transfers=True,
                              connection_threshold=150)

    return G


def renaming_nodes(G, folder_path_data_filtered):
    '''
    Rename the nodes of a graph using data from the datasets
    following a mapping for example of 'RATP_1234' --> '4 - Alésia'

    Parameters
    ----------
    G : Graph
        Graph where the nodes have to be renamed.
    folder_path_data_filtered : string
        Path of the folder where all the filtered data is stored.

    Returns
    -------
    new_G : Graph
        Graph whose nodes have been renamed.
    dict_geo_data : dictionary
        dictionary containing the location of the stops, where the
        key is the cleaned name of the stop and the value is a
        dictionary containing the location data of that stop.
    dict_distances : dictionary
        dictionary containing the distances between each stop
        and other stops, where the key is the cleaned name of
        the stop and the value is a dictionary containing the
        distance between the key-stop and other stops.

    '''
    # loading the datasets
    df_stops = pd.read_csv(folder_path_data_filtered+'stops.txt',
                           low_memory=False)
    df_stop_times = pd.read_csv(folder_path_data_filtered+'stop_times.txt',
                                low_memory=False)
    df_routes = pd.read_csv(folder_path_data_filtered+'routes.txt',
                            low_memory=False)
    df_trips = pd.read_csv(folder_path_data_filtered+'trips.txt',
                           low_memory=False)

    # merging the datasets to get all the data required to rename nodes
    # such as trips, routes, stop_times and stops
    merged_df = df_trips.merge(df_routes[['route_id', 'route_short_name']],
                               on='route_id', how='left')
    merged_df = df_stop_times.merge(merged_df[['trip_id', 'route_short_name']],
                                    on='trip_id', how='left')
    merged_df = merged_df[['stop_id', 'route_short_name']]\
        .merge(df_stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']],
               on='stop_id', how='left')

    merged_df.drop_duplicates(['stop_id', 'route_short_name', 'stop_name'],
                              inplace=True)

    # creating the mapping of stops
    merged_df['combined_name'] = merged_df.apply(
        lambda x: str(x['route_short_name']) + ' - ' + x['stop_name'], axis=1
        )
    merged_df['transformed_stop_id'] = merged_df.apply(
        lambda x: 'RATP_' + str(x['stop_id']), axis=1
        )

    # transforming the mapping to a dictionary to then rename the nodes
    dict_stop_id_stop_name = dict(
        merged_df[['transformed_stop_id', 'combined_name']].values
        )
    new_G = nx.relabel_nodes(G, dict_stop_id_stop_name)

    # creating a dictionary that contains the location of each stop
    geo_data = merged_df[['combined_name', 'stop_lat', 'stop_lon']]
    dict_geo_data = {}
    for index, row in geo_data.iterrows():
        dict_geo_data[row['combined_name']] = {'lat': row['stop_lat'],
                                               'lon': row['stop_lon']}

    # creating a dictionary that contains the distances between each stop
    # and other stops
    dict_distances = {}
    for node in new_G.nodes():
        dict_distances[node] = {}

    for u, v in permutations(new_G, 2):
        distance_km = get_distance_stops(u, v, dict_geo_data)
        dict_distances[u][v] = distance_km
        dict_distances[v][u] = distance_km

    return new_G, dict_geo_data, dict_distances


def updating_edge_costs(G):
    '''
    Updating the edge costs of the edge where the edge is between
    two stops from different lines, i.e. where the edge is a walking edge

    Parameters
    ----------
    G : Graph
        Graph containing walking edges that needs to be reweighted.

    Returns
    -------
    new_G : Graph
        Graph whose walking edges have been reweighted.

    '''
    new_G = G.copy()

    # getting connections between two different lines
    list_connections_edges = [
        edge for edge in list(new_G.edges(data=True))
        if edge[0].split('-')[0] != edge[1].split('-')[0]
                              ]

    # updating the connection cost by adding the wait time of the
    # target stop of the connection
    for connection in list_connections_edges:
        from_node = connection[0]
        to_node = connection[1]
        boarding_cost = new_G.nodes[to_node]['boarding_cost']
        new_G.edges[(from_node, to_node, 0)]['length'] += boarding_cost

    return new_G


def graph_transforming(folder_path_data_filtered):
    '''
    Creates a graph from the data in GTFS format.
    Renames the nodes and reweights the walking edges appropriately.

    Parameters
    ----------
    folder_path_data_filtered : string
        Path of the folder where the filtered data is located.

    Returns
    -------
    new_new_G : Graph
        Cleaned graph containing the data from the GTFS files.
    dict_geo_data : dictionary
        dictionary containing the location of the stops, where the
        key is the cleaned name of the stop and the value is a
        dictionary containing the location data of that stop.

    '''
    print('Starting the graph transformation process...')
    print('Converting the data to a graph...')
    G = converting_data_to_graph(folder_path_data_filtered)
    print(
        'Renaming the nodes appropriately and getting their location data...'
        )
    new_G, dict_geo_data, dict_distances = renaming_nodes(
        G, folder_path_data_filtered
        )
    print('Reweighting the edges by adding stop waiting times...')
    new_new_G = updating_edge_costs(new_G)
    print('Graph transformation process done!')

    return new_new_G, dict_geo_data, dict_distances
