#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from itertools import permutations


def is_strongly_connected(G):
    # checking connectivity
    # the goal of the network is to be strongly connected
    if nx.is_strongly_connected(G):
        print('The directed graph is strongly connected')
    else:
        print('The directed graph is not strongly connected.')


def is_tree(G):
    # checking whether the graph is a tree
    if nx.is_tree(G):
        print('The underlying graph is a tree')
    else:
        print('The underlying graph is not a tree.')


def complexity(G):
    # cyclomatic number - difference between # edges and # vertices
    # it is a measure of route redundancy: the lower the better
    edges = len(G.edges())
    nodes = len(G.nodes())
    parts = nx.components.number_strongly_connected_components(G)
    print('# Edges:', edges)
    print('# Nodes:', nodes)
    print('# Subgraphs:', parts)
    print('Cyclomatic number:', edges - nodes + parts)


def avg_lengths(G):
    # average path lengths (= duration) in minutes
    # from each stop to all other stops
    # the lower, the better
    list_avg_lengths = []
    for node in G.nodes():
        length = nx.single_source_dijkstra_path_length(
            G, node, weight='length'
            )
        avg_len = np.average(list(length.values()))
        list_avg_lengths.append(round(avg_len/60))
    return list_avg_lengths


def graph_degree(G):
    # each degree is divided by 2 because we want to know to how
    # many stops one stop is connected
    list_degrees = [d/2 for n, d in G.degree()]
    return list_degrees


def avg_nb_connections(G):
    # average number of connections between two stops
    # a connection is when the passenger has to change from one
    # line to another
    # the lower the better
    list_avg_nb_connections = []
    for node in G.nodes():
        # getting the shortest path from each stop to the others
        list_paths = nx.single_source_dijkstra_path(G, node, weight='length')
        # computing how many different lines are used to reach other stops
        list_paths = [
            [node_of_path.split(' - ')[0]
             for node_of_path in list_paths[node]]
            for node in list_paths]
        list_paths = [len(np.unique(path))-1 for path in list_paths]
        # computing the average number of connections between two stops
        list_avg_nb_connections.append(np.mean(list_paths))
    return list_avg_nb_connections


def global_efficiency_weighted(G, dict_distances, speed_RER,
                               g_ideal=None, denom=None):
    # function from
    # link: https://stackoverflow.com/questions/56554132/how-can-i-calculate-global-efficiency-more-efficiently

    if denom is None:
        # computing how many unique nodes we have
        # we only count as 1 node multiple stops from
        # different lines that connect at the same hub

        # first, we get all the edges corresponding to a connection
        list_connections = [edge for edge in list(G.edges(data=True))
                            if edge[2]['mode'] == 'walk']
        # we create a graph using those edges
        connection_graph = nx.Graph()
        connection_graph.add_edges_from(list_connections)

        # for each connected component (= hub of stops from different
        # lines connected to each other), we count the number of stops
        # in those connected component
        nb_redundant_stops = 0
        for component in nx.connected_components(connection_graph):
            nb_redundant_stops += len(component)-1

        # the true number of stops is the total number of nodes - the
        # stops present in the hub of stops
        n = len(G)-nb_redundant_stops
        denom = n * (n - 1)

    if denom != 0:
        # getting the shortest paths between each stop and all other stops
        shortest_paths = nx.all_pairs_dijkstra_path_length(G, weight='length')
        # converting the generator to a dictionary
        shortest_paths = {c[0]: c[1] for c in shortest_paths}

        # computing the efficiency
        g_eff = sum(1./shortest_paths[u][v]
                    if shortest_paths[u][v] != 0 else 0.0
                    for u, v in permutations(G, 2)) / denom

        # normalizing it by considering the network where all stops
        # are directly connected by an RER
        if g_ideal is None:
            # getting the distance in km between the stops
            list_geo_dist_km = [dict_distances[u][v]
                                if (u != v) else 0.0
                                for u, v in permutations(G, 2)]
            # computing the efficiency by transforming the distance
            # in a time in seconds
            g_ideal = sum(1./((dist_km/speed_RER)*3600)
                          if dist_km != 0.0 else 0.0
                          for dist_km in list_geo_dist_km) / denom
        return g_eff/g_ideal, g_ideal, denom
    else:
        g_eff = 0
        return g_eff


def computing_metrics(G, title, path):
    '''
    Computing different graph metrics that assess the quality of a
    transportation network. Note that the global weighted efficiency
    is not computed in this function.

    Parameters
    ----------
    G : Graph
        Graph that needs to be analyzed.
    title : string
        title to add to the figures.
    path : string
        path of the folder where to save the graphs.

    Returns
    -------
    None.

    '''

    is_strongly_connected(G)
    print()
    is_tree(G)
    print()
    complexity(G)
    print()

    print('Distribution of node degrees')
    data = graph_degree(G)
    bins = np.arange(0, np.max(data) + 1.5) - 0.5
    # then you plot away
    fig, ax = plt.subplots()
    _ = ax.hist(data, bins, rwidth=0.85)
    ax.set_xticks(bins + 0.5)
    plt.xlabel('Number of stops directly connected')
    plt.ylabel('Number of stops')
    plt.title('Distribution of node degrees - ' + title)
    plt.savefig(path+'_figure1.png')
    print('Figure saved!')
    print()

    print('Average path length')
    fig, ax = plt.subplots()
    plt.hist(avg_lengths(G))
    plt.xlabel('Average time to reach other stops (in minutes)')
    plt.ylabel('Number of stops')
    plt.title('Average path length - ' + title)
    plt.savefig(path+'_figure2.png')
    print('Figure saved!')
    print()

    print('Distribution of connections to make')
    data = avg_nb_connections(G)
    bins = np.arange(0, np.max(data) + 1.5) - 0.5
    # then you plot away
    fig, ax = plt.subplots()
    _ = ax.hist(data, bins, rwidth=0.85)
    ax.set_xticks(bins + 0.5)
    plt.xlabel('Average number of connections to reach other stops')
    plt.ylabel('Number of stops')
    plt.title('Distribution of connections to make - ' + title)
    plt.savefig(path+'_figure3.png')
    print('Figure saved!')
    print()
