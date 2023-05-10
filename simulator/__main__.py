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
import time
from battery_simulator import Simulation
from config.constants import (
    DEVICE_NAME,
    SIM_TIME,
    CYCLE_START,
    TIMESTAMP_START,
    PARTIAL_CYCLE_CHARGING,
    PARTIAL_CYCLE_DISCHARGING,
    ENERGY_CHARGING,
    ENERGY_DISCHARGING,
)
import pandas as pd


if __name__ == "__main__":
    print("--------------------------- Setting up simulation -------------------------------------")
    # read status file and try to find device
    try:
        sf = pd.read_csv("status/" + DEVICE_NAME + ".csv")
        CYCLE_START = int(sf["cycle"].values[0])
        TIMESTAMP_START = sf["timestamp"].values[0]
        PARTIAL_CYCLE_CHARGING = float(sf["partial_charge"].values[0])
        PARTIAL_CYCLE_DISCHARGING = float(sf["partial_discharge"].values[0])
        ENERGY_CHARGING = float(sf["energy_charging"].values[0])
        ENERGY_DISCHARGING = float(sf["energy_discharging"].values[0])
    except:
        print("No status file found. It will be generated after simulation is finished!")

    # create simulation object managing the battery simulation
    sim = Simulation(
        cycle_start=CYCLE_START,
        timestamp_start=TIMESTAMP_START,
        partial_cycle_charging=PARTIAL_CYCLE_CHARGING,
        partial_cycle_discharging=PARTIAL_CYCLE_DISCHARGING,
    )
    # create battery objects with desired parameter and configurations
    sim.create_battery(
        num_stacks=96,
        num_cells_per_stack=1 * 74,
        config_bat="96S1P",
        config_stack="1S74P",
        energy_charging=ENERGY_CHARGING,
        energy_discharging=ENERGY_DISCHARGING,
    )

    # increase volt cut off (volt_min) for tesla model s p85 battery (compared to single panasonic cell)
    # this adjustment originates from comparison to real world data of a Tesla Model S P85
    sim.bat.volt_min /= 0.7267

    # run simulation and get logging dict, measure and output time used for simulation
    print("---------------------------   Start  Simulation   -------------------------------------")
    toc = time.time()
    hist = sim.simulate(sim_time=SIM_TIME)
    print("Simulation of {} cycle(s) took {} sec!".format(sim.bat.cycle - CYCLE_START, time.time() - toc))

    # save latest status of simulation for continuing in future
    print("Saving current state of simulation...")
    data = {
        "deviceId": [DEVICE_NAME],
        "cycle": [sim.bat.cycle],
        "timestamp": [sim.logger.timestamp_latest],
        "partial_charge": [sim.partial_cycle_charging],
        "partial_discharge": [sim.partial_cycle_discharging],
        "energy_charging": [sim.bat.energy_charging],
        "energy_discharging": [sim.bat.energy_discharging],
    }
    s_file = pd.DataFrame(data=data)
    s_file.to_csv("status/" + DEVICE_NAME + ".csv")
    print("Done")
