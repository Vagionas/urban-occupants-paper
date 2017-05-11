import click
import matplotlib.pyplot as plt
import pandas as pd


import urbanoccupants as uo

FEATURES_TO_PLOT = [
    uo.PeopleFeature.AGE,
    uo.PeopleFeature.ECONOMIC_ACTIVITY,
    uo.HouseholdFeature.POPULATION_DENSITY,
    uo.HouseholdFeature.REGION,
    (uo.PeopleFeature.ECONOMIC_ACTIVITY, uo.PeopleFeature.AGE),
    (uo.PeopleFeature.ECONOMIC_ACTIVITY, uo.PeopleFeature.AGE, uo.HouseholdFeature.HOUSEHOLD_TYPE)
]


@click.command()
@click.argument('path_to_ts_association')
@click.argument('path_to_plot')
def association_plots(path_to_ts_association, path_to_plot):
    ts_association = pd.read_pickle(path_to_ts_association)
    ts_association = ts_association.filter([_features_to_string(f) for f in FEATURES_TO_PLOT],
                                           axis=1)
    ax = ts_association.plot(figsize=(14, 7))
    _ = plt.ylabel("Cramer's phi association")
    _ = plt.xlabel("time step")
    plt.savefig(path_to_plot, dpi=300)


def _features_to_string(features):
    if isinstance(features, tuple):
        return tuple([str(feature) for feature in features])
    else:
        return str(features)


if __name__ == '__main__':
    association_plots()
