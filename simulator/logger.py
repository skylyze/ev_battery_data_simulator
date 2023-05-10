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
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
import copy
from config.constants import *
from battery import Battery
from cell import Cell
from typing import List, Dict
from utils import rand

# possible logging parameters
possible_logging_formats = "csv", "parquet", "json", "tesla"
possible_logging_parameter = Battery.__dict__.keys()


class Logger:
    def __init__(
        self,
        filepath: str = LOGGING_DIR,
        obj: Battery = None,
        formats: List[str] = LOGGING_FORMATS,
    ):
        """
        Initialized the logging object, managing the data pipeline.

        :param filepath: Path to directory where files should be logged.
        :type filepath: str
        :param obj: Electrical component (Battery, Stack or Cell, works also recursively) data source.
        :type obj: Battery
        :param formats: Data format(s) for file logging.
        :type formats: list[str]
        """

        self.filepath = filepath
        self.bat = obj
        # case-insensitive file format for data logging
        self.formats = [f.lower() for f in np.unique(formats)]
        # history dict containing the whole progress of desired parameter
        self.hist = {}
        # log dict containing only the current state of timestep
        self.log_dict = {}

        # file format objects and indicators
        # self.csv_file = None
        self.csv = False
        # self.parquet_file = None
        self.parquet = False
        # self.json_file = None
        self.json = False

        # prepare logger if object is provided during initialization
        if obj is not None:
            self.prepare_logger_setup()
        # logging table header
        self.hist_head = None

        self.time = 0  # internal time for logger, synchronized during simulation
        self.stack_turn = 0  # counter for picking stacks for tesla stack value logging

        self.log = lambda x: None  # set logging function depending on logging mode (tesla format or standard)
        self.timestamp_latest = None
        self.datetime = None

    def set_logger(self, filepath: str, obj: Battery, formats: List[str]):
        """
        Provides possibility to set the values for the logger, if default values are not desired.

        :param filepath: Path to directory where files should be logged.
        :type filepath: str
        :param obj: Electrical component (Battery, Stack or Cell, works also recursively) data source.
        :type obj: Battery
        :param formats:Data format(s) for file logging.
        :type formats: list[str]
        """

        self.filepath = filepath
        self.bat = obj
        self.formats = [f.lower() for f in formats]

        self.prepare_logger_setup()

    def add_value_hist(self, dict_obj: Dict, name: str, write: bool = False, obj: Cell = None) -> Dict:
        """
        Function for creating (write==False)/writing to (write==True) history dict with logging parameter provided in
        script constants.py for given object. Return the (updated) history dict.

        :param dict_obj: Logging dictionary usually provided by function "create_log"
        :type dict_obj: Dict
        :param name: Object name
        :type name: str
        :param write: If True, appends value for corresponding key of logging dict. Else creates key.
        :type write: bool
        :param obj: Object providing parameter for logging
        :type obj: Cell
        :return: Logging dictionary
        :rtype: Dict
        """

        for p in LOGGING_PARAMETER:
            if write:
                dict_obj[name + "_" + p].append(obj.__dict__[p])
            else:
                dict_obj[name + "_" + p] = []
        return dict_obj

    def add_value_log(self, dict_obj: Dict, name: str, obj: Cell = None) -> Dict:
        """
        Function for writing to logging dict with logging parameter provided in
        script constants.py for given object. Return the (updated) logging dict.

        :param dict_obj: Logging dictionary.
        :type dict_obj: Dict
        :param name: Object name
        :type name: str
        :param obj: Object providing values for logging
        :type obj: Cell
        :return: Logging dictionary
        :rtype: Dict
        """

        for p in LOGGING_PARAMETER:
            dict_obj[name + "_" + p] = obj.__dict__[p]
        return dict_obj

    # history
    def create_hist(self) -> Dict:
        """
        Creates the backbone history object (headers but no values) for logging the process of the simulation.
        """

        hist = {"time": [], "timestamp": []}
        bat_name = self.bat.name
        hist = self.add_value_hist(hist, bat_name)
        for s in self.bat.stacks:
            stack_name = s.name
            hist = self.add_value_hist(hist, stack_name)
            # for c in s.cells:
            #     cell_name = c.name
            #     hist = self.add_value_hist(hist, cell_name)
        self.hist = hist
        return hist

    def update_hist(self, time: float) -> Dict:
        """
        Updates parameter recursively for objects used in simulation to history dict.

        :param time: Current timestep of simulation.
        :type time: float
        :return: History dictionary containing progress of desired parameter in LOG_FREQ steps.
        :rtype: Dict
        """

        # deepcopy history header to prevent mixing up with previous time steps
        hist = copy.deepcopy(self.hist_head)
        # time for simulation [s]
        hist["time"].append(time * DT)
        # timestamp for use case
        timestamp = (self.datetime + timedelta(seconds=time * DT)).replace(tzinfo=None).isoformat()[:-3] + "Z"
        hist["timestamp"].append(timestamp)
        self.timestamp_latest = timestamp
        for b in [self.bat]:
            bat_name = b.name
            hist = self.add_value_hist(hist, bat_name, write=True, obj=b)
            for s in b.stacks:
                stack_name = s.name
                hist = self.add_value_hist(hist, stack_name, write=True, obj=s)
                # for c in s.cells:
                #     cell_name = c.name
                #     hist = self.add_value_hist(hist, cell_name, write=True, obj=c)

        # merge values of current timestep to global history dict ("add row to logging table")
        for key in self.hist.keys():
            self.hist[key].append(*hist[key])
        return hist

    # logger
    def update_log(self, time: float) -> Dict:
        """
        Updates parameter recursively for objects used in simulation to log dict.

        :param time: Current timestep of simulation.
        :type time: float
        :return: Logging dictionary containing the current row of desired parameter.
        :rtype: Dict
        """

        timestamp = (self.datetime + timedelta(seconds=time * DT)).replace(tzinfo=None).isoformat()[:-3] + "Z"
        hist = {"timestamp": timestamp}
        signals = {}
        self.timestamp_latest = timestamp
        for b in [self.bat]:
            bat_name = b.name
            signals = self.add_value_log(signals, bat_name, obj=b)
            for s in b.stacks:
                stack_name = s.name
                signals = self.add_value_log(signals, stack_name, obj=s)
                # for c in s.cells:
                #     cell_name = c.name
                #     signals = self.add_value_log(signals, cell_name, obj=c)
        hist["signals"] = signals
        return hist

    def prepare_logger_setup(self, timestamp_start: str = None):
        """
        Prepares the logging variables for log and hist. Also writes values for t = 0 and sets up file writers for
        desired file formats.

        :param timestamp_start: Initial timestamp of simulation
        :type timestamp_start: str
        """

        # set starting_time
        self.datetime = (
            datetime.now()
            if timestamp_start is None
            else datetime.strptime(timestamp_start, "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(seconds=60)
        )
        if "tesla" in self.formats:
            # prepare json encoder to output floats with fewer decimal places
            class RoundingFloat(float):
                __repr__ = staticmethod(lambda x: format(x, ".3f"))

            json.encoder.float = RoundingFloat

            self.log_dict = {
                "deviceId": DEVICE_NAME,
                "messageType": "DECODED_CAN_MESSAGES",
                "signalsByTimestampList": [],
            }
            self.log = self.log_tesla  # set logger to tesla mode
        else:
            # create history dict with parameter corresponding to battery object
            self.hist = self.create_hist()
            self.hist_head = copy.deepcopy(self.hist)

            # log values for t = 0
            # propagate electrical properties to stacks and cells
            self.bat.propagate_attributes(electric=True)
            # append current values to log dict
            hist = self.update_hist(time=0)

            for form in self.formats:
                if form == "csv":
                    # convert hist into pandas dataframe for saving
                    hist_pandas = pd.DataFrame(hist)
                    # write into .csv file
                    hist_pandas.to_csv(self.filepath + "log.csv", sep=";", decimal=",", mode="w", index=False)
                    self.csv = True
                elif form == "parquet":
                    self.parquet = True
                elif form == "json":
                    # prepare json encoder to output floats with fewer decimal places
                    class RoundingFloat(float):
                        __repr__ = staticmethod(lambda x: format(x, ".3f"))

                    json.encoder.float = RoundingFloat
                    self.log_dict = {"deviceId": DEVICE_NAME, "signalsByTimestampList": []}

                    self.json = True

                    log_dict = self.update_log(time=0)
                    # self.setup_json_file(time=0)
                    self.log_json(log_dict, time=0)
                else:
                    print(
                        "No valid data format for logging provided. There will be no files saved for the simulation!\nSupported file formats are: {}".format(
                            possible_logging_formats
                        )
                    )
            self.log = self.log_std  # set logger to std mode

    def log_json(self, data: Dict, time: float):
        """
        Logs data to json file.

        :param data: Values of current time step in simulation.
        :type data: Dict
        :param time: Current time step for file
        :type time: float
        """

        with open(self.filepath + "logs/log_" + str(time) + ".json", "w") as f:
            json.dump(data, f)

        self.log_dict = {"deviceId": DEVICE_NAME, "signalsByTimestampList": []}

    def log_csv(self, data: Dict):
        """
        Logs data to csv file.

        :param data: Values of current timestep in simulation.
        :type data: dict
        """

        # convert hist into pandas dataframe for saving
        hist_pandas = pd.DataFrame(data)
        # write into .csv file
        hist_pandas.to_csv(self.filepath + "log.csv", sep=";", decimal=",", mode="a", header=False, index=False)

    def log_parquet(self, data: Dict):
        """
        Logs data to parquet file

        :param data: Values of current timestep in simulation
        :type data: dict
        """

        # convert hist into pandas dataframe for saving
        hist_pandas = pd.DataFrame(data)
        # write into .parquet file
        hist_pandas.to_parquet(self.filepath + "log.parquet", engine="auto", index=False)

    def log_std(self, time: float):
        """
        Calls update functions to get values in simulation timestep and logs into file for corresponding file formats.

        :param time: Current timestep of simulation.
        :type time: float
        """

        if time % DUMP_FREQ == 0:
            # propagate electrical properties to stacks and cells
            self.bat.propagate_attributes(electric=True)
            # append current values to log dict
            hist = self.update_hist(time=time)
            # dump log files
            if self.csv:
                self.log_csv(hist)
            if self.json:
                # update logging dict
                log_dict = self.update_log(time=time)
                self.log_json(log_dict, time=time)

    def pick_stack_volt_and_temp(self, num_stacks: int = 4):
        """
        Select NUM_STACKS sequential stacks from battery and read the voltage and temperature.

        :param num_stacks: Number of sequential stacks to read values from
        :type num_stacks: int
        """

        sig = {}
        idx_list = np.arange(self.stack_turn, self.stack_turn + num_stacks)
        np.random.shuffle(idx_list)
        c = 0  # counter for replacing idx > len(num_stacks)
        for idx in idx_list:
            if idx >= len(self.bat.stacks):
                idx = c
                c += 1
            sig["BMS_Cell_" + str(idx + 1) + "_Voltage"] = self.bat.stacks[idx].volt
            sig["BMS_Cell_" + str(idx + 1) + "_Temp"] = self.bat.stacks[idx].temp
        self.stack_turn = np.max(idx_list) + 1 if c == 0 else c
        return sig

    def tesla_signals_schema(self, time: float, message_type: str, signals: Dict) -> Dict:
        """
        Generates the Tesla Model S BMS signal body in a json format.
        For reference, visit: https://www.ti.com/document-viewer/BQ76PL536A-Q1/datasheet

        :param time: Current time step in simulation
        :type time: float
        :param message_type: Logging message
        :type message_type: str
        :param signals: Logging data
        :type signals: dict
        :return: Logging signal, which is added to overall logging file
        :rtype: dict
        """

        timestamp = (self.datetime + timedelta(seconds=time * DT)).replace(tzinfo=None).isoformat()[:-3] + "Z"
        self.timestamp_latest = timestamp
        return {
            "timestamp": timestamp,
            "canMessageName": message_type,
            "signals": signals,
        }

    def tesla_signals(self, time: float):
        """
        Generates the Tesla Model S BMS signal in a json format for method "tesla_signals_schema".
        There are three levels of acquired signals depending on simulation time intervals:
         - Level 1: Message type BMS_Current_And_Voltage_AWD for every time step (1 DT)
         - Level 2: Message types BMS_cellMonitoring and Battery_Power_Limits for every 10 time steps (10 DT)
         - Level 3: Message types Battery_SOC, BMS_energyStatus, BMS_thermalStatus and Battery_Lifetime_Energy_Stats
                    for every 50 time steps (50 DT)

        :param time: Current time step in simulation
        :type time: float
        """

        if time % LOGGING_FREQ_LVL1 == 0:
            self.log_dict["signalsByTimestampList"].append(
                self.tesla_signals_schema(
                    time=time,
                    message_type="BMS_Current_And_Voltage_AWD",
                    signals={
                        "BMS_Pack_Voltage": self.bat.volt,
                        "BMS_Pack_Current": self.bat.current,
                        "BMS_Pack_Current_Unfiltered": self.bat.current / 2,
                    },
                )
            )
        if time % LOGGING_FREQ_LVL2 == 0:
            # propagate electrical parameter from battery to stacks
            self.bat.propagate_attributes(electric=True)
            self.log_dict["signalsByTimestampList"].append(
                self.tesla_signals_schema(
                    time=time, message_type="BMS_cellMonitoring", signals=self.pick_stack_volt_and_temp(num_stacks=4)
                )
            )
            self.log_dict["signalsByTimestampList"].append(
                self.tesla_signals_schema(
                    time=time,
                    message_type="Battery_Power_Limits",
                    signals={
                        "Max_Regen_Power": self.bat.current_max * self.bat.volt / 1000,  # power in kW
                        "Max_Discharge_Power": abs(self.bat.current_min) * self.bat.volt / 1000,  # power in kW
                    },
                )
            )
            # reset storing variables for next logger loop
            self.bat.current_min = 0
            self.bat.current_max = 0
        if time % LOGGING_FREQ_LVL3 == 0:
            self.log_dict["signalsByTimestampList"].append(
                self.tesla_signals_schema(
                    time=time,
                    message_type="Battery_SOC",
                    signals={
                        "SOC_Min": self.bat.soc_normed * 100,  # ToDo: What's the difference between those?
                        "SOC_UI": self.bat.soc * 100,  # soc in %
                    },
                )
            )
            self.log_dict["signalsByTimestampList"].append(
                self.tesla_signals_schema(
                    time=time,
                    message_type="BMS_energyStatus",
                    signals={
                        "BMS_energyBuffer": 0,  # ?
                        "BMS_energyCounter": 5,  # ?
                        "BMS_energyToChargeComplete": 1.1,  # ?
                        # ToDo: What's the difference between those values?
                        "BMS_expectedEnergyRemaining": self.bat.cap * self.bat.volt / 1000,  # ? [J = Ah * V]
                        "BMS_idealEnergyRemaining": self.bat.cap * self.bat.volt / 1000,  # ? [kWh]
                        "BMS_nominalEnergyRemaining": self.bat.cap * self.bat.volt / 1000,  # ? [kWh]
                        "BMS_nominalFullPackEnergy": self.bat.cap_max * self.bat.volt_max / 1000,  # ? [kWh]
                    },
                )
            )
            self.log_dict["signalsByTimestampList"].append(
                self.tesla_signals_schema(
                    time=time,
                    message_type="BMS_thermalStatus",
                    # ToDo: Add temperature model
                    # values from example json of real Tesla battery
                    signals={
                        "BMS_battTempPct": 33.0,  # ? [%]
                        # status vals: "0": "OFF", "1": "UNAVAILABLE", "2": "HEATING", "3": "COOLING", "4": "COMPLETE"
                        "BMS_dragStripStatus": 1,  # temperature manipulation action ?
                        "BMS_dsTargetTimeEst": 127,  # ? [min]
                        "BMS_flowRequest": 25.0,  # ? [%]
                        "BMS_inletActiveCoolTargetT": 51.0,  # ? [°C]
                        "BMS_inletActiveHeatTargetT": -16.0,  # ? [°C]
                        "BMS_inletPassiveTargetT": 45.0,  # ? [°C]
                        "BMS_noFlowRequest": 0,  # ? possible values: 0 or 1
                        "BMS_packTemperature": self.bat.temp,  # [°C]
                        "BMS_powerDissipation": 0.36,  # ? [kW]
                    },
                )
            )
            self.log_dict["signalsByTimestampList"].append(
                self.tesla_signals_schema(
                    time=time,
                    message_type="Battery_Lifetime_Energy_Stats",
                    signals={
                        "Discharge_Total": self.bat.energy_discharging / 60**2,  # [Wh]
                        "Charge_Total": self.bat.energy_charging / 60**2,  # [Wh]
                    },
                )
            )

    def log_tesla(self, time: float):
        """
        Method for dumping logging files into json file

        :param time: Current time step in simulation
        :type time: float
        """

        self.tesla_signals(time=time)
        # ToDo: Add synchronous file sending if wanted
        if time % DUMP_FREQ == 0:
            with open(self.filepath + "logs/log_" + str(time) + ".json", "w") as f:
                json.dump(self.log_dict, f)
            self.log_dict = {
                "deviceId": DEVICE_NAME,
                "messageType": "DECODED_CAN_MESSAGES",
                "signalsByTimestampList": [],
            }
