# A framework for creating new connections in a transportation system: a case study of the Parisian public transit

### By Damien Chambon and Nadezda Timoshenko

This repository contains the code and the figures used for the study _A framework for creating new connections in a transportation system: a case study of the Parisian public transit"_. The goal of the study was to create an algorithm that finds the best lines to create in a public transportation network in order to optimize its efficiency.

## Data
The data comes from an open data repository from the RATP, the company that manages the public transportation in Paris. The data can be downloaded [here](https://data.ratp.fr/explore/dataset/offre-transport-de-la-ratp-format-gtfs/information/) by clicking on _RATP_GTFS_FULL_.

## Structure of the repo
The repository is structured as follows:

- `docs`: documentation of the data (in French)
- `data`: the data downloaded from the RATP website should be extracted and put in `data/raw` while `data/filtered` remains empty
- `objects`: serialized objects are saved there and loaded from there during the analysis
- `figures`: figures that are created during the analysis
- `src`: code required for the analysis
- `main.py`: main code that needs to be executed to perform the analysis

## How to run the code
To run the code, one needs to use the terminal. After using the `cd` command to go into the root folder of the repo, one should execute `main.py` with two parameters: the first one is the number of connections that will be tested per transportation mode (RER, metro and tramway), the second one is the number of optimal connections to output per transportation mode.

For example, to test 1000 connections for each transportation mode and output the top 5 connections per transportation mode, one needs to run the following command: `main.py -1000 -5`.

While the code is running, figures will be saved in `figures` and results will be shown in the terminal.
