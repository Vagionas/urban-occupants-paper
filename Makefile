# Build MS Word paper.
build:
	mkdir ./build

.PHONY: paper clean tus-data test
paper:  build build/paper.docx

clean:
	rm -rf ./build/*

test:  build
	py.test

tus-data: build/seed.pickle build/markov-ts.pickle

build/seed.pickle: ./data/UKDA-4504-tab/tab/Individual_data_5.tab ./scripts/tus/seed.py  build
	python ./scripts/tus/seed.py ./data/UKDA-4504-tab/tab/Individual_data_5.tab ./build/seed.pickle

build/markov-ts.pickle: ./data/UKDA-4504-tab/tab/diary_data_8.tab ./scripts/tus/markovts.py  build
	python ./scripts/tus/markovts.py ./data/UKDA-4504-tab/tab/diary_data_8.tab ./build/markov-ts.pickle

build/feature-association.pickle build/ts-association.pickle: ./build/seed.pickle ./build/markov-ts.pickle ./scripts/tus/association.py
	python ./scripts/tus/association.py ./build/seed.pickle ./build/markov-ts.pickle ./build/feature-association.pickle ./build/ts-association.pickle

build/ts-association-filtered-stats.csv: build/ts-association.pickle scripts/tus/analyseassociation.py
	python scripts/tus/analyseassociation.py build/seed.pickle build/ts-association.pickle build/ts-association-full-stats.csv build/ts-association-filtered-stats.csv

build/ts-association.png: ./build/ts-association.pickle ./scripts/plot/association.py
	python ./scripts/plot/association.py ./build/ts-association.pickle ./build/ts-association.png

build/population-cluster.png: ./build/seed.pickle ./build/markov-ts.pickle ./scripts/plot/popcluster.py
	python ./scripts/plot/popcluster.py ./build/seed.pickle ./build/markov-ts.pickle ./build/population-cluster.png

build/sim-input.db: ./build/seed.pickle ./build/markov-ts.pickle ./config/default.yaml ./scripts/simulationinput.py
	python ./scripts/simulationinput.py ./build/seed.pickle ./build/markov-ts.pickle ./config/default.yaml build/sim-input.db

build/energy-agents.jar:  build
	curl -Lo build/energy-agents.jar 'https://github.com/Vagionas/energy-agents/releases/download/v1.0.1/energy-agents-1.0.1-jar-with-dependencies.jar'

build/sim-output.db: build/energy-agents.jar build/sim-input.db scripts/runsim.py config/default.yaml
	python scripts/runsim.py build/energy-agents.jar build/sim-input.db build/sim-output.db config/default.yaml

build/sim-output-default-ward.db: build/energy-agents.jar build/seed.pickle build/markov-ts.pickle config/default-ward.yaml scripts/simulationinput.py scripts/runsim.py
	python scripts/simulationinput.py build/seed.pickle build/markov-ts.pickle config/default-ward.yaml build/sim-input-default-ward.db
	python scripts/runsim.py build/energy-agents.jar build/sim-input-default-ward.db build/sim-output-default-ward.db config/default-ward.yaml

build/sim-output-age.db: build/energy-agents.jar build/seed.pickle build/markov-ts.pickle config/age.yaml scripts/simulationinput.py scripts/runsim.py
	python scripts/simulationinput.py build/seed.pickle build/markov-ts.pickle config/age.yaml build/sim-input-age.db
	python scripts/runsim.py build/energy-agents.jar build/sim-input-age.db build/sim-output-age.db config/age.yaml

build/sim-output-qual.db: build/energy-agents.jar build/seed.pickle build/markov-ts.pickle config/qual.yaml scripts/simulationinput.py scripts/runsim.py
	python scripts/simulationinput.py build/seed.pickle build/markov-ts.pickle config/qual.yaml build/sim-input-qual.db
	python scripts/runsim.py build/energy-agents.jar build/sim-input-qual.db build/sim-output-qual.db config/qual.yaml

build/sim-output-pseudo.db: build/energy-agents.jar build/seed.pickle build/markov-ts.pickle config/pseudo.yaml scripts/simulationinput.py scripts/runsim.py
	python scripts/simulationinput.py build/seed.pickle build/markov-ts.pickle config/pseudo.yaml build/sim-input-pseudo.db
	python scripts/runsim.py build/energy-agents.jar build/sim-input-pseudo.db build/sim-output-pseudo.db config/pseudo.yaml

build/thermal-diff.png: build/sim-output-pseudo.db build/sim-output-qual.db
build/thermal-diff.png: build/sim-output-default-ward.db build/sim-output-age.db scripts/plot/powerdiff.py
	python scripts/plot/powerdiff.py build/sim-output-default-ward.db 'age' build/sim-output-age.db 'qualification' build/sim-output-qual.db 'none' build/sim-output-pseudo.db build/thermal-diff.png

build/thermal-power.png build/choropleth.png build/scatter.png: build/sim-output.db config/default.yaml scripts/plot/simulationresults.py
	python scripts/plot/simulationresults.py build/sim-output.db config/default.yaml build/thermal-power.png build/choropleth.png build/scatter.png

build/paper.docx: doc/literature.bib doc/online.bib doc/main.md doc/pandoc-metadata.yml
build/paper.docx: build/ts-association.png build/population-cluster.png build/thermal-power.png
build/paper.docx: build/choropleth.png build/scatter.png build/thermal-diff.png
build/paper.docx: build/ts-association-filtered-stats.csv doc/figures/flow-chart-time-step.png
	cd ./doc && \
	pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos --filter pandoc-citeproc \
		--reference-docx ./paper-template.docx main.md pandoc-metadata.yml -t docx -o ../build/paper.docx


build/sim-input-london.db: ./build/seed.pickle ./build/markov-ts.pickle ./config/greater-london.yaml ./scripts/simulationinput.py
	python ./scripts/simulationinput.py ./build/seed.pickle ./build/markov-ts.pickle ./config/greater-london.yaml build/sim-input-london.db

build/sim-output-london.db: build/energy-agents.jar build/sim-input-london.db scripts/runsim.py config/greater-london.yaml
	python scripts/runsim.py build/energy-agents.jar build/sim-input-london.db build/sim-output-london.db config/greater-london.yaml

build/choropleth-london.png: build/sim-output-london.db config/greater-london.yaml scripts/plot/simulationresultsaggregated.py
	python scripts/plot/simulationresultsaggregated.py build/sim-output-london.db config/greater-london.yaml build/choropleth-london.png


build/choropleth-econ-test-21-07.png:
	python scripts/plot/simulationresults-test-21-07.py build/sim-output-econ-test-21-07.db config/econ-test-21-07.yaml build/choropleth-econ-test-21-07.png


build/sim-input-london-activity.db:
	python ./scripts/simulationinput.py ./build/seed.pickle ./build/markov-ts.pickle ./config/greater-london-activity.yaml build/sim-input-london-activity.db

build/sim-ouput-london-activity.db:
	python scripts/runsim.py build/energy-agents.jar build/sim-input-london-activity.db build/sim-output-london-activity.db config/greater-london-activity.yaml

build/choropleth-london-activity-1200.png: build/sim-output-london.db config/greater-london.yaml scripts/plot/simulationresultsaggregated.py
	python scripts/plot/simulationresultsaggregated-activity.py build/sim-output-london-activity.db config/greater-london-activity.yaml build/choropleth-london-activity-1200.png "2005-01-07 12:00:00"


