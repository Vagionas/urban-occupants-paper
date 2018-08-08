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
@click.argument('path_to_plot')
def plot_simulation_results(path_to_simulation_results, path_to_config,
                            path_to_choropleth_plot, path_to_plot):
    sns.set_context('paper')
    disk_engine = sqlalchemy.create_engine('sqlite:///{}'.format(path_to_simulation_results))
    avg_thermal_power = _read_average_thermal_power(disk_engine)
    std_thermal_power = _read_std_thermal_power(disk_engine)
    geo_data = _read_geo_data(uo.read_simulation_config(path_to_config), avg_thermal_power, std_thermal_power)
    _plot_choropleth(geo_data, path_to_choropleth_plot)
    _plot_thermal_power(avg_thermal_power,std_thermal_power,path_to_plot)


def _read_average_thermal_power(disk_engine):
    avg_thermal_power = pd.read_sql_query(
        'SELECT * FROM averageThermalPower',
        disk_engine,
        index_col='timestamp',
        parse_dates=True
    )
    avg_thermal_power.index = pd.to_datetime(avg_thermal_power.index * 1000 * 1000)
    avg_thermal_power.index.name = 'datetime'
    avg_thermal_power['region'] = avg_thermal_power.id.map(_district_id_int_to_str)
    return avg_thermal_power.reset_index()

def _read_std_thermal_power(disk_engine):
    std_thermal_power = pd.read_sql_query(
        'SELECT * FROM stdThermalPower',
        disk_engine,
        index_col='timestamp',
        parse_dates=True
    )
    std_thermal_power.index = pd.to_datetime(std_thermal_power.index * 1000 * 1000)
    std_thermal_power.index.name = 'datetime'
    std_thermal_power['region'] = std_thermal_power.id.map(_district_id_int_to_str)
    return std_thermal_power.reset_index()

def _district_id_int_to_str(district_id_int):
    as_string = list(str(district_id_int))
    as_string[0] = 'E'
    return "".join(as_string)


def _read_geo_data(config, avg_thermal_power, std_thermal_power):
    geo_data = uo.census.read_shape_file(config['study-area'], config['spatial-resolution'])

    avg_energy = avg_thermal_power.copy()
    std_energy = std_thermal_power.copy()
    avg_energy.value = avg_energy.value * config['time-step-size'].total_seconds() / 1000 / 3600 # kWh
    std_energy.value = std_energy.value * config['time-step-size'].total_seconds() / 1000 / 3600 # kWh
    duration = avg_thermal_power.datetime.max() - avg_thermal_power.datetime.min()
    if config['reweight-to-full-week']:
        print('Reweighting energy to full week. Make sure that is what you want.')
        avg_energy = _reweight_energy(avg_energy)
        std_energy = _reweight_energy(std_energy)
        duration = duration * 7 / 2
    geo_data['average energy'] = (avg_energy.groupby('region').value.sum() /
                                  duration.total_seconds() * ENERGY_TIME_SPAN.total_seconds())
    geo_data['standard deviation energy'] = (std_energy.groupby('region').value.sum() /
                                  duration.total_seconds() * ENERGY_TIME_SPAN.total_seconds())
    return geo_data


def _reweight_energy(energy):
    weekend_mask = ((energy.set_index('datetime', drop=True).index.weekday == 5) |
                    (energy.set_index('datetime', drop=True).index.weekday == 6))
    weekday_mask = np.invert(weekend_mask)
    energy_re = energy.copy()
    energy_re.loc[weekend_mask, 'value'] = energy.loc[weekend_mask, 'value'] * 2
    energy_re.loc[weekday_mask, 'value'] = energy.loc[weekday_mask, 'value'] * 5
    return energy_re


def _plot_choropleth(geo_data, path_to_choropleth):
    # The plot must be scaled, otherwise the legend will look weird. To bring
    # test sizes to a readable level, the seaborn context is set to poster.
    sns.set_context('poster')
    fig = plt.figure(figsize=(18, 8))
    ax = fig.add_subplot(121)
    gpdplt.plot_dataframe(
        geo_data,
        column='average energy',
        categorical=False,
        linewidth=0.2,
        legend=True,
        cmap='viridis',
        ax=ax
    )
    ax.set_aspect(1)
    _ = plt.xticks([])
    _ = plt.yticks([])
    ax.annotate('(a)', xy=[-0.15, 0.5], xycoords='axes fraction')

    ax = fig.add_subplot(122)
    gpdplt.plot_dataframe(
        geo_data,
        column='standard deviation energy',
        categorical=False,
        linewidth=0.2,
        legend=True,
        cmap='viridis',
        ax=ax
    )
    ax.set_aspect(1)
    _ = plt.xticks([])
    _ = plt.yticks([])
    ax.annotate('(b)', xy=[-0.15, 0.5], xycoords='axes fraction')

    fig.savefig(path_to_choropleth, dpi=300)
    sns.set_context('paper')


def _plot_thermal_power(avg_thermal_power, std_thermal_power, path_to_plot):
    def _xTickFormatter(x, pos):
        return pd.to_datetime(x).time()
    fig = plt.figure(figsize=(8, 4), dpi=300)
    ax1 = fig.add_subplot(2, 1, 1)
    sns.tsplot(
        data=avg_thermal_power,
        time='datetime',
        unit='region',
        value='value',
        err_style='unit_traces',
        ax=ax1
    )
    _ = plt.ylabel('average [W]')
    _ = plt.xlabel('time of the day')
    ax1.set_ylim(bottom=0)


    ax2 = fig.add_subplot(2, 1, 2, sharex=ax1)
    sns.tsplot(
        data=std_thermal_power,
        time='datetime',
        unit='region',
        value='value',
        err_style='unit_traces',
        ax=ax2
    )
    _ = plt.ylabel('standard deviation [W]')
    _ = plt.xlabel('time of the day')
    ax2.set_ylim(bottom=0)

    points_in_time = avg_thermal_power.groupby('datetime').value.mean().index
    xtick_locations = [0, 144 // 2-1, 143, 143 + 144 // 2] # not sure why they are shifted
    ax2.set_xticks([points_in_time[x].timestamp() * 10e8 for x in xtick_locations])
    ax2.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(_xTickFormatter))

    ax1.label_outer()
    ax2.label_outer()

    fig.savefig(path_to_plot, dpi=300)


if __name__ == '__main__':
    plot_simulation_results()
