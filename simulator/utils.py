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
import numpy as np
from typing import List
from numpy.random import default_rng
from config.constants import SEED

# random generator object. Set seed for reproducibility
rand = default_rng(seed=SEED)


def add_noise(param_list: List, objs: List, mean: float = 0.0, stdd: float = None, stdd_range: float = 0.01):
    """
    Adds noise to desired parameter to mimic realistic behavior of measurements.

    :param param_list: Specify the parameter where noise should be added.
    :type param_list: list
    :param objs: Specify object (Battery, Stack or Cell) to be manipulated.
    :type objs: list
    :param mean: Mean value for the Gaußian noise distribution.
    :type mean: float
    :param stdd: Standard deviation for the Gaußian noise distribution. If None, calculate it from current mean values.
    :type stdd: float
    :param stdd_range: Adjust stdd to a small range of the calculated mean (~1 %). Only used if stdd = None.
    :type stdd_range: float
    """

    num_values = len(objs)
    for param in param_list:
        if stdd is None:
            stdd = np.mean([o.__dict__[param] for o in objs]) / 2 * stdd_range
        noise = rand.normal(mean, stdd, num_values)
        # center values around zero additionally to mean==0, to reduce discretization error
        noise -= np.mean(noise)
        for i in range(num_values):
            objs[i].__dict__[param] += noise[i]
