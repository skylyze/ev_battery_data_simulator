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
import json
from config.constants import (
    DT,
    AMBIENT_TEMPERATURE,
    BAT_AREA,
    HEAT_TRANS_CONST,
    BMS_INLETPASSIVETARGET,
    BMS_INLETACTIVECOOLTARGET,
    BMS_INLETACTIVEHEATTARGET,
)


class Cell:
    """
    A class for definition of a single battery cell, which is stacked either serially or parallely.
    """

    def __init__(self):
        """
        Initialization of the class Cell serving as the base class for electrical components and containing all relevant
        parameter for simulation.
        """

        self.cycle = 0  # number of current charging/discharging cycle
        self.soc = 0  # cell state of charge from 0 to 100 %
        self.soc_normed = 0  # cell state of charge from 0 to 100% related to currently available capacity
        self.quick_charge_time = 0  # quick charge time [s]
        self.charging_time = 0  # battery nominal charging time [s]
        self.current = 0  # cell nominal current [A]
        self.charge_quick_current = 0  # cell quick charging current [A]
        self.discharge_current_max = 0  # cell max discharging current [A]
        self.volt = 0  # cell nominal voltage [V]
        self.volt_min = 0  # minimum cell voltage [V]
        self.volt_max = 0  # maximum cell voltage [V]
        self.power = 0  # Cell nominal power [W]
        self.energy = 0  # Cell nominal energy during time step [Ws]
        self.cap_max = 0  # cell max capacity [Ah]
        self.cap_max_0 = 0  # original max. capacity @ cycle = 0 (fresh battery)
        self.cap = 0  # cell capacity [Ah] (typical @ 25°C), drops after many cycles
        self.temp = 0  # current cell temperature [°C]
        self.temp_max = 0  # max. allowed cell temperature [°C]
        self.temp_min = 0  # min. allowed cell temperature [°C]
        self.internal_resistance = 0  # cell internal resistance [Ohm]
        self.energy_max = 0  # maximum energy that can be stored in cell [Wh]
        self.capacitance = 0  # cell capacitance [F]
        self.weight = 0  # cell weight [kg]
        self.discharge_volt_slope_lin = 0  # slope of voltage over discharge capacity for 0-90 % state of charge
        self.discharge_volt_slope_nonlin = 0  # slope of voltage over discharge capacity for >90 % state of charge
        self.cycle_pre = 0  # previous cycle number, used for simulations of worn cells with cycle_init > 0
        self.name = ""  # name of object, eg. "cell1", "stack_xyz", "bat_a"
        self.mode = ""  # current mode can be "discharge" or "charge"
        self.tag = ""  # tag for retracing components in wiring
        self.temp_efficiency_factor = 0  # efficiency factor for electrical energy <-> temperature conversion
        self.temp_capacity = 0  # specific temperature capacity for Li-Ion material

    def set_config(self, cycle_start: int = 0, filename: str = "simulator/config/cell.json"):
        """
        Function for setting cell properties to default Panasonic NCR18650B (see data sources).
        Data sources: https://www.imrbatteries.com/content/panasonic_ncr18650b-2.pdf
                      https://www.akkuparts24.de/Panasonic-NCR18650B-36V-3400mAh-Li-Ion-Zelle
                      https://www.jubatec.eu/kapazitat-ladespannung-innenwiderstand/
                      https://www.batterydesign.net/thermal/
               https://www.akkuteile.de/lithium-ionen-akkus/18650/panasonic/panasonic-ncr18650b-3-6v-3400mah_100639_1240

        :param cycle_start: Current cycle of cell, defaults to 0 for new cell
        :type cycle_start: int
        :param filename: Path to config file
        :type filename: str
        """

        # ToDo: Method needs to be adjusted to work with many cells provided in config file!
        with open(filename) as file:
            data = json.load(file)
            # number of current charging/discharging cycle (0 for simulation of new components)
            self.cycle = cycle_start
            # self.cycle_pre = cycle_start - 1
            # name of component, e.g. "cell1". This is only valid for one cell.
            self.name = list(data.keys())[0]
            data_cell = data[self.name]
            for key, value in data_cell.items():
                self.__dict__[key] = value

            self.power = self.volt * self.current  # Cell nominal power [W]
            self.energy = self.power * DT  # Cell nominal energy during time step [Ws]
            self.capacitance = self.cap_max * 60**2 / self.volt_max * 4.6  # cell capacitance [F]

    def calc_state_of_charge(self):
        """
        Calculates the state of charge using the recent in relation to the maximum capacity.
        """

        # cell state of charge from 0 to 1
        self.soc = self.cap / self.cap_max_0
        self.soc_normed = self.cap / self.cap_max

    def discharge_profile(self):
        """
        Linear approximation of discharge voltage dependency on cell capacity and discharge current.
        Temperature dependency is NOT modeled (here @ constant 25°C)! Data from datasheet
        (https://www.imrbatteries.com/content/panasonic_ncr18650b-2.pdf).
        """

        # ToDo: Include temperature dependency
        # Cell depth of discharge (DoC) as the inverse state of charge (SoC)
        doc = 1 - self.soc
        # approximation of discharge characteristic from datasheet using two linear approximations.
        if doc > 0.9:
            # voltage drop for discharge capacity > 3 Ah
            self.volt = (
                self.discharge_volt_slope_nonlin * self.soc * 10  # decreasing voltage for remaining 10 % capacity
                + 0.5 * self.current / self.discharge_current_max  # offset induced by discharge current
                + self.volt_min  # minimum voltage at capacity = 0
            )
        else:
            # voltage drop for 0 % - 90 % cell capacity
            self.volt = (
                -self.discharge_volt_slope_lin * doc  # decreasing voltage during discharging process
                + 0.5 * self.current / self.discharge_current_max  # offset induced by discharge current
                + self.volt_max  # maximum voltage at max capacity
            )

    def degrade(self, decrease_per_cycle: float = 0.05 / 140):  # decrease_per_cycle = 0.15
        """
        Implements the degradation a cell, stack and battery experiences going through many charging/discharging
        processes. Also respects simulation of worn cells with cycle_start > 0.

        Sources: https://evannex.com/blogs/news/understanding-teslas-lithium-ion-batteries,
                 https://www.imrbatteries.com/content/panasonic_ncr18650b-2.pdf

        :param decrease_per_cycle: Amount of decline of capacity per cycle
        :type decrease_per_cycle: float
        """

        # factor for degradation, used if cycle_start > 0
        deg_factor = abs(self.cycle - self.cycle_pre)

        # self.cap *= 1 - decrease_per_cycle * deg_factor  # ToDO: This may cause the high voltage jump
        self.cap_max *= 1 - decrease_per_cycle * deg_factor

        # calc dynamic properties again
        self.power = self.volt * self.current  # Cell nominal power [W]
        self.energy = self.power * DT  # Cell nominal energy during time step [Ws]
        self.capacitance = self.cap_max * 60**2 / self.volt_max * 4.67  # cell capacitance [F]

    def degradation_start(self):
        """
        Implements the initial degradation for worn components (cycle_start > 0) and set cycle_pre accordingly.
        """

        if abs(self.cycle - self.cycle_pre) > 1:
            self.degrade()
            self.cycle_pre = self.cycle - 1

    def calc_temperature(self):
        """
        Method for calculation the temperature of the battery. Model uses a balance of electrical energy loss from
        internal resistance w. r. t. heating, active and passing cooling.
        See: https://en.wikipedia.org/wiki/Convection_(heat_transfer)

        ToDo: It seems there are three parameter for temperature control:
            - "BMS_inletPassiveTargetT": Temp target for passive cooling? (How is this set up?)
            - "BMS_inletActiveCoolTargetT": Active cooling ("negative heating power")
            - "BMS_inletActiveHeatTargetT": Active heating (probably only used in cold environments?)
         Check on real data for parameter calibration (especially, check temperature ranges of cells!
        """

        # power loss at internal resistance
        d_power_loss = self.current**2 * self.internal_resistance  # P = U * I = R * I^2
        # convection battery <-> air
        d_power_air = HEAT_TRANS_CONST * BAT_AREA * (self.temp - AMBIENT_TEMPERATURE)  # P = h * A + (T_bat - T_air)
        # passive cooling power
        d_power_passive = HEAT_TRANS_CONST * BAT_AREA * (self.temp - BMS_INLETPASSIVETARGET)
        # active cooling power
        d_power_cooling = HEAT_TRANS_CONST * BAT_AREA * (self.temp - BMS_INLETACTIVECOOLTARGET)
        # active heating power
        d_power_heating = HEAT_TRANS_CONST * BAT_AREA * (self.temp - BMS_INLETACTIVEHEATTARGET)

        # balance
        d_power_balance = d_power_loss - (d_power_air + d_power_passive + d_power_cooling + d_power_heating)
        self.temp += (
            d_power_balance * DT * self.temp_efficiency_factor / (self.temp_capacity * self.weight)
        )  # E = P * t
