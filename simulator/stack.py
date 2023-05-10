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
from typing import List
from cell import Cell
from utils import add_noise


class Stack(Cell):
    """
    A class for definition of combination of single cells.
    See https://circuitdigest.com/electronic-circuits/designing-12v-li-ion-battery-pack-with-protection-circuit for more
    in depth explanation.
    """

    # ToDo: Is this class needed or can the stacks be represented implicitly in battery class (see duplicated lines)?
    def __init__(self, cell_list: List = None, config: str = "6S74P"):
        """
        Initialization of parameter for class stack. A stack consists of cells, given in cell_list.

        :param cell_list: List containing the single cells, the stack should be composed of
        :type cell_list: list[Cell]
        :param config: Wiring configuration of the stack. Determines electrical properties of the stack based on cells
        :type config: str
        """

        super().__init__()  # Inherit cell parameter from class CELL
        if cell_list is None:
            cell_list = []
        self.num_cells = len(cell_list)  # number of cells the stack is composed of
        self.cells = cell_list
        # ToDo: Check this explicitly, what if order is e.g., flipped?
        self.config = config.upper()  # configuration of stack has to be provided using this syntax
        self.config_num_s = int(self.config.split("S")[0])
        self.config_num_p = int(self.config.split("S")[1].split("P")[0])
        # ToDo: division by 0 are possible for s, p. How to avoid?
        self.cells_serial = None
        self.cells_parallel = None

        # temp characteristics
        self.temp_efficiency_factor = self.cells[0].temp_efficiency_factor
        self.temp_capacity = self.cells[0].temp_capacity

    def calc_stack_prop(self):
        """
        Calculates the electrical properties of stack as the combination of wired cells, depending on config.
        """

        c = 0  # counter variable for current cell
        # create group of parallely wired cells first, then stack those serially
        if self.config_num_p >= self.config_num_s:
            for s in range(self.config_num_s):
                p = 0  # counter variable for number of parallely wired cells
                # initialise stack group parameter
                stack_voltage = 0
                stack_capacity = 0
                stack_capacity_max = 0
                stack_weight = 0
                stack_voltage_min = 0
                stack_voltage_max = 0
                stack_current = 0
                stack_discharge_current_max = 0
                stack_internal_resistance = 0
                stack_discharge_voltage_slope_lin = 0
                stack_discharge_voltage_slope_nonlin = 0
                stack_temperature = 0
                while p < self.config_num_p:  # set parameter according to values in single cells
                    cell = self.cells[c]  # select cell from list
                    # tag cell to retrace components in wiring
                    cell.tag = "s" + str(s) + "_p" + str(p)
                    stack_voltage += cell.volt
                    stack_voltage_min += cell.volt_min
                    stack_voltage_max += cell.volt_max
                    stack_discharge_voltage_slope_lin += cell.discharge_volt_slope_lin
                    stack_discharge_voltage_slope_nonlin += cell.discharge_volt_slope_nonlin
                    stack_internal_resistance += cell.internal_resistance
                    stack_current += cell.current
                    stack_discharge_current_max += cell.discharge_current_max
                    stack_capacity += cell.cap
                    stack_capacity_max += cell.cap_max
                    stack_weight += cell.weight
                    stack_temperature += cell.temp
                    p += 1
                    c += 1
                # add mean of parameters (division by p) to stack, if they are not affected by parallel wiring
                self.volt += stack_voltage / p
                self.volt_min += stack_voltage_min / p
                self.volt_max += stack_voltage_max / p
                self.discharge_volt_slope_lin += stack_discharge_voltage_slope_lin / p
                self.discharge_volt_slope_nonlin += stack_discharge_voltage_slope_nonlin / p
                self.internal_resistance += stack_internal_resistance / p
                self.temp += stack_temperature / p
                self.current += stack_current
                self.discharge_current_max += stack_discharge_current_max
                self.cap += stack_capacity
                self.cap_max += stack_capacity_max
                self.weight += stack_weight
            # scale parameters by number of serially wired cells
            self.cap /= self.config_num_s
            self.cap_max /= self.config_num_s
            self.current /= self.config_num_s
            self.temp /= self.config_num_s

            self.internal_resistance /= self.config_num_s

            self.discharge_current_max /= self.config_num_s
        # ToDo: Is this case needed? Could it be also handled above?
        # create group of serially wired cells first, then stack those parallely
        else:
            for p in range(self.config_num_p):
                s = 0  # counter variable for serially wired cells
                # initialise stack group parameter
                stack_voltage = 0
                stack_capacity = 0
                stack_capacity_max = 0
                stack_weight = 0
                stack_voltage_min = 0
                stack_voltage_max = 0
                stack_current = 0
                stack_discharge_current_max = 0
                stack_internal_resistance = 0
                stack_discharge_voltage_slope_lin = 0
                stack_discharge_voltage_slope_nonlin = 0
                stack_temperature = 0
                # set parameter according to values in single cells
                while s < self.config_num_s:
                    cell = self.cells[c]  # select cell from list
                    # tag cell name to retrace components in wiring
                    cell.tag = "s" + str(s) + "_p" + str(p)
                    stack_voltage += cell.volt
                    stack_voltage_min += cell.volt_min
                    stack_voltage_max += cell.volt_max
                    stack_discharge_voltage_slope_lin += cell.discharge_volt_slope_lin
                    stack_discharge_voltage_slope_nonlin += cell.discharge_volt_slope_nonlin
                    stack_internal_resistance += cell.internal_resistance
                    stack_current += cell.current
                    stack_discharge_current_max += cell.discharge_current_max
                    stack_capacity += cell.cap
                    stack_capacity_max += cell.cap_max
                    stack_weight += cell.weight
                    stack_temperature += cell.temp
                    s += 1
                    c += 1
                # add mean of parameters (division by s) to stack, if they are not affected by serial wiring
                self.volt += stack_voltage
                self.volt_min += stack_voltage_min
                self.volt_max += stack_voltage_max
                self.discharge_volt_slope_lin += stack_discharge_voltage_slope_lin
                self.discharge_volt_slope_nonlin += stack_discharge_voltage_slope_nonlin
                self.internal_resistance += stack_internal_resistance
                self.current += stack_current / s
                self.discharge_current_max += stack_discharge_current_max / s
                self.cap += stack_capacity / s
                self.cap_max += stack_capacity_max / s
                self.temp += stack_temperature / s
                self.weight += stack_weight
            # scale parameters according to number of parallely wired cells
            self.volt /= self.config_num_p
            self.volt_min /= self.config_num_p
            self.volt_max /= self.config_num_p
            self.discharge_volt_slope_lin /= self.config_num_p
            self.discharge_volt_slope_nonlin /= self.config_num_p
            self.internal_resistance /= self.config_num_p
            self.temp /= self.config_num_p
        # calculate stack maximum energy, weight and capacitance independently of configuration
        # ToDo: Value of parameter seems unreasonable. Why does this value divided by 16 lead to the "correct" one?
        self.capacitance = self.cap_max * 60**2 / self.volt_max * 4.67  # cell capacitance [F]
        # ToDo: This (weight) is valid for Tesla Model S battery (P85). How to generalize?
        # self.weight += 4  # Increase stack weight by 4 kg to account for external pars (like wiring, bms, ...)
        self.cap_max_0 = self.cap_max
        # set stack cycle attributes to value of last cell in list. ToDo: What if stack is composed of some older cells?
        self.cycle = cell.cycle
        self.cycle_pre = cell.cycle_pre

    def propagate_attributes(self, attributes=None, electric: bool = False):
        """
        Method for propagating attributes through all cells the stack consists of.

        :param attributes: A list containing the parameter, which should be propagated through composing parts
        :type attributes: list
        :param electric: Indicates if attributes are electrical since wiring logic must be applied in this case
        :type electric: bool
        """

        if attributes is None:
            attributes = []
        if electric:
            # apply wiring logic to electrical parameter
            for cell in self.cells:
                cell.current = self.current / self.config_num_p
                cell.discharge_current_max = self.discharge_current_max / self.config_num_p
                cell.cap = self.cap / self.config_num_p
                cell.cap_max = self.cap_max / self.config_num_p

                cell.volt = self.volt / self.config_num_s
                cell.volt_min = self.volt_min / self.config_num_s
                cell.volt_max = self.volt_max / self.config_num_s
                cell.discharge_volt_slope_lin = self.discharge_volt_slope_lin / self.config_num_s
                cell.discharge_volt_slope_nonlin = self.discharge_volt_slope_nonlin / self.config_num_s

                # remove weight of externals
                # cell.weight = (self.weight - 4) / (self.config_num_s * self.config_num_p)
                cell.temp = self.temp
                cell.calc_state_of_charge()
            add_noise(["volt", "cap", "temp", "weight"], self.cells)  # adds small noise to cell values
        else:
            # non electrical parameter
            for att in attributes:
                stack_att = self.__dict__[att]
                for c in self.cells:
                    c.__dict__[att] = stack_att
