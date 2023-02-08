#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

   Copyright 2014-2019 OpenEEmeter contributors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

"""
import pandas as pd

from eemeter.features import (
    compute_time_features,
    compute_temperature_features,
    compute_usage_per_day_feature,
    merge_features,
)
from eemeter.segmentation import iterate_segmented_dataset
from eemeter.caltrack.hourly import caltrack_hourly_fit_feature_processor
from pkg_resources import resource_filename


__all__ = (
    "create_caltrack_hourly_preliminary_design_matrix",
    "create_caltrack_hourly_segmented_design_matrices",
    "create_caltrack_daily_design_matrix",
    "create_caltrack_billing_design_matrix",
)


def create_caltrack_hourly_preliminary_design_matrix(meter_data, temperature_data, region:str='USA'):
    """A helper function which calls basic feature creation methods to create an
    input suitable for use in the first step of creating a CalTRACK hourly model.

    Parameters
    ----------
    meter_data : :any:`pandas.DataFrame`
        Hourly meter data in eemeter format.
    temperature_data : :any:`pandas.Series`
        Hourly temperature data in eemeter format.
    region : :any 'str'
        The relevant region of the world. See eemeter/region_info.csv for options. Defaults to 'USA' unless otherwise
        specified for alignment with eeweather conventions.

    Returns
    -------
    design_matrix : :any:`pandas.DataFrame`
        A design matrix with meter_value, hour_of_week, hdd_(hbp_default), and cdd_(cbp_default) features.
    """
    temperature_filename = resource_filename("eemeter.samples", "region_info.csv")
    region_info = pd.read_csv(temperature_filename, index_col=0)
    cbp_default = int(region_info.loc["cbp", region])
    hbp_default = int(region_info.loc["hbp", region])

    if region != 'USA':
        temperature_data = 32 + (temperature_data * 1.8)

    time_features = compute_time_features(
        meter_data.index, hour_of_week=True, hour_of_day=False, day_of_week=False
    )

    temperature_features = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[hbp_default],
        cooling_balance_points=[cbp_default],
        degree_day_method="hourly",
    )

    design_matrix = merge_features(
        [meter_data.value.to_frame("meter_value"), temperature_features, time_features]
    )
    return design_matrix

def create_caltrack_billing_design_matrix(meter_data, temperature_data, region:str='USA'):
    """A helper function which calls basic feature creation methods to create a
    design matrix suitable for use with CalTRACK Billing methods.

    Parameters
    ----------
    meter_data : :any:`pandas.DataFrame`
        Hourly meter data in eemeter format.
    temperature_data : :any:`pandas.Series`
        Hourly temperature data in eemeter format.
    region : :any 'str'
        The relevant region of the world. See eemeter/region_info.csv for options. Defaults to 'USA' unless otherwise
        specified for alignment with eeweather conventions.

    Returns
    -------
    design_matrix : :any:`pandas.DataFrame`
        A design matrix with mean usage_per_day, hdd_min-hdd_max, and cdd_min-cdd_max
        features.
    """
    usage_per_day = compute_usage_per_day_feature(meter_data, series_name="meter_value")
    if region != 'USA':
        temperature_data = 32 + (temperature_data * 1.8)

    temperature_features = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=range(30, 91),
        cooling_balance_points=range(30, 91),
        data_quality=True,
        tolerance=pd.Timedelta(
            "35D"
        ),  # limit temperature data matching to periods of up to 35 days.
    )
    design_matrix = merge_features([usage_per_day, temperature_features])
    return design_matrix


def create_caltrack_daily_design_matrix(meter_data, temperature_data, region:str = 'USA'):
    """A helper function which calls basic feature creation methods to create a
    design matrix suitable for use with CalTRACK daily methods.

    Parameters
    ----------
    meter_data : :any:`pandas.DataFrame`
        Hourly meter data in eemeter format.
    temperature_data : :any:`pandas.Series`
        Hourly temperature data in eemeter format.
    region : :any 'str'
        The relevant region of the world. See eemeter/region_info.csv for options. Defaults to 'USA' unless otherwise
        specified for alignment with eeweather conventions.

    Returns
    -------
    design_matrix : :any:`pandas.DataFrame`
        A design matrix with mean usage_per_day, hdd_30-hdd_90, and cdd_30-cdd_90
        features.
    """
    usage_per_day = compute_usage_per_day_feature(meter_data, series_name="meter_value")
    if region != 'USA':
        temperature_data = 32 + (temperature_data * 1.8)

    temperature_features = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=range(30, 91),
        cooling_balance_points=range(30, 91),
        data_quality=True,
    )
    design_matrix = merge_features([usage_per_day, temperature_features])
    return design_matrix


def create_caltrack_hourly_segmented_design_matrices(
    preliminary_design_matrix,
    segmentation,
    occupancy_lookup,
    occupied_temperature_bins,
    unoccupied_temperature_bins,
):
    """A helper function which calls basic feature creation methods to create a
    design matrix suitable for use with segmented CalTRACK hourly models.
    Parameters
    ----------
    preliminary_design_matrix : :any:`pandas.DataFrame`
        A dataframe of the form returned by
        :any:`eemeter.create_caltrack_hourly_preliminary_design_matrix`.
    segmentation : :any:`pandas.DataFrame`
        Weights for each segment. This is a dataframe of the form returned by
        :any:`eemeter.segment_time_series` on the `preliminary_design_matrix`.
    occupancy_lookup : any:`pandas.DataFrame`
        Occupancy for each segment. This is a dataframe of the form returned by
        :any:`eemeter.estimate_hour_of_week_occupancy`.
    occupied_temperature_bins : :any:``
        Occupied temperature bin settings for each segment. This is a dataframe of the
        form returned by :any:`eemeter.fit_temperature_bins`.
    unoccupied_temperature_bins : :any:``
        Ditto, for unoccupied.
    Returns
    -------
    design_matrix : :any:`dict` of :any:`pandas.DataFrame`
        A dict of design matrixes created using the
        :any:`eemeter.caltrack_hourly_fit_feature_processor`.
    """
    return {
        segment_name: segmented_data
        for segment_name, segmented_data in iterate_segmented_dataset(
            preliminary_design_matrix,
            segmentation=segmentation,
            feature_processor=caltrack_hourly_fit_feature_processor,
            feature_processor_kwargs={
                "occupancy_lookup": occupancy_lookup,
                "occupied_temperature_bins": occupied_temperature_bins,
                "unoccupied_temperature_bins": unoccupied_temperature_bins,
            },
        )
    }