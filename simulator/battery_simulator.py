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
from typing import List, Dict, Generator

import numpy as np
import pandas as pd

from config.constants import *
from cell import Cell
from stack import Stack
from battery import Battery
from utils import add_noise, rand
from logger import Logger
from discharge_profile import DischargeCurrentProfiles


class Simulation:
    """
    Handles and manages the simulation of the battery through one or many cycles.
    """

    def __init__(
        self,
        bat: Battery = None,
        t: int = 0,
        cycle_start: int = 0,
        timestamp_start: str = None,
        partial_cycle_charging: float = 0.0,
        partial_cycle_discharging: float = 0.0,
    ):
        """
        Initialization of simulation object with global parameter.

        :param bat: Object used for simulation
        :type bat: Battery
        :param t: Global time [s] used for simulation
        :type t: int
        :param cycle_start: Initial cycle of battery for current run of simulation
        :type cycle_start: int
        :param timestamp_start: Initial timestamp for current run of simulation
        :type timestamp_start: str
        :param partial_cycle_charging: Charging proportion of cycle, saved for checkpointing
        :type partial_cycle_charging: float
        :param partial_cycle_discharging: Discharging proportion of cycle, saved for checkpointing
        :type partial_cycle_discharging: float
        """

        # total time in simulation
        self.t = int(t / DT)
        # battery object used for simulation
        self.bat = bat
        # create logger, which at least provides history object at the end of simulate
        self.logger = Logger(obj=bat)
        # variable for cumulative cycle calculation during charging
        self.partial_cycle_charging = partial_cycle_charging
        # variable for cumulative cycle calculation during discharging
        self.partial_cycle_discharging = partial_cycle_discharging

        # starting variables for resuming simulation runs
        self.cycle_start = cycle_start
        self.timestamp_start = timestamp_start

        # class for discharge profile containing generator which outputs c_values for every time step
        self.discharge_profile = None

    def set_properties(self, prop: Dict):
        """
        Helping function to set battery properties during simulation.

        :param prop: Dictionary containing key and value pairs, which should be set
        :type prop: Dict
        """

        if isinstance(prop, dict):
            for key in prop:
                self.bat.__dict__[key] = prop[key]
        else:
            raise AssertionError(
                "PROP must be a dict containing key and value pairs, e.g. {'voltage': X, 'capacity': Y}"
            )

    def create_battery(
        self,
        num_stacks: int = 16,
        num_cells_per_stack: int = 6 * 74,
        config_bat: str = "16S1P",
        config_stack: str = "6S74P",
        energy_charging: float = 0.0,
        energy_discharging: float = 0.0,
    ) -> Battery:
        """
        Creates a battery object composed of stacks and cells of desired configuration.
        Default values for Tesla Model S P85 Battery, source: https://en.wikipedia.org/wiki/Tesla_Model_S.

        :param num_stacks: Number of stacks the battery should be composed of
        :type num_stacks: int
        :param num_cells_per_stack: Number of cells per stack
        :type num_cells_per_stack: int
        :param config_bat: Wiring configuration of the battery. Determines the electrical properties based on the stacks
        :type config_bat: str
        :param config_stack: Wiring configuration of the stacks. Determines the electrical properties based on the cells
        :type config_stack: str
        :param energy_charging: Cumulative energy from charging, saved for checkpointing
        :type energy_charging:
        :param energy_discharging: Cumulative energy from discharging, saved for checkpointing
        :type energy_discharging:
        :return: Battery object (and it's components) used for simulation
        :rtype: Battery
        """

        # set up cells
        cells = []
        for _ in range(num_stacks * num_cells_per_stack):
            # initialize cell objects
            cell = Cell()
            # set cell configuration to data from datasheet
            cell.set_config(cycle_start=self.cycle_start)
            cells.append(cell)
        # add small noise to some parameter
        add_noise(["volt", "cap", "temp", "weight"], cells)
        for idx, cell in enumerate(cells):
            # apply degradation of cells for cycle_start > 0
            # cell.degradation_start()  ToDo: Reactivate
            # set cells name
            cell.name = "cell" + str(idx)

        # set up stacks
        stacks = []
        for i in range(num_stacks):
            # initialize stack objects
            stack = Stack(cell_list=cells[num_cells_per_stack * i : num_cells_per_stack * (1 + i)], config=config_stack)
            # calc stack properties according to cells used
            stack.calc_stack_prop()
            # apply degradation of stacks for cycle_start > 0
            # stack.degradation_start()  ToDo: Reactivate
            # set stacks name
            stack.name = "stack" + str(i)
            stacks.append(stack)

        # initialize battery object
        bat = Battery(config=config_bat, stack_list=stacks, cycle_start=self.cycle_start)
        # calc battery properties according to stacks used
        bat.calc_bat_prop()
        # apply degradation of battery for cycle_start > 0
        bat.degradation_start()
        bat.name = "bat0"
        self.bat = bat
        # set relevant object to log data from
        self.logger.bat = bat
        # variables for cumulative energy throughput
        self.bat.energy_charging = energy_charging
        self.bat.energy_discharging = energy_discharging
        return bat

    def charging(self, constant_current: float = 1.625, charging_stop: float = 0.065):
        """
        Method for charging the battery.

        :param constant_current: Current [A] for charging in cc (constant current) mode
        :type constant_current: float
        :param charging_stop: Termination criterion for stopping the charging process @ low current [A]
        :type charging_stop: float
        """

        # loading parameter
        self.bat.current = constant_current  # charge battery with 90 A
        # 96 cells are wired serially(=bat_config_num_s * stack.config_num_s), value of voltage from single cell
        # adjusted by linear increment of voltage over capacity
        self.bat.volt = self.bat.volt_min + self.bat.soc / 0.8 * (self.bat.volt_max - self.bat.volt_min)

        self.bat.calc_state_of_charge()
        self.bat.mode = "charge"
        self.bat.propagate_attributes(["mode"])
        self.bat.current_min = 0
        # termination criterion: charging current < X mA && capacity >= capacity_max
        charging_stop_rand = rand.triangular(left=0.6, mode=CHARGING_STOP, right=0.98)  # random stop in sensible range
        while (self.bat.current > charging_stop) and (self.bat.cap <= self.bat.cap_max * charging_stop_rand):
            bat_soc = self.bat.soc  # "old" soc for calculation of cumulative battery cycle
            self.bat.load_battery_step(constant_current=constant_current)
            self.t += 1
            # add incremental soc and energy for cumulative battery cycle
            self.partial_cycle_charging += self.bat.soc - bat_soc
            self.bat.energy_charging += self.bat.volt * self.bat.current * DT
            # log parameter every LOGGING_FREQ steps
            self.logger.log(time=self.t)
        # set battery current to zero after charging
        self.bat.current = 0.0

    def discharge_battery_step(self, current: float):
        """Carries out one step of the battery discharging step.

        :param current: Battery current [A] for a single (time) step of discharging
        :type current: float
        """

        self.bat.calc_state_of_charge()
        self.bat.mode = "discharge"
        self.bat.propagate_attributes(["mode"])
        # "old" soc for calculation of cumulative battery cycle
        bat_soc = self.bat.soc

        self.bat.current = current * self.bat.cap_max_0
        # calculate battery discharge profile (voltage) based on capacity and current
        self.bat.discharge_profile()
        # charge provided from current during time step
        charge_per_timestep = self.bat.current * DT
        # Subtracted (current is negative) capacity in Ah during time step
        self.bat.cap += charge_per_timestep / 60**2

        # update battery state of charge
        self.bat.calc_state_of_charge()
        # calc cell temp
        self.bat.calc_temperature()

        self.t += 1
        # add incremental soc and energy for cumulative battery cycle
        self.partial_cycle_discharging += bat_soc - self.bat.soc
        self.bat.energy_discharging += self.bat.volt * abs(self.bat.current) * DT
        # log parameter every LOGGING_FREQ steps
        self.logger.log(time=self.t)

    def pause(self, time: float = 3 * 60):
        """
        Mode for battery, if no charging or discharging is applied (e.g., parking).

        :param time: Time [s] in pause mode.
        :type time: float
        """

        # counter for time in pause mode
        t_pause = 0
        self.bat.mode = "pause"
        self.bat.propagate_attributes(["mode"])

        self.bat.current_min = 0
        self.bat.current_max = 0
        while t_pause < (time / DT):
            # calc cell temp
            self.bat.calc_temperature()
            # increment time
            self.t += 1
            t_pause += 1
            # log parameter every LOGGING_FREQ steps
            self.logger.log(time=self.t)

    def charge_battery_step(self, current: float):
        """Carries out one step of the battery charging process.

        :param current: Battery current [A] for single (time) step of charging
        :type current: float
        """

        self.bat.calc_state_of_charge()
        self.bat.mode = "charge"
        self.bat.propagate_attributes(["mode"])
        # "old" soc for calculation of cumulative battery cycle
        bat_soc = self.bat.soc

        self.bat.current = current * self.bat.cap_max_0
        # charge provided from constant current during time step
        charge_per_timestep = self.bat.current * DT
        # Added capacity in Ah during time step
        self.bat.cap += charge_per_timestep / 60**2

        dU = charge_per_timestep / self.bat.capacitance  # dU = dQ / C, voltage increment per time step

        self.bat.volt += dU
        # update battery state of charge
        self.bat.calc_state_of_charge()
        # calc cell temp
        self.bat.calc_temperature()

        self.t += 1
        # add incremental soc and energy for cumulative battery cycle
        self.partial_cycle_charging += self.bat.soc - bat_soc
        self.bat.energy_charging += self.bat.volt * self.bat.current * DT
        # log parameter every LOGGING_FREQ steps
        self.logger.log(time=self.t)

    def simulate(
        self, sim_time: int, discharge_stop: float = DISCHARGE_STOP, charge_stop: float = CHARGING_STOP
    ) -> Dict:
        """
        Main method handling the simulation of the battery.

        :param sim_time: Simulation time [s]
        :type sim_time: int
        :param discharge_stop: State of charge limit for stopping battery discharge
        :type discharge_stop: float
        :param charge_stop: State of charge limit for stopping battery charging
        :type charge_stop: float
        :return: History dict containing logging parameter at every LOGGING_FREQ time steps
        :rtype: Dict
        """
        # starting condition
        # set battery voltage to maximum at full capacity
        self.bat.volt = self.bat.volt_max
        self.bat.cap = self.bat.cap_max * charge_stop
        # calc battery state of charge after setting parameter manually above
        self.bat.calc_state_of_charge()
        self.bat.current = 0  # start parking
        # set parameter of Logger, depending on hyperparameter and simulation obj
        self.logger.prepare_logger_setup(timestamp_start=self.timestamp_start)
        # setup generator yielding current for dynamic driving behavior
        args = (
            ["simulator/driving_protocols/wltp_class" + str(WLTP_CLASS) + ".csv"]
            if USE_WLTP
            else [PULSE_LEN_MIN, PULSE_LEN_MAX, C_MIN, C_MAX, C_MEAN]
        )
        self.discharge_profile = DischargeCurrentProfiles(
            battery=self.bat, time_step_size=DT, use_wltp=USE_WLTP, args=args
        )

        while self.t < (sim_time / DT):
            # pause before beginning of discharge
            self.pause(time=rand.uniform(low=5 * 60, high=30 * 60))
            # discharging
            self.dynamic_driving_behavior(
                generator=self.discharge_profile.select_generator(), discharge_stop_mean=discharge_stop
            )
            # check if full cycle reached, then increment and apply degradation
            self.check_increment_cycle()
            # pause before beginning of charging
            self.pause(time=rand.uniform(low=5 * 60, high=30 * 60))  # pause at end of discharging
            # charging
            self.charging(constant_current=90, charging_stop=0.3)  # stop charging @ 300 mA
            # check if full cycle reached, then increment and apply degradation
            self.check_increment_cycle()
            # pause at the end of charging
            self.pause(time=rand.uniform(low=2 * 60**2, high=8 * 60**2))
            # print("Run done.")

        # save history to parquet file if wanted
        if self.logger.parquet:
            self.logger.log_parquet(self.logger.hist)
        # return dict containing the progress of desired parameter during simulation
        return self.logger.hist

    def dynamic_driving_behavior(self, generator: Generator, discharge_stop_mean: float):
        """
        Manages battery charging and discharging processes depending on input current during vehicle driving mode.

        :param generator: Generator yielding random current values, which simulates a driving profile
        :type generator: Generator
        :param discharge_stop_mean: State of charge limit for stopping discharging the battery
        :type discharge_stop_mean: float
        """

        # randomly choose discharge stop criterion with provided mean
        # ToDo: maybe gauss would be better? But it would have to be limited to the left side!
        discharge_stop = rand.triangular(left=0.05, mode=discharge_stop_mean, right=0.6)

        while self.bat.soc > discharge_stop:
            current = next(generator)
            if current <= 0.0:
                self.discharge_battery_step(current=current)
                self.bat.current_min = min(self.bat.current, current * self.bat.cap_max_0)
            else:
                self.charge_battery_step(current=current)
                self.bat.current_max = max(self.bat.current, current * self.bat.cap_max_0)

        # set discharging current to 0 after discharging completed
        self.bat.current = 0.0
        self.discharge_profile.keep_sending = False
        next(generator)

    def check_increment_cycle(self):
        """
        Checks the cumulating (dis-)charging cycles and increments, if a full cycle is reached.
        A full cycle equals one FULL battery discharging AND one FULL battery charging. Full means from 0 % capacity to
        100 % capacity.
        """

        # increment the battery cycle after one full charging and discharging process
        if (self.partial_cycle_discharging >= 1) and (self.partial_cycle_charging >= 1):
            self.bat.increment_cycle()
            self.partial_cycle_discharging -= 1
            self.partial_cycle_charging -= 1

    def plot(self, parameters: List = None, part: str = "bat0"):
        """
        Save plots of PARAMETERS to LOGGING_DIR.

        :param parameters: List of parameter to be plotted.
        :type parameters: list[str]
        :param part: Electrical component from which parameter shall be taken.
        :type part: str
        """

        # ToDo: Include possibility to merge multiple plots into one fig or plot
        import matplotlib.pyplot as plt

        if parameters is None:
            parameters = [""]

        for key in parameters:
            hist_key = part + "_" + key
            if hist_key in self.logger.hist.keys():
                plt.figure()
                plt.plot(self.logger.hist[hist_key])
                plt.title(hist_key)
                plt.xlabel("Time [counts]")
                plt.ylabel(key)
                plt.savefig(LOGGING_DIR + hist_key + ".png")
