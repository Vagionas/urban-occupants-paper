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

import urbanoccupants as uo
import geopandasplotting as gpdplt
ROOT_FOLDER = Path(os.path.abspath(__file__)).parent.parent.parent
CACHE_PATH = ROOT_FOLDER / 'build' / 'web-cache'
requests_cache.install_cache((CACHE_PATH).as_posix())

ENERGY_TIME_SPAN = timedelta(days=7) # energy will be reported as kWh per timespan, e.g kWh per week


@click.command()
@click.argument('path_to_simulation_results')
@click.argument('path_to_config')
@click.argument('path_to_choropleth_plot')
@click.argument('timepoint')
def plot_simulation_results(path_to_simulation_results, path_to_config,
                            path_to_choropleth_plot, timepoint):
    sns.set_context('paper')
    disk_engine = sqlalchemy.create_engine('sqlite:///{}'.format(path_to_simulation_results))
    activity = _read_activity_counts(disk_engine)
    geo_data = _read_geo_data(uo.read_simulation_config(path_to_config), activity, timepoint)
    _plot_choropleth(geo_data, path_to_choropleth_plot)


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


def _read_geo_data(config, activity, timepoint):
    geo_data = uo.census.read_shape_file(config['study-area'], config['spatial-resolution'])

    activity.set_index(['datetime', 'region'], inplace=True)
    occupancy = activity.sort_index().loc[timepoint,:].copy().drop(['id'], axis=1).reset_index(level='datetime', drop=True)
    occupancy.value = occupancy.value.str.replace('{','').str.replace('}','').str.replace(',','').str.split()
    occupancy = occupancy.assign(HOME=np.zeros(len(occupancy)), NOT_AT_HOME=np.zeros(len(occupancy)), SLEEP_AT_HOME=np.zeros(len(occupancy)))
    for i in range(0,len(occupancy)):
        occupancy.iloc[i,1] = next((int(re.split('[A-Z_=]+', occupancy.value[i][j])[1]) for j in range(0,len(occupancy.value[i])) if occupancy.value[i][j][0]=='H'),0)
        occupancy.iloc[i,2] = next((int(re.split('[A-Z_=]+', occupancy.value[i][j])[1]) for j in range(0,len(occupancy.value[i])) if occupancy.value[i][j][0]=='N'),0)
        occupancy.iloc[i,3] = next((int(re.split('[A-Z_=]+', occupancy.value[i][j])[1]) for j in range(0,len(occupancy.value[i])) if occupancy.value[i][j][0]=='S'),0)
    geo_data['occupancy'] = (occupancy.HOME+occupancy.SLEEP_AT_HOME)/(occupancy.NOT_AT_HOME+occupancy.SLEEP_AT_HOME+occupancy.HOME)
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
        #vmin=0,
        #vmax=1,
        ax=ax
    )
    ax.set_aspect(1)
    _ = plt.xticks([])
    _ = plt.yticks([])

    fig.savefig(path_to_choropleth, dpi=300)
    sns.set_context('paper')


if __name__ == '__main__':
    plot_simulation_results()
