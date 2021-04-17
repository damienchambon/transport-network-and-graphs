#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from shapely.geometry import LineString, Point
from itertools import combinations
import numpy as np
from src.graph_metrics import global_efficiency_weighted
from src.utils import get_distance_stops


def computing_potential_connections(G):
    '''
    Finding potential new connections to make in a graph

    Parameters
    ----------
    G : Graph
        Graph where the new connections should be made.

    Returns
    -------
    subset_list_potential_connections : list
        list of the potential connections to create.

    '''
    list_nodes = list(G.nodes())
    list_potential_connections = list(combinations(list_nodes, 2))
    # yields the elements in list_potential_connections that are NOT in G.edges
    list_potential_connections = list(
        set(list_potential_connections) - set(list(G.edges()))
        )

    # list that contains the stops that are connected by a walking edge
    # to a stop that has already been studied
    # such stops should not be taken into account
    existing_connections = []
    subset_list_potential_connections = {}
    subset_list_potential_connections['RER'] = []
    subset_list_potential_connections['metro'] = []
    subset_list_potential_connections['tram'] = []

    for connection in list_potential_connections:
        stop_1 = connection[0]
        stop_2 = connection[1]
        # if no connection has been tested with a stop connected to the stops
        # studied by a walking edge
        if (
                (stop_1 not in existing_connections)
                and (stop_2 not in existing_connections)
        ):
            # creating an option for a connection with the 3 possible
            # transportation modes
            [subset_list_potential_connections[mode].append(
                {'connection': connection, 'mode': mode}
                ) for mode in ['RER', 'tram', 'metro']]

            # adding all stops that are connected by a walking edge
            # in existing_connections so that connections with
            # stops that belong to the same hub are not tested
            connections_stop_1 = [connection[1]
                                  for connection in
                                  list(G.edges(stop_1, data=True))
                                  if connection[2]['mode'] == 'walk']
            connections_stop_2 = [connection[1]
                                  for connection in
                                  list(G.edges(stop_2, data=True))
                                  if connection[2]['mode'] == 'walk']

            [existing_connections.append(connection_stop)
             for connection_stop in connections_stop_1
             if connection_stop not in existing_connections]
            [existing_connections.append(connection_stop)
             for connection_stop in connections_stop_2
             if connection_stop not in existing_connections]
    return subset_list_potential_connections


def getting_cheapest_k_connections(list_potential_connections, k,
                                   dict_distances, dict_costs):
    '''
    Computing the cheapest k connections from a list of potential
    connections.

    Parameters
    ----------
    list_potential_connections : list
        list of potential connections to create.
    k : int
        number of connections to keep for each transportation mode.
    dict_distances : dictionary
        dictionary where the key is a stop and the value is a dictionary
        containing the distances between that stop and all other stops.
    dict_costs : dictionary
        dictionary where the key is a transportation mode and the value
        is the cost in euros of 1 kilometer of railroad.

    Returns
    -------
    top_K_connections : dictionary
        dictionary where the key is a transportation mode and the value
        is the list of K cheapest connections to build.

    '''
    # only keeping the cheapest K connections for each mode
    # and that are far from each other (more than 5km)
    top_K_connections = {}

    for mode in ['RER', 'metro', 'tram']:
        connections_more_5km = []

        for connection in list_potential_connections[mode]:
            # adding all connections that are more than 5km long
            stop1 = connection['connection'][0]
            stop2 = connection['connection'][1]
            distance_km = dict_distances[stop1][stop2]
            cost = distance_km*dict_costs[mode]
            if distance_km > 5:
                connections_more_5km.append(
                    {'connection': connection['connection'],
                     'cost': cost})

        # only taking the cheapest K connections for a particular mode
        sorted_connections_more_5km = sorted(connections_more_5km,
                                             key=lambda x: x['cost'])
        if k < len(sorted_connections_more_5km):
            top_K_connections[mode] = sorted_connections_more_5km[:k]
        else:
            top_K_connections[mode] = sorted_connections_more_5km

    return top_K_connections


