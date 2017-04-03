# Agent-Based Modelling of Occupant Presence in Residential Built Environments

// TODO update title

## Abstract

// TODO update abstract

Energy use in the urban residential sector corresponds directly to operation of energy consuming devices. For instance, space-heating  is a substantial element of residential energy consumption in the UK, but it is as much tied to occupant preferences and timing of their presence in a home, as it is to the physical characterstics of the dwelling. Timing, duration, and in-use efficiency of residential energy consumption are essential for increasing the utilization of district energy systems and demand-side management of (eg. through time-of-use tariffs). The study of occupant driven activities is inherently stochastic and multi-disciplinary. The ongoing IEA-EBC Annex 66 and our own recent work attests that there is a need to develop new methods to represent occupant presence and energy consuming activities in energy demand modelling. Indeed, few studies investigate micro-use patterns of energy use in detail at the urban-scale. This is as much a multi-scale simulation issue, as it is a computational challenge.

Agent-Based Models (ABMs) are able to simulate the distribution of people across the city at high spatial and temporal resolutions. This paper presents a proof-of-concept ABM model in....

Two step approach: (a) occupant presence or absence (b) occupant behaviour when present (setpoint) or absent (heating on timer)

In the near future, we envision that these models will also become crucial tools in optimizing the use of future digital innovations, e.g. smart metering and Internet of Things.

This work aims at identifying the impact of occupant 'presence' on the heating and cooling energy demand in buildings on an urban scale by representing occupants as agents in a city-wide model with high spatial and temporal resolution. The agent-based approach of the model allows for representing spatial variability and analysing space-time relationships by linking energy usage in space and time through occupants, their locations and activities. The model is applied in a case study of London.

## Introduction and Related Works

* heating system set points have high impact on building energy usage, as shown in former research

* if, contrary to normative building energy assessment, one is interested in _actual_ energy usage and not normative energy usage, exact heating set points are hence of high importance

* generally, the heating set point for a heating Zone z can be described by &theta;<sub>set, z</sub> = &theta;<sub>set, z</sub>(L<sub>P<sub>z</sub></sub>, A<sub>P<sub>z</sub></sub>, B<sub>P<sub>z</sub></sub>), where:

    * P<sub>z</sub>: set of people inside the heating zone or related to it
    * L<sub>P<sub>z</sub></sub> location of People P<sub>z</sub>
    * A<sub>P<sub>z</sub></sub> activity of People P<sub>z</sub>
    * B<sub>P<sub>z</sub></sub> heating behaviour (comfort zone, awareness, financial situation, usage pattern) of People P<sub>z</sub>

* for all (comfort zone, location, activity, heating behaviour), the social context is important, which brings spatial dimension into play // TODO rational for the need of spatial dimension still weak

## Methodology

### Conceptual Model

#### Set Point Model

Here the following simplifications are made compared to the general model above:

* zones = entire dwellings
* location = presence
* discrete time with steps of 10 min length
* heating behaviour reduced to simple categories

This leads to the simplified dynamic model of a heating set point for a dwelling d: &theta;<sub>set, d, k</sub> = &theta;<sub>set, d, k</sub>(P<sub>d, k</sub>, a<sub>P, k</sub>, B<sub>d</sub>), where:

* k in K = {all time steps}
* P<sub>d, k</sub> = {p in P<sub>d</sub> | p is in dwelling d at time step k}
* a<sub>P, k</sub> = 1 if at least someone in P<sub>k</sub> awake, 0 otherwise
* B<sub>d</sub> = {'constant set point', 'time triggered', 'presence & activity triggered'}, time invariant heating behaviour for dwelling d

#### People Model

Time heterogeneous markov chain with the following states:

* not at home
* active at home
* asleep at home

#### Thermal Model of Dwelling

See description of [conceptual model](https://github.com/timtroendle/spatial-cimo/blob/develop/doc/conceptual-model.md). // TODO update

Simplified 1 zone building energy model. Using the same model for each dwelling (?).

Rational for using the exact same model for each dwelling: this can be seen similar to the normative building energy assessment where the object of study is the building and its impact on energy demand. Heating behaviour is considered external *and always equal*. Here, the object of study is the heating behaviour of people and its impact on energy demand. The building could be considered external *and always equal*.

### Simulation Platform

agent based simulation

### Model Calibration

#### People Model

using time use survey data: cluster set of people by certain attributes (for example work status, role in household, household income, ...) and derive markov chain for all cluster of people.

The clustering must use and retain the features that will later be used for the synthetic population.

Possible procedure:

* create a people-model time series for each individual in the time use survey
* through feature selection identify the features of individuals that explain their day time series best
* start selecting features starting from the most important one, as long as the remaining cluster will stay large enough (must be at at least > 20) (maybe using ANOVA, analysis of variance)
* cluster people by those features (simply by their different values) and calculate markov chain for all cluster
* (later below: use those features as control features for the synthetic population)

#### Synthetic Population

Synthetic population using Hierarchical Iterative Proportional Fitting: fitting households and individuals at the same time

### Optional: Identification of Heating behaviour

Using measured energy data and using Bayesian inference, estimate the likelihood for a certain heating behaviour in a region.

## Case Study

short intro to London Haringey

describe data sets: UK Time Use Survey 2000, Census 2011, (UKBuildings?)

### Model Calibration Results

which attributes are significant in terms of energy usage?

### Simulation Results

test beds: (a) deterministic versus proposed ABM apporach -- compare timing and magnitude of peak; (b) relative importance of setpoint versus timing and duration of use; (c) relative importance of physical characterstics of dwelling versus stochastic representation of occupant activities

![Average thermal power per ward](../doc/figures/thermal_power_per_ward.png)
![Average thermal power per LSOA](../doc/figures/thermal_power_per_lsoa.png)
![Average thermal power per LSOA choropleth](../doc/figures/thermal_power_lsoa_choropleth.png)
![Distribution of average power](../doc/figures/distributation-average-power.png)
![Thermal power vs household size](../doc/figures/thermal-power-vs-household-size.png)

#### Impact of Population attributes on Energy Demand using Presence&Activity based heating

using the presence&activity based heating behaviour, run full simulation (for a week?) and discuss spatial patterns: different energy usage in certain regions based on population structure

#### Energy Savings Potential

Run another full simulation with a baseline heating behaviour (only time triggered or a mix //TODO howto define realistically?) and compare to the presence&activity based heating. Are there spatial patterns?

#### Likelihood of disaggregated heating behaviour

(optional): if possible, discuss likelihood of certain disaggregated heating behaviour per ward/lsoa

## Discussion & Conclusion

---

## Optional

Validate people's schedule against test data set.

Validate people's travels against London data set.

Validate energy simulation results. Goal: stay in certain *plausible* ranges.

Compare comfort level (temperature when home) for different HVAC control strategies.