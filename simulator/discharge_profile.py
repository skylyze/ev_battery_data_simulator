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
from typing import List, Generator
from battery import Battery

import numpy as np
import pandas as pd
from config.constants import (
    DT,
    WLTP_CLASS,
    MASS_LOAD,
    MASS_VEHICLE,
    GRAVITATION_CONSTANT,
    ROLL_RESISTANCE_COEFFICIENT,
    DENSITY_AIR,
    AIR_RESISTANCE_COEFFICIENT,
    AREA_CAR_CROSSSECTION,
    VELOCITIY_AIR,
    ROTATIONAL_MASS_INERTIA_COEFFICIENT,
    ELECTRICAL_EFFICIENCY_COEFFICIENT,
    POWER_LOSS,
)


def calc_power(velocity: float, acceleration: float, slope: float) -> float:
    """
    Calculates a balance of forces a car is experiencing during driving. The relevant forces are:
        - rolling resistance force
        - climbing resistance force
        - acceleration resistance force
        - acceleration resistance force
    For calculation specific mechanical constants for the car model and velocity, acceleration and slope for the driving
    profile are used. Finally, the mechanical force is transformed into corresponding electrical power.
    Source: https://www.mdpi.com/2032-6653/7/1/41

    :param velocity: Velocity of car for current time step.
    :type velocity: float
    :param acceleration: Acceleration of car for current time step.
    :type acceleration: float
    :param slope: Slope the car has to overcome for current time step.
    :type slope: float
    :return: Electrical power the car needs to use for the corresponding force. Negative power means power DRAIN,
             positive power means power GAIN.
    :rtype: float
    """

    f_vehicle = (
        # rolling resistance force
        (MASS_VEHICLE + MASS_LOAD) * GRAVITATION_CONSTANT * ROLL_RESISTANCE_COEFFICIENT * np.cos(slope / 180 * np.pi)
        # aerodynamic drag force
        + 0.5 * DENSITY_AIR * AIR_RESISTANCE_COEFFICIENT * AREA_CAR_CROSSSECTION * (velocity / 3.6 + VELOCITIY_AIR) ** 2
        # climbing resistance force
        + (MASS_VEHICLE + MASS_LOAD) * GRAVITATION_CONSTANT * np.sin(slope / 180 * np.pi)
        # acceleration resistance force
        + (MASS_VEHICLE + MASS_LOAD) * acceleration * ROTATIONAL_MASS_INERTIA_COEFFICIENT
    )
    # transformation mechanical vehicle power -> electrical battery power
    p_vehicle = f_vehicle * velocity / 3.6
    # power balance, POWER_LOSS has to be adjusted to time step size (because it affects p_vehicle, too)
    return -(p_vehicle * ELECTRICAL_EFFICIENCY_COEFFICIENT ** np.sign(-p_vehicle) + POWER_LOSS)


