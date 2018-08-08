import os
from pathlib import Path
from datetime import timedelta

import click
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
import pandas as pd
import numpy as np
import sqlalchemy
import requests_cache
import re

from multiprocessing import Pool
from itertools import chain
from collections import namedtuple

import urbanoccupants as uo
import geopandasplotting as gpdplt
ROOT_FOLDER = Path(os.path.abspath(__file__)).parent.parent.parent
CACHE_PATH = ROOT_FOLDER / 'build' / 'web-cache'
requests_cache.install_cache((CACHE_PATH).as_posix())

ENERGY_TIME_SPAN = timedelta(days=7) # energy will be reported as kWh per timespan, e.g kWh per week

Occ_state = namedtuple('Occ_state', ['home', 'not_at_home', 'sleep_at_home'])

@click.command()
@click.argument('path_to_simulation_results')
@click.argument('path_to_config')
@click.argument('path_to_choropleth_plot')
@click.argument('path_to_plot')
@click.argument('timepoint')
def plot_simulation_results(path_to_simulation_results, path_to_config,
                            path_to_choropleth_plot, path_to_plot, timepoint):
    sns.set_context('paper')
    disk_engine = sqlalchemy.create_engine('sqlite:///{}'.format(path_to_simulation_results))
    activity = _read_activity_counts(disk_engine)
    occupancy = _activity_to_occupancy(uo.read_simulation_config(path_to_config), activity)
    geo_data = _read_geo_data(uo.read_simulation_config(path_to_config), occupancy, timepoint)
    _plot_choropleth(geo_data, path_to_choropleth_plot)
    _plot_occupancy(occupancy, path_to_plot)

def _read_activity_counts(disk_engine):
    activity = pd.read_sql_query(
        'SELECT * FROM activityCounts',
        disk_engine,
        index_col='timestamp',
        parse_dates=True
    )
    activity.index = pd.to_datetime(activity.index * 1000 * 1000)
    activity.index.name = 'datetime'
    activity['region'] = activity.id.map(_district_id_int_to_str)
    return activity.reset_index()

def _district_id_int_to_str(district_id_int):
    as_string = list(str(district_id_int))
    as_string[0] = 'E'
    return "".join(as_string)

def _activity_to_occupancy(config, activity):
    occupancy = activity.copy().drop(['id'], axis=1)
    occupancy.set_index(['datetime', 'region'], inplace=True)
    occupancy.value = occupancy.value.str.replace('{','').str.replace('}','').str.replace(',','').str.split()

    # For some reason it can't iterate over the whole length of occupancy df, 
    # so I split into occupancy_1, occupancy_2
    occupancy_1 = occupancy.sort_index().iloc[0:len(occupancy)//2,:].copy()
    occupancy_2 = occupancy.sort_index().iloc[len(occupancy)//2:,:].copy()
    with Pool(config['number-processes']) as pool:
        param_1 = (occupancy_1.value[i] for i in range(0,len(occupancy_1)))
        occ_states = list(chain(*
            pool.map(_occupancy_state_counts, param_1)
            ))
        param_2 = (occupancy_2.value[i] for i in range(0,len(occupancy_2)))
        occ_states.extend(list(chain(*
            pool.map(_occupancy_state_counts, param_2)
            )))

    occupancy = occupancy.sort_index().assign(HOME=[occ_state.home for occ_state in occ_states],
                                 NOT_AT_HOME=[occ_state.not_at_home for occ_state in occ_states],
                                 SLEEP_AT_HOME=[occ_state.sleep_at_home for occ_state in occ_states]
                                 )
    occupancy = occupancy.assign(proportion=(
        occupancy.HOME+occupancy.SLEEP_AT_HOME)/(occupancy.NOT_AT_HOME+occupancy.SLEEP_AT_HOME+occupancy.HOME
        ))
    return occupancy

def _occupancy_state_counts(param_tuple):
    occupancy_value = param_tuple
    home = next((int(re.split('[A-Z_=]+', occupancy_value[j])[1])
                    for j in range(0,len(occupancy_value)) if occupancy_value[j][0]=='H'),0
                    )
    not_at_home = next((int(re.split('[A-Z_=]+', occupancy_value[j])[1])
                    for j in range(0,len(occupancy_value)) if occupancy_value[j][0]=='N'),0
                    ) 
    sleep_at_home = next((int(re.split('[A-Z_=]+', occupancy_value[j])[1])
                    for j in range(0,len(occupancy_value)) if occupancy_value[j][0]=='S'),0
                    )
    return [Occ_state(home,not_at_home,sleep_at_home)]

def _read_geo_data(config, occupancy, timepoint):
    geo_data = uo.census.read_shape_file(config['study-area'], config['spatial-resolution'])
    geo_data['occupancy'] = occupancy.sort_index().loc[timepoint,:].reset_index(level='datetime', drop=True).proportion
    return geo_data


def _plot_choropleth(geo_data, path_to_choropleth):
    # The plot must be scaled, otherwise the legend will look weird. To bring
    # test sizes to a readable level, the seaborn context is set to poster.
    sns.set_context('poster')
    fig = plt.figure(figsize=(18, 8))
    ax = fig.add_subplot(111)
    gpdplt.plot_dataframe(
        geo_data,
        column='occupancy',
        categorical=False,
        linewidth=0.2,
        legend=True,
        cmap='viridis',
        vmin=0,
        vmax=1,
        ax=ax
    )
    ax.set_aspect(1)
    _ = plt.xticks([])
    _ = plt.yticks([])

    fig.savefig(path_to_choropleth, dpi=300)
    sns.set_context('paper')


def _plot_occupancy(occupancy, path_to_plot):
    def _xTickFormatter(x, pos):
        return pd.to_datetime(x).time()
    fig = plt.figure(figsize=(8, 4), dpi=300)
    ax = fig.add_subplot(111)
    sns.tsplot(
        data=occupancy.reset_index(),
        time='datetime',
        unit='region',
        value='proportion',
        err_style='unit_traces',
        ax=ax
    )
    _ = plt.ylabel('proportion of people at home (asleep & active)')
    _ = plt.xlabel('time of the day')
    ax.set_ylim(bottom=0)

    ax.label_outer()

    points_in_time = occupancy.reset_index().groupby('datetime').proportion.first().index
    xtick_locations = [0, 144 // 2-1, 143, 143 + 144 // 2] # not sure why they are shifted
    ax.set_xticks([points_in_time[x].timestamp() * 10e8 for x in xtick_locations])
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(_xTickFormatter))

    fig.savefig(path_to_plot, dpi=300)


if __name__ == '__main__':
    plot_simulation_results()