def create_intersection_stops(stop_1, stop_2, G,
                              dict_distances, dict_geo_data):
    '''
    Detecting intersections between a new connection and existing connections.
    For each intersection, the closest existing stop is computed.

    Parameters
    ----------
    stop_1 : string
        name of a stop to be connected.
    stop_2 : string
        name of the other stop to be connected.
    G : Graph
        graph where intersections between connections need to be detected.
    dict_distances : dictionary
        dictionary where the key is a stop and the value is a dictionary
        containing the distances between that stop and all other stops.
    dict_geo_data : dictionary
        dictionary where the key is a stop and the value is a dictionary
        containing its location data.

    Returns
    -------
    list
        list of the stops where the new connection will intersect.
    dict_existing_connections : dictionary
        dictionary where the key is a stop and the value is a list of all
        the stop it connecs to through a walking edge.

    '''
    # list that will contain the list of stops intersecting with the edge
    # between stop_1 and stop_2
    list_intersections = []
    # dictionary containing the stops that are connected by a walking edge
    # with the stops present in list_intersections
    # key = stop in list_intersections, value = list of connected stops
    dict_existing_connections = {}

    # creating a line object connecting the two new stops we want to make
    new_connection = (stop_1, stop_2)
    new_stop_1_location = (dict_geo_data[new_connection[0]]['lon'],
                           dict_geo_data[new_connection[0]]['lat'])
    new_stop_2_location = (dict_geo_data[new_connection[1]]['lon'],
                           dict_geo_data[new_connection[1]]['lat'])
    coords_new = [new_stop_1_location, new_stop_2_location]
    line_new = LineString(coords_new)
    list_intersections.append(stop_1)
    list_intersections.append(stop_2)

    # adding the connections of stop_1 and stop_2
    dict_existing_connections[stop_1] = [connection[1]
                                         for stop in list_intersections
                                         for connection in
                                         list(G.edges(stop_1, data=True))
                                         if connection[2]['mode'] == 'walk']
    dict_existing_connections[stop_2] = [connection[1]
                                         for stop in list_intersections
                                         for connection in
                                         list(G.edges(stop_2, data=True))
                                         if connection[2]['mode'] == 'walk']

    # list of connections to test for intersection
    list_connections = [edge for edge in list(G.edges(data=True))
                        if edge[2]['mode'] != 'walk']
    for existing_connection in list_connections:
        # creating a line object between two existing stops
        old_stop_1 = (dict_geo_data[existing_connection[0]]['lon'],
                      dict_geo_data[existing_connection[0]]['lat'])
        old_stop_2 = (dict_geo_data[existing_connection[1]]['lon'],
                      dict_geo_data[existing_connection[1]]['lat'])
        coords_old = [old_stop_1, old_stop_2]
        line_old = LineString(coords_old)

        if (
                (line_old.intersects(line_new))
                and (len(list(set(coords_old) & set(coords_new))) == 0)
        ):
            # if the two lines intersect, a connection between the new line
            # and the existing line is created
            intersection_coord = line_old.intersection(line_new)

            # computing which stop of the intersecting edge is the closest
            # to the intersection
            if (intersection_coord.distance(Point(old_stop_1))
            < intersection_coord.distance(Point(old_stop_2))):
                intersection_stop = existing_connection[0]
            else:
                intersection_stop = existing_connection[1]

            if (
                (intersection_stop not in list_intersections)
                and intersection_stop not in
                [stop for connection in [*dict_existing_connections.values()]
                 for stop in connection]
               ):
                # useful not to create different transit connections
                # between stops that are already connected
                # we can now add the intersection stop to the list
                # and add the stops it is connected to through a walking edge
                list_intersections.append(intersection_stop)
                dict_existing_connections[intersection_stop] =\
                    [connection[1] for connection in
                     list(G.edges(intersection_stop, data=True))
                     if connection[2]['mode'] == 'walk']

    # now that all intersection stops have been found
    # the distances between stop_1 and all the stops are computed
    # so that the correct ordering of the intersection stops is found
    list_distances = [(stop, dict_distances[stop][stop_1])
                      if stop != stop_1 else (stop, 0)
                      for stop in list_intersections]
    list_distances = sorted(list_distances, key=lambda x: x[1])

    return [stop[0] for stop in list_distances], dict_existing_connections