class DischargeCurrentProfiles:
    def __init__(self, battery: Battery, time_step_size: float, use_wltp: bool = False, args: List = None):
        """
        Initialization specifying discharge current profile.

        :param time_step_size: Size of time step setting the mode of WLTP discharge profile function.
        :type time_step_size: float
        :param use_wltp: Indication if to use WLTP (True) or random (False) profile.
        :type use_wltp: bool
        :param args: Arguments for characterising discharge current profile.
        :type args: List
        """

        self.bat = battery
        self.time_step_size = time_step_size
        self.use_wltp = use_wltp
        if args is None:
            args = []
        self.args = args
        self.keep_sending = True

    def create_random_discharge_current_profile(
        self,
        pulse_len_min: float = 1 * 60,
        pulse_len_max: float = 3 * 60,
        c_min: float = 0.25,
        c_max: float = 1.5,
        c_mean: float = 1,
    ) -> Generator:
        """
        Generation of a random discharge current profile (in C-value!), simulating current drain from battery during
        driving the vehicle. Set negative values for c_min to also include battery charging from recuperation.

        :param pulse_len_min: Minimum duration [s] of discharge pulse.
        :type pulse_len_min: float
        :param pulse_len_max: Maximum duration [s] of discharge pulse.
        :type pulse_len_max: float
        :param c_min: Minimum amplitude of current.
        :type c_min: float
        :param c_max: Maximum amplitude of current.
        :type c_max: float
        :param c_mean: Most common value for C.
        :type c_mean: float
        :return: Current signal for discharging.
        :rtype: Generator
        """

        # provide signal as long as battery state of charge limit is not reached
        while self.keep_sending:
            # rand.uniform(low=c_min, high=c_max)  # sample random current amplitude
            current_val = rand.triangular(left=c_min, mode=c_mean, right=c_max)
            # sample random current signal length
            pulse_len = rand.uniform(low=pulse_len_min / DT, high=pulse_len_max / DT)
            t = 0  # time counter for signal
            # provide current signal until desired length is reached
            while t <= pulse_len:
                t += 1
                yield current_val
                self.keep_sending = True

    def vehicle_profile(self, driving_profile_path: str = "driving_protocols/wltp_class3.csv") -> Generator:
        """
        Transforms a driving profile consisting as time-series data of velocity, acceleration and slope, provided in a
        csv-file, into an electric battery load profile using car model explicit parameter.
        For more information, see directory "driving_protocols".

        :param driving_profile_path: Path to file containing driving profile
        :type driving_profile_path: str
        :return: Current drawn from battery [C]
        :rtype: Generator
        """

        driving_profile = pd.read_csv(driving_profile_path, sep=";", decimal=",")
        # provide signal as long as battery state of charge limit is not reached
        while self.keep_sending:
            for _, v, a, alpha in driving_profile.values:
                # vehicle power due to driving and (de-)acceleration
                p_bat = calc_power(velocity=v, acceleration=a, slope=alpha)
                yield p_bat / self.bat.volt / self.bat.cap_max_0  # current [C]
                self.keep_sending = True

    def vehicle_profile_interpolate(self, driving_profile_path: str = "driving_protocols/wltp_class3.csv") -> Generator:
        """
        Transforms a driving profile consisting as time-series data of velocity, acceleration and slope, provided in a
        csv-file, into an electric battery load profile using car model explicit parameter. Interpolates for time steps
        smaller than one second (in original time series the values are provided for time steps of one second).
        For more information, see directory "driving_protocols".

        :param driving_profile_path: Path to file containing driving profile
        :type driving_profile_path: str
        :return: Current drawn from battery [C]
        :rtype: Generator
        """

        driving_profile = pd.read_csv(driving_profile_path, sep=";", decimal=",")
        # provide signal as long as battery state of charge limit is not reached
        for (_, v, a, alpha), (__, v_next, a_next, alpha_next) in zip(
            driving_profile.values[:-1], driving_profile.values[1:]
        ):
            count = 0
            da = (a_next - a) * DT
            dv = (v_next - v) * DT
            while count < int(1 / DT):
                v += dv
                a += da
                # vehicle power due to driving and (de-)acceleration
                p_bat = calc_power(velocity=v, acceleration=a, slope=alpha)
                count += 1
                yield p_bat / self.bat.volt / self.bat.cap_max_0  # current [C]
                self.keep_sending = True

    def vehicle_profile_sample(self, driving_profile_path: str = "driving_protocols/wltp_class3.csv"):
        """
        Placeholder for sampling WLTP discharge profile function.

        :param driving_profile_path: Path to file containing driving profile
        :type driving_profile_path: str
        """
        # ToDo: Implement function for sampling values over DT > 1 time steps
        yield None

    def select_generator(self) -> Generator:
        """
        Selects appropriate function to create generator depending on class initialization.

        :return: Generator providing discharge current values for every time steps depending on initialization of class.
        :rtype: Generator
        """

        if self.use_wltp:
            print("Using WLTP " + str(WLTP_CLASS) + " discharge profile.")
            if self.time_step_size > 1:
                raise NotImplementedError("Sampling of WLTP for DT > 1 not yet implemented!")
                # return self.vehicle_profile_sample(*self.args)
            elif self.time_step_size < 1:
                return self.vehicle_profile_interpolate(*self.args)
            else:
                return self.vehicle_profile(*self.args)
        else:
            print("Using random discharge profile.")
            return self.create_random_discharge_current_profile(*self.args)
