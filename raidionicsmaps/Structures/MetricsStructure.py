import os
import re
import traceback

import numpy as np
from typing import List
import logging
import pandas as pd

from ..Utils.resources import SharedResources
from ..Utils.utils import get_metrics_target_class

class Metrics:
    """

    """
    _unique_id = ""  # Internal unique identifier for the patient
    _input_folder = None
    _metrics_filepath = None  # Filename containing the computed metrics for the patient (and assessed object)
    _size_metrics = {}  # Dict container for all size-related metrics (e.g., volume, short-axis, and diameter)
    _brain_location_metrics = {}  # Dict container for all brain location related metrics
    _multifocality_metrics = {}  # Dict container for the multifocality metrics
    _cortical_location_metrics = {}  # Dict container for the cortical structures location metrics
    _subcortical_location_metrics = {}  # Dict container for the subcortical structures location metrics

    def __init__(self, uid: str, input_folder: str) -> None:
        """

        """
        self.__reset()
        self._unique_id = uid
        self._input_folder = input_folder
        self._metrics_filepath = os.path.join(self._input_folder,
                                              "computed_metrics_" + get_metrics_target_class() + ".csv")

        if not input_folder or not os.path.exists(input_folder):
            # Error case
            raise ValueError("The provided path does not exist on disk with value: {}".format(input_folder))

        self.__init_from_disk()

    def __reset(self) -> None:
        """
        All objects share class or static variables.
        An instance or non-static variables are different for different objects (every object has a copy).
        """
        self._unique_id = ""
        self._input_folder = None
        self._metrics_filepath = None
        self._size_metrics = {}
        self._multifocality_metrics = {}
        self._brain_location_metrics = {}
        self._cortical_location_metrics = {}
        self._subcortical_location_metrics = {}

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def metrics_filepath(self) -> str:
        return self._metrics_filepath

    @metrics_filepath.setter
    def metrics_filepath(self, fp: str) -> None:
        self.metrics_filepath = fp

    @property
    def size_metrics(self) -> dict:
        return self._size_metrics

    @size_metrics.setter
    def size_metrics(self, m: dict) -> None:
        self.size_metrics = m

    @property
    def multifocality_metrics(self) -> dict:
        return self._multifocality_metrics

    @multifocality_metrics.setter
    def multifocality_metrics(self, m: dict) -> None:
        self.multifocality_metrics = m

    @property
    def brain_location_metrics(self) -> dict:
        return self._brain_location_metrics

    @brain_location_metrics.setter
    def brain_location_metrics(self, m: dict) -> None:
        self.brain_location_metrics = m

    @property
    def cortical_location_metrics(self) -> dict:
        return self._cortical_location_metrics

    @cortical_location_metrics.setter
    def cortical_location_metrics(self, m: dict) -> None:
        self.cortical_location_metrics = m

    @property
    def subcortical_location_metrics(self) -> dict:
        return self._subcortical_location_metrics

    @subcortical_location_metrics.setter
    def subcortical_location_metrics(self, m: dict) -> None:
        self.subcortical_location_metrics = m

    def __init_from_disk(self):
        try:
            if not os.path.exists(self._metrics_filepath):
                return
            metrics_df = pd.read_csv(self._metrics_filepath)
            if "Volume (ml)" in list(metrics_df.columns):
                self.size_metrics["Volume (ml)"] = metrics_df["Volume (ml)"].values[0]
            if "Long-axis diameter (mm)" in list(metrics_df.columns):
                self.size_metrics["Long-axis diameter (mm)"] = metrics_df["Long-axis diameter (mm)"].values[0]
            if "Short-axis diameter (mm)" in list(metrics_df.columns):
                self.size_metrics["Short-axis diameter (mm)"] = metrics_df["Short-axis diameter (mm)"].values[0]
            if "Diameter X (mm)" in list(metrics_df.columns):
                self.size_metrics["Diameter X (mm)"] = metrics_df["Diameter X (mm)"].values[0]
            if "Diameter Y (mm)" in list(metrics_df.columns):
                self.size_metrics["Diameter Y (mm)"] = metrics_df["Diameter Y (mm)"].values[0]
            if "Diameter Z (mm)" in list(metrics_df.columns):
                self.size_metrics["Diameter Z (mm)"] = metrics_df["Diameter Z (mm)"].values[0]

            if "Multifocality" in list(metrics_df.columns):
                self.multifocality_metrics["Multifocality"] = metrics_df["Multifocality"].values[0]
            if "Tumor parts nb" in list(metrics_df.columns):
                self.multifocality_metrics["Tumor parts nb"] = metrics_df["Tumor parts nb"].values[0]
            if "Multifocal distance (mm)" in list(metrics_df.columns):
                self.multifocality_metrics["Multifocal distance (mm)"] = metrics_df["Multifocal distance (mm)"].values[0]

            if "Left laterality (%)" in list(metrics_df.columns):
                self.brain_location_metrics["Left laterality (%)"] = metrics_df["Left laterality (%)"].values[0]
            if "Right laterality (%)" in list(metrics_df.columns):
                self.brain_location_metrics["Right laterality (%)"] = metrics_df["Right laterality (%)"].values[0]
            if "Midline crossing" in list(metrics_df.columns):
                self.brain_location_metrics["Midline crossing"] = metrics_df["Midline crossing"].values[0]

            cortical_atlases = ["MNI", "Schaefer7", "Schaefer17", "Harvard-Oxford"]
            for c in cortical_atlases:
                for k in list(metrics_df.columns):
                    if c in k:
                        if c not in list(self.cortical_location_metrics.keys()):
                            self.cortical_location_metrics[c] = {}
                        key = k.replace(c+'_', '')
                        self.cortical_location_metrics[c][key] = metrics_df[k].values[0]

            subcortical_atlases = ["BCB"]
            for c in subcortical_atlases:
                for k in list(metrics_df.columns):
                    if c in k:
                        if c not in list(self.subcortical_location_metrics.keys()):
                            self.subcortical_location_metrics[c] = {}
                        key = k.replace(c+'_', '')
                        self.subcortical_location_metrics[c][key] = metrics_df[k].values[0]

        except Exception as e:
            logging.error("Issue reading metrics from disk at location {}".format(self._metrics_filepath))

    def size_metrics_exist(self) -> bool:
        res = True
        headers = ["Volume (ml)", "Long-axis diameter (mm)", "Short-axis diameter (mm)", "Diameter X (mm)",
                   "Diameter Y (mm)", "Diameter Z (mm)"]
        for k in headers:
            if k not in list(self.size_metrics.keys()):
                res = False

        return res

    def multifocality_metrics_exist(self) -> bool:
        res = True
        headers = ["Multifocality", "Tumor parts nb", "Multifocal distance (mm)"]
        for k in headers:
            if k not in list(self.multifocality_metrics.keys()):
                res = False

        return res

    def brain_location_metrics_exist(self) -> bool:
        res = True
        headers = ["Left laterality (%)", "Right laterality (%)", "Midline crossing"]
        for k in headers:
            if k not in list(self.brain_location_metrics.keys()):
                res = False

        return res

    def cortical_structures_location_metrics_exist(self) -> bool:
        res = True
        atlases = SharedResources.getInstance().metrics_cortical_features_location
        for k in atlases:
            if k not in list(self.cortical_location_metrics.keys()):
                res = False

        return res

    def subcortical_structures_location_metrics_exist(self) -> bool:
        res = True
        atlases = SharedResources.getInstance().metrics_subcortical_features_location
        for k in atlases:
            if k not in list(self.subcortical_location_metrics.keys()):
                res = False

        return res

    def location_metrics_exist(self) -> bool:
        res = True

        if SharedResources.getInstance().metrics_tumor_size:
            res = res & self.size_metrics_exist()
        if SharedResources.getInstance().metrics_multifocality:
            res = res & self.multifocality_metrics_exist()
        if SharedResources.getInstance().metrics_brain_location:
            res = res & self.brain_location_metrics_exist()

        res = (res & self.cortical_structures_location_metrics_exist() &
               self.subcortical_structures_location_metrics_exist())

        return res

    def fill_size_metrics_from_report(self, report: pd.DataFrame) -> None:
        self.size_metrics["Volume (ml)"] = report["Volume (ml)"].values[0]
        self.size_metrics["Long-axis diameter (mm)"] = report["Long-axis diameter (mm)"].values[0]
        self.size_metrics["Short-axis diameter (mm)"] = report["Short-axis diameter (mm)"].values[0]
        self.size_metrics["Diameter X (mm)"] = report["Diameter X (mm)"].values[0]
        self.size_metrics["Diameter Y (mm)"] = report["Diameter Y (mm)"].values[0]
        self.size_metrics["Diameter Z (mm)"] = report["Diameter Z (mm)"].values[0]

    def fill_multifocality_metrics_from_report(self, report: pd.DataFrame) -> None:
        self.multifocality_metrics["Multifocality"] = report["Overall"]["Multifocality"]
        self.multifocality_metrics["Tumor parts nb"] = report["Overall"]["Tumor parts nb"]
        self.multifocality_metrics["Multifocal distance (mm)"] = report["Overall"]["Multifocal distance (mm)"]

    def fill_brain_location_from_report(self, report: pd.DataFrame) -> None:
        self.brain_location_metrics["Left laterality (%)"] = report["Main"]["Total"]["Left laterality (%)"]
        self.brain_location_metrics["Right laterality (%)"] = report["Main"]["Total"]["Right laterality (%)"]
        self.brain_location_metrics["Midline crossing"] = report["Main"]["Total"]["Midline crossing"]

    def fill_cortical_location_from_report(self, report: pd.DataFrame) -> None:
        for a in SharedResources.getInstance().metrics_cortical_features_location:
            self.cortical_location_metrics[a] = {}
            val_dict = report["Main"]["Total"]["CorticalStructures"][a]
            for c in list(val_dict.keys()):
                self.cortical_location_metrics[a][c] = val_dict[c]

    def fill_subcortical_location_from_report(self, report: pd.DataFrame) -> None:
        for a in SharedResources.getInstance().metrics_subcortical_features_location:
            self.subcortical_location_metrics[a] = {}
            val_dict = report["Main"]["Total"]["SubcorticalStructures"][a]
            for c in list(val_dict.keys()):
                self.subcortical_location_metrics[a][c] = val_dict[c]

    def dump_metrics_file_on_disk(self):
        metrics_columns = []
        metrics_values = []

        try:
            for c in list(self.size_metrics.keys()):
                metrics_columns.append(c)
                metrics_values.append(self.size_metrics[c])

            for c in list(self.brain_location_metrics.keys()):
                metrics_columns.append(c)
                metrics_values.append(self.brain_location_metrics[c])

            for c in list(self.multifocality_metrics.keys()):
                metrics_columns.append(c)
                metrics_values.append(self.multifocality_metrics[c])

            for c in list(self.cortical_location_metrics.keys()):
                for v in list(self.cortical_location_metrics[c].keys()):
                    metrics_columns.append(c + '_' + v)
                    metrics_values.append(self.cortical_location_metrics[c][v])

            for c in list(self.subcortical_location_metrics.keys()):
                for v in list(self.subcortical_location_metrics[c].keys()):
                    metrics_columns.append(c + '_' + v)
                    metrics_values.append(self.subcortical_location_metrics[c][v])

            results_df = pd.DataFrame(np.asarray(metrics_values).reshape((1, len(metrics_columns))),
                                      columns=metrics_columns)
            results_df.to_csv(self._metrics_filepath, index=False)
        except Exception as e:
            logging.error("Collected issue trying to save the metrics on disk: \n{}".format(traceback.format_exc()))
            raise ValueError("Issue trying to save metrics on disk.")