def finding_lines(G, dict_costs, n, top_K_connections,
                  dict_distances, dict_geo_data, dict_speeds,
                  global_efficiency_ideal, denom, current_efficiency):
    list_improvements = {}
    new_graph = G.copy()
    time_walk = dict_speeds['time_walk']
    speed_RER = dict_speeds['RER']
    for mode in ['RER', 'metro', 'tram']:
        print()
        print('Checking potential new ' + mode + ' connections to make...')
        print()
        list_improvements[mode] = []
        connections_to_study = top_K_connections[mode]
        speed_mode = dict_speeds[mode]
        for i in range(len(connections_to_study)):
            if i % 50 == 0 or (i == len(connections_to_study)-1):
                print('{}/{}'.format(i+1, len(connections_to_study)))
            if (i != 0 and i % 300 == 0) or (i == len(connections_to_study)-1):
                print()
                print('Current best ' + str(n) + ' connections to build are:')
                if len(list_improvements[mode]) != 0:
                    print()
                    sorted_list_improvements = sorted(list_improvements[mode],
                                                      key=lambda x: x['score'],
                                                      reverse=True)
                    for improv in sorted_list_improvements:
                        print('* connection:', improv['connection'],
                              ', score:', improv['score'],
                              ', increase_eff:', improv['increase_eff'],
                              ', cost:', improv['cost'],
                              ', route:', improv['route'],
                              )
                    print()

            connection = connections_to_study[i]['connection']
            stop_1 = connection[0]
            stop_2 = connection[1]

            # finding which stops would intersect with the new potential line
            # that list only contains the names of existing stops
            list_intersections_old_stops, dict_existing_connections =\
                create_intersection_stops(stop_1, stop_2, new_graph,
                                          dict_distances, dict_geo_data)

            # adding the new stops to the graph
            list_intersections_names = [stop.split(' - ', 1)[1]
                                        for stop in
                                        list_intersections_old_stops]
            new_stop = mode + '_new - '
            # that list only contains the names of new stops
            list_intersections_new_stops = [new_stop + name_stop
                                            for name_stop
                                            in list_intersections_names]
            for stop in list_intersections_new_stops:
                new_graph.add_node(stop)

            # adding the new connections required for the new line
            # in both ways every time

            # first, adding the transit connection between the new stops
            for i in range(len(list_intersections_new_stops)-1):
                stop_to_connect_1 = list_intersections_new_stops[i]
                stop_to_connect_2 = list_intersections_new_stops[i+1]
                # corresponding existing stops
                old_stop_to_connect_1 = list_intersections_old_stops[i]
                old_stop_to_connect_2 = list_intersections_old_stops[i+1]
                dist_km = \
                    dict_distances[old_stop_to_connect_1][old_stop_to_connect_2]

                expected_time_in_sec = (dist_km/speed_mode)*3600
                new_graph.add_edge(stop_to_connect_1, stop_to_connect_2,
                                   length=expected_time_in_sec, mode='transit')
                new_graph.add_edge(stop_to_connect_2, stop_to_connect_1,
                                   length=expected_time_in_sec, mode='transit')

            # adding the walking connection between the new stops and the
            # old ones using the average walking time between connections
            for i in range(len(list_intersections_new_stops)):
                new_stop = list_intersections_new_stops[i]
                # for each new stop, we get the stops it directly connects to
                # example: if new stop is at Denfert-Rochereau
                corresponding_old_stop = list_intersections_old_stops[i]
                # we may have corresponding_old_stop = 'B - Denfert-Rochereau'
                list_direct_connections = [corresponding_old_stop]

                # list_other_old_stops contains other stops connecting there
                # such as '6 - Denfert-Rochereau' & '4 - Denfert-Rochereau'
                list_other_old_stops = dict_existing_connections[
                    corresponding_old_stop
                    ]
                for stop in list_other_old_stops:
                    list_direct_connections.append(stop)

                # now that we got all stops it'll directly connect to
                # we add the walking connections for each
                for stop in list_direct_connections:
                    new_graph.add_edge(new_stop, stop,
                                       length=time_walk, mode='walk')
                    new_graph.add_edge(stop, new_stop,
                                       length=time_walk, mode='walk')

            # we add the new stops in a copy of dict_distances so that
            # we can compute the efficiency
            new_dict_distances = dict_distances
            for stop in list_intersections_new_stops:
                new_dict_distances[stop] = {}
            # for the new stops, we use the location of the stops they
            # will connect to
            for node in new_graph.nodes():
                for i in range(len(list_intersections_new_stops)):
                    new_stop = list_intersections_new_stops[i]
                    corresponding_old_stop = list_intersections_old_stops[i]
                    if new_stop == node or corresponding_old_stop == node:
                        new_dict_distances[new_stop][node] = 0
                        new_dict_distances[node][new_stop] = 0
                    else:
                        new_dict_distances[new_stop][node] = \
                            new_dict_distances[corresponding_old_stop][node]
                        new_dict_distances[node][new_stop] = \
                            new_dict_distances[corresponding_old_stop][node]

            # computing the efficiency score
            results = global_efficiency_weighted(new_graph, new_dict_distances,
                                                 speed_RER,
                                                 global_efficiency_ideal,
                                                 denom)
            new_efficiency = results[0]

            if new_efficiency > current_efficiency:
                dist_km = get_distance_stops(stop_1, stop_2, dict_geo_data)
                cost = dist_km*dict_costs[mode]
                # computing the score
                # increase in efficiency in % / nb of millions invested in €
                increase_eff = new_efficiency-current_efficiency
                score = ((increase_eff)*100)/(cost/1000000)

                # storing the n top connections to make
                if len(list_improvements[mode]) < n:
                    list_improvements[mode].append(
                        {'connection': connection, 'mode': mode,
                         'score': score, 'increase_eff': increase_eff,
                         'cost': cost,
                         'route': list_intersections_old_stops,
                         'graph': new_graph.copy(),
                         'dict_distances': new_dict_distances})
                else:
                    if score > np.min(
                            [improvement['score']
                             for improvement in list_improvements[mode]]
                            ):
                        list_improvements[mode].append(
                            {'connection': connection, 'mode': mode,
                             'score': score, 'increase_eff': increase_eff,
                             'cost': cost,
                             'route': list_intersections_old_stops,
                             'graph': new_graph.copy(),
                             'dict_distances': new_dict_distances})
                        list_improvements[mode] = sorted(
                            list_improvements[mode], key=lambda x: x['score'],
                            reverse=True)[:-1]

            # finally, we remove the nodes we added
            for stop in list_intersections_new_stops:
                if new_graph.has_node(stop):
                    new_graph.remove_node(stop)

    return list_improvements


def computing(G, dict_costs, n, k, dict_distances, dict_geo_data,
              dict_speeds, global_efficiency_ideal, denom,
              current_efficiency):

    potential_connections = computing_potential_connections(G)
    top_K_connections = getting_cheapest_k_connections(potential_connections,
                                                       k, dict_distances,
                                                       dict_costs)

    improvements = finding_lines(G, dict_costs, n, top_K_connections,
                                 dict_distances, dict_geo_data, dict_speeds,
                                 global_efficiency_ideal, denom,
                                 current_efficiency)
    print('Done!')

    return improvements
