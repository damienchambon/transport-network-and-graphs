#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 16 19:40:23 2021

@author: damienchambon
"""

import src.data_loading_cleaning as data_loading_cleaning
import src.graph_transformation as graph_transformation
import src.graph_metrics as graph_metrics
import src.utils as utils
import src.finding_new_lines as finding_new_lines
import sys

if __name__ == '__main__':
    # number of connections to test for each mode
    # the connections that will be tested are the cheapest ones
    # among those that are more than 5km long
    k = sys.argv[1][1:]
    # number of improvements to be suggested for each mode
    n = sys.argv[2][1:]

    # loading and cleaning the data
    dict_df = data_loading_cleaning.loading_data('data/raw/')
    data_loading_cleaning.cleaning_data(dict_df, 'data/filtered/')
    print()

    # transforming the data
    G, dict_geo_data, dict_distances = graph_transformation.\
        graph_transforming('data/filtered/')

    print()
    # saving the results so that this step does not have to be performed again
    utils.save_obj(G, 'objects/graph.pkl')
    utils.save_obj(dict_geo_data, 'objects/dict_geo_data.pkl')
    utils.save_obj(dict_distances, 'objects/dict_distances.pkl')

    # analyzing the graph
    # loading the objects
    G = utils.load_obj('objects/graph.pkl')
    dict_geo_data = utils.load_obj('objects/dict_geo_data.pkl')
    dict_distances = utils.load_obj('objects/dict_distances.pkl')
    print('Computing some metrics...')
    print()
    graph_metrics.computing_metrics(G, 'current network',
                                    'figures/current_network')

    dict_avg_speed = utils.computing_avg_speed_mode(G, dict_geo_data)
    current_efficiency, g_ideal, denom = graph_metrics\
        .global_efficiency_weighted(G, dict_distances, dict_avg_speed['RER'])
    print('Current global efficiency of the network:', current_efficiency)

    # detecting new routes to create
    # setting the costs of each type of route
    # costs of creating a new line and exploiting it, in €/km
    dict_costs = {}
    dict_costs['tram'] = 22*1000000
    dict_costs['metro'] = 80*1000000
    dict_costs['RER'] = 120*1000000

    improvements = finding_new_lines.computing(G, dict_costs, n, k,
                                               dict_distances, dict_geo_data,
                                               dict_avg_speed, g_ideal, denom,
                                               current_efficiency)

    print()
    for mode in improvements:
        top_improvements = improvements[mode]
        print('Top {} new connections for {}'.format(
            len(top_improvements), mode)
            )
        print()
        for improv in top_improvements:
            print('* connection:', improv['connection'],
                  ', score:', improv['score'],
                  ', increase_eff:', improv['increase_eff'],
                  ', cost:', improv['cost'],
                  ', route:', improv['route']
                  )
        print()
        print('Metrics for the best connection found:')
        best_improv = top_improvements[0]
        best_graph = best_improv['graph']
        graph_metrics.computing_metrics(
            best_graph, 'best graph for mode {}'.format(mode),
            'figures/best_graph_'+mode)
        the_string = 'New efficiency of the network: {} vs current '\
            + 'efficency: {} for an investment of {} euros'
        print(the_string.format(
            current_efficiency + best_improv['increase_eff'],
            current_efficiency, round(best_improv['cost'], 2))
            )
        print()
        print('--------------')
        print()
        utils.save_obj(best_graph, 'objects/best_graph'+mode+'.pkl')
