from collections import OrderedDict
from datetime import datetime, timedelta

import pykov
import pytest

from people import Person


@pytest.fixture
def pseudo_random():
    class Generator:

        number = 0.5

        def __call__(self, min, max):
            return self.number

    return Generator()


@pytest.fixture
def day_markov_chain():
    return pykov.Chain(OrderedDict([
        (('sleep', 'work'), 0.9),
        (('sleep', 'sleep'), 0.1),
        (('work', 'sleep'), 0.2),
        (('work', 'work'), 0.8)
    ]))


@pytest.fixture
def night_markov_chain():
    return pykov.Chain(OrderedDict([
        (('sleep', 'work'), 0.0),
        (('sleep', 'sleep'), 1.0),
        (('work', 'sleep'), 0.7),
        (('work', 'work'), 0.3)
    ]))


@pytest.fixture
def activity_markov_chains(day_markov_chain, night_markov_chain):
    chain = {}
    chain['weekday'] = {hour: day_markov_chain if (hour >= 9 and hour < 17)
                        else night_markov_chain
                        for hour in range(24)}
    chain['weekend'] = {hour: night_markov_chain for hour in range(24)}
    return chain


@pytest.fixture
def sleeping_person(activity_markov_chains, pseudo_random):
    return Person(
        activity_markov_chains=activity_markov_chains,
        number_generator=pseudo_random,
        initial_activity='sleep',
        initial_time=datetime(2016, 12, 13, 16, 00), # Tuesday
        time_step_size=timedelta(hours=1)
    )


@pytest.fixture
def weekend_person(activity_markov_chains, pseudo_random):
    return Person(
        activity_markov_chains=activity_markov_chains,
        number_generator=pseudo_random,
        initial_activity='work',
        initial_time=datetime(2016, 12, 18, 16, 00), # Sunday
        time_step_size=timedelta(hours=1)
    )


def test_sleeping_person_starts_working_during_day(sleeping_person, pseudo_random):
    pseudo_random.number = 0.8
    sleeping_person.step()
    assert sleeping_person.activity == 'work'


def test_sleeping_person_remains_sleeping_during_day(sleeping_person, pseudo_random):
    pseudo_random.number = 0.91
    sleeping_person.step()
    assert sleeping_person.activity == 'sleep'


def test_working_person_remains_working_on_weekend(weekend_person, pseudo_random):
    pseudo_random.number = 0.71
    weekend_person.step()
    assert weekend_person.activity == 'work'


def test_working_person_starts_sleeping_on_weekend(weekend_person, pseudo_random):
    pseudo_random.number = 0.69
    weekend_person.step()
    assert weekend_person.activity == 'sleep'


def test_working_person_starts_sleeping_during_night(sleeping_person, pseudo_random):
    pseudo_random.number = 0.8
    sleeping_person.step()
    pseudo_random.number = 0.69
    sleeping_person.step()
    assert sleeping_person.activity == 'sleep'
