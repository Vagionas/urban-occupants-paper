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
def plot_simulation_results(path_to_simulation_results, path_to_config,
                            path_to_choropleth_plot):
    sns.set_context('paper')
    disk_engine = sqlalchemy.create_engine('sqlite:///{}'.format(path_to_simulation_results))
    dwellings = _read_dwellings(disk_engine)
    people = _read_people(disk_engine)
    activity = _read_activity(disk_engine, people, dwellings)
    geo_data = _read_geo_data(uo.read_simulation_config(path_to_config), activity)
    _plot_choropleth(geo_data, path_to_choropleth_plot)


def _read_dwellings(disk_engine):
    dwellings = pd.read_sql_query(
        'SELECT * FROM {}'.format(uo.DWELLINGS_TABLE_NAME),
        disk_engine,
        index_col='index'
    )
    people = pd.read_sql_query(
        'SELECT * FROM {}'.format(uo.PEOPLE_TABLE_NAME),
        disk_engine,
        index_col='index'
    )
    dwellings['householdSize'] = people.groupby('dwellingId').size()
    return dwellings


def _read_people(disk_engine):
    people = pd.read_sql_query(
        'SELECT * FROM {}'.format('people'),
        disk_engine,
        index_col='index'
    )
    return people
    

def _read_activity(disk_engine, people, dwellings):
    personId_to_dwellingId = {personId: people.loc[personId, 'dwellingId']
                            for personId in people.index}
    dwellingId_to_region = {dwellingId: dwellings.loc[dwellingId, 'region']
                            for dwellingId in dwellings.index}
    activity = pd.read_sql_query(
        'SELECT * FROM activity',
        disk_engine,
        index_col='timestamp',
        parse_dates=True
    )
    activity.index = pd.to_datetime(activity.index * 1000 * 1000)
    activity.index.name = 'datetime'
    activity.rename(columns={'id': 'person_id'}, inplace=True)
    activity['dwelling_id'] = activity.person_id.map(personId_to_dwellingId)
    activity['region'] = activity.dwelling_id.map(dwellingId_to_region)
    return activity.reset_index()


def _read_geo_data(config, activity):
    geo_data = uo.census.read_shape_file(config['study-area'], config['spatial-resolution'])
    occupancy = activity.groupby(['datetime','region']).agg({'value': 'value_counts'})
    geo_data['occupancy'] = occupancy.sort_index(level=2).loc['2005-01-07 12:00:00',:,'HOME'].value
    return geo_data


def _plot_choropleth(geo_data, path_to_choropleth):
    # The plot must be scaled, otherwise the legend will look weird. To bring
    # test sizes to a readable level, the seaborn context is set to poster.
    print(geo_data)
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
        ax=ax
    )
    ax.set_aspect(1)
    _ = plt.xticks([])
    _ = plt.yticks([])

    fig.savefig(path_to_choropleth, dpi=300)
    sns.set_context('paper')


if __name__ == '__main__':
    plot_simulation_results()
