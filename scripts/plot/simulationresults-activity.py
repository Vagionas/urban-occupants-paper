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
from urbanoccupants import PeopleFeature, HouseholdFeature
from urbanoccupants.types import EconomicActivity, AgeStructure
ROOT_FOLDER = Path(os.path.abspath(__file__)).parent.parent.parent
CACHE_PATH = ROOT_FOLDER / 'build' / 'web-cache'
requests_cache.install_cache((CACHE_PATH).as_posix())

ENERGY_TIME_SPAN = timedelta(days=7) # energy will be reported as kWh per timespan, e.g kWh per week


@click.command()
@click.argument('path_to_simulation_results')
@click.argument('path_to_config')
@click.argument('path_to_choropleth_plot')
@click.argument('path_to_plot')
@click.argument('timepoint')
def plot_simulation_results(path_to_simulation_results, path_to_config,
                            path_to_choropleth_plot,path_to_plot,timepoint):
    sns.set_context('paper')
    disk_engine = sqlalchemy.create_engine('sqlite:///{}'.format(path_to_simulation_results))
    dwellings = _read_dwellings(disk_engine)
    people = _read_people(disk_engine)
    print('Read dwellings, people')
    activity = _read_activity(uo.read_simulation_config(path_to_config), disk_engine, people, dwellings)
    print('Read activity')
    occ_EFT = _activity_to_occ_EFT(uo.read_simulation_config(path_to_config), activity)
    print('Created occ_EFT')
    geo_data = _read_geo_data(uo.read_simulation_config(path_to_config), activity, timepoint)
    print('Created geo_data')
    _plot_choropleth(geo_data, path_to_choropleth_plot)
    _plot_occupancy_by_feature(occ_EFT, path_to_plot)


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
        'SELECT * FROM {}'.format(uo.PEOPLE_TABLE_NAME),
        disk_engine,
        index_col='index'
    )
    return people
    

def _read_activity(config, disk_engine, people, dwellings):
    personId_to_dwellingId = {personId: people.loc[personId, 'dwellingId']
                            for personId in people.index}
    dwellingId_to_region = {dwellingId: dwellings.loc[dwellingId, 'region']
                            for dwellingId in dwellings.index}
    personId_to_markovChainId = {personId: people.loc[personId, 'markovChainId']
                            for personId in people.index}
    print('Created id maps')
    activity = pd.read_sql_query(
        'SELECT * FROM activity',
        disk_engine,
        index_col='timestamp',
        parse_dates=True
    )
    print(activity[:3])
    activity.index = pd.to_datetime(activity.index * 1000 * 1000)
    activity.index.name = 'datetime'
    activity.rename(columns={'id': 'person_id'}, inplace=True)
    activity['dwelling_id'] = activity.person_id.map(personId_to_dwellingId)
    activity['region'] = activity.dwelling_id.map(dwellingId_to_region)
    if config['people-features']==[PeopleFeature.ECONOMIC_ACTIVITY] or config['people-features']==[PeopleFeature.AGE]:
        print('Write feature')
        markovChain_id = activity.person_id.map(personId_to_markovChainId)
        markovChainId_to_peopleFeatureName = {markovChainId: _map_featureId_to_featureName(config, _inverse_pairing_function(markovChainId))
                                            for markovChainId in markovChain_id}
        activity['feature'] = markovChain_id.map(markovChainId_to_peopleFeatureName)
    return activity.reset_index()

def _inverse_pairing_function(markovChainId):
    w = int(((8*markovChainId+1)**(0.5)-1)/2)
    t = w*(w+1)/2
    householdFeatureId = markovChainId-t
    peopleFeatureId = w-householdFeatureId
    return peopleFeatureId

def _map_featureId_to_featureName(config, peopleFeatureId):
    if config['people-features']==[PeopleFeature.ECONOMIC_ACTIVITY]:
        peopleFeature_name = EconomicActivity(peopleFeatureId).name
    elif config['people-features']==[PeopleFeature.AGE]:
        peopleFeature_name = AgeStructure(peopleFeatureId).name
    return peopleFeature_name

def _activity_to_occ_EFT(config, activity):
    if config['people-features']==[PeopleFeature.ECONOMIC_ACTIVITY]:
        idx = pd.IndexSlice
        occupancy_by_feature = activity.groupby(['datetime','region','feature']).agg({'value': 'value_counts'})
        occ_EFT = occupancy_by_feature.sort_index().loc[idx[:,:,'EMPLOYEE_FULL_TIME',:],:].unstack().value.fillna(value=0)
        occ_EFT = occ_EFT.assign(proportion=(occ_EFT.HOME+occ_EFT.SLEEP_AT_HOME)/(occ_EFT.HOME+occ_EFT.NOT_AT_HOME+occ_EFT.SLEEP_AT_HOME))
    return occ_EFT.reset_index()

def _read_geo_data(config, activity, timepoint):
    geo_data = uo.census.read_shape_file(config['study-area'], config['spatial-resolution'])
    occupancy = activity.groupby(['datetime','region']).agg({'value': 'value_counts'})
    occupancy = occupancy.unstack().value.fillna(value=0)
    occupancy = occupancy.assign(proportion=(occupancy.HOME+occupancy.SLEEP_AT_HOME)/(occupancy.NOT_AT_HOME+occupancy.SLEEP_AT_HOME+occupancy.HOME))
    geo_data['occupancy'] = occupancy.sort_index().loc[timepoint,'HOME'].reset_index('datetime', drop=True)
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
        ax=ax
    )
    ax.set_aspect(1)
    _ = plt.xticks([])
    _ = plt.yticks([])

    fig.savefig(path_to_choropleth, dpi=300)
    sns.set_context('paper')

def _plot_occupancy_by_feature(occ_EFT, path_to_plot):
    def _xTickFormatter(x, pos):
        return pd.to_datetime(x).time()
    fig = plt.figure(figsize=(8, 4), dpi=300)
    ax1 = fig.add_subplot(111)
    sns.tsplot(
        data=occ_EFT,
        time='datetime',
        unit='region',
        value='proportion',
        err_style='unit_traces',
        ax=ax1
    )
    _ = plt.ylabel('proportion at home')
    _ = plt.xlabel('time of the day')
    ax1.set_ylim(bottom=0)

    points_in_time = occ_EFT.groupby('datetime').proportion.first().index
    xtick_locations = [0, 144 // 2-1, 143, 143 + 144 // 2] # not sure why they are shifted
    ax1.set_xticks([points_in_time[x].timestamp() * 10e8 for x in xtick_locations])
    ax1.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(_xTickFormatter))

    ax1.label_outer()

    fig.savefig(path_to_plot, dpi=300)


if __name__ == '__main__':
    plot_simulation_results()
