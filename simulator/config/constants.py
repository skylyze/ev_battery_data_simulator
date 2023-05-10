# Copyright (C) 2022 - 2023 DSA Skylyze GmbH
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
# ======================================================================================================================
# set seed of random generator for reproducible results
SEED = None

# global time step size [s]
DT = 1

# desired simulation time [s]
SIM_TIME = 10 * 60**2 * 24  # 10 days simulation time

# device name
DEVICE_NAME = "test"

# starting parameter for simulation (used, if no status file available)
# change to values > 0 to start with an already worn battery
CYCLE_START = 0
TIMESTAMP_START = None
PARTIAL_CYCLE_CHARGING = 0.0
PARTIAL_CYCLE_DISCHARGING = 0.0
ENERGY_CHARGING = 0.0
ENERGY_DISCHARGING = 0.0

# limit for stopping discharge process
DISCHARGE_STOP = 0.2
# limit for stopping charging process
CHARGING_STOP = 0.95

# settings for discharge current profile generation
# indicator for using wltp or random profile
USE_WLTP = True

# if WLTP, provide class from 1 to 3
WLTP_CLASS = 3

# if not WLTP provide parameter for random profile
# minimum pulse length
PULSE_LEN_MIN = 2
# maximum pulse length
PULSE_LEN_MAX = 10
# minimum c value of discharge profile
C_MIN = -4.0
# maximum c value of discharge profile
C_MAX = 1.0
# mean c value of discharge profile
C_MEAN = -2.5

# directory for storing the outputs
LOGGING_DIR = "output/"
LOGGING_FORMATS = "tesla"  # "csv", "parquet", "json", "tesla"

# desired parameter of components to be logged during simulation (for csv, parquet or json)
LOGGING_PARAMETER = ["cycle", "soc", "volt", "cap_max", "current", "temp"]

# dump frequency [steps]
DUMP_FREQ = 1000

# TESLA
# log every LOG_FREQ [steps]: LVL1 -> bat_volt, LVL2 -> Cell params, LVL3 -> misc.
LOGGING_FREQ_LVL1 = 5
LOGGING_FREQ_LVL2 = 12 * LOGGING_FREQ_LVL1
LOGGING_FREQ_LVL3 = 24 * LOGGING_FREQ_LVL1

# temperature parameters
AMBIENT_TEMPERATURE = 20  # [°C]

# battery stack, source: https://circuitdigest.com/article/tesla-model-s-battery-system-an-engineers-perspective
BAT_AREA = 11.9 * 26.2 * 2.54 * 16 / 100**2  # only for Tesla P85! First two values in inch, 16 stacks [m²]
HEAT_TRANS_CONST = 50  # [W/(m²K)]
BMS_INLETPASSIVETARGET = 45  # [°C]
BMS_INLETACTIVECOOLTARGET = 50  # [-°C]
BMS_INLETACTIVEHEATTARGET = -16  # [°C]

# vehicle load profiles
# sources:
#   https://www.adac.de/rund-ums-fahrzeug/autokatalog/marken-modelle/tesla/model-s/1generation/237734/#technische-daten
#   https://www.mdpi.com/2032-6653/7/1/41
#   https://unitsky.engineer/assets/files/shares/2015/2015_80.pdf
MASS_VEHICLE = 2175  # mass of the empty car [kg]
MASS_LOAD = 495  # mass of the load (passengers, etc.) [kg]
GRAVITATION_CONSTANT = 9.81  # [m/s^2]
ROLL_RESISTANCE_COEFFICIENT = 0.015  # accounting roll resistance between car tires and ground [a. u.]
DENSITY_AIR = 1.2041  # @ 20 °C [kg/m^3]
AIR_RESISTANCE_COEFFICIENT = 0.24  # accounting opposing force caused by air resistance [a. u.]
AREA_CAR_CROSSSECTION = 2.34  # car cross-section, which effectively gets hit by air [m^2]
VELOCITIY_AIR = 0  # e. g., wind, ... [m/s]
ROTATIONAL_MASS_INERTIA_COEFFICIENT = 1.07  # inertia caused moving mass [a. u.]
ELECTRICAL_EFFICIENCY_COEFFICIENT = (
    0.6  # transformation efficiency mechanical vehicle to electrical battery power [a.u.]
)
POWER_LOSS = 1500  # power loss by other components, which don't contribute to driving (e. g., lighting) [W]
