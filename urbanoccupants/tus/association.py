from itertools import combinations

import click
import pandas as pd
import scipy.stats
import numpy as np

import urbanoccupants as uo

ALL_FEATURES = [
    uo.synthpop.PeopleFeature.ECONOMIC_ACTIVITY,
    uo.synthpop.PeopleFeature.QUALIFICATION,
    uo.synthpop.PeopleFeature.AGE,
    uo.synthpop.HouseholdFeature.HOUSEHOLD_TYPE,
    uo.synthpop.HouseholdFeature.POPULATION_DENSITY,
    uo.synthpop.HouseholdFeature.REGION,
    uo.synthpop.PeopleFeature.CARER,
    uo.synthpop.PeopleFeature.PERSONAL_INCOME
]

filter_features = uo.tus.individuals.filter_features_and_drop_nan


@click.command()
@click.argument('path_to_seed')
@click.argument('path_to_result')
def association_of_features(path_to_seed, path_to_result):
    """Calculates the association between people and household features.

    Association is defined by Cramer's V method.
    """
    seed = pd.read_pickle(path_to_seed)
    feature_correlation = pd.Series(
        index=combinations(ALL_FEATURES, 2),
        data=[cramers_corrected_stat(pd.crosstab(filter_features(seed, features)[features[0]],
                                                 filter_features(seed, features)[features[1]]))
              for features in combinations([str(feature) for feature in ALL_FEATURES], 2)]
    )
    feature_correlation.to_pickle(path_to_result)


def cramers_corrected_stat(confusion_matrix):
    """ Calculate Cramers V statistic for categorial-categorial association.
        uses correction from Bergsma and Wicher,
        Journal of the Korean Statistical Society 42 (2013): 323-328
    """
    # taken from http://stackoverflow.com/a/39266194/1856079
    chi2 = scipy.stats.chi2_contingency(confusion_matrix)[0]
    n = confusion_matrix.sum().sum()
    phi2 = chi2 / n
    r, k = confusion_matrix.shape
    phi2corr = max(0, phi2 - ((k - 1) * (r - 1)) / (n - 1))
    rcorr = r - ((r - 1)**2) / (n - 1)
    kcorr = k - ((k - 1)**2) / (n - 1)
    return np.sqrt(phi2corr / min((kcorr - 1), (rcorr - 1)))
