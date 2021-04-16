#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import glob
import zipfile


def loading_data(folder_path_data_raw):
    '''
    Loads the datasets and stores them in a dictionary

    Parameters
    ----------
    folder_path_data_raw : string
        Path of the folders where the raw datasets are located.

    Returns
    -------
    dict_df : dictionary
        dictionary where the key is the name of the dataframe
        and the value is the dataframe.

    '''
    dict_df = {}
    for file in glob.glob(folder_path_data_raw + "*.txt"):
        # for each dataset of type .txt
        # extract its name
        df_name = file.split('/')[2].split('.')[0]
        # create a dataframe
        vars()['df_'+df_name] = pd.read_csv(file, low_memory=False)
        dict_df[df_name] = vars()['df_'+df_name]

    return dict_df


def removing_bus_data(dict_df):
    '''
    Remove all the data (stops, routes, times) that relates to bus lines.

    Parameters
    ----------
    dict_df : dictionary
        dictionary where the key is the name of the dataframe
        and the value is the dataframe to be cleaned.

    Returns
    -------
    copy_dict_df : dictionary
        dictionary where the key is the name of the dataframe
        and the value is the dataframe that is cleaned.

    '''
    # extracting the dataframes
    df_routes = dict_df['routes']
    df_stop_times = dict_df['stop_times']
    df_stops = dict_df['stops']
    df_trips = dict_df['trips']
    df_transfers = dict_df['transfers']

    # in df_routes,
    # route type = 0 : tramway
    # route type = 1 : subway
    # route type = 2 : RER
    # route type = 3 : bus
    df_routes = df_routes[df_routes['route_type'] != 3]

    # removing bus data in the other dataframes
    df_trips = df_trips[df_trips['route_id'].isin(df_routes['route_id'])]
    df_stop_times = df_stop_times[df_stop_times['trip_id']
                                  .isin(df_trips['trip_id'])]
    df_stops = df_stops[df_stops['stop_id'].isin(df_stop_times['stop_id'])]
    df_transfers = df_transfers[(df_transfers['from_stop_id']
                                 .isin(df_stops['stop_id']))
                                & (df_transfers['to_stop_id']
                                   .isin(df_stops['stop_id']))]

    # storing the filtered dataframes
    copy_dict_df = dict_df
    copy_dict_df['routes'] = df_routes
    copy_dict_df['stop_times'] = df_stop_times
    copy_dict_df['stops'] = df_stops
    copy_dict_df['transfers'] = df_transfers

    return copy_dict_df


