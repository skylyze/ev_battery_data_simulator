# Battery data simulator

A simulator to generate battery data of an electric vehicle (EV) using WLTP or random driving profiles. The battery is
modeled according to an equivalent circuit model with one RC-branch. According to the setup of a real 
Tesla Model S P85 battery, single Panasonic NCR18650B battery cells are stacked in a configuration of "74S96P" to
generate the electrical profile of the whole battery. Although currently the configuration of a Tesla battery is used, the
simulator can be adjusted to other profiles and models (see chapter [customization](#customization)).

The generated data can be logged into a full .csv-file containing the full simulation or into single .json files containing
timestamp data for equidistant time steps according to the BMS of the Tesla Model S P85 (see chapter
[customization](#customization)).

An overview over the technical and scientific background relevant for this project will be provided in chapter
[Technical and scientific background](#technical-and-scientific-background).

## Getting started

To set up the program, use the provided Dockerfile to build a docker image with the necessary requirements:

```
docker build -t battery_simulator .
```
The output data of the simulator will be stored according to the settings in the file
[constants.py](simulator/config/constants.py) into the [simulator/config](./simulator/config) subdirectory. Per default,
it is set up for the subdirectory [output/logs](./output/logs) under the root directory.

After the installation is completed, you can run the simulation using the command:

```
docker run --rm -v "$(pwd)/output":/src/output -v "$(pwd)/simulator/status":/src/status battery_simulator
```

Doing so will start the simulation with pre-defined settings. The most important parameters are:

- DT: Global time step size (in seconds).
- SIM_TIME: Desired total simulation time (in seconds).
- DEVICE_NAME: Name of the device used during the simulation. Useful for resuming simulations.
- CYCLE_START: Number of cycle the battery has at the start of the simulation. A value > 0 indicates an already worn
battery. The cycle number is used to compute the degradation of the battery.
- DISCHARGE_STOP: Limit for stopping the discharging process. This is the mean value of a triangular shaped distribution
with a left cut-off of 5 % and a right cut-off of 60 % for the value used in the individual simulation step.
- CHARGING_STOP: Limit for stopping the charging process. This is the mean value of a triangular shaped distribution
with a left cut-off of 60 % and a right cut-off of 98 % for the value used in the individual simulation step.
- USE_WLTP + WLTP_CLASS <u>**OR**</u> PULSE_{LEN_MIN + LEN_MAX} + C_{MIN + MAX + MEAN}: Defines the discharge current
profile. The combination of WLTP parameter define a real driving profile (see details in chapter.
[Technical and scientific background](#technical-and-scientific-background)). Alternatively, a random profile can be
used defined by.
- LOGGING_{DIR + FORMATS}: Specifies the location for the logging files generated during the simulation process. Per
default, it is set to the [/output/logs](./output/logs) directory. The parameter LOGGING_FORMATS should always be set to
"tesla". This will log the battery data as .json files containing parameter specified in the function "tesla_signals"
defined in the script [./simulator/logger.py](./simulator/logger.py).
- DUMP_FREQ: Number of steps for saving the logging files.
- LOGGING_FREQ_LVL{1,2,3}: Specifies the frequency of saving battery parameters to the logging file. Some parameters
need to be logged more often (e.g. battery current or voltage) while some do not (e.g. battery state of chage).
Using the default settings is a good choice, because they are aligned to a real world setup.

See chapter [customization](#customization) to set up an individual configuration for the simulation. For more
information about the parameter, check chapter
[Technical and scientific background](#technical-and-scientific-background) or the sources provided in the config
scripts.

## Customization
If you run the code as described above, you will be generating data simulating a Tesla Model S P85 battery as described
in the introduction and using the pre-defined settings. You can adapt the simulator to your individual needs by changing
the scripts located in the [config](./simulator/config) directory:

- [cell.json](./simulator/config/cell.json): Contains cell specific parameters. The cells are combined to create the
battery used in the simulation. Apply changes here to build a different battery.
- [constants.py](./simulator/config/constants.py): Contains the parameter controlling the simulation. This includes
general settings like for example the global time step size, overall desired simulation time or data logging, but also
specific parameter for the discharging (driving) profile or the heat model.  


## Technical and scientific background
TBA

[This section describes the basic scientific methods included in this work and add references for more in-depth info]: #
[ECM for modeling batteries, degradation, driving profiles, temperature model]: #
[Test]: #

## Support
You can contact us via E-Mail at contact@skylyze.de. Alternatively, you can reach out to the authors
Marcell Wolnitza (marcell.wolnitza@dsa.de) and Pascal Rößner (pascal.roessner@dsa.de).

## Authors and acknowledgment
This repository is maintained by the company DSA Skylyze GmbH (see license for additional information). Marcell
Wolnitza is the creator and main contributor of this project. Pascal Rößner is the lead development manager regarding
the software engineering. Roland Stoffel and Oguz Budak provided valuable scientific ideas and information and
are responsible for the project management. Christian Rausch helped with the data integrity.

## License
Copyright (C) 2022 - 2023 DSA Skylyze GmbH

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General
Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License along with this program.
If not, see <https://www.gnu.org/licenses/>.
