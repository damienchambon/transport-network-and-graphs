#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pickle
from haversine import haversine
import numpy as np


def save_obj(obj, path):
    with open(path, 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def get_distance_stops(stop1, stop2, dict_geo_data):
    location_stop_1 = dict_geo_data[stop1]
    location_stop_2 = dict_geo_data[stop2]
    lat_stop_1 = location_stop_1['lat']
    lon_stop_1 = location_stop_1['lon']
    lat_stop_2 = location_stop_2['lat']
    lon_stop_2 = location_stop_2['lon']
    distance_km = haversine((lat_stop_1, lon_stop_1), (lat_stop_2, lon_stop_2))
    return distance_km


def computing_avg_speed_mode(G, dict_geo_data):
    # initializing the lists and getting the different connections
    connections_data = list(G.edges(data=True))
    list_speed_RER = []
    list_speed_metro = []
    list_speed_tram = []
    list_speed_walk = []
    list_time_walk = []

    for connection in connections_data:
        # for each connection
        # getting the time in sec
        time_in_sec = connection[2]['length']
        if time_in_sec != 0:
            # computing the distance in km
            distance_km = get_distance_stops(connection[0], connection[1],
                                             dict_geo_data)
            # deducing the speed
            speed_km_h = (distance_km/time_in_sec) * 3600
            # putting the speed in the appropriate list
            if connection[2]['mode'] == 'walk':
                list_speed_walk.append(speed_km_h)
                list_time_walk.append(time_in_sec)
            else:
                if connection[0].split(' - ', 1)[0] in ['A', 'B']:
                    list_speed_RER.append(speed_km_h)
                elif connection[0].split(' - ', 1)[0][0] == 'T':
                    list_speed_tram.append(speed_km_h)
                else:
                    list_speed_metro.append(speed_km_h)
    # computing the average speeds
    speed_RER = np.mean(list_speed_RER)
    speed_metro = np.mean(list_speed_metro)
    speed_tram = np.mean(list_speed_tram)
    speed_walk = np.mean(list_speed_walk)
    time_walk = np.mean(list_time_walk)

    print('Average speed of RERs (km/h):', speed_RER)
    print('Average speed of metros (km/h):', speed_metro)
    print('Average speed of trams (km/h):', speed_tram)
    print('Average speed of walking (km/h):', speed_walk)
    print('Average time spent walking between two stations (sec):', time_walk)

    return {'RER': speed_RER, 'metro': speed_metro, 'tram': speed_tram,
            'speed_walk': speed_walk, 'time_walk': time_walk}