def merging_stops(dict_df):
    '''
    Merging stops that correspond to the same line.
    For example, the two stops '4 - Alésia' from either direction are
    merged into the same stop

    Parameters
    ----------
    dict_df : dictionary
        dictionary where the key is the name of the dataframe
        and the value is the dataframe to be cleaned.

    Returns
    -------
    copy_dict_df : dictionary
        dictionary where the key is the name of the dataframe
        and the value is the dataframe that is cleaned.

    '''
    # extracting the dataframes
    df_routes = dict_df['routes']
    df_stop_times = dict_df['stop_times']
    df_stops = dict_df['stops']
    df_trips = dict_df['trips']
    df_transfers = dict_df['transfers']

    # merging df_trips, df_stop_times and df_stops to compute
    # the route_name and direction linked to each stop
    merged_df = df_trips.merge(df_routes[['route_id', 'route_short_name']],
                               on='route_id', how='left')
    merged_df = df_stop_times.merge(merged_df[
        ['trip_id', 'route_short_name', 'direction_id']
        ], on='trip_id', how='left')
    merged_df = merged_df[['stop_id', 'route_short_name', 'direction_id']]\
        .merge(df_stops[['stop_id', 'stop_name']], on='stop_id', how='left')

    merged_df_wo_duplicates = merged_df.drop_duplicates(
        ['stop_name', 'route_short_name']
        )

    # computing the correspondences between old stop_ids and new stop_ids
    # by considering two stops with the same names and of the same
    # line to be equivalent
    new_merged_df = merged_df[['stop_id', 'stop_name', 'route_short_name']]\
        .merge(merged_df_wo_duplicates, on=['stop_name', 'route_short_name'],
               how='left', suffixes=('_old', None))
    new_merged_df.drop_duplicates(['stop_id_old', 'stop_id'], inplace=True)

    # replacing values in new_df_stops using the correspondences found before
    new_df_stops = df_stops.merge(new_merged_df[['stop_id_old', 'stop_id']],
                                  left_on='stop_id', right_on='stop_id_old',
                                  how='left', suffixes=('_old2', None))

    # replacing the old stop_ids in df_stop_times with the new ones
    new_df_stop_times = df_stop_times.merge(
        new_df_stops[['stop_id_old', 'stop_id']], left_on='stop_id',
        right_on='stop_id_old', how='left', suffixes=('_old', None)
        )
    new_df_stop_times.drop(columns='stop_id_old', inplace=True)

    # replacing the old stop_ids in df_transfers with the new ones
    # for from_stop_id
    new_df_transfers = df_transfers.merge(
        new_df_stops[['stop_id_old', 'stop_id']], left_on='from_stop_id',
        right_on='stop_id_old', how='left', suffixes=('_old', None)
        )
    new_df_transfers.drop(
        columns=['from_stop_id', 'stop_id_old'], inplace=True
        )
    new_df_transfers.rename(columns={'stop_id': 'from_stop_id'}, inplace=True)

    # replacing the old stop_ids in df_transfers with the new ones
    # for to_stop_id
    new_df_transfers = new_df_transfers.merge(
        new_df_stops[['stop_id_old', 'stop_id']], left_on='to_stop_id',
        right_on='stop_id_old', how='left', suffixes=('_old', None)
        )
    new_df_transfers.drop(columns=['to_stop_id', 'stop_id_old'], inplace=True)
    new_df_transfers.rename(columns={'stop_id': 'to_stop_id'}, inplace=True)

    # removing the redundant pairs of 'from_stop_id' and 'to_stop_id'
    # by averaging the min_transfer_time and removing the rows
    # where 'from_stop_id' = 'to_stop_id'
    new_df_transfers = new_df_transfers.groupby(
        ['from_stop_id', 'to_stop_id', 'transfer_type']
        ).mean().reset_index()
    new_df_transfers = new_df_transfers[
        new_df_transfers['from_stop_id'] != new_df_transfers['to_stop_id']
        ]
    new_df_stops.drop(columns=['stop_id_old', 'stop_id_old2'], inplace=True)
    new_df_stops.drop_duplicates(inplace=True)

    # storing the filtered dataframes
    copy_dict_df = dict_df
    copy_dict_df['stops'] = new_df_stops
    copy_dict_df['stop_times'] = new_df_stop_times
    copy_dict_df['transfers'] = new_df_transfers

    return copy_dict_df


def cleaning_data(dict_df, folder_path_data_filtered):
    '''
    Cleans the data after it has been loaded. The cleaning involves
    removing data that is related to buses, and merging stops with the same
    name and from the same line but in different direction.
    Finally, stores the data in a zip folder as is required by the peartree
    package to create the graph.

    Parameters
    ----------
    dict_df : dictionary
        dictionary where the key is the name of the dataframe
        and the value is the dataframe to be cleaned.
    folder_path_data_filtered : string
        path where to store the zip file containing the cleaned dataframes.

    Returns
    -------
    None.

    '''
    print('Starting the cleaning process...')
    print('Removing bus data...')
    new_dict_df = removing_bus_data(dict_df)
    print('Merging stops with the same name and of the same line...')
    new_new_dict_df = merging_stops(new_dict_df)

    print('Saving the datasets in a zip file...')
    list_datafiles = []
    for key in new_new_dict_df:
        # saves the filtered dataframes to a folder
        new_new_dict_df[key].to_csv(folder_path_data_filtered + key + '.txt',
                                    index=False)
        list_datafiles.append(folder_path_data_filtered + key + '.txt')

    zip_file = zipfile.ZipFile(folder_path_data_filtered + 'filtered_dfs.zip',
                               'w')
    with zip_file:
        # writing each file one by one
        for file in list_datafiles:
            zip_file.write(file)
    print('Cleaning done!')
