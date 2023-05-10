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
from utils import add_noise
from typing import List
from config.constants import DT
from cell import Cell
import numpy as np


class Battery(Cell):
    """
    A class for definition of the battery's properties and states. This is the result of aligning STACKS of CELLS either
    serially or parallely.
    See https://circuitdigest.com/electronic-circuits/designing-12v-li-ion-battery-pack-with-protection-circuit for more
    in depth explanation.
    """

    def __init__(self, config: str = "16S", stack_list: List = None, cycle_start: int = 0):
        """
        Initialization of parameter for class battery. A battery consists of stacks, given in stack_list.

        :param config: Wiring configuration of the battery. Determines the electrical properties based on the stacks
        :type config: str
        :param stack_list: List containing the single cells, the stack should be composed of
        :type stack_list: list
        :param cycle_start: Initial cycle of battery for current run of simulation
        :type cycle_start: int
        """

        # Inherit cell parameter from class CELL
        super().__init__()
        if stack_list is None:
            stack_list = []
        self.num_stacks = len(stack_list)  # number of cells the battery is composed of
        self.cycle = cycle_start  # Number of charging/discharging cycle
        # self.cycle_pre = cycle_start - 1
        # are stacks combined either serially ("XS") or parallely ("XP"), with X = number of stacks
        self.config = config.upper()
        # ToDo: Apply config syntax checking similar to the one in class stack
        self.config_num_s = int(self.config.split("S")[0])
        # ToDo: Something like "16S" should also be acceptable (without providing the second part)
        self.config_num_p = int(self.config.split("S")[1].split("P")[0])
        # initialize cell objects, using standard parameter
        self.stacks = stack_list

        # save variables for tracking maximum charging and discharging currents
        self.current_max = 0
        self.current_min = 0

        # save variables for cumulative charging and discharging energies
        self.energy_charging = 0
        self.energy_discharging = 0

        # temp characteristics
        self.temp_efficiency_factor = self.stacks[0].temp_efficiency_factor
        self.temp_capacity = self.stacks[0].temp_capacity

    def calc_bat_prop(self):
        """
        Calculates the electrical properties of battery as the combination of wired stacks, depending on config.
        """

        c = 0  # counter for selecting stack
        for s in range(self.config_num_s):
            # initialize battery module properties
            bat_voltage = 0
            bat_capacity = 0
            bat_capacity_max = 0
            bat_weight = 0
            bat_voltage_min = 0
            bat_voltage_max = 0
            bat_current = 0
            bat_discharge_current_max = 0
            bat_internal_resistance = 0
            bat_discharge_voltage_slope_lin = 0
            bat_discharge_voltage_slope_nonlin = 0
            bat_temperature = 0
            p = 0  # counter variable for number of parallely wired stacks
            # set parameter values according to joined stacks
            while p < self.config_num_p:
                stack = self.stacks[c]  # select stack from list
                stack.tag = "s" + str(s) + "_p" + str(p)  # tag stack name to retrace components in wiring
                bat_voltage += stack.volt
                bat_voltage_min += stack.volt_min
                bat_voltage_max += stack.volt_max
                bat_discharge_voltage_slope_lin += stack.discharge_volt_slope_lin
                bat_discharge_voltage_slope_nonlin += stack.discharge_volt_slope_nonlin
                bat_internal_resistance += stack.internal_resistance
                bat_current += stack.current
                bat_discharge_current_max += stack.discharge_current_max
                bat_capacity += stack.cap
                bat_capacity_max += stack.cap_max
                bat_weight += stack.weight
                bat_temperature += stack.temp
                p += 1
                c += 1
            # add mean (division by p) to parameter, if it is not affected by parallel wiring
            self.volt += bat_voltage / p
            self.volt_min += bat_voltage_min / p
            self.volt_max += bat_voltage_max / p
            self.discharge_volt_slope_lin += bat_discharge_voltage_slope_lin / p
            self.discharge_volt_slope_nonlin += bat_discharge_voltage_slope_nonlin / p
            self.internal_resistance += bat_internal_resistance / p
            self.temp += bat_temperature / p
            self.weight += bat_weight
        self.current += bat_current
        self.discharge_current_max += bat_discharge_current_max
        self.cap += bat_capacity
        self.cap_max += bat_capacity_max
        self.temp /= s + 1
        self.internal_resistance /= s + 1  # scale parameter according to number of serially wired stacks
        # calculate stack maximum energy, weight and capacitance independently of configuration
        self.capacitance = self.cap_max * 60**2 / self.volt_max * 4.67  # cell capacitance [F]
        self.cap_max_0 = self.cap_max
        # set stack cycle attributes to value of last cell in list ToDo: What if stack is composed of some older cells?
        # self.cycle = stack.cycle
        # self.cycle_pre = stack.cycle_pre

    def propagate_attributes(self, attributes: List = None, electric: bool = False):
        """
        Method for propagating attributes through all stacks (and cells recursively) the battery consists of.

        :param attributes: A list containing the parameter, which should be propagated through composing parts
        :type attributes: list[str]
        :param electric: Indicator for logging electrical parameter, which need to be processed according to wiring
        :type electric: bool
        """

        if attributes is None:
            attributes = []
        if electric:
            # apply wiring logic to electrical parameter
            for stack in self.stacks:
                stack.current = self.current / self.config_num_p
                stack.discharge_current_max = self.discharge_current_max / self.config_num_p
                stack.cap = self.cap / self.config_num_p
                stack.cap_max = self.cap_max / self.config_num_p

                stack.volt = self.volt / self.config_num_s
                stack.volt_min = self.volt_min / self.config_num_s
                stack.volt_max = self.volt_max / self.config_num_s
                stack.discharge_voltage_slope_lin = self.discharge_volt_slope_lin / self.config_num_s
                stack.discharge_voltage_slope_nonlin = self.discharge_volt_slope_nonlin / self.config_num_s

                stack.weight = self.weight / (self.config_num_s * self.config_num_p)
                stack.temp = self.temp

                self.capacitance = self.cap_max * 60**2 / self.volt_max * 4.67  # cell capacitance [F]
                stack.calc_state_of_charge()
                stack.propagate_attributes(electric=True)
            add_noise(["volt", "cap", "temp", "weight"], self.stacks)
        else:
            # non electrical parameter
            for att in list(attributes):
                bat_att = self.__dict__[att]
                for s in self.stacks:
                    s.__dict__[att] = bat_att
                    s.propagate_attributes([att])

    def increment_cycle(self, increment: int = 1):
        """
        Method for incrementing the cycle of the battery after one full discharging -> charging process.

        :param increment: Increment value defaults to 1 for most rational cases
        :type increment: int
        """

        self.cycle += increment
        self.cycle_pre += increment
        self.propagate_attributes(["cycle", "cycle_pre"])
        self.degrade()  # degrade battery due to cycle increment
        # degrade stacks and cells of battery caused by cycle increment
        for stack in self.stacks:
            stack.degrade()
            for cell in stack.cells:
                cell.degrade()

    def load_battery_step(self, constant_current: float = 1.625):
        """Carries out one step of the battery charging process.

        :param constant_current: Current [A] used to charge battery during single time step
        :type constant_current: float
        """

        # constant current mode
        if self.volt < self.volt_max:
            self.current = constant_current
            # charge provided from constant current during time step
            charge_per_timestep = self.current * DT
            # Added capacity in Ah during time step
            self.cap += charge_per_timestep / 60**2

            dU = charge_per_timestep / self.capacitance  # dU = dQ / C, voltage increment per time step

            self.volt += dU

            self.current_max = max(self.current_max, self.current)
        # constant voltage mode
        else:
            self.current *= np.exp(-DT / (self.internal_resistance * self.capacitance))

            self.cap += self.current * DT / 60**2
            self.current_max = max(self.current_max, self.current)
        # update battery state of charge
        self.calc_state_of_charge()
        # calc cell temp
        self.calc_temperature()
